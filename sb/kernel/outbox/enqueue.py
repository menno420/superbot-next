"""The in-txn enqueue side (K4, frozen L0 spec 08 §3.3/§3.5/§6.5).

`enqueue` / `enqueue_audit_action` write the event as an `event_outbox` row
on the SAME txn-bound conn as `once()` + the effect (K3 `db.transaction()`),
so the event exists iff the effect committed — no phantom events, no lost
events. `enqueue_all` is the K7 seam (07 §3.3 step 4e/6): ONE in-txn call
that writes every `AT_LEAST_ONCE` row now and RETURNS a `BestEffortBatch`
the caller emits post-commit — the two-call protocol (spec 08 §3.3, pinned).

Name-guard is HARD for the durable lane (spec 08 fork D): a mis-named
guaranteed event raises `UnknownEventError` in-txn and rolls back the whole
effect (delivery was promised; an undeliverable name is a bug caught at
test/CI). Best-effort events keep the shipped soft-warn behavior at the bus.
"""

from __future__ import annotations

import datetime as _dt
import enum
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping

from sb.kernel.outbox.store import STORE, OutboxStore
from sb.spec.events import EVT_AUDIT_ACTION_RECORDED, KNOWN_EVENTS, DeliveryClass

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

logger = logging.getLogger("sb.outbox.enqueue")

__all__ = [
    "BestEffortBatch",
    "UnknownEventError",
    "enqueue",
    "enqueue_all",
    "enqueue_audit_action",
    "to_jsonable",
]


class UnknownEventError(Exception):
    """An AT_LEAST_ONCE enqueue named an event not in KNOWN_EVENTS —
    raised in-txn so the whole effect rolls back (spec 08 fork D)."""

    def __init__(self, name: str) -> None:
        super().__init__(f"unknown event name for durable delivery: {name!r}")
        self.name = name


