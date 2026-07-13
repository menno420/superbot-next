"""IDLE subsystem manifest — the idle-engine game-plugin adapter (PLUG-001).

One command + one status panel declared in the slice (PR #75); increment 2
adds the deferred seams: a ``settings`` facet (the decoded ``SetupConfig``
knobs), an ``events`` facet (the idle lifecycle), and a LIVE render-forwarding
``@handler`` layer over ``idle_engine.render`` routed by three grouped
commands.

Declared OUT OF TREE and consumed by the superbot-next host through the
``sb.plugins`` entry point (host side: ``sb/app/plugin_host.py``; binding
contract: ``docs/game-plugin-contract.md`` @ ``d3dba9b`` in the host repo —
superbot-next). Mirrors the in-tree exemplar
``examples/superbot-plugin-hello/`` for the sb.spec symbols. Pure declarations
+ ref registrations — the same shape as an in-tree ``sb/manifest/<key>.py``
module:

  - importing this module IS reserving (the ``@panel`` / ``@handler``
    registrations below mirror the in-tree decorator discipline);
  - the host pins this manifest's canonical hash in its committed
    ``plugins.lock.json`` and refuses drift at boot — any change to the
    declared surface (a new setting/event/handler) re-hashes: re-pin
    host-side deliberately (``tools/plugin_pin.py --write``, a superbot-next
    PR out of idle scope);
  - the v1 contract facets only: this manifest declares commands, a panel,
    settings, events, and a capability. Persistence is HOST-OWNED —
    ``stores`` / ``data_invariants`` / ``wizard_sections`` are refused at the
    gate, so the idle engine's ``GameState`` saves ride the host store, not
    this plugin.

Increment-2 seams, grounded in the engine (never fabricated):

  - **settings** ← the decoded ``idle_engine.provisioning.SetupConfig``: which
    theme pack loads (``idle.pack``) + the three v1 feature toggles
    (``idle.offline_progress`` / ``idle.upgrades`` / ``idle.prestige``, one
    per ``FEATURE_BITS`` entry). Bindings ride each spec's ``settings_key``;
    no Discord-pointer ``BindingSpec`` is declared — the engine is
    platform-free and has no channel/role/thread target to bind.
  - **events** ← the idle lifecycle: ``idle.tick`` and
    ``idle.offline_return``, observability-only, payloads shaped from the
    engine's real outputs.
  - **handlers** ← ``superbot_idle_plugin.render_forward`` forwards
    ``idle_engine.render.render_status`` / ``render_shop`` / ``render_prestige``
    output VERBATIM. The host state-injection signature is validated host-side
    (see ``render_forward``); idle CI proves the forwarding is byte-identical.
"""

from __future__ import annotations

from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import EventSpec, FieldSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import (
    EmbedFrameSpec,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    handler,
    is_registered,
    panel,
)
from sb.spec.settings import Activation, SettingSpec

from superbot_idle_plugin import render_forward

PANEL_ID = "idle.status"

# Handler ref names — the render-forwarding seam. Each forwards the matching
# idle_engine.render.* output verbatim (see superbot_idle_plugin.render_forward).
HANDLER_STATUS = "idle.render.status"
HANDLER_SHOP = "idle.render.shop"
HANDLER_PRESTIGE = "idle.render.prestige"

# Event names — the idle lifecycle the contract supports.
EVT_TICK = "idle.tick"
EVT_OFFLINE_RETURN = "idle.offline_return"


def idle_status_spec() -> PanelSpec:
    """The one static panel — a text body; the panel engine renders it and the
    engine-injected nav slots carry the never-strand routes. The live views
    ride the render-forwarding handlers (below), not this panel."""
    return PanelSpec(
        panel_id=PANEL_ID,
        subsystem="idle",
        title="Idle status",
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock(
                "⏳ This panel is declared in the **superbot-idle** engine's "
                "`plugin/` adapter — a thin out-of-tree shell over the pure "
                "idle mechanics — and registered through the `sb.plugins` "
                "entry point. It maps the idle engine onto the game-plugin "
                "contract: entry-point discovery, committed hash pin, joint "
                "compile, live dispatch. The `idle status` / `idle shop` / "
                "`idle prestige` commands forward the engine's real views. "
                "Persistence is host-owned."
            ),
        ),
        navigation=NavigationSpec(),
    )


# --- settings facet: the decoded SetupConfig knobs (v1 allowed facet) ---------
# Grounded in idle_engine.provisioning.SetupConfig — the engine's REAL
# provisioning surface, not economy tuning numbers. `settings_key` is each
# spec's binding (the canonical persisted key). No Discord-pointer BindingSpec:
# the engine is platform-free (no channel/role/thread to bind).

