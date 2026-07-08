"""Economy data tables — shipped verbatim (band 3).

JOBS / SHOP_ITEMS / daily tiers from services/economy_helpers.py; the full
ITEM_CATALOGUE from cogs/inventory_cog.py. The catalogue is THE coupled item
namespace (INV-F note in the band contract): every item name any band-3
surface grants or requires MUST resolve here — `assert_item_namespace()` is
the compile-shape fence the unit suite pins. Mining/fishing rows are listed
now (catalogue metadata is static display data); their STORES stay band 6.

Pure data + pure functions; the ONE randomness point takes an injectable
``random.Random``.
"""

from __future__ import annotations

import random

__all__ = [
    "CATEGORY_META",
    "CATEGORY_ORDER",
    "DAILY_COOLDOWN",
    "DAILY_TIERS",
    "ITEM_CATALOGUE",
    "JOBS",
    "RARITY_ORDER",
    "RARITY_TIERS",
    "SHOP_ITEMS",
    "WORK_COOLDOWN",
    "assert_item_namespace",
    "daily_weights",
    "job_pay",
    "pick_daily",
]

# Cooldown configuration (seconds) — shipped verbatim.
WORK_COOLDOWN = 3600     # 1 hour between work sessions
DAILY_COOLDOWN = 86400   # 24 hours between daily claims

# Daily reward tiers (label, rarity_emoji, min, max, base_weight) — verbatim.
DAILY_TIERS: tuple[tuple[str, str, int, int, int], ...] = (
    ("Common", "⬜", 500, 999, 45),
    ("Uncommon", "🟩", 1000, 1999, 25),
    ("Rare", "🟦", 2000, 2999, 15),
    ("Epic", "🟪", 3000, 3999, 8),
    ("Legendary", "🟧", 4000, 4999, 5),
    ("Mythic", "🟥", 5000, 5000, 2),
)

# Job definitions {name: {tier, pay, xp, level, items, emoji, desc}} — verbatim.
JOBS: dict[str, dict] = {
    # Tier 1 — no requirements
    "janitor": {"tier": 1, "pay": 50, "xp": 10, "level": 0, "items": [],
                "emoji": "🧹", "desc": "Sweep floors and empty bins."},
    "cashier": {"tier": 1, "pay": 75, "xp": 15, "level": 0, "items": [],
                "emoji": "🏪", "desc": "Run the register at a store."},
    "dishwasher": {"tier": 1, "pay": 60, "xp": 12, "level": 0, "items": [],
                   "emoji": "🍽️", "desc": "Wash dishes at a restaurant."},
    # Tier 2 — level 5+
    "security_guard": {"tier": 2, "pay": 150, "xp": 25, "level": 5, "items": [],
                       "emoji": "🔒", "desc": "Guard an office building."},
    "delivery_driver": {"tier": 2, "pay": 200, "xp": 30, "level": 5,
                        "items": ["car"], "emoji": "🚗",
                        "desc": "Deliver packages around town."},
    "chef": {"tier": 2, "pay": 175, "xp": 28, "level": 5, "items": [],
             "emoji": "👨‍🍳", "desc": "Cook meals at a restaurant."},
    # Tier 3 — level 15+
    "programmer": {"tier": 3, "pay": 400, "xp": 50, "level": 15, "items": [],
                   "emoji": "💻", "desc": "Write software for clients."},
    "mechanic": {"tier": 3, "pay": 350, "xp": 45, "level": 15,
                 "items": ["toolkit"], "emoji": "🔧",
                 "desc": "Repair vehicles at the garage."},
    "nurse": {"tier": 3, "pay": 380, "xp": 48, "level": 15, "items": [],
              "emoji": "👩‍⚕️", "desc": "Care for patients at the clinic."},
    # Tier 4 — level 30+
    "lawyer": {"tier": 4, "pay": 800, "xp": 80, "level": 30, "items": ["suit"],
               "emoji": "⚖️", "desc": "Represent clients in court."},
    "doctor": {"tier": 4, "pay": 900, "xp": 90, "level": 30, "items": [],
               "emoji": "👨‍⚕️", "desc": "Treat patients at the hospital."},
    "ceo": {"tier": 4, "pay": 1200, "xp": 100, "level": 50,
            "items": ["suit", "car"], "emoji": "👔",
            "desc": "Run your own company."},
}

# Shop items — verbatim.
SHOP_ITEMS: dict[str, dict] = {
    "car": {"price": 5000, "emoji": "🚗",
            "desc": "Required for delivery driver and CEO."},
    "toolkit": {"price": 2000, "emoji": "🔧",
                "desc": "Required for mechanic work."},
    "suit": {"price": 3000, "emoji": "👔",
             "desc": "Required for lawyer and CEO roles."},
}

# --- the coupled item namespace (cogs/inventory_cog.py ITEM_CATALOGUE, verbatim) --

