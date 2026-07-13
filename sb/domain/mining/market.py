"""Mining market — sell values + the gear shop, from the shipped
``utils/mining/{items,market}.py``. Only catalogued RESOURCES sell (the
faucet); tools/gear/unknown items never sell back (no arbitrage, no
minting from junk — shipped verbatim). Fish are size-valued resources
(1…21 by size rank, the shipped ``_fish_value`` rule)."""

from __future__ import annotations

__all__ = [
    "GEAR_SHOP",
    "RESOURCE_VALUES",
    "VAULT_UPGRADE_REASON",
    "sell_price",
    "sellable_inventory",
    "shop_listing",
    "structure_build_reason",
]

#: The economy-ledger reason tag for the vault-capacity coin sink (shipped
#: ``utils/mining/market.py`` VAULT_UPGRADE_REASON verbatim).
VAULT_UPGRADE_REASON = "mining:vault_upgrade"


def structure_build_reason(structure: str) -> str:
    """The economy-audit reason tag for building *structure* (the
    money-flow tag) — shipped ``utils/mining/market.py``
    ``structure_build_reason`` verbatim.

    Derived generically as ``mining:{structure}_build`` — exactly what
    the oracle's named ``*_BUILD_REASON`` constants spelled; the generic
    derivation means a newly-registered structure can **never** crash the
    build path for want of a map entry (the oracle's boathouse
    ``KeyError``, BUG-0031). The ``mining:`` prefix is kept for the
    fishing structures too — they are ``mining_structures`` rows and the
    oracle tagged their debits identically (``mining:tide_pool_build``
    et al.).
    """
    return f"mining:{structure.strip().lower()}_build"

#: The shipped RESOURCE rows (items.py): commonness inverse of worth.
RESOURCE_VALUES: dict[str, int] = {
    "wood": 1, "stone": 1, "bronze": 2, "iron": 3, "silver": 4,
    "gold": 6, "diamond": 12,
}

#: Gear shop (coins to buy — the sink; shipped verbatim). Purchases land
#: in mining_inventory; the equipment system rides the deferred depth
#: port, so bought tools apply via the legacy inventory bonuses only.
GEAR_SHOP: dict[str, int] = {
    "torch": 10, "pickaxe": 25, "sword": 25, "shield": 30,
    "dynamite": 30, "lantern": 40, "iron pickaxe": 60, "lucky charm": 80,
    "fishing charm": 90, "anglers charm": 220, "master angler charm": 420,
    "ration": 20, "energy drink": 40, "gold pickaxe": 140,
    "diamond lantern": 200, "diamond pickaxe": 320,
    "bronze sword": 30, "iron sword": 60, "silver sword": 75,
    "gold sword": 95, "diamond sword": 180,
    "bronze shield": 40, "iron shield": 65, "silver shield": 85,
    "gold shield": 110, "diamond shield": 200,
    "bronze helmet": 35, "iron helmet": 55, "silver helmet": 75,
    "gold helmet": 105, "diamond helmet": 190,
    "bronze chestplate": 55, "iron chestplate": 85,
    "silver chestplate": 115, "gold chestplate": 160,
    "diamond chestplate": 280,
    "bronze leggings": 45, "iron leggings": 70, "silver leggings": 95,
    "gold leggings": 135, "diamond leggings": 240,
    "bronze boots": 25, "iron boots": 40, "silver boots": 55,
    "gold boots": 75, "diamond boots": 130,
}


def _fish_values() -> dict[str, int]:
    from sb.domain.fishing.catalog import SPECIES

    return {s.name: max(1, s.size_rank) for s in SPECIES}


def sell_price(name: str) -> int | None:
    """Coins per unit when selling *name*; None = not sellable."""
    key = name.strip().lower()
    if key in RESOURCE_VALUES:
        return RESOURCE_VALUES[key]
    return _fish_values().get(key)


def shop_listing() -> list[tuple[str, int]]:
    """``[(item, price)]`` for the gear shop, ordered by price then name
    — shipped ``utils/mining/market.shop_listing`` verbatim (the
    ``!market`` embed's Buy-gear order; goldens/mining/sweep_market pins
    the bytes)."""
    return sorted(GEAR_SHOP.items(), key=lambda kv: (kv[1], kv[0]))


def sellable_inventory(inventory: dict[str, int]
                       ) -> list[tuple[str, int, int]]:
    """[(name, qty, unit_price)] for every sellable resource, ordered by
    unit price desc then name (shipped stable display)."""
    rows = [(name, qty, price) for name, qty in inventory.items()
            if qty > 0 and (price := sell_price(name)) is not None]
    rows.sort(key=lambda r: (-r[2], r[0]))
    return rows
