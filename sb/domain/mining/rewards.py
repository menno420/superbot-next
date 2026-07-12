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


# The shipped `!explore` rides the exploration ENGINE
# (disbot/utils/mining/exploration.py): a WEIGHTED pick
# (`chooser.choices(candidates, weights)`) over the CATALOG entries
# eligible at the player's biome with their loadout, luck-scaled
# (identity at luck 0 — the oracle's own test pins
# `_luck_weighted(cands, 0) == [o.weight for o in cands]`). This table is
# the engine's FRESH-PLAYER SURFACE slice, oracle-verbatim where the
# fragment seam reaches (narration/item/amount/weight per entry):
#   abandoned_camp   "found {amount} gold in an abandoned camp!"  gold +1 w2.0
#   secret_chest     "found a secret chest with {amount} wood!"   wood +3 w3.0
#   monster_ambush   "was attacked by monsters and lost {amount}
#                     stone..."                                   stone -2 w2.0 (hazard)
#   got_lost         "got lost and found nothing..."              —     0
# DEVIATION (D-0043, ledgered): the shipped catalog carries ONE more
# surface entry between monster_ambush and got_lost (its tail
# `weight=3.0` is fragment-pinned; key/narration are not reconstructable
# through the search-only oracle seam), and got_lost's exact weight is
# unrecoverable the same way — the corpus draw bounds it (>5.6:
# goldens/mining/sweep_explore, seed 42, selects got_lost at cumulative
# fraction 0.639). Until the D-0043 deep-system port lands the engine
# wholesale, the unreconstructable entry's mass rides the junk roll:
# got_lost carries 6.0 here (the bound's smallest round value), so the
# ported narrations, their relative order, and the golden-pinned seeded
# trajectory are all oracle-true. Deeper-band entries (hidden_diamond_vein
# CAVERN, iron_pocket CAVERN, blasted_vein DEEP, the torch/dynamite-gated
# finds) are loadout/depth-gated engine territory — D-0043; the shipped
# legacy hidden-diamond-vein line left this table with them.
EXPLORE_OUTCOMES: list[tuple[str, str | None, int, float]] = [
    ("found 1 gold in an abandoned camp!", "gold", 1, 2.0),
    ("found a secret chest with 3 wood!", "wood", 3, 3.0),
    ("was attacked by monsters and lost 2 stone...", "stone", -2, 2.0),
    ("got lost and found nothing...", None, 0, 6.0),
]


def roll_explore_outcome(rng: random.Random | None = None,
                         ) -> tuple[str, str | None, int]:
    """One exploration roll — the engine's weighted single-`random()`
    draw shape (`choices(..., k=1)`), shipped verbatim."""
    r = rng or random
    picked = r.choices(EXPLORE_OUTCOMES,
                       weights=[w for *_x, w in EXPLORE_OUTCOMES], k=1)[0]
    return picked[0], picked[1], picked[2]
