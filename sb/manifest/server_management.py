"""SERVER_MANAGEMENT subsystem manifest (band 2) — the guild-config
overview hub (shipped servermanagement/servermenu/guildmenu + the
/server-management slash twin)."""

from __future__ import annotations

from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

_TITLE, _BLURB = "Server management", (
    "Guild configuration overview — per-subsystem hubs hang off this menu.")
ensure_hub("server_management", _TITLE, _BLURB)

MANIFEST = SubsystemManifest(
    key="server_management",
    version=1,
    commands=(
        CommandSpec(name="servermanagement", kind=CommandKind.PREFIX,
                    route=PanelRef("server_management.hub"),
                    aliases=("servermenu", "guildmenu"),
                    summary="Open the server-management menu.",
                    capability="server_management"),
        CommandSpec(name="server-management", kind=CommandKind.SLASH,
                    route=PanelRef("server_management.hub"),
                    summary="Open the server-management menu.",
                    capability="server_management"),
    ),
    panels=(hub_spec("server_management", _TITLE, _BLURB),),
    settings=(), stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("server_management", _TITLE, _BLURB)


ENSURE_REFS = _ensure_refs
