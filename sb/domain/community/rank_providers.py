"""Provider registry for !rank and !leaderboard — the shipped PR-G
registry (services/rank_providers.py) headless: providers take a
guild_id (labels render mentions; display-name resolution is the live
adapter's presentation concern, deviation ledgered).

Band 4 registers the xp / coins / karma providers. Game categories
(mining, deathmatch, rps, counting, farm, fishing, creatures, …) register
HERE at band 6 with their shipped aliases — adding a category means
registering a provider, never editing a consumer (shipped invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

__all__ = [
    "RankEntry",
    "RankProvider",
    "get_provider",
    "provider_names",
    "register_provider",
    "reset_providers_for_tests",
]


@dataclass(frozen=True)
class RankEntry:
    """One row in a ranked top-N response (shipped shape: label is the
    fully-rendered line; name/score/value_text are the structured card
    projection, optional)."""

    label: str
    name: str | None = None
    score: float | None = None
    value_text: str | None = None


@dataclass(frozen=True)
class RankProvider:
    """One leaderboard category (the shipped ABC as frozen data + two
    async callables — headless, guild_id-keyed)."""

    name: str
    display_title: str
    select_label: str
    select_emoji: str | None
    empty_hint: str
    top: Callable[[int], Awaitable[list[RankEntry]]]
    member_rank: Callable[[int, int], Awaitable[tuple[int | None, str | None]]]
    card_theme: str = "midnight"


_PROVIDERS: dict[str, RankProvider] = {}
_ALIASES: dict[str, str] = {}

#: the shipped category order (services/rank_providers.py `_PROVIDERS` —
#: one file, class-definition order; parity/goldens/leaderboard/
#: sweep_leaderboard.json pins the selector rows in exactly this order).
#: The new architecture registers providers from three lanes (band-4
#: builtins here, the games band, the per-game slice-3 stores), so dict
#: insertion order is import-order noise — provider_names() orders by the
#: SHIPPED canon instead; categories the canon never knew append in
#: registration order (visible, never shed).
_SHIPPED_ORDER: tuple[str, ...] = (
    "xp", "coins", "mining", "creatures", "fishing", "farm", "gamexp",
    "crafting", "deathmatch", "rps", "counting", "karma",
)


def register_provider(provider: RankProvider,
                      aliases: tuple[str, ...] = ()) -> RankProvider:
    _PROVIDERS[provider.name] = provider
    for alias in aliases:
        _ALIASES[alias.lower()] = provider.name
    return provider


def provider_names() -> list[str]:
    """Canonical provider names in the SHIPPED order (unknown-to-the-canon
    categories follow, in registration order)."""
    shipped = [n for n in _SHIPPED_ORDER if n in _PROVIDERS]
    return shipped + [n for n in _PROVIDERS if n not in _SHIPPED_ORDER]


def get_provider(key: str | None) -> RankProvider | None:
    if not key:
        return None
    key = key.strip().lower()
    key = _ALIASES.get(key, key)
    return _PROVIDERS.get(key)


# --- the band-4 built-ins ---------------------------------------------------------------

async def _xp_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.xp import store

    rows = await store.top_xp(guild_id, 10)
    return [RankEntry(
        label=f"**<@{r['user_id']}>** — Level {r['level']} ({r['xp']} XP)",
        name=f"<@{r['user_id']}>", score=float(r["xp"]),
        value_text=f"{r['xp']:,} XP") for r in rows]


async def _xp_member_rank(guild_id: int,
                          user_id: int) -> tuple[int | None, str | None]:
    from sb.domain.xp import store

    for i, row in enumerate(await store.all_xp_ordered(guild_id)):
        if int(row["user_id"]) == user_id:
            return i + 1, f"Level {row['level']} ({row['xp']} XP)"
    return None, None


async def _coins_top(guild_id: int) -> list[RankEntry]:
    from sb.kernel.db.pool import fetchall

    rows = await fetchall(
        "SELECT user_id, coins FROM economy_balances WHERE guild_id=$1 "
        "ORDER BY coins DESC LIMIT 10", (guild_id,))
    return [RankEntry(
        label=f"**<@{r['user_id']}>** — {r['coins']} 🪙",
        name=f"<@{r['user_id']}>", score=float(r["coins"]),
        value_text=f"{r['coins']:,} 🪙") for r in rows]


async def _coins_member_rank(guild_id: int,
                             user_id: int) -> tuple[int | None, str | None]:
    from sb.kernel.db.pool import fetchall

    rows = await fetchall(
        "SELECT user_id, coins FROM economy_balances WHERE guild_id=$1 "
        "ORDER BY coins DESC", (guild_id,))
    for i, row in enumerate(rows):
        if int(row["user_id"]) == user_id:
            return i + 1, f"{row['coins']} 🪙"
    return None, None


async def _karma_top(guild_id: int) -> list[RankEntry]:
    from sb.domain.karma import store

    rows = await store.top_karma(guild_id, 10)
    return [RankEntry(
        label=f"**<@{r['user_id']}>** — {r['karma_points']} ✨",
        name=f"<@{r['user_id']}>", score=float(r["karma_points"]),
        value_text=f"{r['karma_points']:,} ✨") for r in rows]


async def _karma_member_rank(guild_id: int,
                             user_id: int) -> tuple[int | None, str | None]:
    from sb.domain.karma import store

    row = await store.get_karma(user_id, guild_id)
    points = int(row.get("karma_points", 0) or 0)
    if points <= 0:
        return None, None
    rank = await store.karma_rank(user_id, guild_id)
    return rank, f"{points} ✨"


def _register_builtins() -> None:
    register_provider(RankProvider(
        name="xp", display_title="🏆 XP Leaderboard", select_label="XP",
        select_emoji="🏆",
        empty_hint="No XP earned yet. Chat in this server to start "
                   "ranking up.",
        top=_xp_top, member_rank=_xp_member_rank),
        aliases=("lb", "rankings"))
    register_provider(RankProvider(
        name="coins", display_title="🪙 Coin Leaderboard",
        select_label="Coins", select_emoji="🪙",
        empty_hint="No coin totals yet. Use `!daily` once per day or "
                   "`!work` to start earning.",
        top=_coins_top, member_rank=_coins_member_rank))
    register_provider(RankProvider(
        name="karma", display_title="✨ Karma Leaderboard",
        select_label="Karma", select_emoji="✨",
        empty_hint="No karma yet. Thank a helpful member with "
                   "`!thanks @user`.",
        top=_karma_top, member_rank=_karma_member_rank),
        aliases=("rep", "reputation", "karmalb"))   # shipped ALIASES rows


_register_builtins()


def reset_providers_for_tests() -> None:
    _PROVIDERS.clear()
    _ALIASES.clear()
    _register_builtins()
