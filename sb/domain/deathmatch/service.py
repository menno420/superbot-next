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
        """!deathmatch @user — the pending challenge + g1 components."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        target = _target_from_args(req)
        result = await engine.run(
            WorkflowRef("deathmatch.challenge"),
            _ctx_from_req(req, {"channel_id": int(req.channel_id or 0),
                                "target_id": target}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Couldn't open the duel.")
        after = next(iter((result.after or {}).values()), {})
        return Reply(SUCCESS, after.get("message", "Challenge sent."))

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
        """!dm_help — the shipped help copy."""
        return Reply(SUCCESS, "\n".join((
            "⚔️ **Deathmatch Help**",
            "**Commands:**",
            "`!deathmatch @User` — Challenge a user to a duel.",
            "`!leaderboard deathmatch` — View the top duelists.",
            "",
            "**During a Duel:**",
            "Use the **⚔️ Attack** and **🛡️ Defend** buttons in the "
            "duel message.",
        )))


_register()


def ensure_handler_refs() -> None:
    _register()
