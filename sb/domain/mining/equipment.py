"""Equipment — pure, cross-game gear→stats model (ported verbatim from the
oracle ``disbot/utils/equipment.py``, superbot @ b7d017d).

Maps the items a player has *equipped* into slots onto a generic
:class:`EffectiveStats` block that game logic reads.  This is the cross-game
"what is my character good at?" read model: a game asks for the stats, never
for specific item names.

It is pure (stdlib-only, no Discord/DB/state) precisely *because* it is
shared: mining reads ``mining_power``/``light_radius``/``depth_access``,
deathmatch reads ``damage``/``defense``/``max_health`` (the D-0045 baseline —
``compute_stats({})`` is all-zero, so every fresh gearless persona duels at
the shipped baseline and no deathmatch/casino golden moves), and a future
stat service can build on it too.

Slots and per-item stats are deliberately data (``_GEAR``): extend by adding
rows.  The combat slots follow the set-piece model (owner decision Q-0092):
weapon + shield + the four armor pieces, each a 5-tier family
(bronze < iron < silver < gold < diamond), with a small same-tier full-set
bonus so collecting a complete set is a goal.
"""

from __future__ import annotations

from dataclasses import dataclass

# Equipment slots — each holds at most one item.  Mining slots (tool/light/
# charm) feed the mining stats; the six combat slots (weapon/shield + the four
# armor pieces) feed the deathmatch stats.  One equip/unequip path serves
# every slot.
TOOL = "tool"
LIGHT = "light"
CHARM = "charm"
WEAPON = "weapon"
SHIELD = "shield"
HELMET = "helmet"
CHESTPLATE = "chestplate"
LEGGINGS = "leggings"
BOOTS = "boots"
SLOTS: tuple[str, ...] = (
    TOOL,
    LIGHT,
    CHARM,
    WEAPON,
    SHIELD,
    HELMET,
    CHESTPLATE,
    LEGGINGS,
    BOOTS,
)

# The set-piece slots: a full same-tier loadout across these six grants the
# set bonus.  Mining slots are deliberately excluded — sets are a combat goal.
SET_SLOTS: tuple[str, ...] = (WEAPON, SHIELD, HELMET, CHESTPLATE, LEGGINGS, BOOTS)

# Gear tiers, weakest → strongest.
TIER_ORDER: tuple[str, ...] = ("bronze", "iron", "silver", "gold", "diamond")


@dataclass(frozen=True)
class EffectiveStats:
    """Generic, game-neutral stat block computed from equipped gear (and,
    later, skills).  Each game reads only the subset it cares about — no game
    imports the item catalog.
    """

    mining_power: int = 0
    light_radius: int = 0
    depth_access: int = 0
    luck: int = 0
    loot_bonus: int = 0
    # Combat gear (deathmatch / PvP).
    damage: int = 0
    defense: int = 0
    max_health: int = 0
    # Fishing gear (Q-0175 / V-14 "matching gear → better fishing").
    fishing_power: int = 0  # biases the catch toward the big end of the band
    bite_luck: int = 0  # quickens the bite wait

    def __add__(self, other: EffectiveStats) -> EffectiveStats:
        return EffectiveStats(
            mining_power=self.mining_power + other.mining_power,
            light_radius=self.light_radius + other.light_radius,
            depth_access=self.depth_access + other.depth_access,
            luck=self.luck + other.luck,
            loot_bonus=self.loot_bonus + other.loot_bonus,
            damage=self.damage + other.damage,
            defense=self.defense + other.defense,
            max_health=self.max_health + other.max_health,
            fishing_power=self.fishing_power + other.fishing_power,
            bite_luck=self.bite_luck + other.bite_luck,
        )


# Display labels for the stat fields, in display order.  Keys MUST match the
# EffectiveStats field names.
STAT_LABELS: dict[str, str] = {
    "mining_power": "Mining power",
    "light_radius": "Light",
    "depth_access": "Depth access",
    "luck": "Luck",
    "loot_bonus": "Loot bonus",
    "damage": "Damage",
    "defense": "Defense",
    "max_health": "Max health",
    "fishing_power": "Fishing power",
    "bite_luck": "Bite luck",
}

