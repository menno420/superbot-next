"""Deathmatch handlers (band 6) — the challenge route, the stats/help
views, and the DeathmatchProvider (aliases dm_leaderboard / dm_lb /
board — the shipped rank_providers rows)."""

from __future__ import annotations

import re

from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs", "register_provider_rows"]


def register_provider_rows() -> None:
    """Deathmatch + rps rank rows; idempotent by REGISTRY truth, not a
    module latch (a latch strands the rows after a
    reset_providers_for_tests() wipe on the cached module — the #141
    re-arm doctrine)."""
    from sb.domain.community.rank_providers import (
        RankEntry,
        RankProvider,
        get_provider,
        register_provider as _register,
    )

    if (get_provider("deathmatch") is not None
            and get_provider("rps") is not None):
        return

    async def _dm_top(guild_id: int) -> list[RankEntry]:
        from sb.domain.deathmatch import store

        rows = await store.leaderboard(guild_id)
        return [RankEntry(
            label=f"**<@{r['user_id']}>** — {r['wins']}W / "
                  f"{r['losses']}L",
            name=f"<@{r['user_id']}>", score=float(r["wins"]),
            value_text=f"{r['wins']}W / {r['losses']}L")
            for r in rows[:10]]

    async def _dm_member_rank(guild_id: int, user_id: int):
        from sb.domain.deathmatch import store

        rows = await store.leaderboard(guild_id)
        for i, row in enumerate(rows):
            if int(row["user_id"]) == user_id:
                return i + 1, f"{row['wins']}W / {row['losses']}L"
        return None, None

    _register(RankProvider(
        name="deathmatch", display_title="⚔️ Deathmatch Leaderboard",
        select_label="Deathmatch", select_emoji="⚔️",
        empty_hint="No deathmatch results yet. Start a match with "
                   "`!deathmatch` to appear here.",
        top=_dm_top, member_rank=_dm_member_rank, card_theme="ember"),
        aliases=("dm_leaderboard", "dm_lb", "board"))

    async def _rps_top(guild_id: int) -> list[RankEntry]:
        from sb.domain.rps import stats

        rows = await stats.leaderboard(guild_id)
        return [RankEntry(
            label=f"**{r['name']}** — {r['wins']}W / {r['losses']}L / "
                  f"{r['ties']}T",
            name=str(r["name"]), score=float(r["wins"]),
            value_text=f"{r['wins']}W / {r['losses']}L / {r['ties']}T")
            for r in rows[:10]]

    async def _rps_member_rank(guild_id: int, user_id: int):
        from sb.domain.rps import stats

        rows = await stats.leaderboard(guild_id)
        for i, row in enumerate(rows):
            if int(row.get("user_id") or 0) == user_id:
                return (i + 1,
                        f"{row['wins']}W / {row['losses']}L / "
                        f"{row['ties']}T")
        return None, None

    _register(RankProvider(
        name="rps", display_title="✂️ RPS Leaderboard",
        select_label="RPS", select_emoji="✂️",
        empty_hint="No RPS games played yet. Challenge someone with "
                   "`!rps` to appear here.",
        top=_rps_top, member_rank=_rps_member_rank),
        aliases=("rpslb",))


