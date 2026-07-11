"""DIAGNOSTIC subsystem manifest — the operator status surface at the
shipped shape (parity flip; goldens/diagnostic, 37 goldens):

* ``diagnostics`` — the shipped 🔧 Diagnostics Hub (band-1 route kept,
  hub reshaped oracle-wins).
* ``latency`` — the shipped Bot Latency card.
* ``platform`` (BOTH) — the shipped 🛰 Platform hub; the bare front door
  is a HandlerRef (undeclared/unported subcommand tokens get the honest
  refusal), so the slash twin declares ``DeferMode.NONE`` explicitly
  (slash+HandlerRef would otherwise AUTO-defer type-5; the golden pins
  a type-4 direct response).
* ``platform <view>`` — one grouped prefix subcommand per shipped
  operator card (sb/domain/diagnostic/platform_views.py), plus the
  ``backfill`` dry-run op, the ``setting``/``finding`` guard routes and
  the ``flag``/``automation`` component panels.

NOT declared: ``platform health/runtime/slow/startup/status`` — the
capture skipped those five as nondeterministic process-state views
(parity/goldens/_sweep_skips.json), so declaring them would mean
inventing bytes; the root handler answers the honest refusal instead."""

from __future__ import annotations

from sb.domain.diagnostic import handlers as _handlers
from sb.domain.diagnostic import panels as _panels
from sb.domain.diagnostic.ops import register_ops
from sb.domain.diagnostic.platform_views import VIEWS
from sb.domain.diagnostic.store import PLATFORM_MIGRATION_CHECKPOINTS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.outcomes import DeferMode
from sb.spec.refs import HandlerRef, PanelRef

_TIER = "administrator"   # the shipped gate (the hub's own footer byte:
                          # "Diagnostics Hub  •  Admin only")


def _sub(name: str, route, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       group="platform", route=route,
                       audience_tier=_TIER, capability="diagnostic",
                       summary=summary, usage=f"!platform {name}")


def _view_commands() -> tuple[CommandSpec, ...]:
    out = []
    for name, view in VIEWS.items():
        ref = HandlerRef(f"diagnostic.pf_{name.replace('-', '_')}")
        out.append(_sub(name, ref, view.title))
    return tuple(out)


MANIFEST = SubsystemManifest(
    key="diagnostic",
    version=1,
    commands=(
        CommandSpec(
            name="diagnostics",
            kind=CommandKind.BOTH,           # shipped surface name, verbatim
            route=PanelRef("diagnostic.hub"),
            summary="Platform status: lifecycle, findings, declarations, AI health.",
            usage="/diagnostics",
            capability="diagnostic",
            slash_common=True,               # operators must reach this on slash
        ),
        CommandSpec(
            name="latency",
            kind=CommandKind.PREFIX,
            route=HandlerRef("diagnostic.latency_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Bot WebSocket latency.",
            usage="!latency",
        ),
        CommandSpec(
            name="platform",
            kind=CommandKind.BOTH,
            route=HandlerRef("diagnostic.pf_root"),
            defer_mode=DeferMode.NONE,       # the type-4 direct slash twin
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Platform diagnostics hub: runtime, catalogues, "
                    "resources, validation.",
            usage="/platform",
        ),
        *_view_commands(),
        _sub("backfill", HandlerRef("diagnostic.pf_backfill_route"),
             "🧩 Binding backfill — dry run"),
        _sub("setting", HandlerRef("diagnostic.pf_setting_route"),
             "⚙️ Declared-setting inspector"),
        _sub("finding", HandlerRef("diagnostic.pf_finding_route"),
             "🩺 Health-finding actions"),
        _sub("flag", PanelRef("diagnostic.flag_manager"),
             "🚩 Flag Manager"),
        _sub("automation", PanelRef("diagnostic.automation_panel"),
             "🤖 Automation panel"),
    ),
    panels=_panels.all_panel_specs(),
    stores=(PLATFORM_MIGRATION_CHECKPOINTS_STORE,),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.diagnostic import ops as _ops
    from sb.domain.diagnostic import store as _store  # noqa: F401 — store spec import

    _panels.ensure_diagnostic_refs()
    _handlers.ensure_handler_refs()
    _ops.ensure_ops_refs()
    register_ops()


# The P1 re-arm hook is a module ATTRIBUTE by convention (like MANIFEST):
# an assignment, so the per-module hook name never trips the namespace
# shadowing checkers (D-0026).
ENSURE_REFS = _ensure_refs
