"""Fishing bait — the optional *second* pre-cast economy knob (band 6,
D-0043 slice 3).

The shipped ``utils/fishing/bait.py`` ported (oracle menno420/superbot @
cdb26804; owner design Q-0175 §4, "Bait as the second economy knob"):
bait is an **optional, coin-bought consumable** that biases the catch
toward rarer / bigger fish for a bounded number of casts. The two-knob
model stays clean:

* **Fishing level** (``game_xp``) gates *what* you can catch — the size
  bands.
* **The rod** (:mod:`sb.domain.fishing.rods`) is the permanent
  *how-well* axis.
* **Bait** is the *consumable* how-well axis with **two** knobs, each
  compounding onto the matching rod knob while you hold charges (one
  charge spent per cast): ``rarity_pull`` (≥ 1) multiplies the rod's
  pull and ``bite_speed`` (≤ 1 = faster) multiplies the rod's bite-wait.

The starter setup still catches fine without bait (bait only improves,
never gates), and the two knobs are *orthogonal*: the shelf has
dedicated rarity baits, dedicated speed baits, and one premium combo
that turns both.

Pure + stdlib-only (no Discord, no DB): the audited fishing ops own the
purchase write + the per-cast consume; the bait shop panel reads this
catalog. DEVIATION (D-0043): the per-cast consume — the loaded knobs
feeding the cast roll and the charge spend — rides the bait/minigame
rung with the rest of the cast knobs (the ops.py under-port ledger);
this slice makes the BAIT STATE live (buy/craft/load persist
``fishing_bait``)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BAIT_CATALOG",
    "BAIT_KEYS",
    "Bait",
    "BaitRecipe",
    "CRAFTABLE_KEYS",
    "CRAFT_RECIPES",
    "PEARL_BAIT_RECIPES",
    "PEARL_CRAFTABLE_KEYS",
    "bait_by_key",
    "craft_recipe",
    "craftable_key_for",
    "bait_effect_text",
    "pearl_craftable_key_for",
    "pearl_recipe",
    "pearl_recipe_text",
    "recipe_text",
]


@dataclass(frozen=True)
class Bait:
    """One bait type — a stable key, presentation, its two knobs, charges, price."""

    key: str  # stable lookup key (stored in the fishing_bait row)
    name: str
    emoji: str
    rarity_pull: float  # ≥ 1 multiplier applied ON TOP of the equipped rod's pull
    charges: int  # casts one bought pack lasts
    price: int  # coin cost of one pack
    bite_speed: float = 1.0  # ≤ 1 multiplier ON TOP of the rod's bite-wait (faster)


#: The bait shelf, grouped by knob family (shipped verbatim). ``rarity_pull``
#: multiplies the rod's own pull and ``bite_speed`` multiplies the rod's
#: bite-wait. Charges bound the boost so it's a *consumable* sink; the two
#: families are kept orthogonal — rarity baits leave speed neutral and
#: vice-versa — so the pre-cast choice is legible; one premium combo turns
#: both for the top coin sink.
BAIT_CATALOG: tuple[Bait, ...] = (
    # Rarity family — bias the catch toward bigger fish (speed neutral).
    Bait("worm", "Worm Bait", "🪱", rarity_pull=1.25, charges=10, price=150),
    Bait("grub", "Glow Grub", "🐛", rarity_pull=1.50, charges=10, price=400),
    Bait("lure", "Shimmer Lure", "✨", rarity_pull=2.00, charges=10,
         price=1000),
    # Speed family — fish bite sooner (rarity neutral); more casts per bar.
    Bait("minnow", "Live Minnow", "🐟", rarity_pull=1.00, charges=10,
         price=200, bite_speed=0.80),
    Bait("spinner", "Flash Spinner", "🌀", rarity_pull=1.00, charges=10,
         price=600, bite_speed=0.60),
    # Combo — the premium pack: pulls hard AND bites fast (the top coin sink).
    Bait("feast", "Royal Feast", "👑", rarity_pull=1.75, charges=10,
         price=1800, bite_speed=0.70),
)

_BY_KEY: dict[str, Bait] = {b.key: b for b in BAIT_CATALOG}

#: The stable keys, in shelf order (for selects / validation).
BAIT_KEYS: tuple[str, ...] = tuple(b.key for b in BAIT_CATALOG)


def bait_by_key(key: str | None) -> Bait | None:
    """The :class:`Bait` for *key*, or ``None`` for an unknown / empty key."""
    if not key:
        return None
    return _BY_KEY.get(key)


def bait_effect_text(bait: Bait) -> str:
    """A short human label of a bait's knobs, e.g. ``×1.5 rarity · −35% wait``.

    The shipped ``effect_text`` — renamed here because the package's
    weather module already exports the shipped weather ``effect_text``
    (check_symbol_shadowing rule 2: public names are package-unique);
    the produced bytes are identical.

    Shared by the shop panel (shelf / select) and the purchase message (op)
    so a speed bait never mislabels itself as "×1 rarity" — only the knobs it
    actually turns are shown (rarity pull above 1, bite-wait reduction below 1).
    """
    parts: list[str] = []
    if bait.rarity_pull > 1.0:
        parts.append(f"×{bait.rarity_pull:g} rarity")
    if bait.bite_speed < 1.0:
        parts.append(f"−{round((1.0 - bait.bite_speed) * 100)}% wait")
    return " · ".join(parts) or "no effect"


# ---------------------------------------------------------------------------
# Bait crafting — turn caught fish into bait, the gameplay-native second source
# ---------------------------------------------------------------------------
#
# The fishing economy loops back on itself (the shipped idea
# ``fishing-bait-crafting-2026-06-22``): crafting lets the *small, common*
# catches (which otherwise just sell cheap) become the lure that lands the
# trophy — ``catch → craft → bait → bigger catch``. A recipe consumes
# ``fish_count`` fish whose ``size_rank`` is ``≤ max_size_rank``
# (smallest-first, so the player keeps their bigger fish) and yields one pack
# (``Bait.charges`` casts). Only the cheaper / mid baits are craftable — the
# premium combo ("feast") stays a pure coin sink.


@dataclass(frozen=True)
class BaitRecipe:
    """A fish → bait recipe: consume *fish_count* small fish, yield one pack.

    Only fish whose ``size_rank`` is ``≤ max_size_rank`` count as ingredients
    (so crafting drains the low-rank catches first); the produced pack carries
    the bait's own :attr:`Bait.charges`.
    """

    bait_key: str
    fish_count: int  # number of eligible fish consumed per craft
    max_size_rank: int  # only fish with size_rank ≤ this are eligible ingredients


#: The craft shelf, keyed by bait key (shipped verbatim). Cheaper baits cost a
#: few of the smallest fish; better baits want more / larger fish. The premium
#: combo ("feast") is deliberately ABSENT — it stays a pure coin sink (the
#: top-end spend reason).
CRAFT_RECIPES: dict[str, BaitRecipe] = {
    "worm": BaitRecipe("worm", fish_count=3, max_size_rank=3),
    "minnow": BaitRecipe("minnow", fish_count=3, max_size_rank=3),
    "grub": BaitRecipe("grub", fish_count=5, max_size_rank=6),
    "spinner": BaitRecipe("spinner", fish_count=5, max_size_rank=6),
    "lure": BaitRecipe("lure", fish_count=6, max_size_rank=9),
}

#: Craftable bait keys, in shelf order (skips any without a recipe).
CRAFTABLE_KEYS: tuple[str, ...] = tuple(
    b.key for b in BAIT_CATALOG if b.key in CRAFT_RECIPES
)


def craft_recipe(key: str | None) -> BaitRecipe | None:
    """The :class:`BaitRecipe` for *key*, or ``None`` if that bait isn't craftable."""
    if not key:
        return None
    return CRAFT_RECIPES.get(key)


