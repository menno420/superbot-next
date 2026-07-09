"""Mining loot tables + explore outcomes — ported from the shipped
``utils/mining/rewards.py`` (pure). DEVIATION (D-0043): the equipped-tool
multiplier path (``equipment.compute_stats``) rides the deferred
equipment/wear system — until that system ports, the multiplier is the
LEGACY inventory-pickaxe path only (shipped kept the two paths matched,
so pre-equipment players are byte-identical)."""

from __future__ import annotations

import random

__all__ = [
    "EXPLORE_OUTCOMES",
    "LEGACY_PICKAXE_MULT",
    "ORE_WEIGHTS",
    "ore_weights_for_depth",
    "roll_explore_outcome",
    "roll_harvest_amount",
    "roll_mine_loot",
]

ORE_WEIGHTS: dict[str, float] = {
    "stone": 3, "bronze": 2.5, "iron": 2, "silver": 1.5, "gold": 1,
    "diamond": 0.5,
}


def ore_weights_for_depth(depth: int) -> dict[str, float]:
    """Deeper = richer: the same six ores, odds shifted off stone/bronze
    toward the precious ores (shipped verbatim)."""
    d = max(0, depth)
    return {
        "stone": max(0.5, ORE_WEIGHTS["stone"] - d),
        "bronze": max(0.5, ORE_WEIGHTS["bronze"] - 0.5 * d),
        "iron": ORE_WEIGHTS["iron"] + 0.5 * d,
        "silver": ORE_WEIGHTS["silver"] + 0.5 * d,
        "gold": ORE_WEIGHTS["gold"] + 0.5 * d,
        "diamond": ORE_WEIGHTS["diamond"] + 0.5 * d,
    }


TOOL_POWER_GAIN = 0.0625
LEGACY_PICKAXE_MULT = 1.0 + 2 * TOOL_POWER_GAIN
BASE_ROLL_MAX = 2


def roll_mine_loot(*, has_pickaxe: bool, depth: int = 0,
                   multiplier: float | None = None,
                   rng: random.Random | None = None) -> tuple[str, int]:
    """(ore_name, amount) for one dig — shipped math, injectable rng."""
    r = rng or random
    weights = ore_weights_for_depth(depth)
    found = r.choices(list(weights.keys()),
                      weights=list(weights.values()), k=1)[0]
    bonus = (multiplier if multiplier is not None
             else (LEGACY_PICKAXE_MULT if has_pickaxe else 1.0))
    amount = max(1, round(r.randint(1, BASE_ROLL_MAX) * bonus))
    return found, amount


def roll_harvest_amount(*, has_axe: bool,
                        rng: random.Random | None = None) -> int:
    r = rng or random
    return r.randint(1, 3) * (2 if has_axe else 1)


EXPLORE_OUTCOMES: list[tuple[str, str | None, int]] = [
    ("found 1 gold in an abandoned camp!", "gold", 1),
    ("stumbled upon a hidden diamond vein and got 1 diamond!", "diamond", 1),
    ("was attacked by monsters and lost 2 stone...", "stone", -2),
    ("found a secret chest with 3 wood!", "wood", 3),
    ("got lost and found nothing...", None, 0),
]


def roll_explore_outcome(rng: random.Random | None = None,
                         ) -> tuple[str, str | None, int]:
    r = rng or random
    return r.choice(EXPLORE_OUTCOMES)
