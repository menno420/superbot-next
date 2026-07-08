"""SETTINGS subsystem manifest (band 1) — pure declarations + handler
registrations (design-spec §1.1/§9.2).

Declares: the `/settings` entry point (opens the hub panel), the hub
PanelSpec, the `settings.changed` advisory event (shipped name verbatim),
and the two stores (`settings`, `subsystem_bindings` — minted in
sb/kernel/db/settings.py, the sole physical authority). Registers the four
K7 mutation ops (the scalar/binding lanes) and the shipped event spec.

The settings subsystem declares no SettingSpecs of its own in v1 — the
facet grammar (sb/spec/settings.py) is band 1's deliverable and every
OTHER band declares its keys as it ports (the 17 settings_keys modules
collapse into the manifests; the verbatim vocabulary lives in
sb/domain/settings/keys.py)."""

from __future__ import annotations

from sb.domain.settings import panels as _panels
from sb.domain.settings.ops import EVT_SETTINGS_CHANGED, register_ops
from sb.kernel.db.settings import BINDINGS_STORE, SETTINGS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef

SETTINGS_CHANGED_EVENT = EventSpec(
    name=EVT_SETTINGS_CHANGED,               # shipped verbatim ("settings.changed")
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("key", "str"),
        FieldSpec("subsystem", "str", required=False),
    ),
    owner_subsystem="settings",
    delivery=DeliveryClass.BEST_EFFORT,      # shipped: advisory, after commit
)

MANIFEST = SubsystemManifest(
    key="settings",
    version=1,
    commands=(
        CommandSpec(
            name="settings",
            kind=CommandKind.BOTH,           # shipped: prefix + slash surfaces
            route=PanelRef("settings.hub"),
            summary="Open the settings hub (per-subsystem configuration).",
            usage="/settings",
            capability="settings",
            slash_common=True,               # D-5: essential platform surface
        ),
    ),
    panels=(_panels.settings_hub_spec(),),
    settings=(),
    stores=(SETTINGS_STORE, BINDINGS_STORE),
    events=(SETTINGS_CHANGED_EVENT,),
    capabilities=(),
)

# Handler/spec registrations (declaring IS reserving — §3.2): the four K7
# ops + the event spec ride the manifest import so the compiler (P1) and
# every checker see one truth.
register_ops()
register_event_specs([SETTINGS_CHANGED_EVENT])


def _ensure_refs() -> None:
    """P1 re-arm hook (see tools/manifest_compile.py): idempotently
    re-register every ref this manifest's declarations resolve to."""
    from sb.domain.settings import ops as _ops
    from sb.kernel.db import settings as _db

    _db.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    register_ops()
    register_event_specs([SETTINGS_CHANGED_EVENT])


# The P1 re-arm hook is a module ATTRIBUTE by convention (like MANIFEST):
# an assignment, so the per-module hook name never trips the namespace
# shadowing checkers (D-0026).
ENSURE_REFS = _ensure_refs
