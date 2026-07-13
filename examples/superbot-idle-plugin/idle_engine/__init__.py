"""idle_engine — deterministic, pure-domain idle-game core.

CORE/SKIN contract: this package contains game MECHANICS only. Every
player-visible noun (names, flavor, emoji, colors) comes from a theme
pack loaded via :mod:`idle_engine.theme`. Engine modules must contain
zero theme vocabulary — a guard test enforces this. No I/O beyond
reading a theme file, no chat-platform calls, no wall-clock reads:
callers pass timestamps in, so identical inputs always yield identical
outputs. Economy numbers live in :mod:`idle_engine.economy`,
pre-registered in docs/design/ before any tuning.
"""

from idle_engine.state import GameState, GeneratorSpec
from idle_engine.engine import offline_progress, production_per_second, tick
from idle_engine.upgrades import (
    BulkPurchaseError,
    UpgradeSpec,
    bulk_upgrade_cost,
    max_affordable_levels,
    purchase_upgrade,
    purchase_upgrades,
    upgrade_cost,
)
from idle_engine.prestige import (
    PrestigeSpec,
    apply_prestige,
    prestige_award,
    prestige_eligible,
)
from idle_engine.achievements import (
    MilestoneSpec,
    award_milestones,
    milestone_earned,
    milestone_percent,
    milestone_progress,
    milestone_reached,
)
from idle_engine.theme import (
    Theme,
    ThemeCurrency,
    ThemeGenerator,
    ThemeMilestone,
    ThemePrestige,
    ThemeUpgrade,
    load_theme,
)
from idle_engine.render import (
    RenderBudgetError,
    embed_color_int,
    render_achievements,
    render_prestige,
    render_shop,
    render_status,
    validate_embed,
)

__all__ = [
    "BulkPurchaseError",
    "GameState",
    "GeneratorSpec",
    "MilestoneSpec",
    "PrestigeSpec",
    "RenderBudgetError",
    "Theme",
    "ThemeCurrency",
    "ThemeGenerator",
    "ThemeMilestone",
    "ThemePrestige",
    "ThemeUpgrade",
    "UpgradeSpec",
    "apply_prestige",
    "award_milestones",
    "bulk_upgrade_cost",
    "embed_color_int",
    "load_theme",
    "max_affordable_levels",
    "milestone_earned",
    "milestone_percent",
    "milestone_progress",
    "milestone_reached",
    "offline_progress",
    "prestige_award",
    "prestige_eligible",
    "production_per_second",
    "purchase_upgrade",
    "purchase_upgrades",
    "render_achievements",
    "render_prestige",
    "render_shop",
    "render_status",
    "tick",
    "upgrade_cost",
    "validate_embed",
]
