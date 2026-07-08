"""`event_outbox` row shape + conn-aware CRUD (K4, frozen L0 spec 08 §3.2/§5).

All statements route through the K3 seam (`sb.kernel.db.pool` helpers) —
never raw `conn.execute` outside `sb/kernel/db` (arch rule spec 08 §7; this
module is the sb-rebuild home of the shipped `utils/db/outbox.py` role).

`event_outbox` is written ONLY by `sb.kernel.outbox` (`OUTBOX_STORE.sole_writer`
+ the INV-OUTBOX-SOLE-WRITER tag); the operator dashboard is a read-only
projection, never a second write path.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Mapping

from sb.kernel.db import pool
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    StoreSpec,
    VersionPolicy,
    register_store,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

__all__ = ["OUTBOX_STORE", "OutboxRow", "OutboxStatus", "OutboxStore"]


class OutboxStatus(enum.Enum):
    PENDING = "pending"      # awaiting (or retrying) delivery; claimable when available_at <= now
    DELIVERED = "delivered"  # relay confirmed publish-accepted; terminal
    DEAD = "dead"            # exceeded MAX_ATTEMPTS delivery failures; terminal; finding recorded


@dataclass(frozen=True)
class OutboxRow:
    """One captured event (spec 08 §3.2).

    Two counters, deliberately separated (finding 6): `claims` counts leases
    TAKEN (crash-loop signal; does NOT gate DEAD); `delivery_attempts` counts
    bus-level delivery FAILURES only — MAX_ATTEMPTS gates DEAD on it, so a
    crash-looping relay can never dead-letter a healthy event.
    """

    outbox_id: uuid.UUID
    dedup_key: str            # == IdempotencyKey.render() — the exactly-once capture key
    event_name: str           # a KNOWN_EVENTS literal (checked at enqueue)
    payload: Mapping[str, object]   # JSON-native emit kwargs (§6.5 codec)
    guild_id: int | None
    created_at: datetime      # enqueue time == the commit fact
    available_at: datetime    # earliest claim; bumped by lease on claim, backoff on retry
    claims: int
    delivery_attempts: int
    status: OutboxStatus
    delivered_at: datetime | None
    last_error: str | None
    correlation_id: uuid.UUID | None   # the producing mutation_id / audit_log link


#: The event_outbox StoreSpec (spec 08 §5.1, on spec 09 §3.2's version-extended
#: grammar). The outbox is a SELF-MANAGED delivery ledger: it does NOT route
#: through resolve_versioned_load; bears_value=False because the row is a
#: delivery ENVELOPE — the state of record already committed to its domain
#: table in the same txn. REJECT_AND_PRESERVE is the non-destructive choice
#: (DROP would strand a still-PENDING row on a schema bump — "no lost events");
#: a schema-drifted PENDING row is re-emitted as-stored (payload_schema is
#: additive-only).
OUTBOX_STORE = register_store(StoreSpec(
    table="event_outbox",
    sole_writer=EngineRef("sb.kernel.outbox"),
    retention="delivered:7d;dead:90d",           # enforced by OutboxReaperLane._prune
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="INV-OUTBOX-SOLE-WRITER",
    reader_domains=("operator_dashboard",),
    payload_version=1,
    bears_value=False,
    version_policy=VersionPolicy.REJECT_AND_PRESERVE,
    # S11 class 12: event payloads carry actor/user ids (pseudonymous). The
    # erasure body (payload scrub, delivery envelope kept) lands with the
    # outbox band; the ref is DECLARED now so the erasure walk is complete.
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("kernel.outbox.scrub_subject"),
))

# Retention windows parsed from OUTBOX_STORE.retention.
DELIVERED_TTL = timedelta(days=7)
DEAD_TTL = timedelta(days=90)

# The atomic claim (spec 08 §5.2): FOR UPDATE SKIP LOCKED is the dual-instance
# guard; the lease bump IS the visibility timeout (no 'claimed' status).
# The claim increments `claims`, never `delivery_attempts` (finding 6).
_CLAIM_SQL = """
WITH due AS (
  SELECT outbox_id FROM event_outbox
   WHERE status = 'pending' AND available_at <= $1
   ORDER BY available_at, outbox_id
   LIMIT $2
   FOR UPDATE SKIP LOCKED
)
UPDATE event_outbox o
   SET claims = o.claims + 1, available_at = $3
  FROM due WHERE o.outbox_id = due.outbox_id
