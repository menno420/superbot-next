"""Cleanup word-filter K7 lane (band 2): add/remove are NATURAL_KEY DB ops
through the sole-writer store; list is a read handler."""

from __future__ import annotations

from sb.domain.cleanup import store
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
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["register_ops"]


def _word_from(ctx: WorkflowContext) -> str:
    word = str(ctx.params.get("word", "") or "")
    if not word:
        argv = tuple(ctx.params.get("argv", ()) or ())
        word = str(argv[0]) if argv else ""
    if not word:
        raise ValueError("no word supplied")
    return word.lower().strip()


@workflow("cleanup.word_add")
async def _word_add(conn, ctx: WorkflowContext) -> LegOutcome:
    word = _word_from(ctx)
    added = await store.add_word(conn, guild_id=int(ctx.guild_id or 0), word=word)
    return LegOutcome(step=StepResult(0, "word_add", True),
                      before={}, after={"word": word, "added": added})


@workflow("cleanup.word_remove")
async def _word_remove(conn, ctx: WorkflowContext) -> LegOutcome:
    word = _word_from(ctx)
    removed = await store.remove_word(conn, guild_id=int(ctx.guild_id or 0),
                                      word=word)
    return LegOutcome(step=StepResult(0, "word_remove", True),
                      before={"present": removed}, after={"word": word})


def _op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="cleanup", lane=WorkflowLane.DOMAIN,
        authority_ref="",
        legs=(LegSpec("write", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


WORD_ADD = _op("cleanup.word_add_op", "word_added", "cleanup.word_add")
WORD_REMOVE = _op("cleanup.word_remove_op", "word_removed", "cleanup.word_remove")
_OPS = (WORD_ADD, WORD_REMOVE)


def _register_handlers() -> None:
    from sb.domain.operator_spine import Reply
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("cleanup.word_list")):
        return

    @handler("cleanup.word_list")
    async def word_list(req) -> Reply:
        try:
            words = await store.get_words(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — headless read
            words = []
        if not words:
            return Reply(SUCCESS, "No prohibited words configured.")
        return Reply(SUCCESS, "Prohibited words: " + ", ".join(
            f"`{w}`" for w in words[:50]))


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2 marker
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    from sb.spec.refs import is_registered, workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))
    _register_handlers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered, workflow as _workflow

    for name, fn in (("cleanup.word_add", _word_add),
                     ("cleanup.word_remove", _word_remove)):
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    register_ops()
