"""The fishing rod ladder — the second, orthogonal progression axis
(band 6, D-0043 slice 2; the shipped ``utils/fishing/rods.py`` ported,
oracle menno420/superbot — owner design Q-0175).

The design's two-axis model (the shipped
``docs/planning/fishing-minigame-design-2026-06-22.md``):

* **Fishing level** (``game_xp``) gates *what* you can catch — the size
  bands.
* **The rod** gates *how well / which-within-band* you catch it — five
  knobs the design sim tuned:

  - ``window_bonus``    — seconds added to the reaction window (the
    fairness knob).
  - ``bite_speed``      — multiplier on the bite wait (<1 = faster bites
    = pacing).
  - ``rarity_pull``     — >1 biases the catch toward the big end of your
    band (the reward-quality knob).
  - ``escape_resist``   — 0…1 reduces the reel-fight snap-free chance.
  - ``premature_grace`` — 0…1 chance a *premature* reel is forgiven
    instead of spooking the fish (spent once per cast).

Crucially the **starter rod still catches fine** — rods make fishing
*nicer and more rewarding*, never *possible* (the plan's "gear is never
required"). Rods are **bought with coins** (a finite sink); each tier
requires the one below it. Prices are tuning constants, shipped verbatim.

DEVIATION (D-0043, honest): only the LADDER + the purchase lane are live
this slice — the knob CONSUMERS (reaction window, bite wait, escape
fight, premature grace) ride the minigame rung with the live timing
layer; ``rarity_pull`` lands on the cast roll when that rung wires the
venue→cast seam. The ``ROD_RECIPES`` fish→rod shelf is carried as DATA
(the shop embed's craft line interpolates it — the golden pins the
bytes); the craft LANE itself stays a pending terminal (`!craftrod` /
`!rodrecipes` — the craft* rung).

Pure + stdlib-only (no Discord, no DB). The store owns the tier row
(``fishing_rod``); the audited ``fishing.rod_upgrade`` op owns the
purchase write."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "MAX_TIER",
    "ROD_LADDER",
    "ROD_RECIPES",
    "Rod",
    "RodRecipe",
    "STARTER",
    "next_rod",
    "rod_for_tier",
    "rod_recipe",
    "rod_recipe_text",
]


@dataclass(frozen=True)
class Rod:
    """One rung of the rod ladder — a tier index, a name, the knobs, price."""

    tier: int
    name: str
    emoji: str
    window_bonus: float  # seconds added to the reaction window
    bite_speed: float  # multiplier on the bite wait (<1 = faster)
    rarity_pull: float  # >1 biases catches toward the big end of the band
    escape_resist: float  # 0…1 reduces reel-fight snap-free chance
    premature_grace: float  # 0…1 chance a premature reel is forgiven
    price: int  # coin cost to upgrade *into* this tier (starter = 0)


#: The ladder, tier 0 (starter) → tier 4 (diamond) — shipped values
#: verbatim (goldens/fishing/sweep_rod pins the rendered ladder bytes).
ROD_LADDER: tuple[Rod, ...] = (
    Rod(0, "Bare Rod", "🎣", window_bonus=0.0, bite_speed=1.00,
        rarity_pull=1.00, escape_resist=0.00, premature_grace=0.00,
        price=0),
    Rod(1, "Bronze Rod", "🥉", window_bonus=0.4, bite_speed=0.95,
        rarity_pull=1.10, escape_resist=0.10, premature_grace=0.15,
        price=250),
    Rod(2, "Silver Rod", "🥈", window_bonus=0.8, bite_speed=0.88,
        rarity_pull=1.25, escape_resist=0.22, premature_grace=0.30,
        price=750),
    Rod(3, "Gold Rod", "🥇", window_bonus=1.2, bite_speed=0.80,
        rarity_pull=1.45, escape_resist=0.35, premature_grace=0.45,
        price=2000),
    Rod(4, "Diamond Rod", "💎", window_bonus=1.7, bite_speed=0.70,
        rarity_pull=1.70, escape_resist=0.50, premature_grace=0.60,
        price=5000),
)

MAX_TIER = len(ROD_LADDER) - 1
STARTER = ROD_LADDER[0]


def rod_for_tier(tier: int) -> Rod:
    """The :class:`Rod` for *tier*, clamped into the ladder (unknown →
    starter)."""
    if tier < 0:
        return STARTER
    if tier > MAX_TIER:
        return ROD_LADDER[MAX_TIER]
    return ROD_LADDER[tier]


def next_rod(tier: int) -> Rod | None:
    """The next rod up from *tier*, or ``None`` if already at the top."""
    if tier >= MAX_TIER:
        return None
    return ROD_LADDER[tier + 1]


# ---------------------------------------------------------------------------
# Fish → rod craft path — carried as DATA this slice (the shop embed's
# craft line; the craft LANE rides the craft* rung). Shipped numbers
# verbatim (the shipped docs/planning/fishing-rod-craft-numbers-2026-06-27).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RodRecipe:
    """A fish → rod recipe: consume *fish_count* eligible fish, gain one
    tier. Only fish whose ``size_rank`` is ``≤ max_size_rank`` count as
    ingredients (the smallest are spent first); *tier* is the rod tier
    this recipe crafts **into** (it requires owning the tier below)."""

    tier: int  # the rod tier crafted into (1…MAX_TIER)
    fish_count: int  # number of eligible fish consumed per craft
    max_size_rank: int  # only fish with size_rank ≤ this are eligible


#: The rod craft shelf, keyed by the tier it crafts into — shipped
#: verbatim (the sweep_rod golden pins the tier-1 craft line's bytes).
ROD_RECIPES: dict[int, RodRecipe] = {
    1: RodRecipe(1, fish_count=10, max_size_rank=6),
    2: RodRecipe(2, fish_count=16, max_size_rank=12),
    3: RodRecipe(3, fish_count=26, max_size_rank=18),
    4: RodRecipe(4, fish_count=40, max_size_rank=21),
}


def rod_recipe(tier: int) -> RodRecipe | None:
    """The :class:`RodRecipe` to craft *into* ``tier``, or ``None``."""
    return ROD_RECIPES.get(tier)


def rod_recipe_text(recipe: RodRecipe) -> str:
    """A short human label of a recipe's cost, e.g. ``10 fish (size ≤ 6)``."""
    return f"{recipe.fish_count} fish (size ≤ {recipe.max_size_rank})"
