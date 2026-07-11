"""Chain handlers (band 6) — typed routes over the K7 lanes, the list
view, and the message-feed core.

``handle_message`` is the shipped ChainStage rule headless (order-20
auto-mod tier): the MESSAGE FEED calls it per non-command message; a
violation decision means the feed deletes via the band-2 moderation
auto-delete seam (rule="chain.violation") and posts the ~5s warning;
an allowed message already had its chain_count advanced through the
audited lane before the decision returns."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs", "handle_message"]


# --- the message-feed core ---------------------------------------------------------


async def handle_message(*, guild_id: int, channel_id: int, user_id: int,
                         content: str, author_mention: str | None = None,
                         actor=None):
    """One message through the chain rule. Returns a ChainDecision, or
    ``None`` when the channel has no chain row (feed does nothing).
    Command messages must be pre-filtered by the feed (shipped
    ``ctx.valid`` check — the feed owns command detection)."""
    from sb.domain.chain import engine as chain_engine
    from sb.domain.chain import store

    row = await store.get_chain_channel(channel_id)
    if not row:
        return None
    decision = chain_engine.check_message(
        content=content,
        author_mention=author_mention or f"<@{user_id}>",
        word=row.get("word"), word_limit=row.get("word_limit"))
    if decision.record_progress:
        from sb.kernel.interaction.request import ActorRef
        from sb.kernel.workflow import engine
        from sb.kernel.workflow.context import WorkflowContext
        from sb.spec.refs import WorkflowRef

        if actor is None:
            actor = ActorRef(user_id=user_id, is_guild_operator=False,
                             is_bot_owner=False, is_dm=False)
        await engine.run(
            WorkflowRef("chain.record_progress"),
            WorkflowContext(actor=actor, guild_id=guild_id,
                            params={"channel_id": channel_id}))
    return decision


# --- routes + views ---------------------------------------------------------------


def _split_channel_and_rest(req) -> tuple[int, list[str]]:
    """Leading ``<#channel>`` mention/ID → target channel; rest = args
    (shipped: blank/omitted channel = the current one)."""
    argv = [str(a) for a in tuple(req.args.get("argv", ()) or ())]
    channel_id = int(req.channel_id or 0)
    rest = argv
    if argv:
        head = argv[0].strip()
        stripped = head.strip("<#>")
        if stripped.isdigit() and (head.startswith("<#") or
                                   head.isdigit()):
            channel_id = int(stripped)
            rest = argv[1:]
    return channel_id, rest


def _modal_channel(req) -> int:
    """Modal 'Channel (mention/ID, blank = current)' field."""
    raw = str(req.args.get("channel") or "").strip()
    stripped = raw.strip("<#>")
    if stripped.isdigit():
        return int(stripped)
    return int(req.channel_id or 0)


def _run_op(ref: str, params_fn):
    async def route(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef(ref),
                                  _ctx_from_req(req, params_fn(req)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't do that.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Done."))
    return route


def _int_or_none(raw) -> int | None:
    text = str(raw or "").strip()
    if text.lstrip("-").isdigit():
        return int(text)
    return None


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("chain.usage_view")):
        return

    @handler("chain.usage_view")
    async def usage_view(req) -> Reply:
        """Bare !chain — the shipped subcommand hint verbatim."""
        return Reply(SUCCESS,
                     "❓ Please specify a subcommand. Use `!chain "
                     "create`, `!chain delete`, `!chain setlimit`, "
                     "`!chain removelimit`, or `!chain list`.")

    @handler("chain.create_route")
    async def create_route(req) -> Reply:
        """!chain create [#channel] <word> (modal: channel + word)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        if req.args.get("word") is not None:      # modal submit
            channel_id = _modal_channel(req)
            word = str(req.args.get("word") or "")
        else:
            channel_id, rest = _split_channel_and_rest(req)
            word = " ".join(rest)
        if not word.strip():
            # the shipped missing-word guard verbatim (chain_cog.create;
            # goldens/chain/sweep_chain_create pins the bytes).
            return Reply(BLOCKED,
                         "❌ Please specify the word to enforce in the "
                         "chain.\n**Usage:** `!chain create [channel] "
                         "<word>`")
        result = await engine.run(
            WorkflowRef("chain.create"),
            _ctx_from_req(req, {"channel_id": channel_id, "word": word}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't create the "
                                                "chain.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Chain created."))

    @handler("chain.delete_route")
    async def delete_route(req) -> Reply:
        """!chain delete [#channel] (modal: channel)."""
        from sb.domain.chain import store

        channel_id = (_modal_channel(req)
                      if req.args.get("channel") is not None
                      else _split_channel_and_rest(req)[0])
        if await store.get_chain_channel(channel_id) is None:
            # the shipped not-applied branch verbatim (chain_cog.delete;
            # goldens/chain/sweep_chain_delete pins the bytes).
            return Reply(BLOCKED,
                         f"❌ No active chain found in <#{channel_id}>.")
        return await _run_op(
            "chain.delete",
            lambda r: {"channel_id": channel_id})(req)

    @handler("chain.setlimit_route")
    async def setlimit_route(req) -> Reply:
        """!chain setlimit [#channel] <n> (modal: channel + limit;
        0 removes the limit)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        if req.args.get("limit") is not None:     # modal submit
            channel_id = _modal_channel(req)
            limit = _int_or_none(req.args.get("limit"))
        else:
            channel_id, rest = _split_channel_and_rest(req)
            limit = _int_or_none(rest[0]) if rest else None
        if limit is None or limit <= 0:
            # the shipped guard verbatim (chain_cog.setlimit: rejects
            # missing AND <= 0 — removal is !chain removelimit's job;
            # goldens/chain/sweep_chain_setlimit pins the bytes).
            return Reply(BLOCKED,
                         "❌ Please specify a valid word limit greater "
                         "than 0.\n**Usage:** `!chain setlimit [channel] "
                         "<number>`")
        result = await engine.run(
            WorkflowRef("chain.set_limit"),
            _ctx_from_req(req, {"channel_id": channel_id,
                                "limit": limit}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't set the limit.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Done."))

    @handler("chain.removelimit_route")
    async def removelimit_route(req) -> Reply:
        """!chain removelimit [#channel] (modal: channel)."""
        from sb.domain.chain import store

        channel_id = (_modal_channel(req)
                      if req.args.get("channel") is not None
                      else _split_channel_and_rest(req)[0])
        row = await store.get_chain_channel(channel_id)
        if row is None or not row.get("word_limit"):
            # the shipped not_found / no_change branch verbatim
            # (chain_cog.removelimit — "nothing was set, matching legacy
            # copy"; goldens/chain/sweep_chain_removelimit pins the bytes).
            return Reply(SUCCESS,
                         f"ℹ️ No word limit is set in <#{channel_id}>.")
        return await _run_op(
            "chain.set_limit",
            lambda r: {"channel_id": channel_id, "limit": 0})(req)

    @handler("chain.list_view")
    async def list_view(req) -> Reply:
        """!chain list — every chain/limit row in the guild."""
        from sb.domain.chain import store

        rows = await store.get_all_chain_channels(int(req.guild_id or 0))
        if not rows:
            # the shipped empty-list byte (chain_cog.list_chains;
            # goldens/chain/sweep_chain_list pins it).
            return Reply(SUCCESS,
                         "ℹ️ There are no active chains or word limits "
                         "in this server.")
        # UNDER-PORT NOTE (no golden pins this branch): the shipped
        # non-empty list is an EMBED ("Active Chains and Word Limits",
        # green, one field per channel — name=channel.name, value
        # "Allowed Word: `w`\n" / "Word Limit: `n` words\n" / "No
        # restrictions set."); Reply carries text only, so the embed
        # shape lands with a result-card slice.
        lines = ["🔗 **Chains in this server**"]
        for row in rows:
            bits = []
            if row.get("word"):
                bits.append(f"word `{row['word']}`")
            if row.get("word_limit"):
                bits.append(f"limit {row['word_limit']}")
            bits.append(f"count {row.get('chain_count', 0)}")
            lines.append(f"• <#{row['channel_id']}> — " + ", ".join(bits))
        return Reply(SUCCESS, "\n".join(lines))


_register()


def ensure_handler_refs() -> None:
    _register()
