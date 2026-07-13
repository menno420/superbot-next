"""The channel subsystem-visibility grid vocabulary (operator-hub edits B).

The shipped ``_SubsystemToggleView`` (disbot/views/channels/
visibility_panel.py) rendered the first 20 non-internal subsystems off
``utils.subsystem_registry.all_subsystems_sorted()`` (ui_priority
ascending) as a tri-state toggle grid. The compiled architecture has no
runtime subsystem-registry walk, so the roster ships as the
oracle-extracted capture literal (the admin cogmgr ``_COGS`` / the
diagnostic ``COMMAND_LIST_PAGES`` precedent) — extracted by importing the
oracle's ``subsystem_registry`` and applying the shipped filter+cap
verbatim: ``visibility_mode not in ("internal",)``, first 20, in
ui_priority order.

Reads ride the governance store (``subsystem_visibility`` rows, scope
``channel``); writes ride the audited ``governance.set_subsystem_
visibility`` op — the SAME seam the games-sections settings surface uses
(sb/domain/games/sections_panel.py), never a direct store write.
"""

from __future__ import annotations

__all__ = [
    "GRID_SUBSYSTEMS",
    "aggregate_state",
    "channel_visibility_rows",
    "grid_label",
]

#: (subsystem key, shipped display_name) — the capture world's toggle
#: roster, ui_priority order (module docstring; oracle
#: utils/subsystem_registry.py).
GRID_SUBSYSTEMS: tuple[tuple[str, str], ...] = (
    ("help", "Help"),
    ("general", "General"),
    ("four_twenty", "420"),
    ("utility", "Utility"),
    ("economy", "Economy"),
    ("inventory", "Inventory"),
    ("treasury", "Treasury"),
    ("ticket", "Support Tickets"),
    ("mining", "Mining"),
    ("ux_lab", "UX Lab"),
    ("fishing", "Fishing"),
    ("creature", "Creatures"),
    ("farm", "Chicken Farm"),
    ("xp", "XP & Levels"),
    ("karma", "Karma"),
    ("games", "Games"),
    ("community", "Community"),
    ("community_spotlight", "Community Spotlight"),
    ("blackjack", "Blackjack"),
    ("welcome", "Welcome"),
)


async def channel_visibility_rows(
        guild_id: int, channel_ids: list[int]) -> list[dict]:
    """Per-channel explicit-visibility rows, aligned with ``channel_ids``
    (the shipped ``_SubsystemToggleView.load``). One chain query (the
    store's shipped ``_fetch_all_visibility`` shape); a headless root
    (no DB pool) degrades to all-inherit rows so the grid still renders."""
    from sb.domain.governance import store

    try:
        chain = [("channel", int(cid)) for cid in channel_ids]
        by_scope = await store.fetch_visibility_for_chain(
            int(guild_id or 0), chain)
        return [dict(by_scope.get(("channel", int(cid)), {}))
                for cid in channel_ids]
    except Exception:  # noqa: BLE001 — headless/unarmed DB = inherit view
        return [{} for _ in channel_ids]


def aggregate_state(rows: list[dict], subsystem: str) -> bool | None | str:
    """Combined state across the picked channels; ``"mixed"`` when they
    differ (the shipped ``_aggregate``, verbatim semantics)."""
    states = {row.get(subsystem) for row in rows}
    if len(states) == 1:
        return next(iter(states))
    return "mixed"


def grid_label(display: str, agg: bool | None | str) -> tuple[str, str]:
    """(label, ActionStyle value) for one toggle — the shipped glyph +
    style mapping (✓ green / ✗ red / ± blurple / ~ grey), labels capped
    at the shipped 80 chars."""
    if agg is True:
        return (f"✓ {display}"[:80], "success")
    if agg is False:
        return (f"✗ {display}"[:80], "danger")
    if agg == "mixed":
        return (f"± {display}"[:80], "primary")
    return (f"~ {display}"[:80], "secondary")
