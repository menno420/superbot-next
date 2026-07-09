"""Pure blackjack card / hand / deck primitives — ported VERBATIM from the
shipped ``services/blackjack_engine.py`` (deterministic except
:func:`new_deck`, which takes an injectable rng so K7 legs stay
reproducible under test).

Cards are strings of the form ``"<rank> <suit>"``, e.g. ``"A ♠"``.
"""

from __future__ import annotations

import random

__all__ = [
    "RANKS",
    "SUITS",
    "hand_str",
    "hand_value",
    "is_blackjack",
    "new_deck",
    "rank_value",
]

SUITS: tuple[str, ...] = ("♠", "♥", "♦", "♣")
RANKS: tuple[str, ...] = (
    "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K",
)


def rank_value(rank: str) -> int:
    """Face value for a single rank string. Aces are 11 by default."""
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand: list[str]) -> int:
    """Total a hand, demoting aces 11 → 1 to stay under 22 when possible."""
    total = sum(rank_value(c.split()[0]) for c in hand)
    aces = sum(1 for c in hand if c.startswith("A"))
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def new_deck(rng: random.Random | None = None) -> list[str]:
    """A fresh shuffled 52-card deck (the only function with an effect —
    parameterised rng is the band-3 injectable-randomness convention)."""
    deck = [f"{r} {s}" for r in RANKS for s in SUITS]
    (rng or random).shuffle(deck)
    return deck


def hand_str(hand: list[str], hide_second: bool = False) -> str:
    """Display a hand; mask the second card when *hide_second* is true."""
    if hide_second:
        return f"{hand[0]}  ||?||"
    return "  ".join(hand)


def is_blackjack(hand: list[str]) -> bool:
    """True iff *hand* is a natural blackjack (two cards totalling 21)."""
    return len(hand) == 2 and hand_value(hand) == 21


def dealer_play(deck: list[str], dealer: list[str]) -> None:
    """Stand-on-17 dealer policy (shipped ``_Game.dealer_play``)."""
    while hand_value(dealer) < 17:
        dealer.append(deck.pop())
