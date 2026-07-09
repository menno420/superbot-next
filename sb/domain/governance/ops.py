"""The governance mutation lanes (band 5) — the shipped
GovernanceMutationPipeline (disbot/governance/writes.py) as K7
CompoundOpSpecs. The pipeline's deterministic sequence maps onto the
engine: input validation + old-value read + DB write + governance audit
row in ONE txn (the leg), the central audit_log row + `audit.action_recorded`
twin from the engine (audit_verb), event emission post-commit
(EventEmitSpec, BEST_EFFORT), in-memory cache invalidation post-run
(service wrappers — see sb/domain/governance/service.py).

Authority verbatim: _WRITE_AUTHORITY_TIER = "moderator" for visibility +
cleanup; the capability-override lane carries the ADR-005 administrator
floor (D-0039 — the shipped overlay had no in-repo write surface; the
revoke lane lands at the same floor its READ side protects).

Event names are compat-frozen (governance/events.py: "Do NOT rename
after v1").
"""

from __future__ import annotations

import uuid

from sb.domain.governance import store
from sb.domain.governance.models import (
    VALID_CLEANUP_SCOPE_TYPES,
    VALID_VISIBILITY_SCOPE_TYPES,
)
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = [
    "EVT_CACHE_INVALIDATED",
    "EVT_CLEANUP_CHANGED",
    "EVT_EXECUTION_ALLOWED",
    "EVT_EXECUTION_DENIED",
    "EVT_VISIBILITY_CHANGED",
    "ensure_ops_refs",
    "register_ops",
]

# canonical governance event names (events.py verbatim — compat-frozen)
EVT_VISIBILITY_CHANGED = "governance.visibility.changed"
EVT_CLEANUP_CHANGED = "governance.cleanup.changed"
EVT_EXECUTION_DENIED = "governance.execution.denied"
EVT_EXECUTION_ALLOWED = "governance.execution.allowed"
EVT_CACHE_INVALIDATED = "governance.cache.invalidated"


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


def _validator_error(message: str):
    """Copy-only ValidatorError — the raise-site sentence IS the user copy,
    rendered bare (the D-0060/D-0061 refusal-copy posture; the one-arg
    param form wrapped every sentence in the missing-argument
    boilerplate)."""
    from sb.kernel.interaction.errors import ValidatorError

    return ValidatorError("", message)


def _scope_args(ctx: WorkflowContext) -> tuple[str, int]:
    scope_type = str(ctx.params.get("scope_type", "") or "")
    try:
        scope_id = int(ctx.params.get("scope_id"))
    except (TypeError, ValueError):
        raise _validator_error("scope_id must be an integer") from None
    return scope_type, scope_id


# --- legs ---------------------------------------------------------------------

@workflow("governance.record_set_visibility")
async def _record_set_visibility(conn, ctx: WorkflowContext) -> LegOutcome:
    """Validate + read-old + upsert + governance audit row — one txn
    (the shipped pipeline steps 1/3/4)."""
    from sb.domain.governance.registry import SUBSYSTEM_META

    scope_type, scope_id = _scope_args(ctx)
    subsystem = str(ctx.params.get("subsystem", "") or "")
    enabled = ctx.params.get("enabled")  # True | False | None (= clear)
    if enabled is not None:
        enabled = bool(enabled)

    if scope_type not in VALID_VISIBILITY_SCOPE_TYPES:
        raise _validator_error(
            f"Invalid scope_type {scope_type!r}. Must be one of: "
            f"{sorted(VALID_VISIBILITY_SCOPE_TYPES)}. "
            "Role-scoped overrides are not yet supported.")
    if subsystem not in SUBSYSTEM_META:
        raise _validator_error(
            f"Unknown subsystem {subsystem!r}.  Only registered subsystems "
            "may have visibility overrides.")

    gid = int(ctx.guild_id or 0)
    old_enabled = await store.get_visibility_override(
        gid, scope_type, scope_id, subsystem, conn=conn)
    await store.upsert_visibility(
        conn, guild_id=gid, scope_type=scope_type, scope_id=scope_id,
        subsystem=subsystem, enabled=enabled)
    await store.insert_governance_audit(
        conn, guild_id=gid, actor_id=_actor_id(ctx), action="set_visibility",
        scope_type=scope_type, scope_id=scope_id, subsystem=subsystem,
        old_value={"enabled": old_enabled}, new_value={"enabled": enabled})

    ctx.params["_evt_mutation_id"] = str(uuid.uuid4())
    return LegOutcome(
        step=StepResult(gid, "set_visibility", True),
        before={"enabled": old_enabled},
        after={"enabled": enabled, "scope_type": scope_type,
               "scope_id": scope_id, "subsystem": subsystem},
        payload={"old": old_enabled, "new": enabled},
    )


