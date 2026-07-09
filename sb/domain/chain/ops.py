"""Chain K7 lanes (band 6) — the shipped RS07 ``chain_service``
canonical-writer semantics as audited one-leg ops:

* ``chain.create`` — normalize (``strip().lower()``), reject empty,
  refuse a channel with an active word, PRESERVE an existing
  limit-only row's word_limit (the shipped
  ``test_create_chain_preserves_existing_limit`` pin).
* ``chain.delete`` — remove the row (word AND limit).
* ``chain.set_limit`` — set (>0) / remove (0); requires an existing
  row; a no-change write is skipped (SUCCESS, no mutation copy).
* ``chain.record_progress`` — the per-message chain_count increment
  (the hot path; K7's central audit row REPLACES the shipped
  deliberately-unaudited direct write — ledgered D-0044).
"""

from __future__ import annotations

from sb.domain.chain import store
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


def _describe_row(row: dict | None) -> str | None:
    """Compact audit string for an existing chain row (shipped)."""
    if not row:
        return None
    parts: list[str] = []
    if row.get("word"):
        parts.append(f"word={row['word']}")
    if row.get("word_limit"):
        parts.append(f"limit={row['word_limit']}")
    return " ".join(parts) or "(empty row)"


@workflow("chain.record_create")
async def _record_create(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = int(ctx.params.get("channel_id") or 0)
    normalized = str(ctx.params.get("word") or "").strip().lower()
    if not normalized:
        raise ValidatorError("Please provide the allowed word.")
    existing = await store.get_chain_channel(channel_id, conn=conn)
    if existing and existing.get("word"):
        raise ValidatorError(
            f"❌ A chain already exists in <#{channel_id}> "
            f"({_describe_row(existing)}). Delete it first.")
    await store.set_chain_channel(
        conn, channel_id=channel_id, guild_id=gid, word=normalized,
        limit=(existing or {}).get("word_limit") or 0)
    return LegOutcome(
        step=StepResult(uid, "create_chain", True),
        before={"row": _describe_row(existing)},
        after={"word": normalized,
               "message": f"✅ Chain created in <#{channel_id}>. Only "
                          f"the word `{normalized}` is allowed in this "
                          f"channel."})


@workflow("chain.record_delete")
async def _record_delete(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, _gid = _ids(ctx)
    channel_id = int(ctx.params.get("channel_id") or 0)
    existing = await store.get_chain_channel(channel_id, conn=conn)
    if not existing:
        raise ValidatorError(
            f"❌ No chain or word limit is set for <#{channel_id}>.")
    await store.delete_chain_channel(conn, channel_id=channel_id)
    return LegOutcome(
        step=StepResult(uid, "delete_chain", True),
        before={"row": _describe_row(existing)},
        after={"message": f"🗑️ Chain removed from <#{channel_id}>."})


@workflow("chain.record_set_limit")
async def _record_set_limit(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, _gid = _ids(ctx)
    channel_id = int(ctx.params.get("channel_id") or 0)
    limit = ctx.params.get("limit")
    if not isinstance(limit, int) or limit < 0:
        raise ValidatorError(
            "Word limit must be a non-negative integer (0 removes it).")
    existing = await store.get_chain_channel(channel_id, conn=conn)
    if not existing:
        raise ValidatorError(
            f"❌ No chain is set up in <#{channel_id}> — create one "
            f"first with `!chain create`.")
    old_limit = existing.get("word_limit") or 0
    if old_limit == limit:
        return LegOutcome(
            step=StepResult(uid, "set_chain_limit", True),
            before={"limit": old_limit},
            after={"limit": limit, "no_change": True,
                   "message": f"The word limit in <#{channel_id}> is "
                              f"already **{limit}**."})
    await store.set_chain_limit(conn, channel_id=channel_id, limit=limit)
    if limit:
        message = (f"📏 Word limit in <#{channel_id}> set to "
                   f"**{limit}** word(s).")
    else:
        message = f"📏 Word limit removed from <#{channel_id}>."
    return LegOutcome(
        step=StepResult(uid, "set_chain_limit", True),
        before={"limit": old_limit},
        after={"limit": limit, "message": message})


@workflow("chain.record_progress_leg")
async def _record_progress(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, _gid = _ids(ctx)
    channel_id = int(ctx.params.get("channel_id") or 0)
    count = await store.increment_chain_count(conn, channel_id=channel_id)
    return LegOutcome(step=StepResult(uid, "record_progress", True),
                      before={}, after={"chain_count": count})


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="chain", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb)


CREATE = _op("chain.create", "create_chain", "chain.record_create")
DELETE = _op("chain.delete", "delete_chain", "chain.record_delete")
SET_LIMIT = _op("chain.set_limit", "set_chain_limit",
                "chain.record_set_limit")
RECORD_PROGRESS = _op("chain.record_progress", "chain_progressed",
                      "chain.record_progress_leg")

_OPS = (CREATE, DELETE, SET_LIMIT, RECORD_PROGRESS)

_REF_TABLE = (
    ("chain.record_create", _record_create),
    ("chain.record_delete", _record_delete),
    ("chain.record_set_limit", _record_set_limit),
    ("chain.record_progress_leg", _record_progress),
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
