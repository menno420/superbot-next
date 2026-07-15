"""Skill tree — pure, table-driven skill→stats model (ported verbatim from the
oracle ``disbot/utils/mining/skills.py``).

Four branches, each capped, mapping allocated points onto the shared
:class:`~sb.domain.mining.equipment.EffectiveStats` block so skills stack with
gear through one read model (``sb.domain.mining.character.character_stats``).  A
**soft total cap** below ``len(BRANCHES) × PER_BRANCH_CAP`` forces a
specialization (digger / duelist / tycoon / smith).

Pure + stdlib-only (no Discord / DB / state), like
:mod:`sb.domain.mining.equipment`.
"""

from __future__ import annotations

from sb.domain.mining.equipment import EffectiveStats

# The four skill branches.  Branch names are the stored ``player_skills.branch``
# vocabulary and the UI/command tokens.
MINING = "mining"
COMBAT = "combat"
FORTUNE = "fortune"
CRAFTING = "crafting"
BRANCHES: tuple[str, ...] = (MINING, COMBAT, FORTUNE, CRAFTING)

# Per-branch cap and the soft total cap.  20 < 4 × 10 = 40 ⇒ a fully-levelled
# player can fill at most two branches (or spread thinner) — never all four.
PER_BRANCH_CAP = 10
SOFT_TOTAL_CAP = 20

# Human-readable branch blurbs (panel copy; pure, no Discord).
BRANCH_LABELS: dict[str, str] = {
    MINING: "⛏️ Mining — raw digging power",
    COMBAT: "⚔️ Combat — duel damage & health",
    FORTUNE: "🍀 Fortune — luck & loot",
    CRAFTING: "🛠️ Crafting — loot yield",
}

# Respec price: a base fee plus a per-level scaler, so deep characters pay more
# to re-spend a bigger pool (a real, level-scaled coin sink — ``skill_service``
# verbatim).  The skills panel footer pins ``respec_cost(level)``
# (goldens/mining/sweep_skills: level 0 -> 200).  The respec write itself is the
# coin-bearing lane and rides the deferred panel port (D-0043).
RESPEC_BASE_COST = 200
RESPEC_COST_PER_LEVEL = 50
#: The economy-audit reason tag for a full respec (``skill_service`` verbatim —
#: ``RESPEC_REASON = "mining:skill_respec"``); the money-flow tag the WP-7 respec
#: leg (``mining.record_respec``) debits under.
RESPEC_REASON = "mining:skill_respec"


def respec_cost(level: int) -> int:
    """The coin cost to respec at *level* (base + per-level scaler)."""
    return RESPEC_BASE_COST + RESPEC_COST_PER_LEVEL * max(0, level)


def is_branch(branch: str) -> bool:
    """True if *branch* is a real skill branch."""
    return branch in BRANCHES


def branch_stats(branch: str, points: int) -> EffectiveStats:
    """The :class:`EffectiveStats` contribution of *points* in one *branch*.

    Recommended v1 mapping (1 point each, kept deliberately simple):
    - mining → ``mining_power`` +1 per point
    - combat → ``damage`` +1 every 2 points, ``max_health`` +2 per point
    - fortune → ``luck`` +1 per point, ``loot_bonus`` +1 every 2 points
    - crafting → ``loot_bonus`` +1 per point

    Unknown branches and non-positive points contribute nothing.
    """
    if points <= 0 or branch not in BRANCHES:
        return EffectiveStats()
    if branch == MINING:
        return EffectiveStats(mining_power=points)
    if branch == COMBAT:
        return EffectiveStats(damage=points // 2, max_health=points * 2)
    if branch == FORTUNE:
        return EffectiveStats(luck=points, loot_bonus=points // 2)
    # CRAFTING
    return EffectiveStats(loot_bonus=points)


def skill_stats(alloc: dict[str, int]) -> EffectiveStats:
    """Sum the stat contribution of every allocated branch in *alloc*.

    *alloc* is ``{branch: points}``.  An empty allocation yields all-zero stats
    (the additive safety property — skills change nothing until a point is
    spent).
    """
    total = EffectiveStats()
    for branch, points in alloc.items():
        total = total + branch_stats(branch, points)
    return total


def total_spent(alloc: dict[str, int]) -> int:
    """Total points allocated across all branches in *alloc*."""
    return sum(max(0, p) for p in alloc.values())


__all__ = [
    "MINING",
    "COMBAT",
    "FORTUNE",
    "CRAFTING",
    "BRANCHES",
    "PER_BRANCH_CAP",
    "SOFT_TOTAL_CAP",
    "BRANCH_LABELS",
    "RESPEC_BASE_COST",
    "RESPEC_COST_PER_LEVEL",
    "RESPEC_REASON",
    "respec_cost",
    "is_branch",
    "branch_stats",
    "skill_stats",
    "total_spent",
]