SETTINGS = (
    SettingSpec(
        name="pack",
        value_type=str,
        default="",
        settings_key="idle.pack",
        hint="Which idle theme pack this instance loads — the decoded setup "
        "code's theme id (idle_engine.provisioning.SetupConfig.theme_id).",
        input_hint="text",
    ),
    SettingSpec(
        name="offline_progress",
        value_type=bool,
        settings_key="idle.offline_progress",
        hint="Credit production accrued while away on a player's return "
        "(SetupConfig.offline_progress / FEATURE_BITS bit 0).",
        activation=Activation.ON_BY_DEFAULT,
    ),
    SettingSpec(
        name="upgrades",
        value_type=bool,
        settings_key="idle.upgrades",
        hint="Enable the upgrade shop mechanic "
        "(SetupConfig.upgrades / FEATURE_BITS bit 1).",
        activation=Activation.ON_BY_DEFAULT,
    ),
    SettingSpec(
        name="prestige",
        value_type=bool,
        settings_key="idle.prestige",
        hint="Enable the prestige reset mechanic "
        "(SetupConfig.prestige / FEATURE_BITS bit 2).",
        activation=Activation.ON_BY_DEFAULT,
    ),
)


# --- events facet: the idle lifecycle (v1 allowed facet) ----------------------
# Observability-only, BEST_EFFORT delivery (the default); payload fields are
# shaped from the engine's real outputs (idle_engine.engine.offline_progress /
# apply_offline_progress).

EVENTS = (
    EventSpec(
        name=EVT_TICK,
        payload_schema=(
            FieldSpec(name="subsystem_key", type="str"),
            FieldSpec(name="now", type="int"),
            FieldSpec(name="elapsed_s", type="int"),
        ),
        owner_subsystem="idle",
        observability_only=True,
    ),
    EventSpec(
        name=EVT_OFFLINE_RETURN,
        payload_schema=(
            FieldSpec(name="subsystem_key", type="str"),
            FieldSpec(name="last_seen", type="int"),
            FieldSpec(name="now", type="int"),
            FieldSpec(name="gains", type="dict"),
        ),
        owner_subsystem="idle",
        observability_only=True,
    ),
)


def _ensure_refs() -> None:
    """Idempotent ref registration (the in-tree ``ENSURE_REFS`` discipline:
    decorators run at first import only; the compiler's test seam may clear
    the ref table without evicting module caches)."""
    if not is_registered(PanelRef(PANEL_ID)):
        panel(PANEL_ID)(idle_status_spec)
    if not is_registered(HandlerRef(HANDLER_STATUS)):
        handler(HANDLER_STATUS)(render_forward.forward_status)
    if not is_registered(HandlerRef(HANDLER_SHOP)):
        handler(HANDLER_SHOP)(render_forward.forward_shop)
    if not is_registered(HandlerRef(HANDLER_PRESTIGE)):
        handler(HANDLER_PRESTIGE)(render_forward.forward_prestige)


_ensure_refs()
ENSURE_REFS = _ensure_refs


MANIFEST = SubsystemManifest(
    key="idle",
    version=1,
    commands=(
        CommandSpec(
            name="idle",
            kind=CommandKind.BOTH,
            route=PanelRef(PANEL_ID),
            summary="Open the idle-engine status panel.",
            usage="!idle",
            audience_tier="user",
            capability="idle",
        ),
        # The live render-forwarding views: commands route directly at the
        # render handlers (CommandSpec.route accepts a HandlerRef — the
        # command-only class in the frozen §2.2 grammar).
        CommandSpec(
            name="status",
            kind=CommandKind.BOTH,
            group="idle",
            route=HandlerRef(HANDLER_STATUS),
            summary="Show the live idle status view (balances, rates, offline gains).",
            usage="!idle status",
            audience_tier="user",
            capability="idle",
        ),
        CommandSpec(
            name="shop",
            kind=CommandKind.BOTH,
            group="idle",
            route=HandlerRef(HANDLER_SHOP),
            summary="Show the live upgrade-shop view.",
            usage="!idle shop",
            audience_tier="user",
            capability="idle",
        ),
        CommandSpec(
            name="prestige",
            kind=CommandKind.BOTH,
            group="idle",
            route=HandlerRef(HANDLER_PRESTIGE),
            summary="Show the live prestige view.",
            usage="!idle prestige",
            audience_tier="user",
            capability="idle",
        ),
    ),
    panels=(idle_status_spec(),),
    settings=SETTINGS,
    events=EVENTS,
    capabilities=("idle.game.play",),
)
