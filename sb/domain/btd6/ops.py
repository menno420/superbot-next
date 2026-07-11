"""BTD6 K7 lanes (band 7):

* ``btd6.submit_strategy`` — a member submits a strategy (guild
  visibility, pending review; the strategy-intake NL path and the
  ``!btd6strat submit`` command share this lane).
* ``btd6.review_strategy`` — a staff/AI reviewer records the verdict
  (approve / reject; the AI reviewer is the Sonnet-reserved
  ``btd6.strategy_review`` task — its verdict lands through THIS lane so
  the mutation is audited like any other write).
* ``btd6.scrub_strategy_submitter`` — the MEMBER_PII erasure body
  (anonymize, row retained — shipped identity-state transition).

Shipped ``btd6_strategy_audit`` transitions ride the K7 central audit
row (D-0046)."""

from __future__ import annotations

from sb.domain.btd6 import store
from sb.kernel.interaction.errors import ValidatorError
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

__all__ = ["ensure_ops_refs", "register_ops"]

_REVIEW_STATUSES = frozenset({"approved", "rejected", "unpublished"})


def _ids(ctx: WorkflowContext) -> tuple[int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0))


@workflow("btd6.record_submit_strategy")
async def _record_submit(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    title = str(ctx.params.get("title") or "").strip()
    summary = str(ctx.params.get("summary") or "").strip()
    if not title or not summary:
        raise ValidatorError(
            "A strategy needs a title and a summary — try "
            "`!btd6strat submit` again with both.")
    strategy_id = await store.insert_strategy(
        conn, guild_id=gid, title=title[:120], summary=summary[:2000],
        map_name=(str(ctx.params.get("map") or "").strip() or None),
        mode=(str(ctx.params.get("mode") or "").strip() or None),
        hero=(str(ctx.params.get("hero") or "").strip() or None),
        submitted_by=uid,
        submitter_display=(
            str(ctx.params.get("_display_name") or "").strip() or None),
    )
    return LegOutcome(
        step=StepResult(uid, "submit_strategy", True), before={},
        after={"strategy_id": strategy_id,
               "message": f"✅ Strategy **#{strategy_id}** submitted for "
                          "review — staff (or the AI reviewer) will look "
                          "at it soon."})


@workflow("btd6.record_review_strategy")
async def _record_review(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, _gid = _ids(ctx)
    strategy_id = int(ctx.params.get("strategy_id") or 0)
    verdict = str(ctx.params.get("approval_status") or "").strip().lower()
    if verdict not in _REVIEW_STATUSES:
        raise ValidatorError(
            "Review verdict must be approved, rejected, or unpublished.")
    existing = await store.get_strategy(strategy_id, conn=conn)
    if not existing:
        raise ValidatorError(f"❌ No strategy #{strategy_id} on record.")
    approved_by = str(ctx.params.get("approved_by") or "staff")
    await store.set_review(
        conn, strategy_id=strategy_id, approval_status=verdict,
        approved_by=(approved_by if verdict == "approved" else None),
        approved_by_id=(uid if verdict == "approved" else None),
        review_notes={"notes": str(ctx.params.get("notes") or "")[:1000],
                      "reviewer_kind": approved_by})
    return LegOutcome(
        step=StepResult(uid, "review_strategy", True),
        before={"approval_status": existing.get("approval_status")},
        after={"strategy_id": strategy_id, "approval_status": verdict,
               "message": f"Strategy #{strategy_id} → **{verdict}**."})


#: the shipped legacy-KV settings key (utils/settings_keys.py
#: BTD6_VERSION_ANNOUNCEMENT_CHANNEL, verbatim — the
#: sweep_btd6_ops_announcechannel golden pins the row bytes).
ANNOUNCE_CHANNEL_KEY = "btd6_version_announcement_channel"


@workflow("btd6.record_announce_channel")
async def _record_announce_channel(conn, ctx: WorkflowContext) -> LegOutcome:
    """`!btd6 ops announcechannel` — the shipped guild_settings KV upsert
    (btd6_version_announce.set_channel / clear_channel wrote value "" to
    disable; the sb/domain/games/tournament_flag.py precedent for shipped
    guild_settings rows written by an audited domain op)."""
    from sb.kernel.db.pool import execute

    uid, gid = _ids(ctx)
    channel_id = ctx.params.get("channel_id")
    value = str(int(channel_id)) if channel_id else ""
    await execute(
        "INSERT INTO guild_settings (guild_id, key, value) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value",
        (gid, ANNOUNCE_CHANNEL_KEY, value), conn=conn)
    return LegOutcome(
        step=StepResult(uid, "announce_channel", True), before={},
        after={"key": ANNOUNCE_CHANNEL_KEY, "value": value})


@workflow("btd6.scrub_strategy_submitter")
async def _scrub_submitter(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    touched = await store.anonymize_submitter(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "scrub", True), before={},
                      after={"rows_touched": touched,
                             "disposition": "anonymized"})


def _op(op_key: str, verb: str, leg_ref: str,
        authority: str = "user") -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="btd6", lane=WorkflowLane.DOMAIN,
        authority_ref=authority,
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb)


SUBMIT = _op("btd6.submit_strategy", "btd6_strategy_submitted",
             "btd6.record_submit_strategy")
REVIEW = _op("btd6.review_strategy", "btd6_strategy_reviewed",
             "btd6.record_review_strategy", authority="staff")
ANNOUNCE = _op("btd6.set_announce_channel", "btd6_announce_channel_set",
               "btd6.record_announce_channel", authority="staff")

_OPS = (SUBMIT, REVIEW, ANNOUNCE)

_REF_TABLE = (
    ("btd6.record_submit_strategy", _record_submit),
    ("btd6.record_review_strategy", _record_review),
    ("btd6.record_announce_channel", _record_announce_channel),
    ("btd6.scrub_strategy_submitter", _scrub_submitter),
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
