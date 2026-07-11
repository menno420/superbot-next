"""The AI policy-mutation K7 lanes (band 7, the policy-mutation slice) —
the shipped ``services.ai_policy_mutation`` scoped setters as audited
CompoundOps:

* ``ai.set_channel_policy`` / ``ai.set_category_policy`` /
  ``ai.set_role_policy`` — ONE DB leg each (the scoped upsert + the
  shipped bump_generation, same transaction; the K7 central audit row
  replaces the shipped mutation_id-only result), the shipped advisory
  ``ai.policy.{channel,category,role}_changed`` events AFTER commit
  (BEST_EFFORT — the shipped ``core.events.bus.emit`` posture: a failed
  emit never drags the write down).
* ``ai.scrub_policy_editor`` — MEMBER_ID erasure body for the three
  override stores (detach editorship, the preset-authorship precedent).

Value validation (mode/decision rosters, the optional-int parses) runs in
the widget handlers BEFORE the op — the shipped views validated before
calling the mutation seam — and the legs re-check the rosters so no raw
caller can write an undeclared mode/decision (the §4.1 seam-authority
posture)."""

from __future__ import annotations

from sb.domain.ai import policy_store as store
from sb.kernel.interaction.errors import ValidatorError
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
from sb.spec.refs import WorkflowRef, is_registered, workflow

__all__ = [
    "EVT_POLICY_CATEGORY_CHANGED",
    "EVT_POLICY_CHANNEL_CHANGED",
    "EVT_POLICY_ROLE_CHANGED",
    "VALID_MODES",
    "VALID_ROLE_DECISIONS",
    "ensure_policy_ops_refs",
    "register_policy_ops",
]

#: shipped event names, verbatim (services/ai_policy_mutation.py).
EVT_POLICY_CHANNEL_CHANGED = "ai.policy.channel_changed"
EVT_POLICY_CATEGORY_CHANGED = "ai.policy.category_changed"
EVT_POLICY_ROLE_CHANGED = "ai.policy.role_changed"

#: the shipped roster tuples (views + mutation service agree on them).
VALID_MODES = ("inherit", "always_reply", "mention_only", "disabled")
VALID_ROLE_DECISIONS = ("allow", "deny", "inherit")


def _ids(ctx: WorkflowContext) -> tuple[int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0))


def _optional_int(value) -> int | None:
    return None if value is None else int(value)


@workflow("ai.record_channel_policy")
async def _set_channel_policy(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    mode = str(ctx.params.get("mode") or "")
    if mode not in VALID_MODES:
        # the shipped InvalidAIPolicyValueError sentence body.
        raise ValidatorError(
            f"channel mode must be one of {sorted(VALID_MODES)}, "
            f"got {mode!r}")
    channel_id = int(ctx.params.get("channel_id") or 0)
    prior = await store.upsert_channel_policy(
        conn, guild_id=gid, channel_id=channel_id, mode=mode,
        min_level=_optional_int(ctx.params.get("min_level")),
        cooldown_seconds=_optional_int(ctx.params.get("cooldown_seconds")),
        updated_by=uid)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "policy_write", True),
        before=prior or {},
        after={"table": "ai_channel_policy", "target_id": channel_id,
               "generation": generation})


@workflow("ai.record_category_policy")
async def _set_category_policy(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    mode = str(ctx.params.get("mode") or "")
    if mode not in VALID_MODES:
        raise ValidatorError(
            f"category mode must be one of {sorted(VALID_MODES)}, "
            f"got {mode!r}")
    category_id = int(ctx.params.get("category_id") or 0)
    prior = await store.upsert_category_policy(
        conn, guild_id=gid, category_id=category_id, mode=mode,
        min_level=_optional_int(ctx.params.get("min_level")),
        cooldown_seconds=_optional_int(ctx.params.get("cooldown_seconds")),
        updated_by=uid)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "policy_write", True),
        before=prior or {},
        after={"table": "ai_category_policy", "target_id": category_id,
               "generation": generation})


@workflow("ai.record_role_policy")
async def _set_role_policy(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    decision = str(ctx.params.get("decision") or "")
    if decision not in VALID_ROLE_DECISIONS:
        raise ValidatorError(
            f"role decision must be one of {sorted(VALID_ROLE_DECISIONS)}, "
            f"got {decision!r}")
    min_level_override = _optional_int(ctx.params.get("min_level_override"))
    if min_level_override is not None and min_level_override < 0:
        raise ValidatorError("min_level_override must be >= 0")
    role_id = int(ctx.params.get("role_id") or 0)
    prior = await store.upsert_role_policy(
        conn, guild_id=gid, role_id=role_id, decision=decision,
        min_level_override=min_level_override,
        bypass_cooldown=bool(ctx.params.get("bypass_cooldown")),
        updated_by=uid)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "policy_write", True),
        before=prior or {},
        after={"table": "ai_role_policy", "target_id": role_id,
               "generation": generation})


@workflow("ai.scrub_policy_editor")
async def _scrub_editor(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    touched = await store.detach_policy_editor(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "scrub", True), before={},
                      after={"rows_touched": touched,
                             "disposition": "detached"})


@workflow("ai.policy_changed_payload")
def _changed_payload(ctx: WorkflowContext, result) -> dict:
    # the shipped emit kwargs verbatim (bus.emit(event, guild_id=…,
    # mutation_id=…) — the handler mints the uuid, the shipped seam shape).
    return {
        "guild_id": int(ctx.guild_id or 0),
        "mutation_id": str(ctx.params.get("mutation_id") or ""),
    }


def _policy_op(op_key: str, verb: str, leg_ref: str,
               event: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="ai", lane=WorkflowLane.DOMAIN,
        authority_ref="staff",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb,
        emits=(EventEmitSpec(event,
                             WorkflowRef("ai.policy_changed_payload"),
                             DeliveryClass.BEST_EFFORT),))


SET_CHANNEL_POLICY = _policy_op(
    "ai.set_channel_policy", "ai_policy_channel_set",
    "ai.record_channel_policy", EVT_POLICY_CHANNEL_CHANGED)
SET_CATEGORY_POLICY = _policy_op(
    "ai.set_category_policy", "ai_policy_category_set",
    "ai.record_category_policy", EVT_POLICY_CATEGORY_CHANGED)
SET_ROLE_POLICY = _policy_op(
    "ai.set_role_policy", "ai_policy_role_set",
    "ai.record_role_policy", EVT_POLICY_ROLE_CHANGED)

_OPS = (SET_CHANNEL_POLICY, SET_CATEGORY_POLICY, SET_ROLE_POLICY)

_REF_TABLE = (
    ("ai.record_channel_policy", _set_channel_policy),
    ("ai.record_category_policy", _set_category_policy),
    ("ai.record_role_policy", _set_role_policy),
    ("ai.scrub_policy_editor", _scrub_editor),
    ("ai.policy_changed_payload", _changed_payload),
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


def register_policy_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_policy_ops_refs() -> None:
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
