"""The AI orchestration-mutation K7 lanes (band 7, the
orchestration-mutation slice — the D-0070 parked tools profile pickers)
— the shipped ``services.ai_orchestration_mutation`` scoped setters as
audited CompoundOps:

* ``ai.set_guild_orchestration`` / ``ai.set_channel_orchestration`` /
  ``ai.set_category_orchestration`` — ONE DB leg each (the shipped
  column-only orchestration upsert — or the guild KV twin — + the
  shipped bump_generation, same transaction; the K7 central audit row
  replaces the shipped mutation_id-only result), the shipped advisory
  ``ai.orchestration.{guild,channel,category}_changed`` events AFTER
  commit (BEST_EFFORT — the shipped ``_emit`` posture: "failures must
  not break the write").

Value validation is the shipped seam's: ``profile_key=None`` clears the
override; a non-null key must name a REGISTERED orchestration profile
(sb/kernel/ai/orchestration.py — the shipped "validated against the
built-in presets at the audited service seam" rule, which is why
migration 0031 carries no CHECK constraint). The widget pre-checks the
roster for the shipped error echo; the legs RE-CHECK it (§4.1 seam
authority) so no raw caller can persist an unknown key. Compensator
allowlist stays EMPTY (single reversible DB leg per op)."""

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
    "EVT_ORCH_CATEGORY_CHANGED",
    "EVT_ORCH_CHANNEL_CHANGED",
    "EVT_ORCH_GUILD_CHANGED",
    "ensure_orchestration_ops_refs",
    "known_profile_keys",
    "register_orchestration_ops",
    "validate_profile_key",
]

#: shipped event names, verbatim (services/ai_orchestration_mutation.py /
#: core/events_catalogue.py).
EVT_ORCH_GUILD_CHANGED = "ai.orchestration.guild_changed"
EVT_ORCH_CHANNEL_CHANGED = "ai.orchestration.channel_changed"
EVT_ORCH_CATEGORY_CHANGED = "ai.orchestration.category_changed"


def known_profile_keys() -> tuple[str, ...]:
    """Every registered orchestration profile key (the shipped
    ``ai_orchestration_presets.known_profile_keys()`` twin)."""
    from sb.kernel.ai import orchestration

    return tuple(p.key for p in orchestration.registered_profiles())


def validate_profile_key(profile_key: str | None) -> None:
    """The shipped seam validation, sentence body verbatim
    (``InvalidAIOrchestrationValueError`` — None/clear always passes)."""
    if profile_key is None:
        return
    valid = sorted(known_profile_keys())
    if profile_key not in valid:
        raise ValidatorError(
            f"unknown orchestration profile {profile_key!r}; "
            f"must be one of {valid} (or null to clear)")


def _ids(ctx: WorkflowContext) -> tuple[int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0))


def _profile_key(ctx: WorkflowContext) -> str | None:
    raw = ctx.params.get("profile_key")
    key = None if raw is None else str(raw)
    validate_profile_key(key)
    return key


@workflow("ai.record_guild_orchestration")
async def _set_guild_orchestration(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    key = _profile_key(ctx)
    prior = await store.set_guild_orchestration_profile(
        conn, guild_id=gid, profile_key=key)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "orchestration_write", True),
        before={"orchestration_profile": prior},
        after={"table": "guild_settings", "target_id": gid,
               "profile_key": key, "generation": generation})


@workflow("ai.record_channel_orchestration")
async def _set_channel_orchestration(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    key = _profile_key(ctx)
    channel_id = int(ctx.params.get("channel_id") or 0)
    prior = await store.upsert_channel_orchestration(
        conn, guild_id=gid, channel_id=channel_id,
        orchestration_profile=key, updated_by=uid)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "orchestration_write", True),
        before=prior or {},
        after={"table": "ai_channel_policy", "target_id": channel_id,
               "profile_key": key, "generation": generation})


@workflow("ai.record_category_orchestration")
async def _set_category_orchestration(conn,
                                      ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    key = _profile_key(ctx)
    category_id = int(ctx.params.get("category_id") or 0)
    prior = await store.upsert_category_orchestration(
        conn, guild_id=gid, category_id=category_id,
        orchestration_profile=key, updated_by=uid)
    generation = await store.bump_generation(conn, guild_id=gid)
    return LegOutcome(
        step=StepResult(uid, "orchestration_write", True),
        before=prior or {},
        after={"table": "ai_category_policy", "target_id": category_id,
               "profile_key": key, "generation": generation})


@workflow("ai.orchestration_changed_payload")
def _changed_payload(ctx: WorkflowContext, result) -> dict:
    # the shipped _emit kwargs verbatim (bus.emit(event, guild_id=…,
    # mutation_id=…) — events_catalogue.py: "Payload: guild_id,
    # mutation_id. Same swallow-on-subscriber-failure contract as
    # ai.policy.*."; the handler mints the uuid, the ai.policy_ops shape).
    return {
        "guild_id": int(ctx.guild_id or 0),
        "mutation_id": str(ctx.params.get("mutation_id") or ""),
    }


def _orch_op(op_key: str, verb: str, leg_ref: str,
             event: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="ai", lane=WorkflowLane.DOMAIN,
        authority_ref="staff",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb,
        emits=(EventEmitSpec(event,
                             WorkflowRef("ai.orchestration_changed_payload"),
                             DeliveryClass.BEST_EFFORT),))


SET_GUILD_ORCHESTRATION = _orch_op(
    "ai.set_guild_orchestration", "ai_orchestration_guild_set",
    "ai.record_guild_orchestration", EVT_ORCH_GUILD_CHANGED)
SET_CHANNEL_ORCHESTRATION = _orch_op(
    "ai.set_channel_orchestration", "ai_orchestration_channel_set",
    "ai.record_channel_orchestration", EVT_ORCH_CHANNEL_CHANGED)
SET_CATEGORY_ORCHESTRATION = _orch_op(
    "ai.set_category_orchestration", "ai_orchestration_category_set",
    "ai.record_category_orchestration", EVT_ORCH_CATEGORY_CHANGED)

_OPS = (SET_GUILD_ORCHESTRATION, SET_CHANNEL_ORCHESTRATION,
        SET_CATEGORY_ORCHESTRATION)

_REF_TABLE = (
    ("ai.record_guild_orchestration", _set_guild_orchestration),
    ("ai.record_channel_orchestration", _set_channel_orchestration),
    ("ai.record_category_orchestration", _set_category_orchestration),
    ("ai.orchestration_changed_payload", _changed_payload),
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


def register_orchestration_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_orchestration_ops_refs() -> None:
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
