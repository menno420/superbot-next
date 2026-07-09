"""COMMUNITY subsystem manifest (band 4) — the shipped router-only hub
(cogs/community_cog.py): !community + /community open the navigation
panel; no stores, no settings, no business logic (shipped posture,
verbatim). Counting/Chain cross-links join at band 6.
"""

from __future__ import annotations

from sb.domain.community import handlers as _handlers
from sb.domain.community import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import ReplyVisibility
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="community",
    version=1,
    commands=(
        CommandSpec(name="community", kind=CommandKind.PREFIX,
                    route=PanelRef("community.hub"),
                    audience_tier="user", capability="community",
                    summary="Open the Community hub — XP, Karma, and "
                            "community activities.",
                    usage="!community"),
        CommandSpec(name="community", kind=CommandKind.SLASH,
                    route=PanelRef("community.hub"),
                    reply_visibility=ReplyVisibility.EPHEMERAL,
                    audience_tier="user", capability="community",
                    summary="Open the Community hub (XP, Karma, and "
                            "community games).",
                    usage="/community"),
    ),
    panels=(_panels.community_hub_spec(),),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
