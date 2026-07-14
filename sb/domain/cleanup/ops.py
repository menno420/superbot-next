"""Cleanup word-filter K7 lane (band 2): add/remove are NATURAL_KEY DB ops
through the sole-writer store; list is a read handler. The anti-evasion
strict flag (migration 0053) writes on its own audited op — the shipped
`prohibited_words_service.set_wordfilter_strict` audit posture
(mutation_type "wordfilter_strict") as the op's audit_verb."""

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
        # the shipped signature was greedy (`*, word: str`) — every
        # remaining token joins into one word phrase.
        argv = tuple(ctx.params.get("argv", ()) or ())
        word = " ".join(str(t) for t in argv).strip()
    if not word:
        # ValidatorError ⇒ polite user_error denial with a usage hint,
        # never a BUG envelope (the band-2 parse_target_and_reason lesson).
        from sb.kernel.interaction.errors import ValidatorError

        raise ValidatorError("word", "no word supplied")
    return word.lower().strip()


@workflow("cleanup.word_add")
async def _word_add(conn, ctx: WorkflowContext) -> LegOutcome:
    word = _word_from(ctx)
    added = await store.add_word(conn, guild_id=int(ctx.guild_id or 0), word=word)
    # the shipped copy verbatim (disbot/cogs/cleanup_cog.py word_add;
    # goldens/cleanup/sweep_word_add.json pins the added branch byte-
    # for-byte — the earlier "answered with SILENCE" note observed a
    # different surface; the golden is the oracle record, #193 law)
    # through the sanctioned DB-leg `user_message` channel.
    copy = (f"Added '{word}' to the prohibited words list." if added
            else f"The word '{word}' is already in the prohibited list.")
    return LegOutcome(step=StepResult(0, "word_add", True),
                      before={}, after={"word": word, "added": added},
                      user_message=copy)


@workflow("cleanup.word_remove")
async def _word_remove(conn, ctx: WorkflowContext) -> LegOutcome:
    word = _word_from(ctx)
    removed = await store.remove_word(conn, guild_id=int(ctx.guild_id or 0),
                                      word=word)
    # shipped copy verbatim (cleanup_cog.py word_remove; goldens/cleanup/
    # sweep_word_remove.json pins the not-present branch).
    copy = (f"Removed '{word}' from the prohibited words list." if removed
            else f"The word '{word}' is not in the prohibited list.")
    return LegOutcome(step=StepResult(0, "word_remove", True),
                      before={"present": removed}, after={"word": word},
                      user_message=copy)


@workflow("cleanup.wordfilter_strict")
async def _wordfilter_strict(conn, ctx: WorkflowContext) -> LegOutcome:
    """The shipped set_wordfilter_strict upsert as one DB leg — the
    in-transaction prior read backs the audit's prev_value (the shipped
    service emitted prev=str(not strict); the real prior is stricter)."""
    strict = bool(ctx.params.get("strict"))
    guild_id = int(ctx.guild_id or 0)
    prior = await store.get_wordfilter_strict(guild_id, conn=conn)
    await store.set_wordfilter_strict(conn, guild_id=guild_id, strict=strict)
    return LegOutcome(step=StepResult(0, "wordfilter_strict", True),
                      before={"strict": prior}, after={"strict": strict})


def _op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="cleanup", lane=WorkflowLane.DOMAIN,
        authority_ref="",
        legs=(LegSpec("write", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


WORD_ADD = _op("cleanup.word_add_op", "word_added", "cleanup.word_add")
WORD_REMOVE = _op("cleanup.word_remove_op", "word_removed", "cleanup.word_remove")
WORDFILTER_STRICT = _op("cleanup.wordfilter_strict_op", "wordfilter_strict",
                        "cleanup.wordfilter_strict")
_OPS = (WORD_ADD, WORD_REMOVE, WORDFILTER_STRICT)


def _register_handlers() -> None:
    from sb.domain.operator_spine import Reply
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("cleanup.word_list")):
        return

    @handler("cleanup.word_list")
    async def word_list(req) -> Reply:
        """``!word`` / ``!word list`` — the shipped render verbatim
        (cleanup_cog.py word_cmd/word_list: the per-guild `_word_cache`
        read, load-on-miss; goldens/cleanup/sweep_word pins the empty
        copy, sweep_word_list the sorted backtick listing over the
        CACHE — see sb/domain/cleanup/service.py's cache contract)."""
        from sb.domain.cleanup import service

        try:
            words = await service.get_words_cached(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — headless read
            words = []
        if not words:
            return Reply(SUCCESS, "No prohibited words are currently set.")
        return Reply(SUCCESS, "Prohibited words: " + ", ".join(
            f"`{w}`" for w in sorted(words)))


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2 marker
        from sb.domain.cleanup import service
        from sb.kernel.workflow import engine

        result = await engine.run(op, ctx)
        # the shipped post-mutation cache refresh (cleanup_cog.py
        # reloaded `_word_cache` after add/remove) — invalidate-only,
        # AFTER the engine settles the txn (post-commit, so an aborted
        # leg never poisons the cache; the next read reloads).
        service.invalidate_word_cache(int(ctx.guild_id or 0))
        return result
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
                     ("cleanup.word_remove", _word_remove),
                     ("cleanup.wordfilter_strict", _wordfilter_strict)):
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    register_ops()
