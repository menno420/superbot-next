"""Unified-inventory assembly (band 3) — the shipped cogs/inventory_cog.py
pure helpers verbatim (grouping, rarity tiers, sort modes) over the economy
`inventory` store, with an installable EXTRA-SOURCE port for the shipped
mining_inventory merge (that table is a band-6 store — the port waits
honestly; installed sources merge exactly like the shipped
`_build_combined_inventory` lowercased-key fold).
"""

from __future__ import annotations

from typing import Awaitable, Callable

from sb.domain.economy.catalogue import (
    CATEGORY_META,
    CATEGORY_ORDER,
    ITEM_CATALOGUE,
    RARITY_ORDER,
    RARITY_TIERS,
)

__all__ = [
    "SORT_MODES",
    "build_combined_inventory",
    "group_by_rarity",
    "install_extra_inventory_source",
    "item_line",
    "render_hub_lines",
    "reset_inventory_ports_for_tests",
    "sort_items",
]

# (item_key -> qty) async source: (user_id, guild_id) -> dict
InventorySource = Callable[[int, int], Awaitable[dict]]

_extra_sources: list[InventorySource] = []


def install_extra_inventory_source(source: InventorySource) -> None:
    """Band-6 seam: mining/fishing tables merge in here when their band
    lands (the shipped get_mining_inventory leg)."""
    _extra_sources.append(source)


def reset_inventory_ports_for_tests() -> None:
    _extra_sources.clear()


async def build_combined_inventory(
        user_id: int, guild_id: int) -> dict[str, list[tuple[str, int, dict]]]:
    """{category: [(item_key, qty, meta), ...]} — non-empty categories only,
    rarest-first within each (shipped verbatim)."""
    from sb.domain.economy.store import get_inventory

    combined: dict[str, int] = {}
    for source in _extra_sources:
        for k, v in (await source(user_id, guild_id)).items():
            key = str(k).lower()
            combined[key] = combined.get(key, 0) + int(v)
    for k, v in (await get_inventory(user_id, guild_id)).items():
        key = str(k).lower()
        combined[key] = combined.get(key, 0) + int(v)

    grouped: dict[str, list[tuple[str, int, dict]]] = {}
    for item_key, qty in combined.items():
        if qty <= 0:
            continue
        meta = ITEM_CATALOGUE.get(item_key, {})
        cat = meta.get("category", "Other")
        grouped.setdefault(cat, []).append((item_key, qty, meta))

    for cat_items in grouped.values():
        cat_items.sort(key=lambda x: RARITY_ORDER.get(x[2].get("rarity", ""), 99))
    return grouped


# --- pure display helpers (shipped verbatim) ----------------------------------------

def item_line(item_key: str, qty: int, meta: dict) -> str:
    """One inventory item as a display line (name · qty · type)."""
    emoji = meta.get("emoji", "📦")
    itype = meta.get("type", "Item")
    display_name = item_key.replace("_", " ").title()
    return f"{emoji} **{display_name}** × {qty} · {itype}"


def group_by_rarity(
        page_items: list[tuple[str, int, dict]]) -> list[tuple[str, list[str]]]:
    """(tier_label, lines) pairs, rarest-first; unknown rarity => Unknown."""
    buckets: dict[str, list[str]] = {}
    for item_key, qty, meta in page_items:
        rarity = meta.get("rarity", "Unknown")
        tier = rarity if rarity in RARITY_ORDER else "Unknown"
        buckets.setdefault(tier, []).append(item_line(item_key, qty, meta))
    return [(tier, buckets[tier]) for tier in RARITY_TIERS if tier in buckets]


SORT_MODES: tuple[str, ...] = ("rarity", "quantity", "name")


def sort_items(items: list[tuple[str, int, dict]],
               mode: str) -> list[tuple[str, int, dict]]:
    """A pure, total order per mode (item key breaks ties) — shipped."""
    if mode == "quantity":
        return sorted(items, key=lambda x: (-x[1], x[0]))
    if mode == "name":
        return sorted(items, key=lambda x: x[0])
    return sorted(items,
                  key=lambda x: (RARITY_ORDER.get(x[2].get("rarity", ""), 99),
                                 x[0]))


def render_hub_lines(grouped: dict[str, list[tuple[str, int, dict]]]) -> list[str]:
    """The hub overview lines (category — preview, +N more) — shipped."""
    if not grouped:
        return ["No items yet — go mining with `!mine` or visit `!shop`!"]
    lines = []
    ordered = [c for c in CATEGORY_ORDER if c in grouped]
    if "Other" in grouped:
        ordered.append("Other")
    for cat in ordered:
        cat_meta = CATEGORY_META.get(cat, {"emoji": "📦"})
        items = grouped[cat]
        preview_parts = [f"{m.get('emoji', '📦')} {n.replace('_', ' ').title()}"
                         for n, _, m in items[:3]]
        preview = ", ".join(preview_parts)
        if len(items) > 3:
            preview += f" +{len(items) - 3} more"
        lines.append(f"{cat_meta['emoji']} **{cat}** — {preview}")
    return lines
