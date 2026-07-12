"""ADMIN subsystem manifest (band 2 + the parity flip + the wave-9
re-homes) — the shipped ``_AdminPanelView`` Server & Admin hub, the
``!coglist`` Cog Manager view and the ``!serverstats`` census card
(sb/domain/admin/panels.py + cogmgr.py — goldens/admin/ pins every wire
byte) over the band-2 operator reads (manifest registry, log levels, K5
lifecycle). NOT ported (deploy-ops, no compiled-architecture analog —
D-0030): cog / loadall / unloadall / syncslash (all capture-skipped in
_sweep_skips.json; sweep_cog.json retired with the skip entry, 471→470
corpus ruling 2026-07-12)."""

from __future__ import annotations

from sb.domain.admin import cogmgr as _cogmgr
from sb.domain.admin import handlers as _handlers
from sb.domain.admin import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

_TITLE = "Admin"


def _cmd(name, route, summary, *, kind=CommandKind.PREFIX, aliases=()):
    return CommandSpec(name=name, kind=kind, route=route, summary=summary,
                       aliases=tuple(aliases), capability="admin")


MANIFEST = SubsystemManifest(
    key="admin",
    version=1,
    commands=(
        _cmd("adminmenu", PanelRef("admin.hub"), "Open the admin menu."),
        _cmd("admin", PanelRef("admin.hub"), "Open the admin menu.",
             kind=CommandKind.BOTH),
        _cmd("serverstats", HandlerRef("admin.serverstats_view"),
             "Guild census stats."),
        # the shipped `!coglist` opened the interactive Cog Manager view
        # ("the panel's 📋 Cog List button" — admin_cog.py help text;
        # goldens/admin/sweep_coglist pins the open bytes).
        _cmd("coglist", PanelRef("admin.cogmgr"),
             "Open the interactive cog manager.",
             aliases=("cogs", "listcogs", "cogslist")),
        _cmd("slashes", HandlerRef("admin.slash_inventory"),
             "List the declared slash surface.", aliases=("slashlist",)),
        _cmd("loglevel", HandlerRef("admin.loglevel"),
             "Show or set the sb log level."),
        _cmd("restart", HandlerRef("admin.restart"),
             "Request a drain + restart (K5 lifecycle)."),
    ),
    panels=(_panels.admin_hub_spec(), _panels.server_stats_spec(),
            _cogmgr.cogmgr_spec()),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _cogmgr.ensure_cogmgr_refs()


ENSURE_REFS = _ensure_refs
