"""The moderation mutation lane (band 2) — K7 CompoundOpSpecs over the
shipped moderation_service semantics: mod_logs row + warn-count escalation
INSIDE the seam (WarnOutcome, PR10 verbatim), the Discord state mutation as
a post-commit EFFECT leg through the guild-action port, and ONE domain
event (`moderation.action_taken` — subscribers dispatch on payload["action"],
shipped contract).

Authority: op-level `authority_ref=""` = the ADMIN floor (shipped v1
policy); the governance band's capability resolver narrows it later
(the band-1 settings-lane precedent).
"""

from __future__ import annotations

from sb.domain.moderation import service, store
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
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.events import DeliveryClass
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["EVT_MOD_ACTION", "register_ops"]

#: shipped event name, verbatim (services/moderation_service.py:88)
EVT_MOD_ACTION = "moderation.action_taken"


async def _policy_and_target(ctx: WorkflowContext, action: str):
    policy = await service.load_policy(int(ctx.guild_id or 0))
    target_id, reason = service.parse_target_and_reason(dict(ctx.params))
    reason = service.resolve_reason(reason, policy, action=action)
    return policy, target_id, reason


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


# --- DB legs ---------------------------------------------------------------------

@workflow("moderation.record_warn")
async def _record_warn(conn, ctx: WorkflowContext) -> LegOutcome:
    policy, target_id, reason = await _policy_and_target(ctx, "warn")
    count = await store.add_warning(conn, user_id=target_id,
                                    guild_id=int(ctx.guild_id or 0))
    await store.log_mod_action(conn, guild_id=int(ctx.guild_id or 0),
                               action="warn", target_id=target_id,
                               moderator_id=_actor_id(ctx), reason=reason)
    escalation = None
    if (count >= policy.warn_threshold
            and policy.warn_escalation_action in ("timeout", "kick", "ban")):
        escalation = policy.warn_escalation_action
        # shipped ladder: escalate then RESET the count (warn -> auto-action
        # -> clear), recorded as its own history row in the same txn.
        await store.clear_warnings(conn, user_id=target_id,
                                   guild_id=int(ctx.guild_id or 0))
        await store.log_mod_action(
            conn, guild_id=int(ctx.guild_id or 0), action=escalation,
            target_id=target_id, moderator_id=_actor_id(ctx),
            reason=f"warn threshold reached ({count}/{policy.warn_threshold})")
    # thread the decision to the EFFECT leg + payload through params
    ctx.params["_warn_count"] = count
    ctx.params["_warn_threshold"] = policy.warn_threshold
    ctx.params["_escalation"] = escalation
    ctx.params["_timeout_minutes"] = policy.warn_timeout_minutes
    ctx.params["_target_id"] = target_id
    ctx.params["_reason"] = reason
    ctx.params["_event_action"] = "warn"
    return LegOutcome(
        step=StepResult(0, "record_warn", True),
        before={"warnings": count - 1},
        after={"warnings": 0 if escalation else count,
               "escalated": escalation or "none"},
    )


def _record_action_leg(name: str, action: str):
    @workflow(name)
    async def _leg(conn, ctx: WorkflowContext) -> LegOutcome:
        _policy, target_id, reason = await _policy_and_target(ctx, action)
        await store.log_mod_action(conn, guild_id=int(ctx.guild_id or 0),
                                   action=action, target_id=target_id,
                                   moderator_id=_actor_id(ctx), reason=reason)
        ctx.params["_target_id"] = target_id
        ctx.params["_reason"] = reason
        ctx.params["_event_action"] = action
        return LegOutcome(step=StepResult(0, name.split(".")[-1], True),
                          before={}, after={"action": action,
                                            "target_id": target_id})
    return _leg


_record_timeout = _record_action_leg("moderation.record_timeout", "timeout")
_record_kick = _record_action_leg("moderation.record_kick", "kick")
_record_ban = _record_action_leg("moderation.record_ban", "ban")
_record_unban = _record_action_leg("moderation.record_unban", "unban")


@workflow("moderation.record_clearwarnings")
async def _record_clearwarnings(conn, ctx: WorkflowContext) -> LegOutcome:
    target_id, _reason = service.parse_target_and_reason(dict(ctx.params))
    prior = await store.get_warnings(target_id, int(ctx.guild_id or 0), conn=conn)
    await store.clear_warnings(conn, user_id=target_id,
                               guild_id=int(ctx.guild_id or 0))
    await store.log_mod_action(conn, guild_id=int(ctx.guild_id or 0),
                               action="clear_warnings", target_id=target_id,
                               moderator_id=_actor_id(ctx),
                               reason="warnings cleared")
    ctx.params["_target_id"] = target_id
    ctx.params["_reason"] = "warnings cleared"
    ctx.params["_event_action"] = "clear_warnings"
    return LegOutcome(step=StepResult(0, "record_clearwarnings", True),
                      before={"warnings": prior}, after={"warnings": 0})


