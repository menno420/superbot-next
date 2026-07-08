"""The K7 audit spine (frozen L0 spec 07 §3.4/§5): ONE `audit_log` DB row +
ONE durable `audit.action_recorded` bus event per compound-op invocation,
both written INSIDE the step-4 txn.

- The row is `mutation_id`-keyed (PK — `once()` upstream makes it
  uncontended; the PK is belt-and-braces), `mutation_type = op.audit_verb`,
  prev/new the leg before/after rollup, the N legs as `detail` JSONB,
  `correlation_id = ctx.correlation_id` (the draft-apply grouping column —
  the DB spine carries correlation; the frozen 11-field bus payload is NEVER
  extended, spec 07 §5 / seam-correction 4).
- The bus trace rides the outbox durable twin `enqueue_audit_action(conn,…)`
  (AT_LEAST_ONCE — the v1 default per spec 07 §9.7, owner-gated with 08's
  OD-1); the shipped `emit_audit_action` BEST_EFFORT fallback arms only if
  the owner rules the event best-effort.

Migration: `0003_audit_spine.sql`. `AUDIT_LOG_STORE` follows the kernel-store
convention (module StoreSpec constant + migration, S5 pattern — not a
manifest facet until a kernel manifest exists).
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from sb.kernel.db import pool
from sb.kernel.outbox.enqueue import enqueue_audit_action
from sb.spec.refs import EngineRef
from sb.spec.versioning import CheckpointClass, StoreSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

    from sb.kernel.workflow.context import WorkflowContext
    from sb.kernel.workflow.spec import CompoundOpSpec

__all__ = ["AUDIT_LOG_STORE", "emit_central_audit"]

AUDIT_LOG_STORE = StoreSpec(
    table="audit_log",
    sole_writer=EngineRef("kernel.workflow"),
    retention="permanent",  # operator forensic spine; pruning = owner-gated retention
    checkpoint_class=CheckpointClass.LEDGER,  # append-only forensic ledger
    invariant_tag="audit_spine",
    reader_domains=("server_logging", "diagnostics"),
    payload_version=1,
    bears_value=False,
)


def _to_text(value: object) -> str | None:
    """prev/new rollup serialization: None stays None; scalars stringify;
    structures render as compact JSON (the operator forensic log is text)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


async def emit_central_audit(
    conn: "asyncpg.Connection",
    *,
    spec: "CompoundOpSpec",
    ctx: "WorkflowContext",
    mutation_id: str,
    prev_value: object,
    new_value: object,
    detail: dict,
    occurred_at,
) -> tuple[bool, bool]:
    """Write the central row + the durable bus twin, in-txn. Returns
    (audit_emitted, event_emitted) — publish-accepted-only honesty."""
    actor_id = getattr(ctx.actor, "user_id", None)
    actor_type = getattr(ctx.actor, "actor_type", "user") or "user"
    scope = "guild" if ctx.guild_id else "global"
    correlation: uuid.UUID | None
    try:
        correlation = uuid.UUID(str(ctx.correlation_id)) if ctx.correlation_id else None
    except ValueError:
        correlation = None

    await pool.execute(
        "INSERT INTO audit_log (mutation_id, subsystem, mutation_type, target, scope, "
        "guild_id, prev_value, new_value, actor_id, actor_type, occurred_at, detail, "
        "correlation_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",
        (
            mutation_id, spec.domain, spec.audit_verb, spec.op_key, scope,
            ctx.guild_id or None, _to_text(prev_value), _to_text(new_value),
            actor_id, actor_type, occurred_at, json.dumps(detail, default=str),
            correlation,
        ),
        conn=conn,
    )

    event_emitted = await enqueue_audit_action(
        conn,
        mutation_id=mutation_id,
        subsystem=spec.domain,
        mutation_type=spec.audit_verb,
        target=spec.op_key,
        scope=scope,
        guild_id=ctx.guild_id or None,
        prev_value=_to_text(prev_value),
        new_value=_to_text(new_value),
        actor_id=actor_id,
        actor_type=actor_type,
        occurred_at=occurred_at,
    )
    return True, event_emitted
