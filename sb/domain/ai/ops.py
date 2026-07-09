"""AI-surface K7 lanes (band 7):

* ``ai.record_review_entry`` — insert one review-log row (the stage's
  fail-safe writers call this lane; system-volume is bounded by actual
  AI misses/corrections).
* ``ai.resolve_review_entry`` — flip reviewed=TRUE (!aireview resolve).
* ``ai.set_preset`` / ``ai.remove_preset`` — the vetted-answer preset
  mutations (the shipped audited write seam; the K7 central audit row
  replaces the shipped audit.action_recorded emit).
* ``ai.scrub_review_subject`` — MEMBER_PII erasure body (delete the
  subject's review rows, detach preset authorship) — also the waiting
  body for kernel.ai.scrub_decision_audit's sibling roster.
"""

from __future__ import annotations

from sb.domain.ai import normalize, store
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


def _ids(ctx: WorkflowContext) -> tuple[int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0))


@workflow("ai.record_review_entry_leg")
async def _record_entry(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    p = ctx.params
    kind = str(p.get("kind") or "")
    if kind not in ("unknown", "correction"):
        raise ValidatorError("Review entry kind must be unknown|correction.")
    entry_id = await store.insert_entry(
        conn, guild_id=gid, channel_id=int(p.get("channel_id") or 0),
        user_id=int(p.get("user_id") or uid), kind=kind,
        reason_code=p.get("reason_code"), task=p.get("task"),
        route=p.get("route"), question=p.get("question"),
        answer=p.get("answer"), correction=p.get("correction"),
        corrected_by=p.get("corrected_by"),
        message_id=p.get("message_id"),
        reply_message_id=p.get("reply_message_id"),
        provider=p.get("provider"), model=p.get("model"))
    return LegOutcome(step=StepResult(uid, "record_review", True),
                      before={}, after={"entry_id": entry_id})


@workflow("ai.record_resolve_entry")
async def _resolve_entry(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    entry_id = int(ctx.params.get("entry_id") or 0)
    existing = await store.get_entry(gid, entry_id, conn=conn)
    if not existing:
        raise ValidatorError(f"❌ No review entry #{entry_id} here.")
    await store.mark_reviewed(conn, guild_id=gid, entry_id=entry_id)
    return LegOutcome(
        step=StepResult(uid, "resolve_review", True),
        before={"reviewed": existing.get("reviewed")},
        after={"entry_id": entry_id,
               "message": f"✅ Review entry #{entry_id} marked reviewed."})


@workflow("ai.record_set_preset")
async def _set_preset(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    question = str(ctx.params.get("question") or "")
    answer = str(ctx.params.get("answer") or "").strip()
    key = normalize.normalize_question(question)
    if not key:
        raise ValidatorError("The question is empty after normalization.")
    if not answer:
        raise ValidatorError("The vetted answer cannot be blank.")
    preset_id = await store.upsert_preset(
        conn, guild_id=gid, question_key=key, question=question[:500],
        answer=answer[:2000], task=ctx.params.get("task"),
        source=str(ctx.params.get("source") or "operator"),
        created_by=uid)
    return LegOutcome(
        step=StepResult(uid, "set_preset", True), before={},
        after={"preset_id": preset_id,
               "message": f"✅ Vetted answer stored (preset #{preset_id}) — "
                          "served verbatim, zero model call."})


@workflow("ai.record_remove_preset")
async def _remove_preset(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    key = normalize.normalize_question(str(ctx.params.get("question") or ""))
    if not key:
        raise ValidatorError("The question is empty after normalization.")
    removed = await store.remove_preset(conn, guild_id=gid, question_key=key)
    if not removed:
        raise ValidatorError("❌ No preset stored for that question.")
    return LegOutcome(step=StepResult(uid, "remove_preset", True),
                      before={"question_key": key},
                      after={"message": "🗑️ Preset removed."})


@workflow("ai.scrub_review_subject")
async def _scrub_subject(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    touched = await store.erase_subject(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "scrub", True), before={},
                      after={"rows_touched": touched,
                             "disposition": "deleted+detached"})


def _op(op_key: str, verb: str, leg_ref: str,
        authority: str = "staff") -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="ai", lane=WorkflowLane.DOMAIN,
        authority_ref=authority,
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb)


RECORD_ENTRY = _op("ai.record_review_entry", "ai_review_logged",
                   "ai.record_review_entry_leg", authority="user")
RESOLVE_ENTRY = _op("ai.resolve_review_entry", "ai_review_resolved",
                    "ai.record_resolve_entry")
SET_PRESET = _op("ai.set_preset", "ai_preset_set", "ai.record_set_preset")
REMOVE_PRESET = _op("ai.remove_preset", "ai_preset_removed",
                    "ai.record_remove_preset")

_OPS = (RECORD_ENTRY, RESOLVE_ENTRY, SET_PRESET, REMOVE_PRESET)

_REF_TABLE = (
    ("ai.record_review_entry_leg", _record_entry),
    ("ai.record_resolve_entry", _resolve_entry),
    ("ai.record_set_preset", _set_preset),
    ("ai.record_remove_preset", _remove_preset),
    ("ai.scrub_review_subject", _scrub_subject),
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
