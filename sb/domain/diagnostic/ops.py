"""Diagnostic K7 lane — the shipped ``!platform backfill`` DRY RUN as an
audited one-leg op (``diagnostic.backfill_dry_run``).

Shipped semantics (disbot/services/binding_backfill.py +
disbot/cogs/diagnostic/_backfill.py @ the corpus posture, reconstructed
fragment-by-fragment via search_code): classify each catalogued
``(legacy_key → subsystem.binding_name)`` pair, write ONE
``platform_migration_checkpoints`` row (name=binding_backfill,
status=dry_run_complete, summary_json = the classification document),
and render the preview embed. ``backfill apply`` (the candidate_valid
writer) is NOT ported — no golden drives it; the handler answers the
honest refusal.

The shipped catalog is exactly the two HOMED legacy pointers (the
oracle's own docstring: "xp_announce_channel → (xp, announce_channel,
CHANNEL) — homed. economy_log_channel → (economy, log_channel, CHANNEL)
— homed."); DEFERRED_KEYS never entered the candidate list.

Classification in v1: the legacy KV side is STRUCTURALLY absent (the
old ``config`` KV store did not survive the v1 schema epoch — the
ticket/service.py constant-None precedent), so the reachable cells are
``both_absent`` (binding also unset — the golden-pinned class,
goldens/diagnostic/sweep_platform_backfill) and the legacy-absent/
binding-present cell, whose SHIPPED member name could not be
reconstructed through the search_code fragment lane; the port names it
``binding_present`` (live-only — no golden can pin it: every parity
case starts from a truncated DB). Revisit if the oracle fragment
surfaces."""

from __future__ import annotations

import datetime as _dt
import json

from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.refs import WorkflowRef, is_registered, workflow

__all__ = [
    "BACKFILL_CATALOG",
    "ensure_ops_refs",
    "register_ops",
    "run_backfill_dry_run",
]

#: the shipped homed-pointer catalog (order = the shipped scan order; the
#: golden pins xp first, economy second).
BACKFILL_CATALOG: tuple[dict, ...] = (
    {"legacy_key": "xp_announce_channel", "subsystem": "xp",
     "binding_name": "announce_channel", "kind": "channel"},
    {"legacy_key": "economy_log_channel", "subsystem": "economy",
     "binding_name": "log_channel", "kind": "channel"},
)


def _read_legacy(_guild_id: int, _key: str) -> None:
    """The old KV ``config`` read — STRUCTURALLY None at the v1 schema
    epoch (the legacy table did not survive the import; the ticket
    constant-None precedent). The name carries the boundary."""
    return None


async def _classify(guild_id: int) -> list[dict]:
    from sb.kernel.db.settings import get_binding

    out: list[dict] = []
    for entry in BACKFILL_CATALOG:
        legacy_raw = _read_legacy(guild_id, entry["legacy_key"])
        binding = await get_binding(guild_id, entry["subsystem"],
                                    entry["binding_name"])
        binding_id = binding if binding is not None else None
        binding_status = "bound" if binding is not None else None
        if legacy_raw is None and binding_id is None:
            classification = "both_absent"
            reason = "neither legacy nor binding has a value"
        else:
            # legacy is structurally None in v1, so this is the
            # binding-present cell (module docstring: shipped member
            # name unreconstructed; live-only).
            classification = "binding_present"
            reason = "binding row already carries a value"
        out.append({
            "legacy_key": entry["legacy_key"],
            "subsystem": entry["subsystem"],
            "binding_name": entry["binding_name"],
            "kind": entry["kind"],
            "legacy_raw": legacy_raw,
            "legacy_target_id": None,
            "binding_target_id": binding_id,
            "binding_status": binding_status,
            "classification": classification,
            "reason": reason,
        })
    return out


@workflow("diagnostic.record_backfill_dry_run")
async def _record_dry_run(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.diagnostic import store

    uid = int(getattr(ctx.actor, "user_id", 0) or 0)
    gid = int(ctx.guild_id or 0)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    candidates = await _classify(gid)
    counts: dict[str, int] = {}
    for c in candidates:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    summary = {
        "summary_version": 1,
        "started_at": now,
        "completed_at": now,
        "counts": counts,
        "candidates": candidates,
    }
    await store.insert_checkpoint(
        conn, name="binding_backfill", guild_id=gid,
        status="dry_run_complete", summary_json=json.dumps(summary))
    return LegOutcome(
        step=StepResult(uid, "backfill_dry_run", True),
        before={},
        after={"counts": counts, "candidates": candidates})


BACKFILL_DRY_RUN = CompoundOpSpec(
    op_key="diagnostic.backfill_dry_run",
    domain="diagnostic",
    lane=WorkflowLane.DOMAIN,
    authority_ref="administrator",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("diagnostic.record_backfill_dry_run"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY,
    dedup_key=None,
    audit_verb="backfill_dry_run",
)

_OPS = (BACKFILL_DRY_RUN,)

_REF_TABLE = (
    ("diagnostic.record_backfill_dry_run", _record_dry_run),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


async def run_backfill_dry_run(ctx: WorkflowContext):
    from sb.kernel.workflow import engine

    return await engine.run(BACKFILL_DRY_RUN, ctx)


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