RETURNING o.*;
"""


def _row_from_record(record: Mapping[str, object]) -> OutboxRow:
    return OutboxRow(
        outbox_id=record["outbox_id"],
        dedup_key=record["dedup_key"],
        event_name=record["event_name"],
        payload=record["payload"],
        guild_id=record["guild_id"],
        created_at=record["created_at"],
        available_at=record["available_at"],
        claims=record["claims"],
        delivery_attempts=record["delivery_attempts"],
        status=OutboxStatus(record["status"]),
        delivered_at=record["delivered_at"],
        last_error=record["last_error"],
        correlation_id=record["correlation_id"],
    )


class OutboxStore:
    """Conn-aware CRUD over `event_outbox` (spec 08 §3.2/§5)."""

    async def insert(
        self,
        conn: "asyncpg.Connection",
        *,
        dedup_key: str,
        event_name: str,
        payload: Mapping[str, object],
        guild_id: int | None,
        now: datetime,
        correlation_id: uuid.UUID | None = None,
    ) -> bool:
        """The exactly-once capture: `INSERT … ON CONFLICT (dedup_key) DO
        NOTHING` INSIDE the caller's txn. True = row inserted; False = already
        captured (replay/dup — the caller treats it as success)."""
        row = await pool.fetchone(
            "INSERT INTO event_outbox "
            "(outbox_id, dedup_key, event_name, payload, guild_id, created_at, "
            " available_at, claims, delivery_attempts, status, correlation_id) "
            "VALUES ($1, $2, $3, $4, $5, $6, $6, 0, 0, 'pending', $7) "
            "ON CONFLICT (dedup_key) DO NOTHING RETURNING outbox_id",
            (uuid.uuid4(), dedup_key, event_name, dict(payload), guild_id,
             now, correlation_id),
            conn=conn,
        )
        return row is not None

    async def claim(
        self, now: datetime, *, batch_size: int, lease_s: int,
    ) -> tuple[OutboxRow, ...]:
        """One atomic claim cycle (autocommit — its own statement)."""
        records = await pool.fetchall(
            _CLAIM_SQL, (now, batch_size, now + timedelta(seconds=lease_s)),
        )
        return tuple(_row_from_record(r) for r in records)

    async def mark_delivered(self, outbox_id: uuid.UUID, now: datetime) -> None:
        await pool.execute(
            "UPDATE event_outbox SET status='delivered', delivered_at=$2 "
            "WHERE outbox_id=$1",
            (outbox_id, now),
        )

    async def mark_retry_or_dead(
        self,
        row: OutboxRow,
        *,
        now: datetime,
        error: str,
        max_attempts: int,
        backoff_s: int,
    ) -> bool:
        """Step-3 bus-level failure path — the ONLY writer of
        `delivery_attempts`. Returns True when the row went DEAD."""
        attempts = row.delivery_attempts + 1
        if attempts >= max_attempts:
            await pool.execute(
                "UPDATE event_outbox SET status='dead', "
                "delivery_attempts=$2, last_error=$3 WHERE outbox_id=$1",
                (row.outbox_id, attempts, error),
            )
            return True
        await pool.execute(
            "UPDATE event_outbox SET status='pending', delivery_attempts=$2, "
            "available_at=$3, last_error=$4 WHERE outbox_id=$1",
            (row.outbox_id, attempts, now + timedelta(seconds=backoff_s), error),
        )
        return False

    async def prune(self, now: datetime, *, batch: int = 500) -> int:
        """Bounded retention sweep (spec 08 §5.1: delivered:7d; dead:90d)."""
        result = await pool.execute(
            "DELETE FROM event_outbox WHERE outbox_id IN ("
            "  SELECT outbox_id FROM event_outbox"
            "   WHERE (status='delivered' AND delivered_at < $1)"
            "      OR (status='dead' AND created_at < $2)"
            "   LIMIT $3)",
            (now - DELIVERED_TTL, now - DEAD_TTL, batch),
        )
        try:
            return int(str(result).rsplit(" ", 1)[-1])
        except (ValueError, IndexError):
            return 0


#: Module-level default instance (the enqueue side + composition root use it;
#: tests inject fakes into the lanes instead).
STORE = OutboxStore()