# Compact glyphs for tight surfaces (shop rows, recipe pickers), damage/defence
# first so combat gear compares at a glance.  Keys MUST be EffectiveStats fields.
STAT_GLYPHS: dict[str, str] = {
    "damage": "⚔️",
    "defense": "🛡️",
    "max_health": "❤️",
    "mining_power": "⛏️",
    "light_radius": "💡",
    "depth_access": "🔽",
    "luck": "🍀",
    "loot_bonus": "💰",
    "fishing_power": "🎣",
    "bite_luck": "🐟",
}


# Which slot each gear item fits, and the stats it contributes.
_GEAR: dict[str, tuple[str, EffectiveStats]] = {
    "pickaxe": (TOOL, EffectiveStats(mining_power=2)),
    "iron pickaxe": (TOOL, EffectiveStats(mining_power=4)),
    "gold pickaxe": (TOOL, EffectiveStats(mining_power=6)),
    "diamond pickaxe": (TOOL, EffectiveStats(mining_power=8, luck=1)),
    "torch": (LIGHT, EffectiveStats(light_radius=1, depth_access=1)),
    "lantern": (LIGHT, EffectiveStats(light_radius=2, depth_access=2)),
    "diamond lantern": (LIGHT, EffectiveStats(light_radius=3, depth_access=3)),
    "lucky charm": (CHARM, EffectiveStats(luck=1, loot_bonus=1)),
    "fishing charm": (CHARM, EffectiveStats(fishing_power=2, bite_luck=1)),
    "anglers charm": (CHARM, EffectiveStats(fishing_power=4, bite_luck=2)),
    "master angler charm": (CHARM, EffectiveStats(fishing_power=6, bite_luck=3)),
    # Starter combat gear — pre-metal entry pieces, strictly below bronze.
    "sword": (WEAPON, EffectiveStats(damage=3)),
    "shield": (SHIELD, EffectiveStats(defense=2, max_health=10)),
    # Swords (weapon slot).
    "bronze sword": (WEAPON, EffectiveStats(damage=4)),
    "iron sword": (WEAPON, EffectiveStats(damage=6)),
    "silver sword": (WEAPON, EffectiveStats(damage=7)),
    "gold sword": (WEAPON, EffectiveStats(damage=8)),
    "diamond sword": (WEAPON, EffectiveStats(damage=10)),
    # Shields.
    "bronze shield": (SHIELD, EffectiveStats(defense=2, max_health=12, damage=1)),
    "iron shield": (SHIELD, EffectiveStats(defense=3, max_health=14, damage=1)),
    "silver shield": (SHIELD, EffectiveStats(defense=3, max_health=16, damage=2)),
    "gold shield": (SHIELD, EffectiveStats(defense=4, max_health=18, damage=2)),
    "diamond shield": (SHIELD, EffectiveStats(defense=4, max_health=20, damage=2)),
    # Helmets.
    "bronze helmet": (HELMET, EffectiveStats(defense=1, max_health=2)),
    "iron helmet": (HELMET, EffectiveStats(defense=1, max_health=3)),
    "silver helmet": (HELMET, EffectiveStats(defense=2, max_health=4)),
    "gold helmet": (HELMET, EffectiveStats(defense=2, max_health=5)),
    "diamond helmet": (HELMET, EffectiveStats(defense=2, max_health=6)),
    # Chestplates.
    "bronze chestplate": (CHESTPLATE, EffectiveStats(defense=2, max_health=6)),
    "iron chestplate": (CHESTPLATE, EffectiveStats(defense=2, max_health=8)),
    "silver chestplate": (CHESTPLATE, EffectiveStats(defense=3, max_health=10)),
    "gold chestplate": (CHESTPLATE, EffectiveStats(defense=3, max_health=12)),
    "diamond chestplate": (CHESTPLATE, EffectiveStats(defense=4, max_health=15)),
    # Leggings.
    "bronze leggings": (LEGGINGS, EffectiveStats(defense=1, max_health=4)),
    "iron leggings": (LEGGINGS, EffectiveStats(defense=1, max_health=5)),
    "silver leggings": (LEGGINGS, EffectiveStats(defense=2, max_health=6)),
    "gold leggings": (LEGGINGS, EffectiveStats(defense=2, max_health=8)),
    "diamond leggings": (LEGGINGS, EffectiveStats(defense=2, max_health=10)),
    # Boots.
    "bronze boots": (BOOTS, EffectiveStats(defense=1, max_health=2)),
    "iron boots": (BOOTS, EffectiveStats(defense=1, max_health=3)),
    "silver boots": (BOOTS, EffectiveStats(defense=1, max_health=4)),
    "gold boots": (BOOTS, EffectiveStats(defense=2, max_health=5)),
    "diamond boots": (BOOTS, EffectiveStats(defense=2, max_health=6)),
}