@workflow("governance.record_set_cleanup")
async def _record_set_cleanup(conn, ctx: WorkflowContext) -> LegOutcome:
    scope_type, scope_id = _scope_args(ctx)
    if scope_type not in VALID_CLEANUP_SCOPE_TYPES:
        raise _validator_error(
            f"Invalid scope_type {scope_type!r} for cleanup policy. "
            f"Must be one of: {sorted(VALID_CLEANUP_SCOPE_TYPES)}. "
            "cleanup_policies does not support thread scope (migration 009).")
    gid = int(ctx.guild_id or 0)
    div = bool(ctx.params.get("delete_invalid_commands", True))
    dfc = bool(ctx.params.get("delete_failed_commands", True))
    das = int(ctx.params.get("delete_after_seconds", 5))

    old = await store.get_cleanup_policy(gid, scope_type, scope_id, conn=conn)
    await store.upsert_cleanup_policy(
        conn, guild_id=gid, scope_type=scope_type, scope_id=scope_id,
        delete_invalid_commands=div, delete_failed_commands=dfc,
        delete_after_seconds=das)
    await store.insert_governance_audit(
        conn, guild_id=gid, actor_id=_actor_id(ctx), action="set_cleanup",
        scope_type=scope_type, scope_id=scope_id, subsystem=None,
        old_value=dict(old) if old else None,
        new_value={"delete_invalid_commands": div,
                   "delete_failed_commands": dfc,
                   "delete_after_seconds": das})

    ctx.params["_evt_mutation_id"] = str(uuid.uuid4())
    return LegOutcome(
        step=StepResult(gid, "set_cleanup", True),
        before={"policy": dict(old) if old else None},
        after={"delete_invalid_commands": div, "delete_failed_commands": dfc,
               "delete_after_seconds": das, "scope_type": scope_type,
               "scope_id": scope_id},
        payload={},
    )


@workflow("governance.record_remove_cleanup")
async def _record_remove_cleanup(conn, ctx: WorkflowContext) -> LegOutcome:
    scope_type, scope_id = _scope_args(ctx)
    if scope_type not in VALID_CLEANUP_SCOPE_TYPES:
        raise _validator_error(
            f"Invalid scope_type {scope_type!r} for cleanup policy. "
            f"Must be one of: {sorted(VALID_CLEANUP_SCOPE_TYPES)}. "
            "cleanup_policies does not support thread scope (migration 009).")
    gid = int(ctx.guild_id or 0)
    removed = await store.remove_cleanup_policy(
        conn, guild_id=gid, scope_type=scope_type, scope_id=scope_id)
    await store.insert_governance_audit(
        conn, guild_id=gid, actor_id=_actor_id(ctx), action="remove_cleanup",
        scope_type=scope_type, scope_id=scope_id, subsystem=None,
        old_value={"removed": removed}, new_value=None)

    ctx.params["_evt_mutation_id"] = str(uuid.uuid4())
    return LegOutcome(
        step=StepResult(gid, "remove_cleanup", True),
        before={"present": removed},
        after={"removed": removed, "scope_type": scope_type,
               "scope_id": scope_id},
        payload={"removed": removed},
    )