# --- privacy erasure bodies (the store-declared refs; flag-18 discipline) ---------

@workflow("moderation.tombstone_subject")
async def _tombstone_subject(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.tombstone_subject_rows(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_subject", True),
                      before={}, after={"tombstoned_rows": rows})


@workflow("moderation.clear_subject_warnings")
async def _clear_subject_warnings(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    guild_id = int(ctx.params.get("guild_id", ctx.guild_id or 0))
    await store.clear_warnings(conn, user_id=subject, guild_id=guild_id)
    return LegOutcome(step=StepResult(0, "clear_subject_warnings", True),
                      before={}, after={"warnings": 0})


# --- EFFECT legs (post-commit; the guild-action port) -----------------------------

@workflow("moderation.apply_warn_effects")
async def _apply_warn_effects(conn, ctx: WorkflowContext) -> LegOutcome:
    escalation = ctx.params.get("_escalation")
    target_id = int(ctx.params.get("_target_id", 0))
    reason = str(ctx.params.get("_reason", service.DEFAULT_REASON))
    if escalation == "timeout":
        await service.active_actions().timeout_member(
            int(ctx.guild_id or 0), target_id,
            minutes=int(ctx.params.get("_timeout_minutes", 10)), reason=reason)
    elif escalation == "kick":
        await service.active_actions().kick_member(
            int(ctx.guild_id or 0), target_id, reason=reason)
    elif escalation == "ban":
        await service.active_actions().ban_member(
            int(ctx.guild_id or 0), target_id, reason=reason,
            delete_message_days=0)
    return LegOutcome(step=StepResult(0, "apply_warn_effects", True),
                      before={}, after={"escalation": escalation or "none"})


def _apply_action_leg(name: str, action: str):
    @workflow(name)
    async def _leg(conn, ctx: WorkflowContext) -> LegOutcome:
        target_id = int(ctx.params.get("_target_id", 0))
        reason = str(ctx.params.get("_reason", service.DEFAULT_REASON))
        actions = service.active_actions()
        if action == "timeout":
            policy = await service.load_policy(int(ctx.guild_id or 0))
            minutes = min(int(ctx.params.get("minutes",
                                             policy.warn_timeout_minutes)),
                          policy.max_timeout_minutes)
            await actions.timeout_member(int(ctx.guild_id or 0), target_id,
                                         minutes=minutes, reason=reason)
        elif action == "kick":
            await actions.kick_member(int(ctx.guild_id or 0), target_id,
                                      reason=reason)
        elif action == "ban":
            policy = await service.load_policy(int(ctx.guild_id or 0))
            await actions.ban_member(
                int(ctx.guild_id or 0), target_id, reason=reason,
                delete_message_days=policy.ban_delete_message_days)
        elif action == "unban":
            await actions.unban_member(int(ctx.guild_id or 0), target_id,
                                       reason=reason)
        return LegOutcome(step=StepResult(0, name.split(".")[-1], True),
                          before={}, after={"applied": action})
    return _leg


_apply_timeout = _apply_action_leg("moderation.apply_timeout", "timeout")
_apply_kick = _apply_action_leg("moderation.apply_kick", "kick")
_apply_ban = _apply_action_leg("moderation.apply_ban", "ban")
_apply_unban = _apply_action_leg("moderation.apply_unban", "unban")


@workflow("moderation.compensate_ban")
async def _compensate_ban(conn, ctx: WorkflowContext) -> LegOutcome:
    """Ban's compensator: unban restores membership eligibility."""
    target_id = int(ctx.params.get("_target_id", 0))
    await service.active_actions().unban_member(
        int(ctx.guild_id or 0), target_id,
        reason="compensating failed ban flow")
    return LegOutcome(step=StepResult(0, "compensate_ban", True),
                      before={}, after={"compensated": "ban"})


@workflow("moderation.compensate_unban")
async def _compensate_unban(conn, ctx: WorkflowContext) -> LegOutcome:
    """Unban's compensator: re-ban restores the prior state."""
    target_id = int(ctx.params.get("_target_id", 0))
    await service.active_actions().ban_member(
        int(ctx.guild_id or 0), target_id,
        reason="compensating failed unban flow", delete_message_days=0)
    return LegOutcome(step=StepResult(0, "compensate_unban", True),
                      before={}, after={"compensated": "unban"})


@workflow("moderation.action_payload")
def _action_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "action": str(ctx.params.get("_event_action", "")),
        "target_id": int(ctx.params.get("_target_id", 0)),
        "actor_id": _actor_id(ctx),
        "reason": str(ctx.params.get("_reason", "")),
    }


_EMITS = (EventEmitSpec(EVT_MOD_ACTION, WorkflowRef("moderation.action_payload"),
                        DeliveryClass.BEST_EFFORT),)


def _op(op_key: str, verb: str, db_ref: str, effect_ref: str | None, *,
        effect_reversibility: str = "reversible",
        compensator: str | None = None,
        confirmation: ConfirmationSpec | None = None) -> CompoundOpSpec:
    """Per-leg reversibility is an HONEST author declaration: timeouts are
    liftable (reversible), ban/unban compensate each other (compensatable),
    kick has no compensator (irreversible => ConfirmationSpec, the frozen
    §2.7 fence — a deliberate deviation from the shipped no-confirm !kick,
    ledgered in D-0029)."""
    legs = [LegSpec("record", LegKind.DB, WorkflowRef(db_ref), "reversible")]
    if effect_ref:
        legs.append(LegSpec(
            "apply", LegKind.EFFECT, WorkflowRef(effect_ref),
            effect_reversibility,
            compensator=WorkflowRef(compensator) if compensator else None))
    return CompoundOpSpec(
        op_key=op_key,
        domain="moderation",
        lane=WorkflowLane.DOMAIN,
        authority_ref="",                 # ADMIN floor (shipped v1 policy; the
                                          # governance band narrows per-capability)
        legs=tuple(legs),
        idempotency=IdempotencyPosture.NATURAL_KEY,
        dedup_key=None,
        audit_verb=verb,
        confirmation=confirmation,
        emits=_EMITS,
    )


WARN = _op("moderation.warn", "member_warned",
           "moderation.record_warn", "moderation.apply_warn_effects",
           effect_reversibility="reversible")   # escalation default = liftable timeout
TIMEOUT = _op("moderation.timeout", "member_timed_out",
              "moderation.record_timeout", "moderation.apply_timeout",
              effect_reversibility="reversible")
KICK = _op("moderation.kick", "member_kicked",
           "moderation.record_kick", "moderation.apply_kick",
           effect_reversibility="irreversible",
           confirmation=ConfirmationSpec(reversibility="irreversible",
                                         challenge=Challenge.TYPED_PHRASE))
BAN = _op("moderation.ban", "member_banned",
          "moderation.record_ban", "moderation.apply_ban",
          effect_reversibility="compensatable",
          compensator="moderation.compensate_ban")
UNBAN = _op("moderation.unban", "member_unbanned",
            "moderation.record_unban", "moderation.apply_unban",
            effect_reversibility="compensatable",
            compensator="moderation.compensate_unban")
CLEAR_WARNINGS = _op("moderation.clearwarnings", "warnings_cleared",
                     "moderation.record_clearwarnings", None)

_OPS = (WARN, TIMEOUT, KICK, BAN, UNBAN, CLEAR_WARNINGS)

_REF_TABLE = (
    ("moderation.record_warn", _record_warn),
    ("moderation.record_timeout", _record_timeout),
    ("moderation.record_kick", _record_kick),
    ("moderation.record_ban", _record_ban),
    ("moderation.record_unban", _record_unban),
    ("moderation.record_clearwarnings", _record_clearwarnings),
    ("moderation.tombstone_subject", _tombstone_subject),
    ("moderation.clear_subject_warnings", _clear_subject_warnings),
    ("moderation.apply_warn_effects", _apply_warn_effects),
    ("moderation.apply_timeout", _apply_timeout),
    ("moderation.apply_kick", _apply_kick),
    ("moderation.apply_ban", _apply_ban),
    ("moderation.apply_unban", _apply_unban),
    ("moderation.compensate_ban", _compensate_ban),
    ("moderation.compensate_unban", _compensate_unban),
    ("moderation.action_payload", _action_payload),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    """Refs-table twins of the REGISTRY op keys — the compiler's P2
    resolves WorkflowRef command routes against the refs table."""
    from sb.spec.refs import is_registered, workflow as _workflow

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
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