# Same-tier full-set bonus (Q-0092): equipping all six SET_SLOTS with gear of
# one tier adds ``damage = tier_index`` and ``max_health = 3 × tier_index``
# (bronze +1/+3 … diamond +5/+15).  Defense is deliberately NOT in the bonus.
SET_BONUS_DAMAGE_PER_TIER = 1
SET_BONUS_HEALTH_PER_TIER = 3


# Max durability — how many uses the "active" unit of a gear item survives
# before it breaks.  Items absent from this table never wear.
MAX_DURABILITY: dict[str, int] = {
    "pickaxe": 60,
    "iron pickaxe": 150,
    "gold pickaxe": 220,
    "diamond pickaxe": 400,
    "torch": 40,
    "lantern": 100,
    "diamond lantern": 180,
    "lucky charm": 80,
    "fishing charm": 80,
    "anglers charm": 140,
    "master angler charm": 220,
    "sword": 60,
    "shield": 90,
}

# Combat-set durability — one ladder for all six families.
_SET_DURABILITY: tuple[int, ...] = (80, 150, 200, 260, 320)
_SET_FAMILIES: tuple[str, ...] = (
    "sword",
    "shield",
    "helmet",
    "chestplate",
    "leggings",
    "boots",
)
MAX_DURABILITY.update(
    {
        f"{tier} {family}": _SET_DURABILITY[i]
        for i, tier in enumerate(TIER_ORDER)
        for family in _SET_FAMILIES
    },
)


def max_durability(item_name: str) -> int | None:
    """Uses before *item_name* breaks, or None if it does not wear."""
    return MAX_DURABILITY.get(item_name.lower())


def gear_names() -> tuple[str, ...]:
    """Every equippable item name (for fuzzy resolution / pickers)."""
    return tuple(_GEAR)


def slot_for(item_name: str) -> str | None:
    """The slot *item_name* equips into, or None if it is not equippable."""
    entry = _GEAR.get(item_name.lower())
    return entry[0] if entry else None


def is_equippable(item_name: str) -> bool:
    return slot_for(item_name) is not None


def item_stats(item_name: str) -> EffectiveStats:
    """Stat contribution of a single gear item (all-zero if unknown)."""
    entry = _GEAR.get(item_name.lower())
    return entry[1] if entry else EffectiveStats()


def gear_tier(item_name: str) -> str | None:
    """The set tier of *item_name* (``"bronze"`` … ``"diamond"``), or None.

    Only set-slot gear is tiered.  Starters ("sword", "shield") and mining
    gear return None.
    """
    entry = _GEAR.get(item_name.lower())
    if entry is None or entry[0] not in SET_SLOTS:
        return None
    first = item_name.lower().split()[0]
    return first if first in TIER_ORDER else None


