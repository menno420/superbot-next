"""DIAGNOSTIC subsystem manifest — the operator status surface at the
shipped shape (parity flip; goldens/diagnostic, 43 goldens):

* ``diagnostics`` — the shipped 🔧 Diagnostics Hub (band-1 route kept,
  hub reshaped oracle-wins).
* ``latency`` — the shipped Bot Latency card.
* the shipped DiagnosticCog tool commands (the wave-9 re-home;
  disbot/cogs/diagnostic_cog.py): ``lifecycle`` [lc] (the
  ``!platform lifecycle`` card's shortcut), ``check_database``
  [checkdb], ``find_command`` [findcmd], ``list_commands_detailed``
  [listcmds] (the ◀ Prev / Next ▶ registry paginator panel),
  ``test_notification`` [testnotify] and ``validate_json_files``
  [validatejson]. Three of the bare names (and their checkdb / findcmd
  / listcmds aliases) sit in the shipped bootstrap allowlist
  (sb/namespace/bootstrap.py — the K6 channel-access classifier);
  declaring them ACTIVATES those shipped roster rows — K1's command
  claims key on (value, surface, parent_group), so the bare
  ``lifecycle`` and the grouped ``platform lifecycle`` are distinct
  reservations and check_namespace stays clean.
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
inventing bytes; the root handler answers the honest refusal instead.
``query_logs`` / ``recent_errors`` are NOT declared either — their
sweeps embedded run-order-dependent live log-ring lines and were
RETIRED under the 2026-07-12 corpus ruling (the same process-state
class; parity/parity.yml source.retired_goldens)."""

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
        # --- the shipped DiagnosticCog tool commands (wave-9 re-home:
        # goldens/diagnostic/sweep_lifecycle, sweep_check_database,
        # sweep_find_command, sweep_list_commands_detailed,
        # sweep_test_notification, sweep_validate_json_files pin the
        # bytes; names/aliases oracle-verbatim, diagnostic_cog.py).
        CommandSpec(
            name="lifecycle",
            kind=CommandKind.PREFIX,
            aliases=("lc",),
            route=HandlerRef("diagnostic.lifecycle_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Lifecycle state (phase, pending request, recent "
                    "events).",
            usage="!lifecycle",
        ),
        CommandSpec(
            name="check_database",
            kind=CommandKind.PREFIX,
            aliases=("checkdb",),
            route=HandlerRef("diagnostic.check_database_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Verify that all expected PostgreSQL tables exist.",
            usage="!check_database",
        ),
        CommandSpec(
            name="find_command",
            kind=CommandKind.PREFIX,
            aliases=("findcmd",),
            route=HandlerRef("diagnostic.find_command_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Search for commands by keyword in their name or "
                    "description.",
            usage="!find_command <keyword>",
        ),
        CommandSpec(
            name="list_commands_detailed",
            kind=CommandKind.PREFIX,
            aliases=("listcmds",),
            route=PanelRef("diagnostic.command_list"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="List all registered commands with details, "
                    "paginated by cog.",
            usage="!list_commands_detailed",
        ),
        CommandSpec(
            name="test_notification",
            kind=CommandKind.PREFIX,
            aliases=("testnotify",),
            route=HandlerRef("diagnostic.test_notification_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Send a test notification via the webhook reporter.",
            usage="!test_notification",
        ),
        CommandSpec(
            name="validate_json_files",
            kind=CommandKind.PREFIX,
            aliases=("validatejson",),
            route=HandlerRef("diagnostic.validate_json_view"),
            audience_tier=_TIER,
            capability="diagnostic",
            summary="Validate the structure of all JSON files in the "
                    "data directory.",
            usage="!validate_json_files",
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
    from sb.domain.diagnostic import store as _store

    _store.ensure_refs()
    _panels.ensure_diagnostic_refs()
    _handlers.ensure_handler_refs()
    _ops.ensure_ops_refs()
    register_ops()


# The P1 re-arm hook is a module ATTRIBUTE by convention (like MANIFEST):
# an assignment, so the per-module hook name never trips the namespace
# shadowing checkers (D-0026).
ENSURE_REFS = _ensure_refs
