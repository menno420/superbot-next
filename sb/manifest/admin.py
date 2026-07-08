"""ADMIN subsystem manifest (band 2) — operator/process surfaces on kernel
truth sources. NOT ported (deploy-ops, no compiled-architecture analog —
D-0030): cog / loadall / unloadall / syncslash."""

from __future__ import annotations

from sb.domain.admin import handlers as _handlers
from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef

_TITLE, _BLURB = "Admin", ("Operator surfaces over the kernel truth sources "
                           "(manifest registry, lifecycle, log levels).")
ensure_hub("admin", _TITLE, _BLURB)


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
    panels=(hub_spec("admin", _TITLE, _BLURB),),
    settings=(),
    stores=(),
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("admin", _TITLE, _BLURB)
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
