"""The karma mutation lane (band 4) — ONE K7 CompoundOpSpec
(``karma.give``) over the shipped karma_service semantics (INV-K): the
data-level rules (enabled / no self-grant / per-recipient cooldown /
per-giver daily cap) enforce IN the leg, the credit + given_count bump +
audit row write in the SAME txn, and ``karma.granted`` emits BEST_EFFORT
post-commit with the shipped payload keys.

The typed rejection ladder (Self/Disabled/Cooldown/DailyCap) classifies
as ValidatorError => USER_ERROR/BLOCKED with the shipped user copy —
nothing is written on a block (the shipped write-nothing guarantee rides
the txn + raise-before-write ordering).
"""

from __future__ import annotations

from datetime import timedelta

from sb.domain.karma import store
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
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["EVT_KARMA_GRANTED", "register_ops"]

#: shipped event name, verbatim (services/karma_service.py:38)
EVT_KARMA_GRANTED = "karma.granted"


class SelfKarmaError(ValidatorError):
    """A member cannot grant karma to themselves."""


class KarmaDisabledError(ValidatorError):
    """Karma is disabled for the guild."""


class KarmaCooldownError(ValidatorError):
    """The giver already thanked this recipient within the window."""


class KarmaDailyCapError(ValidatorError):
    """The giver hit their per-day grant cap."""


def _actor_id(ctx: WorkflowContext) -> int:
    actor = getattr(ctx, "actor", None)
    return int(getattr(actor, "user_id", 0) or 0)


def _target_from(ctx: WorkflowContext) -> int | None:
    target = ctx.params.get("target_id") or ctx.params.get("member")
    if target is None:
        argv = tuple(ctx.params.get("argv", ()) or ())
        for token in argv:
            stripped = str(token).strip("<@!>")
            if stripped.isdigit():
                target = stripped
                break
    if target is None:
        return None
    return int(str(target).strip("<@!>"))


def _reason_from(ctx: WorkflowContext) -> str | None:
    reason = ctx.params.get("reason")
    if reason is None:
        argv = tuple(ctx.params.get("argv", ()) or ())
        tail = [str(t) for t in argv if not str(t).strip("<@!>").isdigit()]
        reason = " ".join(tail).strip() or None
    return str(reason) if reason else None


# --- THE DB leg ------------------------------------------------------------------------

@workflow("karma.record_give")
async def _record_give(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.economy.service import format_remaining
    from sb.domain.karma.policy import load_policy

    gid = int(ctx.guild_id or 0)
    from_user = _actor_id(ctx)
    to_user = _target_from(ctx)
    amount = int(ctx.params.get("amount", 1) or 1)
    source = str(ctx.params.get("source", "") or "command")
    reason = _reason_from(ctx)

    if to_user is None:
        raise ValidatorError("Usage: `!thanks @user [reason]`")
    if amount <= 0:
        raise ValidatorError("❌ Karma amount must be positive.")
    if from_user == to_user:
        raise SelfKarmaError("You can't give karma to yourself.")

    policy = await load_policy(gid)
    if not policy.enabled:
        raise KarmaDisabledError("Karma is disabled on this server.")

    now = ctx.clock()

    # Per-(giver -> receiver) cooldown (audit-log read, shipped).
    if policy.cooldown_seconds > 0:
        window_start = now - timedelta(seconds=policy.cooldown_seconds)
        recent = await store.recent_grant_count(gid, from_user, to_user,
                                                window_start, conn=conn)
        if recent > 0:
            raise KarmaCooldownError(
                f"You've already thanked <@{to_user}> recently — try again "
                f"in {format_remaining(policy.cooldown_seconds)}.")

    # Per-giver daily cap (rolling 24 h, shipped).
    day_start = now - timedelta(days=1)
    given_today = await store.grants_given_since(gid, from_user, day_start,
                                                 conn=conn)
    if given_today >= policy.daily_cap:
        raise KarmaDailyCapError(
            f"You've reached your daily limit of {policy.daily_cap} karma "
            f"grants. Come back tomorrow!")

    # Row stamps ride ctx.clock() (NOT DB NOW()) so the cooldown/cap reads
    # above compare against the SAME clock they were written with — under
    # the parity harness's pinned clock a NOW()-stamped row sat outside
    # every logical window and the cooldown never fired on replay (the
    # band-3 SYSTEM_CLOCK seam finding, D-0060 precedent).
    new_total = await store.credit_karma(conn, to_user=to_user, guild_id=gid,
                                         amount=amount, now=now)
    await store.increment_given(conn, from_user=from_user, guild_id=gid)
    await store.insert_karma_audit(conn, guild_id=gid, from_user=from_user,
                                   to_user=to_user, delta=amount,
                                   source=source, reason=reason,
                                   occurred_at=now)

    ctx.params["_from_user"] = from_user
    ctx.params["_to_user"] = to_user
    ctx.params["_delta"] = amount
    ctx.params["_new_total"] = new_total
    ctx.params["_source"] = source
    return LegOutcome(
        step=StepResult(to_user, "give", True),
        before={"karma": new_total - amount},
        after={"to_user": to_user, "new_total": new_total, "delta": amount,
               "source": source},
    )


# --- privacy erasure bodies --------------------------------------------------------------

@workflow("karma.erase_subject_karma")
async def _erase_subject_karma(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_karma(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_karma", True),
                      before={}, after={"rows": rows})


@workflow("karma.tombstone_subject_audit")
async def _tombstone_subject_audit(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.tombstone_subject_audit(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "tombstone_subject_audit", True),
                      before={}, after={"rows": rows})


# --- event payload builder (shipped payload keys, verbatim) --------------------------------

@workflow("karma.granted_payload")
def _granted_payload(ctx: WorkflowContext, result) -> dict:
    return {
        "guild_id": int(ctx.guild_id or 0),
        "from_user": int(ctx.params.get("_from_user", 0) or 0),
        "to_user": int(ctx.params.get("_to_user", 0) or 0),
        "delta": int(ctx.params.get("_delta", 0) or 0),
        "new_total": int(ctx.params.get("_new_total", 0) or 0),
        "source": str(ctx.params.get("_source", "") or ""),
    }


GIVE = CompoundOpSpec(
    op_key="karma.give", domain="karma", lane=WorkflowLane.DOMAIN,
    authority_ref="user",                 # member-facing (TIER lane)
    legs=(LegSpec("record", LegKind.DB, WorkflowRef("karma.record_give"),
                  "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="karma_granted",
    emits=(EventEmitSpec(EVT_KARMA_GRANTED,
                         WorkflowRef("karma.granted_payload"),
                         DeliveryClass.BEST_EFFORT),))

_OPS = (GIVE,)

_REF_TABLE = (
    ("karma.record_give", _record_give),
    ("karma.erase_subject_karma", _erase_subject_karma),
    ("karma.tombstone_subject_audit", _tombstone_subject_audit),
    ("karma.granted_payload", _granted_payload),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
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
