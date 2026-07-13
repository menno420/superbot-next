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
bought one. The gear-multiplier half of the shipped module
(EffectiveStats pull/bite mults) already lives with the equipment port;
only the craft shelf lands here.

Pure + stdlib-only (no Discord, no DB)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CHARM_RECIPES",
    "CRAFTABLE_CHARM_NAMES",
    "CharmRecipe",
    "charm_recipe",
    "charm_recipe_text",
    "craftable_charm_for",
]


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
