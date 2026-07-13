"""The fishing charm-craft shelf — the catch→charm earn path (band 6,
D-0043 slice 3).

The shipped ``utils/fishing/gear.py`` charm-recipe half ported (oracle
menno420/superbot @ cdb26804): the three CHARM-slot fishing charms gain
a gameplay-native second source beside the mining gear shop's coin
price — an inventory→gear conversion, NOT a coin sink. A
:class:`CharmRecipe` consumes ``fish_count`` caught fish whose
``size_rank`` is ``≤ max_size_rank`` (smallest-first via the shared
spend planner, :mod:`sb.domain.fishing.crafting`) and grants one charm
item into the shared mining inventory; the charm then equips through
the normal mining gear panel (CHARM slot).

The charm *names* are the mining equipment-catalog keys byte-for-byte
(``sb/domain/mining/equipment.py`` — "fishing charm" / "anglers charm" /
"master angler charm"), so a crafted charm is indistinguishable from a
bought one. The gear-multiplier half of the shipped module (the
EffectiveStats → cast-knob converters, oracle ``utils/fishing/gear.py``
:33-65) lands below with the cast-leg depth wiring: ``fishing_power`` →
a rarity-pull multiplier (≥ 1) and ``bite_luck`` → a bite-speed
multiplier (≤ 1 = faster), both bounded and default-preserving — with
no fishing gear equipped every multiplier is exactly ``1.0``, so a
cast is byte-identical to the pre-gear behaviour.

Pure + stdlib-only (no Discord, no DB); the converters duck-type the
mining ``EffectiveStats`` (``fishing_power`` / ``bite_luck``) so this
module keeps zero imports."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BITE_SPEED_PER_BITE_LUCK",
    "CHARM_RECIPES",
    "CRAFTABLE_CHARM_NAMES",
    "CharmRecipe",
    "MAX_GEAR_PULL",
    "MIN_GEAR_BITE_SPEED",
    "PULL_PER_FISHING_POWER",
    "charm_recipe",
    "charm_recipe_text",
    "craftable_charm_for",
    "fishing_bite_speed_mult",
    "fishing_pull_mult",
    "has_fishing_bonus",
]

# --- the gear → cast-knob converters (shipped verbatim, oracle
# utils/fishing/gear.py:33-65) ------------------------------------------------

#: Per-point rarity-pull added by ``fishing_power`` (the full ladder's
#: ``fishing_power=6`` → ×1.24, a touch under a Silver rod's 1.25 pull).
PULL_PER_FISHING_POWER = 0.04
#: Per-point bite-wait reduction from ``bite_luck`` (``bite_luck=3`` → ×0.91).
BITE_SPEED_PER_BITE_LUCK = 0.03

#: Hard caps so gear can never dominate the rod×bait×weather stack even if a
#: future item or stacking path pushes the stats far past the charm ladder.
MAX_GEAR_PULL = 1.40  # ceiling on the rarity-pull multiplier
MIN_GEAR_BITE_SPEED = 0.75  # floor on the bite-speed multiplier (faster)


def fishing_pull_mult(stats) -> float:
    """Rarity-pull multiplier (≥ 1.0) contributed by ``stats.fishing_power``.

    ``1.0`` when no fishing gear is equipped (``fishing_power <= 0``);
    rises :data:`PULL_PER_FISHING_POWER` per point, capped at
    :data:`MAX_GEAR_PULL` (shipped verbatim). *stats* is the mining
    ``EffectiveStats`` (duck-typed)."""
    power = max(0, stats.fishing_power)
    return min(1.0 + PULL_PER_FISHING_POWER * power, MAX_GEAR_PULL)


def fishing_bite_speed_mult(stats) -> float:
    """Bite-speed multiplier (≤ 1.0 = faster) contributed by ``stats.bite_luck``.

    ``1.0`` when no fishing gear is equipped (``bite_luck <= 0``); falls
    :data:`BITE_SPEED_PER_BITE_LUCK` per point, floored at
    :data:`MIN_GEAR_BITE_SPEED` (shipped verbatim)."""
    luck = max(0, stats.bite_luck)
    return max(1.0 - BITE_SPEED_PER_BITE_LUCK * luck, MIN_GEAR_BITE_SPEED)


def has_fishing_bonus(stats) -> bool:
    """Whether *stats* carry any fishing gear contribution (for the
    cast-panel 🎣 note — shipped verbatim)."""
    return stats.fishing_power > 0 or stats.bite_luck > 0


@dataclass(frozen=True)
class CharmRecipe:
    """A fish → charm recipe: consume *fish_count* small fish, gain one charm.

    Only fish whose ``size_rank`` is ``≤ max_size_rank`` count as ingredients
    (the smallest are spent first), so crafting drains the common catches a
    fisher accumulates rather than the trophies.  *charm* is the equipment item
    name produced (the mining-inventory key / gear-catalog name).
    """

    charm: str  # the equipment item name produced (mining-inventory key)
    fish_count: int  # number of eligible fish consumed per craft
    max_size_rank: int  # only fish with size_rank ≤ this are eligible ingredients


#: The charm craft shelf, keyed by charm name (shipped verbatim).  Costs climb
#: up the ladder and the better charms accept larger fish (so the top charm can
#: absorb a deep haul).  Monotonic, and far pricier in fish than the bait shelf
#: — a charm is permanent gear, not a consumable pack.
CHARM_RECIPES: dict[str, CharmRecipe] = {
    "fishing charm": CharmRecipe("fishing charm", fish_count=8,
                                 max_size_rank=8),
    "anglers charm": CharmRecipe("anglers charm", fish_count=12,
                                 max_size_rank=14),
    "master angler charm": CharmRecipe("master angler charm", fish_count=18,
                                       max_size_rank=21),
}

#: Craftable charm names, in ladder order.
CRAFTABLE_CHARM_NAMES: tuple[str, ...] = tuple(CHARM_RECIPES)


def charm_recipe(name: str | None) -> CharmRecipe | None:
    """The :class:`CharmRecipe` for *name*, or ``None`` if that charm isn't craftable."""
    if not name:
        return None
    return CHARM_RECIPES.get(name.strip().lower())


def charm_recipe_text(recipe: CharmRecipe) -> str:
    """A short human label of a recipe's cost, e.g. ``8 fish (size ≤ 8)``."""
    return f"{recipe.fish_count} fish (size ≤ {recipe.max_size_rank})"


def craftable_charm_for(text: str | None) -> str | None:
    """Resolve typed *text* to a **craftable** charm name (case-insensitive).

    Matches the charm's stored equipment name (``fishing charm``); returns
    ``None`` for empty input or a non-craftable charm — so ``!craftcharm fishing
    charm`` works but a typo / unknown charm does not resolve.
    """
    if not text:
        return None
    needle = text.strip().lower()
    return needle if needle in CHARM_RECIPES else None
