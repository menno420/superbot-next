"""Fishing bait — the optional *second* pre-cast economy knob (band 6,
D-0043 slice 2; the shipped ``utils/fishing/bait.py`` ported, oracle
menno420/superbot — owner design Q-0175 §4).

Bait is an **optional, coin-bought consumable** that biases the catch
toward rarer / bigger fish for a bounded number of casts. The two-knob
model stays clean:

* **Fishing level** (``game_xp``) gates *what* you can catch.
* **The rod** (:mod:`sb.domain.fishing.rods`) is the permanent
  *how-well* axis.
* **Bait** is the *consumable* how-well axis with **two** knobs, each
  compounding onto the matching rod knob while you hold charges (one
  charge spent per cast): ``rarity_pull`` (≥ 1, multiplies the rod's
  pull) and ``bite_speed`` (≤ 1 = faster, multiplies the rod's
  bite-wait). The starter setup still catches fine without bait (bait
  only improves, never gates); the shelf keeps the two families
  orthogonal plus one premium combo.

DEVIATION (D-0043, honest): only the CATALOG + the purchase lane are
live this slice — the per-cast CONSUME + the knob consumers ride the
minigame rung with the rod knobs. The ``CRAFT_RECIPES`` /
``PEARL_BAIT_RECIPES`` shelves are carried as DATA (the shop embed's
craft fields interpolate them — the golden pins the bytes); the craft
LANES stay pending terminals (`!craftbait` / `!craftpearl` — the craft*
rung).

Pure + stdlib-only (no Discord, no DB). The store owns the loadout row
(``fishing_bait``); the audited ``fishing.bait_buy`` op owns the
purchase write."""

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
    "effect_text",
    "pearl_craftable_key_for",
    "pearl_recipe",
    "pearl_recipe_text",
    "recipe_text",
]


@dataclass(frozen=True)
class Bait:
    """One bait type — a stable key, presentation, its two knobs,
    charges, price."""

    key: str  # stable lookup key (stored in the fishing_bait row)
    name: str
    emoji: str
    rarity_pull: float  # ≥ 1 multiplier ON TOP of the equipped rod's pull
    charges: int  # casts one bought pack lasts
    price: int  # coin cost of one pack
    bite_speed: float = 1.0  # ≤ 1 multiplier ON TOP of the rod's bite-wait


#: The bait shelf, grouped by knob family — shipped values verbatim
#: (goldens/fishing/sweep_bait pins the rendered shelf bytes).
BAIT_CATALOG: tuple[Bait, ...] = (
    # Rarity family — bias the catch toward bigger fish (speed neutral).
    Bait("worm", "Worm Bait", "🪱", rarity_pull=1.25, charges=10,
         price=150),
    Bait("grub", "Glow Grub", "🐛", rarity_pull=1.50, charges=10,
         price=400),
    Bait("lure", "Shimmer Lure", "✨", rarity_pull=2.00, charges=10,
         price=1000),
    # Speed family — fish bite sooner (rarity neutral).
    Bait("minnow", "Live Minnow", "🐟", rarity_pull=1.00, charges=10,
         price=200, bite_speed=0.80),
    Bait("spinner", "Flash Spinner", "🌀", rarity_pull=1.00, charges=10,
         price=600, bite_speed=0.60),
    # Combo — the premium pack: pulls hard AND bites fast.
    Bait("feast", "Royal Feast", "👑", rarity_pull=1.75, charges=10,
         price=1800, bite_speed=0.70),
)

_BY_KEY: dict[str, Bait] = {b.key: b for b in BAIT_CATALOG}

#: The stable keys, in shelf order (for selects / validation).
BAIT_KEYS: tuple[str, ...] = tuple(b.key for b in BAIT_CATALOG)


def bait_by_key(key: str | None) -> Bait | None:
    """The :class:`Bait` for *key*, or ``None`` for an unknown / empty
    key."""
    if not key:
        return None
    return _BY_KEY.get(key)


def _effect_text(bait: Bait) -> str:
    """A short human label of a bait's knobs, e.g. ``×1.5 rarity ·
    −35% wait`` — shared by the shop shelf/selects and the purchase
    message so a speed bait never mislabels itself (shipped verbatim).
    Private def + public alias below (the ``wager.debit_in_txn``
    pattern): the sibling weather module owns the package's public
    ``effect_text`` def, and the namespace guard forbids a second
    public def of the same name in one package."""
    parts: list[str] = []
    if bait.rarity_pull > 1.0:
        parts.append(f"×{bait.rarity_pull:g} rarity")
    if bait.bite_speed < 1.0:
        parts.append(f"−{round((1.0 - bait.bite_speed) * 100)}% wait")
    return " · ".join(parts) or "no effect"


#: public name — the shipped ``bait.effect_text`` call shape, kept for
#: every caller (shop providers/renderer, the buy leg, tests).
effect_text = _effect_text


# ---------------------------------------------------------------------------
# Bait crafting — carried as DATA this slice (the shop embed's craft
# fields; the craft LANES ride the craft* rung). Shipped numbers verbatim.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaitRecipe:
    """A fish → bait recipe: consume *fish_count* small fish, yield one
    pack. Only fish whose ``size_rank`` is ``≤ max_size_rank`` count as
    ingredients; the produced pack carries the bait's own
    :attr:`Bait.charges`."""

    bait_key: str
    fish_count: int  # number of eligible fish consumed per craft
    max_size_rank: int  # only fish with size_rank ≤ this are eligible


#: The craft shelf, keyed by bait key. The premium combo ("feast") is
#: deliberately ABSENT — it stays a pure coin sink (shipped verbatim).
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
    """The :class:`BaitRecipe` for *key*, or ``None`` if not craftable."""
    if not key:
        return None
    return CRAFT_RECIPES.get(key)


def recipe_text(recipe: BaitRecipe) -> str:
    """A short human label of a recipe's cost, e.g. ``3 fish (size ≤ 3)``."""
    return f"{recipe.fish_count} fish (size ≤ {recipe.max_size_rank})"


def craftable_key_for(text: str | None) -> str | None:
    """Resolve typed *text* (a key or a bait name) to a **craftable**
    bait key — case-insensitive over key and display name; ``None`` for
    empty input or a bait with no recipe (shipped verbatim)."""
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
# (data only this slice; the shipped fishing-pearl-numbers doc's values).
# ---------------------------------------------------------------------------

#: Pearl-only recipes, keyed by bait key → pearls consumed per craft.
#: Only baits with NO fish recipe belong here (the premium combo).
PEARL_BAIT_RECIPES: dict[str, int] = {
    "feast": 4,  # 4 pearls → one Royal Feast pack
}

#: Pearl-craftable bait keys, in shelf order.
PEARL_CRAFTABLE_KEYS: tuple[str, ...] = tuple(
    b.key for b in BAIT_CATALOG if b.key in PEARL_BAIT_RECIPES
)


def pearl_recipe(key: str | None) -> int | None:
    """Pearls needed to craft *key*, or ``None`` if no pearl recipe."""
    if not key:
        return None
    return PEARL_BAIT_RECIPES.get(key)


def pearl_recipe_text(pearl_cost: int) -> str:
    """A short human label of a pearl recipe's cost, e.g. ``4 🦪 pearls``."""
    return f"{pearl_cost} 🦪 pearls"


def pearl_craftable_key_for(text: str | None) -> str | None:
    """Resolve typed *text* to a **pearl-craftable** key (shipped
    verbatim)."""
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
