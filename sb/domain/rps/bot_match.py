"""RPS bot matches (band 6) — the shipped ``!rpsbot`` per-player match
loop, headless (oracle: menno420/superbot
``disbot/cogs/rps_tournament/_bot_matches.py``).

Shipped semantics carried verbatim where the cog held them:

* match state is IN-MEMORY per player (the cog's ``_bot_matches`` dict —
  a restart forfeits the match; no money is at stake, shipped bot matches
  are free play);
* one match per player at a time — a new ``!rpsbot`` REPLACES the
  player's running match (the shipped ``_bot_matches[player] = {...}``
  overwrite); the superseded view answers "The match is already over."
  via the match-id mismatch;
* per-round resolution is the shipped body: normalize the typed move,
  the bot throws ``random.choice(GAME_MODES[mode])``, ``determine_winner``
  scores it, first to ``best_of // 2 + 1`` ends the match.

DELIBERATE DEVIATION (the tournament port's ledgered posture,
sb/domain/rps/tournament.py): the match runs as a BUTTON view in the
invoking channel instead of a private match channel + no-prefix message
parsing — channel provisioning rides the resource-provision port.
Per-round stats ride the audited ``rps.bot_round`` op (the shipped
``update_player_stats`` site, one row per throw)."""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from sb.domain.rps import rules

__all__ = [
    "BotMatch",
    "record_bot_move",
    "reset_bot_matches_for_tests",
    "set_bot_rng_for_tests",
    "start_match",
    "bot_state_or_none",
]


@dataclass
class BotMatch:
    match_id: str
    guild_id: int
    user_id: int
    mode: str
    best_of: int
    wins: int = 0          # the player's round wins (shipped key "wins")
    bot_wins: int = 0      # shipped key "bot_wins"
    done: bool = False

    @property
    def needed(self) -> int:
        """Shipped: ``required_wins = (match["best_of"] // 2) + 1``."""
        return self.best_of // 2 + 1


_MATCHES: dict[tuple[int, int], BotMatch] = {}
_SEQ = itertools.count(1)
_rng: random.Random = random.Random()


def set_bot_rng_for_tests(rng: random.Random) -> None:
    global _rng
    _rng = rng


def reset_bot_matches_for_tests() -> None:
    global _SEQ
    _MATCHES.clear()
    _SEQ = itertools.count(1)


def bot_state_or_none(guild_id: int, user_id: int) -> BotMatch | None:
    return _MATCHES.get((int(guild_id), int(user_id)))


def start_match(guild_id: int, user_id: int, *, mode: str,
                best_of: int) -> BotMatch:
    """Seed one player's match (the shipped ``_bot_matches[player] =
    {...}`` write — replacing any running match, exactly the overwrite
    the cog shipped)."""
    match = BotMatch(match_id=f"b{next(_SEQ)}", guild_id=int(guild_id),
                     user_id=int(user_id), mode=str(mode),
                     best_of=int(best_of))
    _MATCHES[(match.guild_id, match.user_id)] = match
    return match


def record_bot_move(guild_id: int, user_id: int, match_id: str,
                raw_move: str) -> dict:
    """One button throw into the player's match — the shipped
    ``handle_bot_match_move`` body, pure in-memory. Returns a stage
    mapping the handler renders:

    ``{"stage": "over" | "invalid" | "round" | "match_won" |
       "match_lost", ...}``

    with ``move`` / ``bot_move`` / ``result`` ("win"|"loss"|"tie" — the
    shipped ``update_player_stats`` argument) on every played round.
    """
    match = _MATCHES.get((int(guild_id), int(user_id)))
    if match is None or match.match_id != str(match_id) or match.done:
        # the shipped already-over guard (a superseded/finished match)
        return {"stage": "over"}
    move = rules.normalize_move(str(raw_move).lower().strip(), match.mode)
    if move is None:
        return {"stage": "invalid", "match": match}
    bot_move = _rng.choice(rules.GAME_MODES[match.mode])
    winner = rules.determine_winner(move, bot_move, match.mode)
    if winner == 0:
        result = "tie"
    elif winner == 1:
        result = "win"
        match.wins += 1
    else:
        result = "loss"
        match.bot_wins += 1
    out = {"match": match, "move": move, "bot_move": bot_move,
           "result": result}
    if match.wins >= match.needed:
        match.done = True
        _MATCHES.pop((match.guild_id, match.user_id), None)
        return {"stage": "match_won", **out}
    if match.bot_wins >= match.needed:
        match.done = True
        _MATCHES.pop((match.guild_id, match.user_id), None)
        return {"stage": "match_lost", **out}
    return {"stage": "round", **out}
