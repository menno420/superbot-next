"""Mining structures (band 6, slice 4) — pure build/gating math for the §7.5
structure sinks, ported from the oracle ``disbot/utils/mining/structures.py``.

Slice 4 scope: the **Forge** (a built coin + material sink that unlocks
higher-tier gear crafting) and the **Campfire** (a cheap single-level structure
that gates cooking fish into food). Both are ``(user, guild, structure, level)``
rows in the generic ``mining_structures`` table and share one ``BuildCost``
shape. The fishing depth port (slice 4, the locations slice) added the oracle's
four **coral fishing structures** verbatim — the Tide Pool / Dock / Boathouse /
Fishery keys, level names, build ladders and mult/bonus functions
(``utils/mining/structures.py`` L36-39 / L65-110 / L153-198 / L269-315) — kept
in THIS module because the oracle keeps them here (they are generic
``mining_structures`` rows; the fishing panels read this one source of truth
through the same registry). Only the Home backdrop still rides its own deferred
system.

Design (kept **additive**, verbatim from the oracle): the forge requirement is
derived from a recipe's gear tier, but only the **top two** tiers gate —
bronze / iron / silver gear, every tool, and every structure stay craftable at
forge level 0, so existing play is unchanged until a player reaches gold/diamond
gear. Gold needs a level-1 forge, diamond a level-2 forge.

This is a pure-math module: it imports stdlib + ``sb.domain.mining.equipment``
only (no store / db), so the panel, op, and handler layers share one source of
truth. The numbers are the pinned oracle defaults
(docs/planning/forge-numbers-2026-06-15.md).

Guard-only-capture (A-16): the row-bearing MINING build write (`!forge` 🔥
Build / `!build campfire`) rides the deferred structures BUILD system (the
`!build` command stays a D-0043 pending terminal); every imported sweep drove
only the bare `!forge` — which renders the not-built card off the store's no-row
level 0 (goldens/mining/sweep_forge.json) — so mining_structures is a
declared-but-guard-only mining surface (depth.exemptions.mining). The FISHING
panels' Build buttons (fishing slice 4) run the LIVE audited
``fishing.build_structure`` op — but no golden drives a build click either
(every fishing structure sweep pins the fresh not-built render), so the
exemption posture is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sb.domain.mining import equipment

#: The buildable structures declared this slice. Each is a
#: ``(user, guild, structure, level)`` row in the generic ``mining_structures``
#: table and shares the same build math.
FORGE = "forge"
HOME = "home"
CAMPFIRE = "campfire"
TIDE_POOL = "tide_pool"
DOCK = "dock"
BOATHOUSE = "boathouse"
FISHERY = "fishery"

#: Gear at or below this tier index needs **no** forge (bronze=1, iron=2,
#: silver=3 are free; gold=4 → forge 1; diamond=5 → forge 2). ``forge_level =
#: max(0, tier_index - FREE_TIER_CEILING)``.
FREE_TIER_CEILING = 3

#: The forge level shown in the panel / gate message per level.
_FORGE_LEVEL_NAMES = ("(not built)", "Forge I", "Forge II")

#: Home (slice 6) is purely cosmetic: each level unlocks a nicer Character-card
#: backdrop. No gameplay gate — Home is a coin/material *sink* with a visible
#: reward, never a wall. Ported verbatim from the oracle ``structures.py``.
_HOME_LEVEL_NAMES = ("(not built)", "Cozy Cabin", "Stone Keep", "Grand Hall")

#: Campfire (2026-06-22, owner-chosen): a cheap single-level structure that
#: gates cooking fish into food (energy refill). A small coin + material sink,
#: buildable early — a progression beat, not a wall.
_CAMPFIRE_LEVEL_NAMES = ("(not built)", "Campfire")

#: Tide Pool (2026-07-01): the deepwater-**coral** structure sink — coral's
#: first *functional* payoff (the cosmetic curios are its other sink). A
#: stocked reef pool nudges the fishing catch toward the big end of the
#: unlocked band: each level adds a small ``rarity_pull`` bonus folded into
#: ``begin_cast`` as the 5th "how-well" knob (rod × bait × weather × gear ×
#: tide pool). Unbuilt ⇒ ×1.0 ⇒ byte-identical casts — additive, never a wall.
_TIDE_POOL_LEVEL_NAMES = ("(not built)", "Reef Pool", "Tidal Basin",
                          "Grand Reef")

#: Per-level rarity-pull bonus (added to the ×1.0 base). Level 3 ⇒ ×1.12 — a
#: modest edge (the fishing-level axis still owns which fish are reachable at
#: all; this only reweights the band). The pinned oracle default.
_TIDE_POOL_PULL_STEP = 0.04

#: Dock (2026-07-01): the Tide Pool's **sibling** — a second coral structure,
#: but the *entry* one (cheaper, adds a common material) with a different
#: payoff: it speeds up the bite rather than pulling rarer fish. Each level
#: shortens the bite wait via a ``bite_speed`` multiplier ≤ 1.0 folded into
#: ``begin_cast`` (the same knob rod/bait use). Unbuilt ⇒ ×1.0 ⇒
#: byte-identical. Together with the Tide Pool it makes coral a real
#: *choice* — faster fishing vs. rarer fish.
_DOCK_LEVEL_NAMES = ("(not built)", "Fishing Dock", "Deepwater Pier")

#: Per-level bite-speed reduction (subtracted from the ×1.0 base — lower =
#: faster bite). Level 2 ⇒ ×0.88. The pinned oracle default.
_DOCK_BITE_STEP = 0.06

#: Boathouse (2026-07-01): the **third** coral structure, giving coral a
#: distinct *third* payoff — faster **fishing energy regen** (endurance),
#: where the Tide Pool is quality and the Dock is per-cast throughput. Each
#: level shortens the passive energy-refill interval via a ``regen``
#: multiplier ≤ 1.0 (lower = faster refill) applied to the fishing
#: ``REGEN_SECONDS`` in ``begin_cast`` / ``get_energy``. Unbuilt ⇒ ×1.0 ⇒
#: the interval is exactly ``REGEN_SECONDS`` ⇒ byte-identical energy.
_BOATHOUSE_LEVEL_NAMES = ("(not built)", "Boathouse", "Grand Boathouse")

#: Per-level regen speed-up (subtracted from the ×1.0 base — lower = faster
#: regen). Level 2 ⇒ ×0.76. The pinned oracle default.
_BOATHOUSE_REGEN_STEP = 0.12

#: Fishery (2026-07-01): the **fourth** coral structure, giving coral a
#: genuinely distinct *fourth* payoff — a higher **lucky double-catch**
#: chance (yield / abundance), where the Tide Pool is quality, the Dock is
#: per-cast throughput, and the Boathouse is endurance. A well-stocked
#: fishery keeps the waters plentiful, so a landed reel is more likely to
#: hook a *second* copy of the same fish (extra craft fodder / sell
#: material) — folded into the catch commit as a bonus **added** to the base
#: ``BONUS_CATCH_CHANCE``. Unbuilt ⇒ +0.0 ⇒ the base chance is unchanged ⇒
#: byte-identical catch economics.
_FISHERY_LEVEL_NAMES = ("(not built)", "Fishery", "Grand Fishery")

#: Per-level double-catch-chance bonus (**added** to the base chance —
#: higher = more double catches). Level 2 ⇒ +0.10 (0.10 base → 0.20). The
#: pinned oracle default.
_FISHERY_BONUS_STEP = 0.05


@dataclass(frozen=True)
class BuildCost:
    """The cost to build/upgrade a structure one level: coins + raw materials."""

    coins: int
    materials: dict[str, int] = field(default_factory=dict)


#: Forge build ladder — cost to go level → level + 1. Index ``i`` is the cost to
#: build the *(i+1)*-th level (index 0 = unbuilt → Forge I). Rising coin +
#: material sink; the pinned oracle defaults.
_FORGE_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Forge I (unlocks gold-tier gear)
    BuildCost(coins=3_000, materials={"iron": 25, "stone": 15}),
    # → Forge II (unlocks diamond-tier gear)
    BuildCost(coins=8_000, materials={"gold": 20, "iron": 10}),
)

#: Home build ladder — a rising coin + material sink for the three cosmetic
#: tiers (the pinned oracle defaults, docs/planning/home-numbers-2026-06-15.md).
_HOME_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Cozy Cabin (a warm backdrop)
    BuildCost(coins=2_000, materials={"wood": 30, "stone": 20}),
    # → Stone Keep (a cool stone backdrop)
    BuildCost(coins=5_000, materials={"stone": 50, "iron": 15}),
    # → Grand Hall (a regal backdrop)
    BuildCost(coins=12_000, materials={"gold": 15, "diamond": 3}),
)

#: Campfire build ladder — one cheap level that unlocks cooking.
_CAMPFIRE_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Campfire (unlocks !cook)
    BuildCost(coins=500, materials={"wood": 20, "stone": 10}),
)

#: Tide Pool build ladder — a rising coin + **coral** sink for the three
#: levels (coral is the deepwater-only reel drop; it reuses the generic
#: ``mining_inventory`` store). Comparable total-coral cost to carving the
#: full curio shelf, so coral has two real sinks to choose between. The
#: pinned oracle defaults (goldens/fishing/sweep_tidepool pins the bytes).
_TIDE_POOL_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Reef Pool (×1.04 rarity pull)
    BuildCost(coins=1_500, materials={"coral": 3}),
    # → Tidal Basin (×1.08)
    BuildCost(coins=4_000, materials={"coral": 6}),
    # → Grand Reef (×1.12)
    BuildCost(coins=9_000, materials={"coral": 10}),
)

#: Dock build ladder — the *entry* coral structure: cheaper than the Tide
#: Pool and it adds a common material (wood) so a shore-heavy player can
#: afford it early with only a little coral. The pinned oracle defaults
#: (goldens/fishing/sweep_dock pins the bytes).
_DOCK_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Fishing Dock (×0.94 bite wait — 6% faster)
    BuildCost(coins=1_200, materials={"coral": 2, "wood": 15}),
    # → Deepwater Pier (×0.88 — 12% faster)
    BuildCost(coins=3_500, materials={"coral": 5, "wood": 30}),
)

#: Boathouse build ladder — a coral + **wood** sink priced *between* the
#: Dock and the Tide Pool (coral total 9, vs Dock 7 / Tide Pool 19). The
#: pinned oracle defaults (goldens/fishing/sweep_boathouse pins the bytes).
_BOATHOUSE_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Boathouse (×0.88 regen interval — 12% faster refill)
    BuildCost(coins=2_000, materials={"coral": 3, "wood": 20}),
    # → Grand Boathouse (×0.76 — 24% faster)
    BuildCost(coins=5_000, materials={"coral": 6, "wood": 40}),
)

#: Fishery build ladder — a coral + **wood** sink priced *above* the
#: Boathouse (coral total 12, vs Boathouse 9, Dock 7) — its yield payoff
#: compounds every catch, so it is the dearest of the three coral+wood
#: structures (the coral-only Tide Pool is dearer still on coral alone).
#: The pinned oracle defaults (goldens/fishing/sweep_fishery pins the bytes).
_FISHERY_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Fishery (+0.05 double-catch chance — 0.10 → 0.15)
    BuildCost(coins=2_500, materials={"coral": 4, "wood": 25}),
    # → Grand Fishery (+0.10 — 0.10 → 0.20)
    BuildCost(coins=6_000, materials={"coral": 8, "wood": 45}),
)


@dataclass(frozen=True)
class StructureDef:
    """A buildable structure: its display name, build ladder, and level names."""

    key: str
    display: str
    ladder: tuple[BuildCost, ...]
    level_names: tuple[str, ...]


#: The structure registry — the single source of truth for build math + naming.
_DEFS: dict[str, StructureDef] = {
    FORGE: StructureDef(FORGE, "Forge", _FORGE_BUILD_LADDER,
                        _FORGE_LEVEL_NAMES),
    HOME: StructureDef(HOME, "Home", _HOME_BUILD_LADDER, _HOME_LEVEL_NAMES),
    CAMPFIRE: StructureDef(CAMPFIRE, "Campfire", _CAMPFIRE_BUILD_LADDER,
                           _CAMPFIRE_LEVEL_NAMES),
    # the four coral fishing structures (oracle registry order verbatim)
    DOCK: StructureDef(DOCK, "Dock", _DOCK_BUILD_LADDER, _DOCK_LEVEL_NAMES),
    BOATHOUSE: StructureDef(
        BOATHOUSE,
        "Boathouse",
        _BOATHOUSE_BUILD_LADDER,
        _BOATHOUSE_LEVEL_NAMES,
    ),
    FISHERY: StructureDef(
        FISHERY,
        "Fishery",
        _FISHERY_BUILD_LADDER,
        _FISHERY_LEVEL_NAMES,
    ),
    TIDE_POOL: StructureDef(
        TIDE_POOL,
        "Tide Pool",
        _TIDE_POOL_BUILD_LADDER,
        _TIDE_POOL_LEVEL_NAMES,
    ),
}

STRUCTURES: tuple[str, ...] = tuple(_DEFS)

#: Highest forge level (level 2 unlocks the diamond tier — the top of the gear
#: ladder, so nothing above it needs a higher forge).
MAX_FORGE_LEVEL = len(_FORGE_BUILD_LADDER)

#: Highest Home level (the top cosmetic backdrop — the Grand Hall).
MAX_HOME_LEVEL = len(_HOME_BUILD_LADDER)

#: Highest Campfire level (a single buildable level).
MAX_CAMPFIRE_LEVEL = len(_CAMPFIRE_BUILD_LADDER)

#: Highest Tide Pool level (the top rarity-pull bonus).
MAX_TIDE_POOL_LEVEL = len(_TIDE_POOL_BUILD_LADDER)

#: Highest Dock level (the top bite-speed bonus).
MAX_DOCK_LEVEL = len(_DOCK_BUILD_LADDER)

#: Highest Boathouse level (the top energy-regen bonus).
MAX_BOATHOUSE_LEVEL = len(_BOATHOUSE_BUILD_LADDER)

#: Highest Fishery level (the top double-catch-chance bonus).
MAX_FISHERY_LEVEL = len(_FISHERY_BUILD_LADDER)


def cooking_unlocked(campfire_level: int) -> bool:
    """True if a campfire at *campfire_level* unlocks cooking (level >= 1)."""
    return campfire_level >= 1


def tide_pool_pull_mult(level: int) -> float:
    """The fishing rarity-pull multiplier a Tide Pool at *level* grants
    (≥ 1.0).

    Folded into the cast roll as the 5th "how-well" knob. Level 0
    (unbuilt) ⇒ exactly ``1.0`` so an existing cast is byte-identical —
    the additive-safety property the fishing gear knob relies on.
    Clamped to the ladder so an out-of-range level can never over-reward.
    """
    level = max(0, min(level, MAX_TIDE_POOL_LEVEL))
    return round(1.0 + _TIDE_POOL_PULL_STEP * level, 4)


def dock_bite_speed_mult(level: int) -> float:
    """The bite-speed multiplier a Dock at *level* grants (≤ 1.0 — lower
    = faster).

    Folded into the cast's ``effective_bite_speed`` (the same knob
    rod/bait use, where a smaller value means a shorter bite wait).
    Level 0 (unbuilt) ⇒ exactly ``1.0`` ⇒ byte-identical. Clamped to the
    ladder.
    """
    level = max(0, min(level, MAX_DOCK_LEVEL))
    return round(1.0 - _DOCK_BITE_STEP * level, 4)


def boathouse_regen_mult(level: int) -> float:
    """The energy-regen multiplier a Boathouse at *level* grants (≤ 1.0
    — lower = faster).

    Applied to the fishing ``REGEN_SECONDS`` interval, where a shorter
    interval means faster passive energy refill. Level 0 (unbuilt) ⇒
    exactly ``1.0`` ⇒ the interval is unchanged ⇒ byte-identical energy.
    Clamped to the ladder so an out-of-range level can never over-reward.
    """
    level = max(0, min(level, MAX_BOATHOUSE_LEVEL))
    return round(1.0 - _BOATHOUSE_REGEN_STEP * level, 4)


def fishery_bonus_chance(level: int) -> float:
    """The double-catch-chance bonus a Fishery at *level* grants (≥ 0.0
    — higher = more).

    **Added** to the base ``BONUS_CATCH_CHANCE`` at catch-commit time
    (the effective chance is clamped to ``[0, 1]`` there). Level 0
    (unbuilt) ⇒ exactly ``0.0`` ⇒ the base chance is unchanged ⇒
    byte-identical catch economics. Clamped to the ladder so an
    out-of-range level can never over-reward.
    """
    level = max(0, min(level, MAX_FISHERY_LEVEL))
    return round(_FISHERY_BONUS_STEP * level, 4)


def is_structure(name: str) -> bool:
    """True if *name* is a buildable structure (case/space-insensitive)."""
    return name.strip().lower() in _DEFS


# --------------------------------------------------------------------------- #
# Generic per-structure build math — the registry-driven source of truth.
# --------------------------------------------------------------------------- #


def display_name(structure: str) -> str:
    """The human display name of *structure* (e.g. ``"Forge"``)."""
    return _DEFS[structure].display


def max_level(structure: str) -> int:
    """The highest level *structure* can reach (= its build-ladder length)."""
    return len(_DEFS[structure].ladder)


def level_name(structure: str, level: int) -> str:
    """A short display name for *structure* at *level* (clamped to its ladder)."""
    defn = _DEFS[structure]
    level = max(0, min(level, len(defn.ladder)))
    return defn.level_names[level]


def build_cost(structure: str, level: int) -> BuildCost | None:
    """Cost to upgrade *structure* **from** *level* to *level* + 1, or ``None``
    if maxed."""
    defn = _DEFS[structure]
    if level < 0 or level >= len(defn.ladder):
        return None
    return defn.ladder[level]


# --------------------------------------------------------------------------- #
# Forge-specific helpers — thin wrappers over the generic math (the Slice B
# forge panel shape; behaviour byte-identical to the oracle).
# --------------------------------------------------------------------------- #


def forge_level_name(level: int) -> str:
    """A short display name for a forge at *level* (clamped to the ladder)."""
    return level_name(FORGE, level)


def forge_build_cost(level: int) -> BuildCost | None:
    """Cost to upgrade the forge **from** *level* to *level* + 1, or ``None`` if
    maxed."""
    return build_cost(FORGE, level)


def forge_level_required(recipe_name: str) -> int:
    """Minimum forge level needed to craft *recipe_name* (0 = no forge needed).

    Derived from the recipe product's gear tier: only gold/diamond set-gear
    gates. Tools, structures, starters, and bronze/iron/silver gear all return
    0, so the overwhelming majority of recipes are forge-free (the additive
    property — existing craft paths never change behaviour).
    """
    tier = equipment.gear_tier(recipe_name)
    if tier is None:
        return 0
    return max(0, equipment.tier_index(tier) - FREE_TIER_CEILING)


def meets_forge_requirement(recipe_name: str, forge_level: int) -> bool:
    """True if a forge at *forge_level* may craft *recipe_name*."""
    return forge_level >= forge_level_required(recipe_name)


def tiers_unlocked_at(forge_level: int) -> tuple[str, ...]:
    """The gear tiers a forge at *forge_level* unlocks **beyond** the free tiers.

    For the panel: Forge I → ("gold",), Forge II → ("gold", "diamond"). An
    unbuilt forge unlocks nothing extra (the free tiers craft without it).
    """
    unlocked: list[str] = []
    for tier in equipment.TIER_ORDER:
        need = max(0, equipment.tier_index(tier) - FREE_TIER_CEILING)
        if 0 < need <= forge_level:
            unlocked.append(tier)
    return tuple(unlocked)


__all__ = [
    "FORGE",
    "HOME",
    "CAMPFIRE",
    "TIDE_POOL",
    "DOCK",
    "BOATHOUSE",
    "FISHERY",
    "STRUCTURES",
    "MAX_FORGE_LEVEL",
    "MAX_HOME_LEVEL",
    "MAX_CAMPFIRE_LEVEL",
    "MAX_TIDE_POOL_LEVEL",
    "MAX_DOCK_LEVEL",
    "MAX_BOATHOUSE_LEVEL",
    "MAX_FISHERY_LEVEL",
    "FREE_TIER_CEILING",
    "BuildCost",
    "StructureDef",
    "is_structure",
    "cooking_unlocked",
    "tide_pool_pull_mult",
    "dock_bite_speed_mult",
    "boathouse_regen_mult",
    "fishery_bonus_chance",
    "display_name",
    "max_level",
    "level_name",
    "build_cost",
    "forge_level_name",
    "forge_build_cost",
    "forge_level_required",
    "meets_forge_requirement",
    "tiers_unlocked_at",
]
