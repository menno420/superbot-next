"""COMMUNITY_SPOTLIGHT subsystem manifest (band 4) — the shipped live
activity dashboard (cogs/community_spotlight_cog.py): !spotlight
(!activity) opens the panel; the level-up feed is the DECLARED
``xp.level_up`` consumption (the band-4 contract — the subscribe(bus)
arming is a composition-root/harness obligation, the band-2 fan-out
precedent). No stores (the feed is a bounded in-memory cache, shipped),
no settings.
"""

from __future__ import annotations

from sb.domain.community import handlers as _handlers
from sb.domain.community import panels as _panels
from sb.domain.community import spotlight as _spotlight
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="community_spotlight",
    version=1,
    commands=(
        CommandSpec(name="spotlight", kind=CommandKind.PREFIX,
                    route=PanelRef("community_spotlight.hub"),
                    aliases=("activity",),
                    cooldown=CooldownSpec(rate=2, per_s=15),
                    audience_tier="user", capability="community_spotlight",
                    summary="Show the Community Spotlight — live XP, "
                            "coins, games, and level-ups.",
                    usage="!spotlight"),
    ),
    panels=(_panels.spotlight_hub_spec(), _panels.spotlight_games_spec()),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
