"""The canonical idempotency-key contract (K3, frozen L0 spec 05 §3.7 — T2-2 seed).

Exactly-once over an at-least-once substrate: every mutating action that can
double-fire on deploy-overlap (L-6) guards on an `IdempotencyKey` inside ONE
`db.transaction()` conn shared with its effect. This module owns the SHAPE
(`IdempotencyKey`, `PriorOutcome`, `once`, `record_outcome`, `read_outcome`,
the `idempotency_keys` table — migration 0001); strand-2 completes the
per-action `dedup_token` definitions and the in-txn outbox (spec 05 §3.7 V-3).

Canonical usage (the atomic pattern, spec 05 §3.7):

    async with db.transaction() as conn:            # one connection, one txn
        if await once(key, conn=conn):              # first sighting
            result = await apply_effect(conn=conn)  # effect joins THIS txn
            await record_outcome(key, result.outcome,
                                 result_ref=result.audit_id, conn=conn)
        else:                                       # already applied elsewhere
            prior = await read_outcome(key, conn=conn)  # None if mid-flight
            return prior                            # reproduce / no-op
    # commit — guard row + effect + outcome all land together, or none do

Outcome vocabulary: the frozen §2.7 constants, RE-HOMED at S7 to the K6
`sb/spec/outcomes.py` leaf (RC-6) — `OUTCOMES` here is a re-export of that
single source (the shipped lowercase values, `contracts.py:48-52` verbatim);
`record_outcome` validates against it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sb.kernel.db import pool
from sb.spec.outcomes import OUTCOMES
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import CheckpointClass, DataClass, ForwardMapKind, StoreSpec, register_store

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

# S11 class 12: dedup tokens carry message/interaction ids (the R-3 axis) —
# a pseudonymous MEMBER_ID store. Retention: message-dedup families PRUNE
# (money/audit families' durable trail is the audit spine, not this table);
# the pruning body + erasure body land with the ops band; refs DECLARED now.
IDEMPOTENCY_STORE = register_store(StoreSpec(
    table="idempotency_keys",
    sole_writer=EngineRef("sb.kernel.db.idempotency"),
    retention="90d",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="idempotency_guard",
    forward_map_kind=ForwardMapKind.NEW_ONLY,  # fresh-chain kernel table (S14)
    reader_domains=(),
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("kernel.idempotency.prune_subject"),
))

__all__ = [
    "OUTCOMES",
    "IdempotencyKey",
    "PriorOutcome",
    "once",
    "read_outcome",
    "record_outcome",
]

@dataclass(frozen=True)
class IdempotencyKey:
    """THE canonical key shape (spec 05 §3.7, fork 10: natural-key derived).

    Deterministic string: a retry of the SAME Discord event/entity must
    produce the SAME key or dedup fails (a random UUID defeats it).
    """

    namespace: str      # the action family, namespace-reserved ("economy.daily", "rps.forfeit")
    guild_id: int
    dedup_token: str    # the action's NATURAL key: message_id | interaction_id | ...

    def __post_init__(self) -> None:
        if not self.namespace or ":" in self.namespace:
            raise ValueError(f"namespace must be non-empty and colon-free: {self.namespace!r}")
        if not self.dedup_token:
            raise ValueError("dedup_token must be non-empty")

    def render(self) -> str:
        """The stored PK: f"{namespace}:{guild_id}:{dedup_token}"."""
        return f"{self.namespace}:{self.guild_id}:{self.dedup_token}"

    @classmethod
    def parse(cls, rendered: str) -> "IdempotencyKey":
        """Inverse of render(). The dedup_token may itself contain colons
        (spec 08 §3.5 event-disambiguator suffixes), so split at most twice.
        """
        parts = rendered.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"not a rendered IdempotencyKey: {rendered!r}")
        namespace, guild_id_s, dedup_token = parts
        try:
            guild_id = int(guild_id_s)
        except ValueError:
            raise ValueError(f"non-integer guild_id in key: {rendered!r}") from None
        return cls(namespace=namespace, guild_id=guild_id, dedup_token=dedup_token)


@dataclass(frozen=True)
class PriorOutcome:
    """What a prior first-run committed for a key — the False-branch read."""

    outcome: str            # §2.7 frozen vocab ONLY
    result_ref: str | None  # optional pointer to the durable result (audit/mutation id)
    first_seen_at: int


async def once(key: IdempotencyKey, *, conn: "asyncpg.Connection") -> bool:
    """INSERT ... ON CONFLICT DO NOTHING RETURNING (spec 05 §3.7).

    True => first sighting, caller proceeds inside the SAME txn. False =>
    already applied, caller no-ops (and may read the prior outcome via
    read_outcome). MUST be called with a txn-bound `conn` from
    `db.transaction()` so the guard row and the action's effect commit
    atomically — the fast-release deploy handoff (T2-2) relies on this.
    """
    row = await pool.fetchone(
        "INSERT INTO idempotency_keys (key, namespace, first_seen_at) "
        "VALUES ($1, $2, $3) ON CONFLICT (key) DO NOTHING RETURNING key",
        (key.render(), key.namespace, int(time.time())),
        conn=conn,
    )
    return row is not None


async def record_outcome(
    key: IdempotencyKey,
    outcome: str,
    *,
    result_ref: str | None = None,
    conn: "asyncpg.Connection",
) -> None:
    """Write-back — fills the guard row's outcome/result_ref AFTER the effect
    is written, INSIDE the same txn/`conn` as once() and the effect, BEFORE
    commit — so the recorded outcome commits atomically with the effect it
    describes (a crash before commit rolls back BOTH, and the key row too).
    `outcome` MUST be one of the §2.7 constants — any other value => ValueError.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} not in the frozen §2.7 vocab {OUTCOMES}")
    await pool.execute(
        "UPDATE idempotency_keys SET outcome = $2, result_ref = $3 WHERE key = $1",
        (key.render(), outcome, result_ref),
        conn=conn,
    )


async def read_outcome(
    key: IdempotencyKey, *, conn: "asyncpg.Connection",
) -> PriorOutcome | None:
    """The False-branch read path: the prior committed PriorOutcome for an
    already-applied key, or None when the row exists but outcome is not yet
    recorded (a concurrent first-run still mid-flight). Read-only — safe
    with or without an open txn.
    """
    row = await pool.fetchone(
        "SELECT outcome, result_ref, first_seen_at FROM idempotency_keys WHERE key = $1",
        (key.render(),),
        conn=conn,
    )
    if row is None or row["outcome"] is None:
        return None
    return PriorOutcome(
        outcome=row["outcome"],
        result_ref=row["result_ref"],
        first_seen_at=row["first_seen_at"],
    )
