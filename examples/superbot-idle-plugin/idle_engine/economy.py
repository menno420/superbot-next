"""Pre-registered economy parameters (PROVISIONAL) and spec builders.

INTEGRITY FLOOR: every number here is committed with rationale in
``docs/design/upgrades-prestige-v0.md`` BEFORE any tuning, and is
explicitly PROVISIONAL pending the economy design doc slice and
Simulator pinning (Q-0264). Themes never carry these numbers — a theme
names the slots (SKIN), this module prices them (CORE). Change a value
here and the design doc must change in the same PR, or the pre-registration
is a lie.
"""

from __future__ import annotations

from idle_engine.achievements import MilestoneSpec
from idle_engine.prestige import PrestigeSpec
from idle_engine.state import GeneratorSpec
from idle_engine.upgrades import UpgradeSpec

# --- PROVISIONAL v0 parameters (docs/design/upgrades-prestige-v0.md) ---------

#: An upgrade's level-0 cost = this many seconds of the target generator's
#: base output (one generator's worth).
UPGRADE_BASE_COST_SECONDS = 60

#: Geometric cost growth per level, as an exact rational (num, den): x1.15.
UPGRADE_COST_GROWTH_NUM = 115
UPGRADE_COST_GROWTH_DEN = 100

#: Additive percent added to the target generator's rate per upgrade level.
UPGRADE_EFFECT_PERCENT = 25

#: Lifetime earnings of the measured currency required before a reset.
PRESTIGE_THRESHOLD = 100_000

#: Award = isqrt(lifetime // divisor); divisor == threshold, so the first
#: eligible reset awards exactly 1.
PRESTIGE_AWARD_DIVISOR = 100_000

#: Additive percent added to ALL production per prestige unit held.
PRESTIGE_BONUS_PERCENT = 10

# --- PROVISIONAL v0 milestone parameters (docs/design/achievements-v0.md) ----

#: Threshold ladder for the ``owned`` track (TOTAL generators owned).
MILESTONE_OWNED_THRESHOLDS = (10, 100, 1_000)

#: Threshold ladder for the ``lifetime`` track (run-lifetime earnings of
#: the measured currency — the prestige track's currency when declared).
MILESTONE_LIFETIME_THRESHOLDS = (1_000, 100_000, 10_000_000)

#: Threshold ladder for the ``prestige`` track (prestige units held).
MILESTONE_PRESTIGE_THRESHOLDS = (1, 5, 25)

#: Additive percent added to ALL production per milestone EARNED.
MILESTONE_BONUS_PERCENT = 5


def build_upgrade_spec(upgrade_id: str, target: GeneratorSpec) -> UpgradeSpec:
    """Price one theme-declared upgrade slot against the v0 curve table."""
    return UpgradeSpec(
        spec_id=upgrade_id,
        cost_currency=target.produces,
        base_cost=target.base_rate * UPGRADE_BASE_COST_SECONDS,
        cost_growth_num=UPGRADE_COST_GROWTH_NUM,
        cost_growth_den=UPGRADE_COST_GROWTH_DEN,
        target=target.spec_id,
        effect_percent=UPGRADE_EFFECT_PERCENT,
    )


def build_prestige_spec(awards: str, measures: str) -> PrestigeSpec:
    """Bind one theme-declared prestige track to the v0 threshold/award table."""
    return PrestigeSpec(
        awards=awards,
        measures=measures,
        threshold=PRESTIGE_THRESHOLD,
        award_divisor=PRESTIGE_AWARD_DIVISOR,
        bonus_percent=PRESTIGE_BONUS_PERCENT,
    )


def build_milestone_specs(
    lifetime_currency: str, prestige_currency: str | None
) -> list[MilestoneSpec]:
    """The engine-derived milestone slots for one pack's roster.

    Every pack gets the same pre-registered ladders — three ``owned``
    rungs (total generators), three ``lifetime`` rungs bound to
    ``lifetime_currency``, and, when the pack declares a prestige track,
    three ``prestige`` rungs bound to ``prestige_currency``. Slot ids
    are canonical (``owned-1`` … ``prestige-3``): the theme's optional
    ``milestones`` block skins these ids with nouns, never creates or
    reprices them.
    """
    ladders: list[tuple[str, str, tuple[int, ...]]] = [
        ("owned", "", MILESTONE_OWNED_THRESHOLDS),
        ("lifetime", lifetime_currency, MILESTONE_LIFETIME_THRESHOLDS),
    ]
    if prestige_currency is not None:
        ladders.append(("prestige", prestige_currency, MILESTONE_PRESTIGE_THRESHOLDS))
    return [
        MilestoneSpec(
            spec_id=f"{kind}-{rank}",
            kind=kind,
            subject=subject,
            threshold=threshold,
            bonus_percent=MILESTONE_BONUS_PERCENT,
        )
        for kind, subject, ladder in ladders
        for rank, threshold in enumerate(ladder, 1)
    ]
