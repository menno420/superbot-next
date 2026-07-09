"""Band-6 RankProviders — the game leaderboard categories registered into
the band-4 registry (the never-edit-a-consumer seam): mining / creatures
/ fishing / farm / gamexp / crafting with the shipped alias rows.
Deathmatch / RPS / counting register with their slice-3 stat stores."""

from __future__ import annotations

from sb.domain.community.rank_providers import (
    RankEntry,
    RankProvider,
    register_provider,
)

__all__ = ["register_game_providers"]


def _simple(rows_label):
    async def _member_rank(guild_id: int, user_id: int):
        return None, None
    return _member_rank


async def _mining_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.mining.store import mining_totals

    return [RankEntry(label=f"**<@{r['user_id']}>** — {r['total']} items",
                      name=f"<@{r['user_id']}>", score=float(r["total"]),
                      value_text=f"{r['total']:,} items")
            for r in await mining_totals(guild_id)]


async def _creatures_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.creature.store import top_catchers

    return [RankEntry(
        label=f"**<@{r['user_id']}>** — {r['species']} species "
              f"({r['total']} caught)",
        name=f"<@{r['user_id']}>", score=float(r["species"]),
        value_text=f"{r['species']} species")
        for r in await top_catchers(guild_id)]


async def _fishing_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.fishing.catalog import fish_names
    from sb.domain.fishing.store import top_fishers

    return [RankEntry(
        label=f"**<@{r['user_id']}>** — {r['total']} fish",
        name=f"<@{r['user_id']}>", score=float(r["total"]),
        value_text=f"{r['total']:,} fish")
        for r in await top_fishers(guild_id, fish_names())]


async def _farm_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.farm.store import top_farmers

    return [RankEntry(
        label=f"**<@{r['user_id']}>** — {r['chickens']} "
              f"{'hen' if r['chickens'] == 1 else 'hens'} "
              f"(coop Lv {r['coop_level']})",
        name=f"<@{r['user_id']}>", score=float(r["chickens"]),
        value_text=f"{r['chickens']} hens")
        for r in await top_farmers(guild_id)]


def _game_xp_top(game: str | None):
    async def _top(guild_id: int) -> list[RankEntry]:
        from sb.domain.games.store import top_game_xp

        return [RankEntry(
            label=f"**<@{r['user_id']}>** — {r['xp']:,} XP",
            name=f"<@{r['user_id']}>", score=float(r["xp"]),
            value_text=f"{r['xp']:,} XP")
            for r in await top_game_xp(guild_id, game=game)]
    return _top


def register_game_providers() -> None:
    register_provider(RankProvider(
        name="mining", display_title="⛏️ Mining Leaderboard",
        select_label="Mining", select_emoji="⛏️",
        empty_hint="No miners yet — try `!mine`!",
        top=_mining_top, member_rank=_simple("mining")),
        aliases=("minelb", "miningleaderboard"))
    register_provider(RankProvider(
        name="creatures", display_title="🐾 Creature Leaderboard",
        select_label="Creatures", select_emoji="🐾",
        empty_hint="No catchers yet — try `!catch`!",
        top=_creatures_top, member_rank=_simple("creatures")),
        aliases=("creature", "creaturelb"))
    register_provider(RankProvider(
        name="fishing", display_title="🎣 Fishing Leaderboard",
        select_label="Fishing", select_emoji="🎣",
        empty_hint="No anglers yet — try `!fish`!",
        top=_fishing_top, member_rank=_simple("fishing")),
        aliases=("fishlb", "fishingleaderboard", "anglerlb"))
    register_provider(RankProvider(
        name="farm", display_title="🐔 Farm Leaderboard",
        select_label="Farm", select_emoji="🐔",
        empty_hint="No farmers yet — try `!farm`!",
        top=_farm_top, member_rank=_simple("farm")),
        aliases=("farmlb", "farming", "chickenlb"))
    register_provider(RankProvider(
        name="gamexp", display_title="🌍 World Level Leaderboard",
        select_label="World Level", select_emoji="🌍",
        empty_hint="No game XP yet — play any game!",
        top=_game_xp_top(None), member_rank=_simple("gamexp")),
        aliases=("gxp", "gamelevel", "game_xp"))
    register_provider(RankProvider(
        name="crafting", display_title="🔨 Crafting Leaderboard",
        select_label="Crafting", select_emoji="🔨",
        empty_hint="No crafters yet.",
        top=_game_xp_top("crafting"), member_rank=_simple("crafting")),
        aliases=("crafting_top", "craftlb"))
