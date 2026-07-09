"""Derive BTD6 tower/upgrade costs for any difficulty from the Medium
price — shipped ``utils/btd6/difficulty_costs.py`` @7f7628e1 VERBATIM.

Multipliers (verified exact against the published Bomb Shooter table):
Easy ×0.85 · Medium ×1.00 · Hard ×1.08 · Impoppable ×1.20; rounding to
the nearest $5 with exact half-ties resolving DOWN (``Fraction`` so the
tie boundary is exact). CHIMPS prices as Hard. Pure, stdlib-only."""

from __future__ import annotations

import math
from fractions import Fraction

# Canonical difficulty keys, in display order.
DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard", "impoppable")

_MULTIPLIERS: dict[str, Fraction] = {
    "easy": Fraction(85, 100),
    "medium": Fraction(1),
    "hard": Fraction(108, 100),
    "impoppable": Fraction(120, 100),
}

_DIFFICULTY_ALIASES: dict[str, str] = {
    "": "medium",
    "normal": "medium",
    "standard": "medium",
    "chimps": "hard",
}


def _round_to_5_ties_down(value: Fraction) -> int:
    """Round to the nearest multiple of 5; exact .5-of-5 ties go down."""
    fifths = math.ceil(value / 5 - Fraction(1, 2))
    return fifths * 5


def normalize_difficulty(difficulty: str) -> str:
    """Map a free-form difficulty/mode label to a canonical key (raises
    ``ValueError`` for anything unrecognised — never silently Medium)."""
    key = difficulty.strip().lower()
    key = _DIFFICULTY_ALIASES.get(key, key)
    if key not in _MULTIPLIERS:
        raise ValueError(f"unknown BTD6 difficulty: {difficulty!r}")
    return key


def cost_for_difficulty(medium_cost: int, difficulty: str) -> int:
    """Scale a Medium cost to ``difficulty`` (mode aliases accepted)."""
    key = normalize_difficulty(difficulty)
    if key == "medium":
        return medium_cost
    return _round_to_5_ties_down(Fraction(medium_cost) * _MULTIPLIERS[key])


def all_difficulty_costs(medium_cost: int) -> dict[str, int]:
    """Return ``{difficulty: cost}`` for all four difficulties."""
    return {d: cost_for_difficulty(medium_cost, d) for d in DIFFICULTIES}


__all__ = [
    "DIFFICULTIES",
    "all_difficulty_costs",
    "cost_for_difficulty",
    "normalize_difficulty",
]