def tier_index(tier: str) -> int:
    """1-based strength index of *tier* (bronze=1 … diamond=5)."""
    return TIER_ORDER.index(tier) + 1


def material_rank(item_name: str) -> int:
    """Rarity rank of any item by its material prefix — ``0`` for a starter/base
    item, else the 1-based tier rank (bronze=1 … diamond=5).
    """
    first = item_name.lower().split()[0] if item_name else ""
    return TIER_ORDER.index(first) + 1 if first in TIER_ORDER else 0


def active_set_tier(equipped: dict[str, str]) -> str | None:
    """The tier of a complete same-tier combat set, or None."""
    tiers: set[str] = set()
    for slot in SET_SLOTS:
        tier = gear_tier(equipped.get(slot, ""))
        if tier is None:
            return None
        tiers.add(tier)
    return tiers.pop() if len(tiers) == 1 else None


def set_bonus(equipped: dict[str, str]) -> EffectiveStats:
    """The same-tier full-set bonus for *equipped* (all-zero without a set)."""
    tier = active_set_tier(equipped)
    if tier is None:
        return EffectiveStats()
    idx = tier_index(tier)
    return EffectiveStats(
        damage=SET_BONUS_DAMAGE_PER_TIER * idx,
        max_health=SET_BONUS_HEALTH_PER_TIER * idx,
    )


def set_progress(equipped: dict[str, str]) -> tuple[str, int] | None:
    """``(tier, pieces_equipped)`` for the player's most-advanced partial set.

    Ties break toward the stronger tier; returns None when no set-slot item is
    tiered.
    """
    counts: dict[str, int] = {}
    for slot in SET_SLOTS:
        tier = gear_tier(equipped.get(slot, ""))
        if tier is not None:
            counts[tier] = counts.get(tier, 0) + 1
    if not counts:
        return None
    best = max(counts, key=lambda t: (counts[t], tier_index(t)))
    return best, counts[best]


def compute_stats(equipped: dict[str, str]) -> EffectiveStats:
    """Sum the stats of every equipped item, plus any full-set bonus.

    *equipped* is ``{slot: name}``.  ``compute_stats({})`` is all-zero (the
    D-0045 baseline every gearless persona reads).
    """
    total = EffectiveStats()
    for item_name in equipped.values():
        total = total + item_stats(item_name)
    return total + set_bonus(equipped)


def describe_stats(stats: EffectiveStats) -> list[tuple[str, int]]:
    """Non-zero ``(label, value)`` pairs in display order — pure (no Discord)."""
    return [
        (STAT_LABELS[name], getattr(stats, name))
        for name in STAT_LABELS
        if getattr(stats, name)
    ]


def describe_stats_compact(item_name: str) -> str:
    """Compact glyph stat line for *item_name* — ``"⚔️+6"`` /
    ``"⚔️+1 🛡️+3 ❤️+14"`` (damage/defence first), or ``""`` for an item with
    no stats.
    """
    stats = item_stats(item_name)
    return " ".join(
        f"{STAT_GLYPHS[field]}+{getattr(stats, field)}"
        for field in STAT_GLYPHS
        if getattr(stats, field)
    )


__all__ = [
    "TOOL",
    "LIGHT",
    "CHARM",
    "WEAPON",
    "SHIELD",
    "HELMET",
    "CHESTPLATE",
    "LEGGINGS",
    "BOOTS",
    "SLOTS",
    "SET_SLOTS",
    "TIER_ORDER",
    "SET_BONUS_DAMAGE_PER_TIER",
    "SET_BONUS_HEALTH_PER_TIER",
    "EffectiveStats",
    "STAT_LABELS",
    "STAT_GLYPHS",
    "MAX_DURABILITY",
    "max_durability",
    "gear_names",
    "slot_for",
    "is_equippable",
    "item_stats",
    "gear_tier",
    "tier_index",
    "material_rank",
    "active_set_tier",
    "set_bonus",
    "set_progress",
    "compute_stats",
    "describe_stats",
    "describe_stats_compact",
]
