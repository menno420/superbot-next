"""Level math — shipped verbatim (disbot/utils/db/xp.py @7f7628e1).

Pure functions; the ONE curve every consumer (award leg, rank card,
import seam, INV-G level-consistency invariant) shares.
"""

from __future__ import annotations

__all__ = ["level_progress", "total_xp_for_level", "xp_for_level"]


def xp_for_level(level: int) -> int:
    """XP needed to clear *level* (the per-level rung)."""
    return 5 * (level**2) + 50 * level + 100


def level_progress(total_xp: int) -> tuple[int, int, int]:
    """(level, xp_into_level, xp_needed_for_next) for a raw XP total."""
    level = 0
    remaining = total_xp
    while True:
        needed = xp_for_level(level)
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
        level += 1


def total_xp_for_level(level: int) -> int:
    """Cumulative XP required to *reach* ``level`` — the inverse of
    :func:`level_progress` (the bot-to-bot import target).

    ``level_progress(total_xp_for_level(L)) == (L, 0, xp_for_level(L))``
    for every ``L >= 0``.
    """
    if level <= 0:
        return 0
    return sum(xp_for_level(k) for k in range(level))
