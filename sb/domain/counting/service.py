"""Counting handlers (band 6) — typed-command routes over the K7 lanes,
the read views (count_info / counttop / count_rules), the message-feed
core, and the CountingProvider.

* ``handle_message`` is the shipped on_message hot path headless (the
  band-4 ``xp.handle_chat_message`` precedent): the MESSAGE FEED that
  calls it arms with the message band / live adapter; the feed applies
  the returned decision (delete via the band-2 moderation auto-delete
  seam, reply, reaction).
* DEVIATION (D-0044): ``!start_match`` arms counting in the CURRENT
  channel (the shipped panel's Enable-Here lane) — the shipped
  auto-created ``<mode>-counting-<timestamp>`` channel rides the
  resource-provision port; ``!end_match`` removes the match row and
  KEEPS the channel until the teardown port arms.
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "Reply",
    "ensure_handler_refs",
    "handle_message",
    "register_provider_rows",
]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


# --- the message-feed core ---------------------------------------------------------


async def handle_message(*, guild_id: int, channel_id: int, user_id: int,
                         content: str, author_mention: str | None = None,
                         actor=None) -> dict | None:
    """One counting message through the audited lane. Returns the
    decision mapping for the feed (``None`` = channel not active /
    lane declined — the feed does nothing)."""
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    if actor is None:
        from sb.kernel.interaction.request import ActorRef

        actor = ActorRef(user_id=user_id, is_guild_operator=False,
                         is_bot_owner=False, is_dm=False)
    ctx = WorkflowContext(
        actor=actor, guild_id=guild_id,
        params={"channel_id": channel_id, "content": content,
                "author_mention": author_mention or f"<@{user_id}>"})
    result = await engine.run(WorkflowRef("counting.record_count"), ctx)
    if result.outcome != SUCCESS:
        return None
    after = next(iter((result.after or {}).values()), {})
    if not after.get("active"):
        return None
    return after


# --- provider (the shipped CountingProvider totals fold) ---------------------------


async def _counting_totals(guild_id: int) -> list[tuple[int, int]]:
    from sb.domain.counting import store

    state = await store.get_state(guild_id)
    totals: dict[int, int] = {}
    for ch_data in (state.get("channels") or {}).values():
        for uid_str, cnt in (ch_data.get("leaderboard") or {}).items():
            try:
                uid = int(uid_str)
            except (TypeError, ValueError):
                continue
            totals[uid] = totals.get(uid, 0) + int(cnt)
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)


_provider_registered = False


def register_provider_rows() -> None:
    """CountingProvider (alias countlb / counting_leaderboard) — the
    shipped rank_providers rows; idempotent."""
    global _provider_registered
    if _provider_registered:
        return
    from sb.domain.community.rank_providers import (
        RankEntry,
        RankProvider,
        register_provider as _register,
    )

    async def _top(guild_id: int) -> list[RankEntry]:
        totals = await _counting_totals(guild_id)
        return [RankEntry(
            label=f"**<@{uid}>** — {cnt} counts", name=f"<@{uid}>",
            score=float(cnt), value_text=f"{cnt:,} counts")
            for uid, cnt in totals[:10]]

    async def _member_rank(guild_id: int, user_id: int):
        totals = await _counting_totals(guild_id)
        for i, (uid, cnt) in enumerate(totals):
            if uid == user_id:
                return i + 1, f"{cnt:,} counts"
        return None, None

    _register(RankProvider(
        name="counting", display_title="🔢 Counting Leaderboard",
        select_label="Counting", select_emoji="🔢",
        empty_hint="No counting activity yet. Count in the counting "
                   "channel to appear here.",
        top=_top, member_rank=_member_rank),
        aliases=("countlb", "counting_leaderboard"))
    _provider_registered = True


# --- routes + views ---------------------------------------------------------------


def _target_channel(req) -> int:
    raw = req.args.get("channel_id")
    if raw:
        try:
            return int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    argv = tuple(req.args.get("argv", ()) or ())
    for token in argv:
        text = str(token).strip().strip("<#>")
        if text.isdigit():
            return int(text)
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


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("counting.start_match_route")):
        return

    @handler("counting.start_match_route")
    async def start_match_route(req) -> Reply:
        """!start_match <mode> [args] — arms counting HERE (the
        auto-created match channel rides the provisioning port)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = [str(a) for a in tuple(req.args.get("argv", ()) or ())]
        if not argv:
            from sb.domain.counting.ops import VALID_MODES

            return Reply(BLOCKED,
                         "Usage: `!start_match <mode> [args]` — modes: "
                         + ", ".join(VALID_MODES) + ".")
        mode = argv[0].lower()
        params: dict = {"channel_id": int(req.channel_id or 0),
                        "mode": mode}
        if mode == "multiples":
            if len(argv) < 2 or not argv[1].lstrip("-").isdigit():
                return Reply(BLOCKED,
                             "Please specify a multiple for "
                             "'multiples' mode.")
            params["multiple"] = int(argv[1])
        elif mode == "custom":
            raw = " ".join(argv[1:])
            try:
                seq = [int(n.strip()) for n in raw.split(",") if n.strip()]
            except ValueError:
                seq = []
            if not seq:
                return Reply(BLOCKED,
                             "Invalid sequence. Please provide a "
                             "comma-separated list of integers.")
            params["custom_sequence"] = seq
        elif mode == "skip" and len(argv) > 1:
            if not argv[1].isdigit() or int(argv[1]) < 1:
                return Reply(BLOCKED,
                             "Skip step must be a positive integer, "
                             "e.g. `!start_match skip 5`.")
            params["skip_step"] = int(argv[1])
        result = await engine.run(WorkflowRef("counting.enable_channel"),
                                  _ctx_from_req(req, params))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't start a match.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Match started.")
                     + " (Auto-created match channels arm with the "
                       "channel-provisioning port — this match runs "
                       "right here.)")

    @handler("counting.enable_here_route")
    async def enable_here_route(req) -> Reply:
        """The hub's Enable-Here selector — values[0] = a no-arg mode."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        values = tuple(req.args.get("values", ()) or ())
        mode = str(values[0]).lower() if values else ""
        result = await engine.run(
            WorkflowRef("counting.enable_channel"),
            _ctx_from_req(req, {"channel_id": int(req.channel_id or 0),
                                "mode": mode}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't start a match.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Match started."))

    handler("counting.end_match_route")(_run_op(
        "counting.disable_channel",
        lambda req: {"channel_id": _target_channel(req)}))
    handler("counting.reset_route")(_run_op(
        "counting.reset_count",
        lambda req: {"channel_id": _target_channel(req)}))
    handler("counting.toggle_turns_route")(_run_op(
        "counting.toggle_flag",
        lambda req: {"channel_id": _target_channel(req),
                     "flag": "taking_turns"}))
    handler("counting.toggle_reset_route")(_run_op(
        "counting.toggle_flag",
        lambda req: {"channel_id": _target_channel(req),
                     "flag": "reset_on_wrong_count"}))

    @handler("counting.set_skip_route")
    async def set_skip_route(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = [str(a) for a in tuple(req.args.get("argv", ()) or ())]
        step = None
        channel_id = int(req.channel_id or 0)
        for token in argv:
            text = token.strip()
            if text.strip("<#>").isdigit() and text.startswith("<#"):
                channel_id = int(text.strip("<#>"))
            elif text.isdigit():
                step = int(text)
        result = await engine.run(
            WorkflowRef("counting.set_skip_step"),
            _ctx_from_req(req, {"channel_id": channel_id, "step": step}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't set the step.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Done."))

    @handler("counting.info_view")
    async def info_view(req) -> Reply:
        """!count_info — the shipped embed fields as a text card."""
        from sb.domain.counting import game_logic, store

        gid = int(req.guild_id or 0)
        channel_id = _target_channel(req)
        state = await store.get_state(gid)
        data = (state.get("channels") or {}).get(str(channel_id))
        if data is None:
            return Reply(SUCCESS,
                         "Counting game is not set up for this channel.")
        mode = data.get("mode", "normal")
        lines = [f"🔢 **Counting — <#{channel_id}>**",
                 f"Mode: **{mode}**",
                 f"Current Count: **{data.get('current_count', 0)}**",
                 f"Taking Turns Mode: **{data.get('taking_turns', False)}**",
                 "Reset on Wrong Count: "
                 f"**{data.get('reset_on_wrong_count', False)}**"]
        if mode == "random":
            lines.append(f"Secret number is between: "
                         f"**{data.get('range_lo')}–{data.get('range_hi')}**")
        elif mode == "skip":
            lines.append(f"Skip step: **{data.get('step', 1)}**")
        elif data.get("step", 1) != 1:
            lines.append(f"Step: **{data.get('step', 1)}**")
        top = game_logic.top_counters(data.get("leaderboard") or {},
                                      limit=3)
        if top:
            lines.append("Top counters: " + ", ".join(
                f"<@{uid}> ({cnt})" for uid, cnt in top))
        return Reply(SUCCESS, "\n".join(lines))

    @handler("counting.top_view")
    async def top_view(req) -> Reply:
        """!counttop — this channel's ranked tally."""
        from sb.domain.counting import game_logic, store

        gid = int(req.guild_id or 0)
        channel_id = _target_channel(req)
        state = await store.get_state(gid)
        data = (state.get("channels") or {}).get(str(channel_id))
        if data is None:
            return Reply(SUCCESS,
                         "Counting game is not set up for this channel.")
        ranked = game_logic.top_counters(data.get("leaderboard") or {})
        if not ranked:
            return Reply(SUCCESS,
                         "No counts yet — be the first to count!")
        lines = [f"🔢 **Top counters — <#{channel_id}>**"] + [
            f"{i + 1}. <@{uid}> — {cnt} counts"
            for i, (uid, cnt) in enumerate(ranked)]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("counting.rules_view")
    async def rules_view(req) -> Reply:
        """!count_rules — the shipped rules embed as text (copy kept)."""
        return Reply(SUCCESS, "\n".join((
            "🔢 **Counting Rules**",
            "**1. Follow the Sequence** — post the next number in the "
            "active mode's sequence.",
            "**2. Taking Turns** — when enabled, you can't count twice "
            "in a row.",
            "**3. Mode-Specific Rules** — multiples/prime/custom modes "
            "only accept numbers that fit the mode.",
            "**4. Respect the Channel** — invalid messages are removed "
            "to keep the count readable.",
            "**5. Have Fun!**",
        )))


_register()


def ensure_handler_refs() -> None:
    _register()
