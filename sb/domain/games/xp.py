"""Game-XP core (band 6) — the shared cross-game progression track, ported
from the shipped ``services/game_xp_service.py`` (§7.4).

Chat XP keeps driving the auto-role tiers untouched (band 4); game XP is a
separate, guild-scoped track shared by ALL game subsystems — prestige +
leaderboard, never content gates. One central award policy (XP ≈
effort/risk; money moves award nothing), one soft cap, and the SHARED level
derives from SUM(xp) through the ONE chat-XP curve
(``sb.domain.xp.levels`` — no second formula, no stored level column).

Transaction contract (shipped Q-0071, kept): :func:`award_in_txn` takes the
owning K7 leg's open conn so the XP write commits atomically with the
action that earned it; the events emit AFTER commit via the op's
EventEmitSpecs (game_xp.awarded always, game_xp.level_up only on a
boundary — the D-0036 conditional-emission rider).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sb.domain.games import store
from sb.domain.xp.levels import level_progress

__all__ = [
    "AWARDS",
    "CAPPED_RATE",
    "DAILY_SOFT_CAP",
    "EVT_GAME_XP_AWARDED",
    "EVT_GAME_LEVEL_UP",
    "GAME_CRAFTING",
    "GAME_CREATURE",
    "GAME_FARM",
    "GAME_FISHING",
    "GAME_LABELS",
    "GAME_MINING",
    "GameXpAward",
    "award_in_txn",
    "game_display",
    "shared_level",
]

# Event names — shipped verbatim (core/events_catalogue KNOWN_EVENTS).
EVT_GAME_XP_AWARDED = "game_xp.awarded"
EVT_GAME_LEVEL_UP = "game_xp.level_up"

# Game identifiers (the `game` column) — shipped verbatim. New games add a
# constant and call award_in_txn(); no schema or service change.
GAME_MINING = "mining"
GAME_CRAFTING = "crafting"
GAME_FISHING = "fishing"
GAME_CREATURE = "creature"
GAME_FARM = "farm"

#: (emoji, label) per game key — the world card / leaderboard display map,
#: shipped verbatim; unknown keys fall back to a titled key.
GAME_LABELS: dict[str, tuple[str, str]] = {
    GAME_MINING: ("⛏️", "Mining"),
    GAME_CRAFTING: ("🔨", "Crafting"),
    GAME_FISHING: ("🎣", "Fishing"),
    GAME_CREATURE: ("🐾", "Creatures"),
    GAME_FARM: ("🐔", "Farm"),
}


def game_display(game: str) -> tuple[str, str]:
    """``(emoji, label)`` for a game key — falls back to a titled key."""
    return GAME_LABELS.get(game, ("🎮", game.replace("_", " ").title()))


#: Per-game, per-UTC-day full-rate budget; beyond it awards scale by
#: CAPPED_RATE (floor 1 — soft, never zero). Shipped constants verbatim.
DAILY_SOFT_CAP = 400
CAPPED_RATE = 0.25

#: The central award table — action → base XP; depth-scaled actions add
#: the player's current band. Shipped verbatim (sell/buy award NOTHING).
AWARDS: dict[str, int] = {
    "mine": 3,
    "harvest": 2,
    "explore": 4,
    "fish": 5,
    "collect_eggs": 3,
    "catch": 4,
    "battle_win": 6,
    "depth_record": 25,
    "craft": 8,
    "quick_craft": 8,
    "repair": 3,
}
DEPTH_SCALED = frozenset({"mine", "explore"})


@dataclass(frozen=True)
class GameXpAward:
    """Result of one award — everything the emit builders need."""

    game: str
    action: str
    amount: int          # post-cap amount actually written (0 = no write)
    new_game_xp: int
    new_total_xp: int
    new_level: int
    leveled_up: bool


def base_amount(action: str, *, depth: int = 0) -> int:
    amount = AWARDS.get(action, 0)
    if action in DEPTH_SCALED:
        amount += max(0, depth)
    return amount


def apply_soft_cap(amount: int, day_xp_so_far: int) -> int:
    """The shipped per-game daily soft cap: full rate up to the budget,
    then CAPPED_RATE with floor 1 — soft, never zero."""
    if amount <= 0:
        return 0
    if day_xp_so_far >= DAILY_SOFT_CAP:
        return max(1, int(amount * CAPPED_RATE))
    return amount


def _day_of(now: int) -> str:
    return dt.datetime.fromtimestamp(now, tz=dt.timezone.utc).date().isoformat()


async def award_in_txn(conn, *, user_id: int, guild_id: int, game: str,
                       action: str, now: int, depth: int = 0,
                       ) -> GameXpAward:
    """Grant XP for *action* under *game* inside the caller's txn.

    Unknown actions (and money moves) award nothing. Returns the award
    carrying leveled_up so the op's level_up payload builder can emit
    conditionally (None on a non-boundary)."""
    amount = base_amount(action, depth=depth)
    if amount <= 0:
        total = await store.total_game_xp(user_id, guild_id, conn=conn)
        level, _, _ = level_progress(total)
        return GameXpAward(game, action, 0, 0, total, level, False)
    day = _day_of(now)
    prior_total = await store.total_game_xp(user_id, guild_id, conn=conn)
    prior_level, _, _ = level_progress(prior_total)
    day_so_far = await store.day_xp_for(user_id, guild_id, game, day,
                                        conn=conn)
    amount = apply_soft_cap(amount, day_so_far)
    new_game_xp = await store.add_game_xp(
        conn, user_id=user_id, guild_id=guild_id, game=game, amount=amount,
        day=day, day_xp_add=amount, now=now)
    new_total = prior_total + amount
    new_level, _, _ = level_progress(new_total)
    return GameXpAward(game, action, amount, new_game_xp, new_total,
                       new_level, new_level > prior_level)


async def shared_level(user_id: int, guild_id: int) -> tuple[int, int]:
    """(level, total_xp) — the derived shared world level."""
    total = await store.total_game_xp(user_id, guild_id)
    level, _, _ = level_progress(total)
    return level, total