@workflow("governance.record_set_capability_override")
async def _record_set_capability_override(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.governance.registry import CAPABILITY_TO_SUBSYSTEM

    gid = int(ctx.guild_id or 0)
    capability = str(ctx.params.get("capability", "") or "")
    allowed = ctx.params.get("allowed")  # True | False | None (= clear)
    if allowed is not None:
        allowed = bool(allowed)
    if capability not in CAPABILITY_TO_SUBSYSTEM:
        raise _validator_error(
            f"Unknown capability {capability!r} — only registered "
            "capabilities may carry execution overrides.")

    old = (await store.fetch_capability_overrides(gid, conn=conn)).get(capability)
    await store.upsert_capability_override(
        conn, guild_id=gid, capability=capability, allowed=allowed)
    await store.insert_governance_audit(
        conn, guild_id=gid, actor_id=_actor_id(ctx),
        action="set_capability_override", scope_type="guild", scope_id=gid,
        subsystem=CAPABILITY_TO_SUBSYSTEM[capability],
        old_value={"allowed": old}, new_value={"allowed": allowed})

    ctx.params["_evt_mutation_id"] = str(uuid.uuid4())
    return LegOutcome(
        step=StepResult(gid, "set_capability_override", True),
        before={"allowed": old},
        after={"allowed": allowed, "capability": capability},
        payload={"capability": capability, "allowed": allowed},
    )


# --- privacy erasure body ---------------------------------------------------------

@workflow("governance.tombstone_subject_audit")
async def _tombstone_subject_audit(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.tombstone_subject_governance_audit(
        conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_subject_audit", True),
                      before={}, after={"rows": rows})


# --- event payload builders -----------------------------------------------------

@workflow("governance.visibility_payload")
def _visibility_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "scope_type": str(ctx.params.get("scope_type", "") or ""),
        "scope_id": int(ctx.params.get("scope_id", 0) or 0),
        "subsystem": str(ctx.params.get("subsystem", "") or ""),
        "enabled": ctx.params.get("enabled"),
        "mutation_id": str(ctx.params.get("_evt_mutation_id", "") or ""),
        "occurred_at": ctx.clock().isoformat(),
        "actor_id": _actor_id(ctx),
    }


@workflow("governance.cleanup_payload")
def _cleanup_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "scope_type": str(ctx.params.get("scope_type", "") or ""),
        "scope_id": int(ctx.params.get("scope_id", 0) or 0),
        "mutation_id": str(ctx.params.get("_evt_mutation_id", "") or ""),
        "occurred_at": ctx.clock().isoformat(),
        "actor_id": _actor_id(ctx),
    }


@workflow("governance.cache_invalidated_payload")
def _cache_invalidated_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "mutation_id": str(ctx.params.get("_evt_mutation_id", "") or ""),
        "occurred_at": ctx.clock().isoformat(),
    }


_CACHE_EMIT = EventEmitSpec(
    EVT_CACHE_INVALIDATED,
    WorkflowRef("governance.cache_invalidated_payload"),
    DeliveryClass.BEST_EFFORT)

_VIS_EMITS = (
    EventEmitSpec(EVT_VISIBILITY_CHANGED,
                  WorkflowRef("governance.visibility_payload"),
                  DeliveryClass.BEST_EFFORT),
    _CACHE_EMIT,
)
_CLEANUP_EMITS = (
    EventEmitSpec(EVT_CLEANUP_CHANGED,
                  WorkflowRef("governance.cleanup_payload"),
                  DeliveryClass.BEST_EFFORT),
    _CACHE_EMIT,
)


def _op(op_key: str, verb: str, ref: str, authority: str,
        emits: tuple) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="governance", lane=WorkflowLane.DOMAIN,
        authority_ref=authority,
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=emits)


SET_VISIBILITY = _op("governance.set_visibility", "governance_visibility_set",
                     "governance.record_set_visibility", "moderator",
                     _VIS_EMITS)
SET_CLEANUP = _op("governance.set_cleanup", "governance_cleanup_set",
                  "governance.record_set_cleanup", "moderator",
                  _CLEANUP_EMITS)
REMOVE_CLEANUP = _op("governance.remove_cleanup", "governance_cleanup_removed",
                     "governance.record_remove_cleanup", "moderator",
                     _CLEANUP_EMITS)
SET_CAPABILITY_OVERRIDE = _op(
    "governance.set_capability_override", "governance_capability_override_set",
    "governance.record_set_capability_override", "administrator",
    (_CACHE_EMIT,))

_OPS = (SET_VISIBILITY, SET_CLEANUP, REMOVE_CLEANUP, SET_CAPABILITY_OVERRIDE)

_REF_TABLE = (
    ("governance.record_set_visibility", _record_set_visibility),
    ("governance.record_set_cleanup", _record_set_cleanup),
    ("governance.record_remove_cleanup", _record_remove_cleanup),
    ("governance.record_set_capability_override",
     _record_set_capability_override),
    ("governance.tombstone_subject_audit", _tombstone_subject_audit),
    ("governance.visibility_payload", _visibility_payload),
    ("governance.cleanup_payload", _cleanup_payload),
    ("governance.cache_invalidated_payload", _cache_invalidated_payload),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
