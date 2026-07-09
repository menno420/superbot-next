"""BTD6 paragon degree-dependent stat scaling — the scalar formulas of
shipped ``utils/btd6/paragon_degrees.py`` @7f7628e1, VERBATIM (ported
field-for-field from the wiki's own ``Module:BTD6 stats`` renderer)::

    cooldown(d)   = rate / (1 + 0.01 * sqrt(50 * (d-1)))
    damage(d)     = base * (1 + 0.01*(d-1)) + floor((d-1)/10)   # d < 100
    pierce(d)     = floor(base * (1 + 0.01*(d-1))) + (d-1)/10   # d < 100
    damage_mod(d) = base * (1 + 0.01*(d-1))                     # d < 100
    <all three above at d == 100> = base * 2 + 10
    boss_mult(d)  = 1.0/1.25/1.5/1.75/2.0 every 20 degrees, 2.25 at 100
    power(d)      = the rounded cubic (degree 1 pinned to 0)

The full per-degree ROW traversal (``degree_row`` over the cleaned stats
node — every attack/ability/zone cell) is a NAMED SUCCESSOR PORT with the
deep BTD6 stats surface (D-0046); the grounding headline uses the scalar
formulas below. Pure, stdlib-only."""

from __future__ import annotations

import math

from sb.domain.btd6 import paragon_math

MAX_DEGREE = paragon_math.MAX_DEGREE  # 100

# A "rate" at or above this is the wiki's "no real cooldown" sentinel.
RATE_SENTINEL = 9999
# Pierce at or above this is effectively infinite.
PIERCE_SENTINEL = 99999


def power_for_degree(degree: int) -> int:
    """Cumulative power required to reach ``degree`` (the table's Power
    column — the ROUNDED cubic; degree 1 pinned to 0, degree 100 to the
    published 200,000 cap)."""
    if degree <= 1:
        return 0
    if degree >= MAX_DEGREE:
        return paragon_math.TOTAL_POWER_FOR_MAX_DEGREE
    return round((50 * degree**3 + 5025 * degree**2 + 168324 * degree + 843000) / 600)


def boss_multiplier(degree: int) -> float:
    """Boss-damage multiplier for ``degree`` (steps every 20 degrees)."""
    if degree < 20:
        return 1.0
    if degree < 40:
        return 1.25
    if degree < 60:
        return 1.5
    if degree < 80:
        return 1.75
    if degree != MAX_DEGREE:
        return 2.0
    return 2.25


# Paragons deal DOUBLE their boss damage to Elite Bosses — a runtime
# constant the engine applies, NOT a game-data field (shipped curation).
ELITE_BOSS_DAMAGE_MULTIPLIER = 2.0


def elite_boss_multiplier(degree: int) -> float:
    """Elite-boss damage multiplier (×2 at every degree, on top of the
    degree-scaled boss multiplier)."""
    return boss_multiplier(degree) * ELITE_BOSS_DAMAGE_MULTIPLIER


def scale_cooldown(rate: float, degree: int) -> float:
    """Attack/ability cooldown at ``degree`` (decreases with degree)."""
    return rate / (1 + 0.01 * math.sqrt((degree - 1) * 50))


def scale_damage(amount: float, degree: int) -> float:
    """Projectile/effect damage at ``degree``."""
    if degree == MAX_DEGREE:
        return amount * 2 + 10
    return amount * (1 + (degree - 1) * 0.01) + math.floor((degree - 1) / 10)


def scale_pierce(amount: float, degree: int) -> float:
    """Projectile pierce at ``degree`` (integer part floored BEFORE the
    per-ten bonus is added un-floored — faithful to the wiki)."""
    if degree == MAX_DEGREE:
        return amount * 2 + 10
    return math.floor(amount * (1 + (degree - 1) * 0.01)) + (degree - 1) / 10


def scale_damage_modifier(amount: float, degree: int) -> float:
    """A bonus-damage modifier (vs bosses / ceramic / …) at ``degree``."""
    if degree == MAX_DEGREE:
        return amount * 2 + 10
    return amount * (1 + (degree - 1) * 0.01)


def format_value(value: float) -> str:
    """Render a scaled value like the wiki (4 significant figures)."""
    return f"{value:.4g}"


__all__ = [
    "ELITE_BOSS_DAMAGE_MULTIPLIER",
    "MAX_DEGREE",
    "PIERCE_SENTINEL",
    "RATE_SENTINEL",
    "boss_multiplier",
    "elite_boss_multiplier",
    "format_value",
    "power_for_degree",
    "scale_cooldown",
    "scale_damage",
    "scale_damage_modifier",
    "scale_pierce",
]
