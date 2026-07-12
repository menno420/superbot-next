"""The poker GAME registry (band 6 play-layer port) — the SHIPPED in-hand
half of ``disbot/views/casino/poker_table.py``: one live :class:`PokerGame`
per channel, process-memory keyed by ``channel_id`` exactly like the lobby
registry in :mod:`sb.domain.casino.table` (the shipped module-level
``self.game`` handle on the per-channel view).

This is the successor the D-0045 note named: ``start`` past the lobby guards
now DEALS a hand through the ported betting engine
(:mod:`sb.domain.casino.engine`) instead of stopping at the honest blocked
terminal.  The engine is Discord-free and deterministic given its deck, so
the play layer is driven headless (buttons → ``act()`` → re-render the public
spectator view) and the per-player hand renders as a PURE projection of the
one :meth:`PokerGame.snapshot`  (:mod:`sb.domain.casino.view`) — no live
per-message ephemeral handles, the D-0045 deviation this port makes explicit.

Play-chips only — every seat starts on ``START_STACK`` table chips and chips
never leave the table (no economy leg, exactly like the shipped v1 and the
goldens' zero economy rows).  In-memory and NOT restart-safe by design (the
shipped ``Hands aren't restart-safe.`` end-of-hand footer says so)."""

from __future__ import annotations

import random

from sb.domain.casino.engine import Player, PokerError, PokerGame
from sb.domain.casino.table import BIG_BLIND, SMALL_BLIND, START_STACK

__all__ = [
    "PokerError",
    "PokerGame",
    "end_game",
    "get_game",
    "reset_games_for_tests",
    "start_game",
]

# the shipped per-channel game handle (one live hand per channel).
_games: dict[int, PokerGame] = {}


def get_game(channel_id: int) -> PokerGame | None:
    return _games.get(int(channel_id))


def start_game(channel_id: int, seats: list[tuple[int, str]], *,
               rng: random.Random | None = None) -> PokerGame:
    """Seat every lobby player on ``START_STACK`` chips and DEAL the first
    hand (the shipped ``PokerGame([...], small_blind=SMALL_BLIND,
    big_blind=BIG_BLIND, button=0)`` + ``begin_hand()``).

    ``rng`` defaults to the global :mod:`random` module so a capture that
    calls ``random.seed(42)`` before driving (the golden harness) gets a
    reproducible shuffle, while live play draws from the OS-seeded global —
    the shipped nondeterminism boundary (cards.make_deck's only random
    source).  Raises :class:`PokerError` on fewer than two funded seats
    (the caller has already enforced ``MIN_PLAYERS`` at the lobby guard)."""
    players = [Player(user_id=int(uid), name=name, stack=START_STACK)
               for uid, name in seats]
    game = PokerGame(players, small_blind=SMALL_BLIND, big_blind=BIG_BLIND,
                     button=0, rng=rng or random)
    game.begin_hand()
    _games[int(channel_id)] = game
    return game


def end_game(channel_id: int) -> None:
    _games.pop(int(channel_id), None)


def reset_games_for_tests() -> None:
    _games.clear()
