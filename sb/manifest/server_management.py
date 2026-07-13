"""SERVER_MANAGEMENT subsystem manifest (band 2) — the guild-config
overview hub (shipped servermanagement/servermenu/guildmenu + the
/server-management slash twin, cogs/server_management_cog.py PR14).

Both front doors open the REAL shipped Server Management Hub (the parity
flip): the 🧭 read-only health-badge navigation surface
(sb/domain/server_management/panels.py; goldens/server_management/
sweep_slash_server-management.json pins the slash bytes). The shipped
slash path answered DIRECTLY with the ephemeral hub (type-4, flags 64 —
no defer), hence ``DeferMode.NONE``.

DELIBERATE NAME PAIR (curation row 73 ruling, 2026-07-13): the oracle
ships this surface under TWO different names — prefix ``!servermanagement``
(cogs/server_management_cog.py ``@commands.command``) and slash
``/server-management`` (``@app_commands.command``; discord.py forbids the
unhyphenated multi-word form on the slash tree, the setup-* precedent) —
so the port declares two CommandSpecs. ``CommandKind.BOTH`` folds only
SAME-name twins (G-6: the `!karma`/`/karma` class), and the grammar
deliberately carries no slash-twin-name field: growing one would be
schema growth with this pair as its sole consumer. Two specs IS the
regular declaration for a differently-named pair; both goldens live in
goldens/server_management/ (sweep_servermanagement prefix +
sweep_slash_server-management slash — the split servermanagement/ dir
retired with this ruling, the _unmapped-retirement mechanism)."""

from __future__ import annotations

from sb.domain.server_management import access_map as _access_map
from sb.domain.server_management import handlers as _handlers
from sb.domain.server_management import help_preview as _help_preview
from sb.domain.server_management import ops as _ops
from sb.domain.server_management import panels as _panels
from sb.domain.server_management import routing as _routing
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
        # the shipped ephemeral slash twin — a DELIBERATE second spec, see
        # the module-docstring name-pair ledger (goldens/server_management/
        # sweep_slash_server-management pins the bare type-4 with flags 64
        # — answered directly, no defer).
        CommandSpec(name="server-management", kind=CommandKind.SLASH,
                    route=PanelRef("server_management.hub"),
                    defer_mode=DeferMode.NONE,
                    audience_tier="administrator",
                    summary="Open the server-management menu.",
                    capability="server_management"),
    ),
    panels=(_panels.server_management_hub_spec(),
            # the PORTED 🔓 Access Map + 👁 Help Preview subpanels (P1C
            # over the P1A projection — access_map.py / help_preview.py).
            _access_map.access_map_spec(),
            _help_preview.help_preview_spec()),
    settings=(),
    # the routing port (compound-ops slice 2): command_routing_policy —
    # axis 3 of the access projection reads it; the K7 routing.set_policy
    # op (ops.py) is its sole writer.
    stores=(_routing.COMMAND_ROUTING_STORE,),
    events=(), capabilities=(),
)

_ops.register_ops()


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _access_map.ensure_access_map_refs()
    _help_preview.ensure_help_preview_refs()
    _routing.ensure_refs()
    _ops.ensure_ops_refs()


ENSURE_REFS = _ensure_refs