def _target_from_args(req) -> int:
    raw = req.args.get("target_id")
    if raw:
        try:
            return int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    for token in tuple(req.args.get("argv", ()) or ()):
        match = re.fullmatch(r"<@!?(\d+)>|(\d{15,21})", str(token).strip())
        if match:
            return int(match.group(1) or match.group(2))
    return 0


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("deathmatch.challenge_route")):
        return

    @handler("deathmatch.challenge_route")
    async def challenge_route(req) -> Reply:
        """!deathmatch @user — the audited challenge guard, then the
        shipped ``_ChallengeView`` as the session-lifecycle challenge
        card (embed + ✅ Accept / ❌ Decline on run-minted ids —
        sweep_dm_challenge pins the wire bytes). Challenger/target ride
        the card's binding args: the pre-accept challenge is process
        memory, never a row (the ops-module D-0042-review note)."""
        import dataclasses

        from sb.domain.deathmatch.panels import CHALLENGE_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.kernel.workflow import engine
        from sb.spec.refs import PanelRef, WorkflowRef

        target = _target_from_args(req)
        result = await engine.run(
            WorkflowRef("deathmatch.challenge"),
            _ctx_from_req(req, {"channel_id": int(req.channel_id or 0),
                                "target_id": target}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't open the duel.")
        after = next(iter((result.after or {}).values()), {})
        card_req = dataclasses.replace(req, args={
            **dict(req.args), "stage": "challenge",
            "challenger": int(after.get("challenger") or 0),
            "target": int(after.get("target") or 0),
            "channel_id": int(req.channel_id or 0)})
        await open_panel(PanelRef(CHALLENGE_PANEL_ID), card_req)
        return Reply(SUCCESS, None)

    @handler("deathmatch.challenge_click")
    async def challenge_click(req) -> Reply:
        """✅ Accept / ❌ Decline on the challenge card (session-lifecycle
        binding → resolve() → here): run the audited op with the OPEN
        args (challenger/target ride the in-memory binding — the shipped
        ``_ChallengeView`` analog), then edit the card in place. Accept
        swaps the card onto the duel stage (g1 Attack/Defend over the
        row the op just minted); decline disables the controls and tears
        the session down (the shipped ``view.stop()``)."""
        from sb.domain.games.session import EXPIRED_MESSAGE
        from sb.kernel.panels.engine import refresh_session_view
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        action = str(req.args.get("session_action") or "")
        op_key = {"dm_accept": "deathmatch.accept",
                  "dm_decline": "deathmatch.decline"}.get(action)
        if op_key is None:
            return Reply(BLOCKED, EXPIRED_MESSAGE)
        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(req.args)))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message
                         or "Couldn't answer the challenge.")
        after = next(iter((result.after or {}).values()), {})
        if action == "dm_decline":
            params = {"stage": "declined",
                      "message": after.get("message", "")}
            expire = True
        else:
            params = {"stage": "match",
                      "session_id": str(after.get("session_id") or ""),
                      "message": after.get("message", "")}
            expire = False
        message = getattr(req.origin, "message", None)
        message_key = str(getattr(message, "id", "") or "")
        refreshed = await refresh_session_view(
            req, message_key=message_key, params=params, expire=expire)
        if not refreshed:
            # session evicted/restarted mid-answer: the duel row (on an
            # accept) is still authoritative — degrade to the text line.
            return Reply(SUCCESS, after.get("message") or None)
        return Reply(SUCCESS, None)

    @handler("deathmatch.stats_view")
    async def stats_view(req) -> Reply:
        from sb.domain.deathmatch import store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        stats = await store.get_stats(uid, int(req.guild_id or 0))
        total = stats["wins"] + stats["losses"]
        if not total:
            return Reply(SUCCESS,
                         "⚔️ No duels yet — challenge someone with "
                         "`!deathmatch @user`!")
        return Reply(SUCCESS,
                     f"⚔️ **Your deathmatch record** — "
                     f"{stats['wins']}W / {stats['losses']}L "
                     f"({total} duel(s)).")

    @handler("deathmatch.top_view")
    async def top_view(req) -> Reply:
        from sb.domain.deathmatch import store

        rows = await store.leaderboard(int(req.guild_id or 0))
        if not rows:
            return Reply(SUCCESS,
                         "⚔️ No deathmatch results yet. Start a match "
                         "with `!deathmatch`!")
        lines = ["⚔️ **Deathmatch Leaderboard**"] + [
            f"{i + 1}. <@{r['user_id']}> — {r['wins']}W / {r['losses']}L"
            for i, r in enumerate(rows[:10])]
        return Reply(SUCCESS, "\n".join(lines))

    @handler("deathmatch.help_view")
    async def help_view(req) -> Reply:
        """!dm_help — the shipped blue help embed (sweep_dm_help pins
        it), rendered by the pure grammar off the help-card spec."""
        from sb.domain.deathmatch.panels import HELP_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(HELP_PANEL_ID), req)
        return Reply(SUCCESS, None)


_register()


def ensure_handler_refs() -> None:
    _register()
