"""ADMIN subsystem manifest (band 2 + the parity flip) — the shipped
``_AdminPanelView`` Server & Admin hub (sb/domain/admin/panels.py —
goldens/admin/ pins every wire byte on both surfaces) over the band-2
operator reads (manifest registry, log levels, K5 lifecycle). NOT ported
(deploy-ops, no compiled-architecture analog — D-0030): cog / loadall /
unloadall / syncslash (all capture-skipped in _sweep_skips.json)."""

from __future__ import annotations

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
        _cmd("coglist", HandlerRef("admin.subsystems_view"),
             "List loaded subsystems (the manifest registry).",
             aliases=("cogs", "listcogs", "cogslist")),
        _cmd("slashes", HandlerRef("admin.slash_inventory"),
             "List the declared slash surface.", aliases=("slashlist",)),
        _cmd("loglevel", HandlerRef("admin.loglevel"),
             "Show or set the sb log level."),
        _cmd("restart", HandlerRef("admin.restart"),
             "Request a drain + restart (K5 lifecycle)."),
    ),
    panels=(_panels.admin_hub_spec(),),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