def recipe_text(recipe: BaitRecipe) -> str:
    """A short human label of a recipe's cost, e.g. ``3 fish (size ≤ 3)``."""
    return f"{recipe.fish_count} fish (size ≤ {recipe.max_size_rank})"


def craftable_key_for(text: str | None) -> str | None:
    """Resolve typed *text* (a key or a bait name) to a **craftable** bait key.

    Case-insensitive; matches either the stable key (``worm``) or the display
    name (``Worm Bait``). Returns ``None`` for empty input or a bait that has no
    recipe — so ``!craftbait worm`` and ``!craftbait "worm bait"`` both work but
    a non-craftable bait (the premium combo) does not resolve.
    """
    if not text:
        return None
    needle = text.strip().lower()
    for key in CRAFTABLE_KEYS:
        bait = _BY_KEY.get(key)
        if bait is None:
            continue
        if needle in (key.lower(), bait.name.lower()):
            return key
    return None


# ---------------------------------------------------------------------------
# Pearl crafting — the rare-material earn path for the premium bait
# ---------------------------------------------------------------------------
#
# The premium combo bait ("feast" — Royal Feast) is deliberately ABSENT from
# the fish-craft shelf above: it stays a top-end coin sink. The **pearl**
# (``sb.domain.fishing.ops.PEARL_ITEM``) is the rare reel drop (size-scaled),
# and this shelf is its sink: spending ``PEARL_BAIT_RECIPES[key]`` pearls
# crafts one pack of that otherwise-uncraftable bait. Because bait is
# *consumable*, pearls have a perpetual home — a lucky fisher can earn the
# Royal Feast by fishing, while coins stay the fast alternative.

#: Pearl-only recipes, keyed by bait key → pearls consumed per craft.  Only
#: baits with **no** fish recipe belong here (the premium combo), so the two
#: earn paths never overlap.
PEARL_BAIT_RECIPES: dict[str, int] = {
    "feast": 4,  # 4 pearls → one Royal Feast pack
}

#: Pearl-craftable bait keys, in shelf order.
PEARL_CRAFTABLE_KEYS: tuple[str, ...] = tuple(
    b.key for b in BAIT_CATALOG if b.key in PEARL_BAIT_RECIPES
)


def pearl_recipe(key: str | None) -> int | None:
    """Pearls needed to craft *key*, or ``None`` if it has no pearl recipe."""
    if not key:
        return None
    return PEARL_BAIT_RECIPES.get(key)


def pearl_recipe_text(pearl_cost: int) -> str:
    """A short human label of a pearl recipe's cost, e.g. ``4 🦪 pearls``."""
    return f"{pearl_cost} 🦪 pearls"


def pearl_craftable_key_for(text: str | None) -> str | None:
    """Resolve typed *text* (a key or a bait name) to a **pearl-craftable** key.

    Case-insensitive; matches either the stable key (``feast``) or the display
    name (``Royal Feast``).  Returns ``None`` for empty input or a bait with no
    pearl recipe.
    """
    if not text:
        return None
    needle = text.strip().lower()
    for key in PEARL_CRAFTABLE_KEYS:
        bait = _BY_KEY.get(key)
        if bait is None:
            continue
        if needle in (key.lower(), bait.name.lower()):
            return key
    return None