def to_jsonable(payload: Mapping[str, object]) -> dict[str, object]:
    """The JSONB serialize contract (spec 08 §6.5): datetime -> .isoformat()
    string, enum -> .value, uuid -> str; JSON-native values verbatim
    (recursively). The relay re-emits AS STORED — the shipped subscribers
    already receive e.g. occurred_at as an ISO string, so no inverse is
    needed for the audit canary."""

    def convert(value: object) -> object:
        if isinstance(value, _dt.datetime):
            return value.isoformat()
        if isinstance(value, enum.Enum):
            return value.value
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, Mapping):
            return {str(k): convert(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [convert(v) for v in value]
        return value

    return {str(k): convert(v) for k, v in payload.items()}


def _check_payload_keys(event_name: str, payload: Mapping[str, object]) -> None:
    """Deferral-3 key-presence check: every required payload_schema field
    must be present (full type validation is the compile-time superset
    check's job, not enqueue's)."""
    spec = KNOWN_EVENTS[event_name]
    missing = [f.name for f in spec.payload_schema if f.required and f.name not in payload]
    if missing:
        raise ValueError(
            f"event {event_name!r} payload missing required field(s): {missing}")


async def enqueue(
    conn: "asyncpg.Connection",
    *,
    event_name: str,
    payload: Mapping[str, object],
    guild_id: int | None,
    dedup_token: str,
    namespace: str = "outbox",
    correlation_id: uuid.UUID | None = None,
    _store: OutboxStore = STORE,
    _now: _dt.datetime | None = None,
) -> bool:
    """Write one AT_LEAST_ONCE event row INSIDE the caller's txn.

    True = row inserted; False = ON CONFLICT (already captured — a
    replay/dup; the caller treats it as success, never an error).
    `dedup_key = IdempotencyKey(namespace, guild_id or 0, dedup_token).render()`
    — the §3.5 derivation table owns the per-producer token shapes.
    """
    if event_name not in KNOWN_EVENTS:
        raise UnknownEventError(event_name)
    _check_payload_keys(event_name, payload)
    from sb.kernel.db.idempotency import IdempotencyKey

    dedup_key = IdempotencyKey(
        namespace=namespace, guild_id=guild_id or 0, dedup_token=dedup_token,
    ).render()
    now = _now or _dt.datetime.now(tz=_dt.timezone.utc)
    return await _store.insert(
        conn,
        dedup_key=dedup_key,
        event_name=event_name,
        payload=to_jsonable(payload),
        guild_id=guild_id,
        now=now,
        correlation_id=correlation_id,
    )


async def enqueue_audit_action(
    conn: "asyncpg.Connection",
    *,
    mutation_id: str,
    subsystem: str,
    mutation_type: str,
    target: str,
    scope: str,
    guild_id: int | None,
    prev_value: str | None,
    new_value: str | None,
    actor_id: int | None,
    actor_type: str,
    occurred_at: _dt.datetime,
    _store: OutboxStore = STORE,
) -> bool:
    """The DURABLE TWIN of the shipped `emit_audit_action` (spec 08 §12.2 —
    a twin, never an edit; the shipped 11-field signature is frozen).

    dedup_token = mutation_id (the frozen audit link, vocab §③.2);
    namespace = "audit" (distinct from any owner_subsystem — cannot collide
    even if a domain event on the same mutation shares mutation_id);
    payload carries occurred_at ALREADY serialized via .isoformat(), so the
    relayed event is byte-identical to what the shipped subscriber receives.
    """
    correlation: uuid.UUID | None
    try:
        correlation = uuid.UUID(mutation_id)
    except (ValueError, AttributeError, TypeError):
        correlation = None
    payload = {
        "mutation_id": mutation_id,
        "subsystem": subsystem,
        "mutation_type": mutation_type,
        "target": target,
        "scope": scope,
        "guild_id": guild_id,
        "prev_value": prev_value,
        "new_value": new_value,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "occurred_at": occurred_at.isoformat(),
    }
    return await enqueue(
        conn,
        event_name=EVT_AUDIT_ACTION_RECORDED,
        payload=payload,
        guild_id=guild_id,
        dedup_token=mutation_id,
        namespace="audit",
        correlation_id=correlation,
        _store=_store,
    )


@dataclass
class BestEffortBatch:
    """The post-commit half of the two-call protocol (spec 08 §3.3).

    The K7 caller captures this return from the in-txn `enqueue_all` (step
    4e) and invokes `emit_after_commit()` AFTER the `db.transaction()` block
    commits (step 6). Dropping it = best-effort events never emit.
    """

    _events: list[tuple[str, Mapping[str, object]]] = field(default_factory=list)
    _bus: object | None = None

    async def emit_after_commit(self) -> int:
        """bus.emit each captured best-effort event, POST-commit."""
        emitted = 0
        for name, payload in self._events:
            if self._bus is None:
                logger.warning(
                    "best-effort event %r dropped: no bus wired (pre-K5 composition)",
                    name,
                )
                continue
            await self._bus.emit(name, **payload)
            emitted += 1
        return emitted


async def enqueue_all(
    emits: tuple,
    ctx: object,
    result: object,
    *,
    conn: "asyncpg.Connection",
    bus: object | None = None,
    _store: OutboxStore = STORE,
) -> BestEffortBatch:
    """The K7 seam (07 §3.3 step 4e; I own the body + return protocol).

    Called IN-TXN. For each emit (emit_index = its position):
      delivery==AT_LEAST_ONCE => enqueue(conn, …) NOW, dedup_token per §3.5;
      delivery==BEST_EFFORT   => append to the returned batch (post-commit).

    §3.5 K7-lane token derivation (finalized when S8 lands WorkflowResult):
      - result.dedup_key present (a DURABLE_ONCE op's once() IdempotencyKey)
        => f"{dedup_key.render()}:{emit_index}" — shares the op's key;
      - else f"{result.mutation_id}:{emit_index}" (fresh per real invocation).
    namespace = the op key (result.op_key / ctx.op_key), duck-typed until S8.
    """
    batch = BestEffortBatch(_bus=bus)
    guild_id = getattr(ctx, "guild_id", None)
    namespace = (
        getattr(result, "op_key", None) or getattr(ctx, "op_key", None) or "workflow"
    )
    op_dedup_key = getattr(result, "dedup_key", None)
    mutation_id = getattr(result, "mutation_id", None)
    for emit_index, emit in enumerate(emits):
        payload_builder = getattr(emit, "payload_builder", None)
        payload = payload_builder(ctx, result) if payload_builder else {}
        if payload is None:
            # Conditional emission (band 4, D-0036): the payload builder IS
            # the condition point — None means "this invocation does not
            # cross the event's boundary" (xp.level_up on a non-boundary
            # award is the arming case). emit_index positions stay stable
            # per the DECLARED tuple, so dedup tokens never shift.
            continue
        event_name = getattr(emit, "event", None) or getattr(emit, "event_name", "")
        if getattr(emit, "delivery", DeliveryClass.BEST_EFFORT) is DeliveryClass.AT_LEAST_ONCE:
            if op_dedup_key is not None:
                token = f"{op_dedup_key.render()}:{emit_index}"
            else:
                token = f"{mutation_id}:{emit_index}"
            await enqueue(
                conn,
                event_name=str(event_name),
                payload=payload,
                guild_id=guild_id,
                dedup_token=token,
                namespace=str(namespace),
                _store=_store,
            )
        else:
            batch._events.append((str(event_name), to_jsonable(payload)))
    return batch
