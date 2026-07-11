"""SERVER_MANAGEMENT subsystem manifest (band 2) — the guild-config
overview hub (shipped servermanagement/servermenu/guildmenu + the
/server-management slash twin, cogs/server_management_cog.py PR14).

Both front doors open the REAL shipped Server Management Hub (the parity
flip): the 🧭 read-only health-badge navigation surface
(sb/domain/server_management/panels.py; goldens/servermanagement/
sweep_slash_server-management.json pins the slash bytes). The shipped
slash path answered DIRECTLY with the ephemeral hub (type-4, flags 64 —
no defer), hence ``DeferMode.NONE``."""

from __future__ import annotations

from sb.domain.server_management import handlers as _handlers
from sb.domain.server_management import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import DeferMode
from sb.spec.refs import PanelRef

MANIFEST = SubsystemManifest(
    key="server_management",
    version=1,
    commands=(
        CommandSpec(name="servermanagement", kind=CommandKind.PREFIX,
                    route=PanelRef("server_management.hub"),
                    aliases=("servermenu", "guildmenu"),
                    audience_tier="administrator",
                    summary="Open the server-management menu.",
                    capability="server_management"),
        # the shipped ephemeral slash twin (goldens/servermanagement pins
        # the bare type-4 with flags 64 — answered directly, no defer).
        CommandSpec(name="server-management", kind=CommandKind.SLASH,
                    route=PanelRef("server_management.hub"),
                    defer_mode=DeferMode.NONE,
                    audience_tier="administrator",
                    summary="Open the server-management menu.",
                    capability="server_management"),
    ),
    panels=(_panels.server_management_hub_spec(),),
    settings=(), stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
