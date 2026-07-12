"""Mining structures (band 6, slice 4) — pure build/gating math for the §7.5
structure sinks, ported from the oracle ``disbot/utils/mining/structures.py``.

Slice 4 scope: the **Forge** (a built coin + material sink that unlocks
higher-tier gear crafting) and the **Campfire** (a cheap single-level structure
that gates cooking fish into food). Both are ``(user, guild, structure, level)``
rows in the generic ``mining_structures`` table and share one ``BuildCost``
shape. The remaining oracle structures (Home + the four coral fishing
structures) ride their own deferred systems (the Home backdrop / the fishing
port), so only the two slice-4 structures are declared here — the bounded-port
convention this module set follows for capacity.py (vault only) and world.py
(depth only).

Design (kept **additive**, verbatim from the oracle): the forge requirement is
derived from a recipe's gear tier, but only the **top two** tiers gate —
bronze / iron / silver gear, every tool, and every structure stay craftable at
forge level 0, so existing play is unchanged until a player reaches gold/diamond
gear. Gold needs a level-1 forge, diamond a level-2 forge.

This is a pure-math module: it imports stdlib + ``sb.domain.mining.equipment``
only (no store / db), so the panel, op, and handler layers share one source of
truth. The numbers are the pinned oracle defaults
(docs/planning/forge-numbers-2026-06-15.md).

Guard-only-capture (A-16): the row-bearing build write (`!forge` 🔥 Build /
`!build campfire`) rides the deferred structures BUILD system (the `!build`
command stays a D-0043 pending terminal this slice); every imported sweep drove
only the bare `!forge` — which renders the not-built card off the store's no-row
level 0 (goldens/mining/sweep_forge.json) — so mining_structures is a
declared-but-guard-only mining surface (depth.exemptions.mining).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sb.domain.mining import equipment

#: The buildable structures declared this slice. Each is a
#: ``(user, guild, structure, level)`` row in the generic ``mining_structures``
#: table and shares the same build math.
FORGE = "forge"
CAMPFIRE = "campfire"

#: Gear at or below this tier index needs **no** forge (bronze=1, iron=2,
#: silver=3 are free; gold=4 → forge 1; diamond=5 → forge 2). ``forge_level =
#: max(0, tier_index - FREE_TIER_CEILING)``.
FREE_TIER_CEILING = 3

#: The forge level shown in the panel / gate message per level.
_FORGE_LEVEL_NAMES = ("(not built)", "Forge I", "Forge II")

#: Campfire (2026-06-22, owner-chosen): a cheap single-level structure that
#: gates cooking fish into food (energy refill). A small coin + material sink,
#: buildable early — a progression beat, not a wall.
_CAMPFIRE_LEVEL_NAMES = ("(not built)", "Campfire")


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

#: Campfire build ladder — one cheap level that unlocks cooking.
_CAMPFIRE_BUILD_LADDER: tuple[BuildCost, ...] = (
    # → Campfire (unlocks !cook)
    BuildCost(coins=500, materials={"wood": 20, "stone": 10}),
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
    CAMPFIRE: StructureDef(CAMPFIRE, "Campfire", _CAMPFIRE_BUILD_LADDER,
                           _CAMPFIRE_LEVEL_NAMES),
}

STRUCTURES: tuple[str, ...] = tuple(_DEFS)

#: Highest forge level (level 2 unlocks the diamond tier — the top of the gear
#: ladder, so nothing above it needs a higher forge).
MAX_FORGE_LEVEL = len(_FORGE_BUILD_LADDER)

#: Highest Campfire level (a single buildable level).
MAX_CAMPFIRE_LEVEL = len(_CAMPFIRE_BUILD_LADDER)


def cooking_unlocked(campfire_level: int) -> bool:
    """True if a campfire at *campfire_level* unlocks cooking (level >= 1)."""
    return campfire_level >= 1


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
    "CAMPFIRE",
    "STRUCTURES",
    "MAX_FORGE_LEVEL",
    "MAX_CAMPFIRE_LEVEL",
    "FREE_TIER_CEILING",
    "BuildCost",
    "StructureDef",
    "is_structure",
    "cooking_unlocked",
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