ITEM_CATALOGUE: dict[str, dict] = {
    # Mining Materials (mining_inventory table — band 6 stores)
    "stone": {"category": "Mining Materials", "emoji": "🪨", "type": "Ore",
              "rarity": "Common"},
    "iron": {"category": "Mining Materials", "emoji": "⚙️", "type": "Ore",
             "rarity": "Uncommon"},
    "gold": {"category": "Mining Materials", "emoji": "🥇", "type": "Ore",
             "rarity": "Rare"},
    "diamond": {"category": "Mining Materials", "emoji": "💎", "type": "Gem",
                "rarity": "Epic"},
    "wood": {"category": "Mining Materials", "emoji": "🪵", "type": "Resource",
             "rarity": "Common"},
    # Crafted/built structures (mining_inventory after !build)
    "stone hut": {"category": "Crafted Items", "emoji": "🏚️",
                  "type": "Structure", "rarity": "Common"},
    "wooden house": {"category": "Crafted Items", "emoji": "🏠",
                     "type": "Structure", "rarity": "Uncommon"},
    "gold statue": {"category": "Crafted Items", "emoji": "🗿",
                    "type": "Structure", "rarity": "Rare"},
    "diamond throne": {"category": "Crafted Items", "emoji": "💺",
                       "type": "Structure", "rarity": "Epic"},
    # Tools (mining_inventory + economy inventory)
    "iron pickaxe": {"category": "Tools", "emoji": "⛏️", "type": "Tool",
                     "rarity": "Uncommon"},
    "axe": {"category": "Tools", "emoji": "🪓", "type": "Tool",
            "rarity": "Uncommon"},
    "toolkit": {"category": "Tools", "emoji": "🔧", "type": "Job Unlock",
                "rarity": "Uncommon"},
    # Economy items (inventory table, guild-scoped)
    "car": {"category": "Economy Items", "emoji": "🚗", "type": "Job Unlock",
            "rarity": "Rare"},
    "suit": {"category": "Economy Items", "emoji": "👔", "type": "Job Unlock",
             "rarity": "Rare"},
    # Fishing rare materials (mining_inventory) — reel-drop crafting materials.
    "pearl": {"category": "Fishing", "emoji": "🦪", "type": "Material",
              "rarity": "Rare"},
    "coral": {"category": "Fishing", "emoji": "🪸", "type": "Material",
              "rarity": "Rare"},
    # Fishing curios (mining_inventory) — cosmetic carvings crafted from coral.
    "coral shell": {"category": "Collectibles", "emoji": "🐚", "type": "Curio",
                    "rarity": "Uncommon"},
    "coral seahorse": {"category": "Collectibles", "emoji": "🌊",
                       "type": "Curio", "rarity": "Rare"},
    "coral idol": {"category": "Collectibles", "emoji": "🗿", "type": "Curio",
                   "rarity": "Epic"},
}

CATEGORY_ORDER: tuple[str, ...] = (
    "Mining Materials", "Crafted Items", "Tools", "Fishing", "Collectibles",
    "Economy Items",
)

CATEGORY_META: dict[str, dict] = {
    "Mining Materials": {"emoji": "⛏️"},
    "Crafted Items": {"emoji": "🏗️"},
    "Tools": {"emoji": "🔧"},
    "Fishing": {"emoji": "🎣"},
    "Collectibles": {"emoji": "🏆"},
    "Economy Items": {"emoji": "💼"},
    "Other": {"emoji": "📦"},
}

RARITY_ORDER: dict[str, int] = {"Epic": 0, "Rare": 1, "Uncommon": 2, "Common": 3}
RARITY_TIERS: tuple[str, ...] = ("Epic", "Rare", "Uncommon", "Common", "Unknown")


def assert_item_namespace() -> None:
    """INV-F coupling fence: every shop item and every job requirement is a
    catalogue name — the item namespace has ONE authority."""
    missing = [name for name in SHOP_ITEMS if name not in ITEM_CATALOGUE]
    for job, data in JOBS.items():
        missing.extend(f"{job}:{item}" for item in data["items"]
                       if item not in ITEM_CATALOGUE)
    if missing:
        raise ValueError(f"item names outside ITEM_CATALOGUE: {missing}")


# --- pure reward math (economy_helpers.py verbatim) --------------------------------

def daily_weights(streak: int) -> list[float]:
    """Higher streak shifts weight toward better tiers (capped at 60 days)."""
    luck = min(streak, 60)
    weights = [float(t[4]) for t in DAILY_TIERS]
    shift = luck * 0.25
    take_c = min(weights[0] - 5, shift * 0.65)
    take_u = min(weights[1] - 5, shift * 0.35)
    taken = take_c + take_u
    weights[0] -= take_c
    weights[1] -= take_u
    per = taken / 4
    for i in range(2, 6):
        weights[i] += per
    return weights


def pick_daily(streak: int, rng: random.Random | None = None) -> tuple[int, str, str]:
    """Return (amount, tier_label, rarity_emoji) for a daily claim."""
    r = rng or random
    weights = daily_weights(streak)
    tier = r.choices(DAILY_TIERS, weights=weights, k=1)[0]
    label, emoji, low, high, _ = tier
    return r.randint(low, high), label, emoji


def job_pay(job_name: str, times_worked: int) -> int:
    """Base pay × (1 + min(times_worked, 100) / 100)."""
    base = JOBS[job_name]["pay"]
    return int(base * (1 + min(times_worked, 100) / 100))
