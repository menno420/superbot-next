"""Diagnostic panels (diagnostic flip) — the shipped operator surfaces at
byte parity (goldens/diagnostic/* @ corpus sha 7f7628e1):

* ``diagnostic.hub`` — the shipped 🔧 Diagnostics Hub
  (disbot/cogs/diagnostic — sweep_diagnostics): eight tool buttons on a
  session view (run-minted ids → ``<cid:N>``), the 8-field overview
  embed, blue, "Diagnostics Hub  •  Admin only". The band-1 projection
  hub this file used to declare is replaced by the shipped shape (the
  logging/D-0067 oracle-wins lane). 📡 Latency, 🗄️ Database, 📄 JSON
  Files, 📋 Commands and 🔔 Test Notify route their ported tools (the
  wave-9 re-home — the same cards/panel the command twins render); Bot
  Status / System Info / Recent Errors are LIVE SUCCESSOR READS (ORDER
  017 fix slice): the capture skipped their command twins as
  nondeterministic process state (parity/goldens/_sweep_skips.json), so
  no golden constrains their bytes — the cards keep the shipped SHAPE
  (diagnostic_helpers builders verbatim) over v1's own reads
  (handlers.py diag_status_view / diag_sysinfo_view / diag_errors_view;
  process_state.py + log_buffer.py + the gateway-census seam).

* ``diagnostic.card`` — the generic one-embed reply card (the ai.card
  lane) every ``!platform <view>`` / ``!latency`` handler presents.

* ``diagnostic.command_list`` — the shipped ``!list_commands_detailed``
  paginator (disbot/views/diagnostic/paginator.py ``_PaginatorView``
  over ``build_command_list_pages`` — sweep_list_commands_detailed): a
  true session view (both button ids run-minted → ``<cid:N>``), the
  ◀ Prev / Next ▶ secondary pair with Prev disabled on page 1, page 1
  of the shipped 14-page registry as the capture literal
  (command_catalog.py; the admin cogmgr roster precedent). ALL 14
  pages page in place (ORDER 017 fix slice): ◀/▶ re-open the panel on
  the stepped ``cmdlist_page`` (the projmoon fresh-re-open class) and
  the renderer edge-disables both buttons (the shipped
  ``_update_buttons``).

* ``diagnostic.platform_hub`` — the shipped 🛰 Platform hub
  (disbot/views/diagnostic/platform_panel.py — sweep_platform +
  sweep_slash_platform): four PERSISTENT-id category selects
  (``platform_hub.runtime/catalogues/resources/validation`` — verbatim
  ``custom_id_override`` pins; the shipped view was itself sent as a
  plain session send, never anchored — no panel_anchors row in either
  golden) + the ↩ Overview / 🚩 Flag manager button row
  (``platform_hub.overview`` / ``platform_hub.flag_manager``). The
  slash twin is the same panel: slash+PanelRef resolves DeferMode.NONE
  and Audience.INVOKER presents ephemeral on interactions (flags 64) —
  exactly the two goldens' split.

* ``diagnostic.flag_manager`` — the shipped 🚩 Flag Manager
  (sweep_platform_flag): the persistent ``flag_manager:*`` ids pinned
  verbatim (the help:back precedent); the option list is the capture
  world's 8-flag declaration registry (pinned; declarations ported
  verbatim in flag_catalog.py). ORDER 017 fix slice: the select renders
  the flag's DETAIL embed (the shipped handle_select →
  build_flag_detail_embed shape) and Enable/Disable run the shipped
  guard ladder, REFUSING the silent no-op write with final copy — the
  v1 kernel has no flag rollout pipeline and no flag consumer, and the
  oracle's own rule is "never offer a no-op control".

* ``diagnostic.automation_panel`` — the shipped 🤖 Automation panel
  (sweep_platform_automation): a true session view (all five component
  ids run-minted → ``<cid:N>``), the no-rules placeholder option, the
  orange scheduler-not-registered snapshot line (true in BOTH worlds —
  the capture harness never started services.automation_scheduler and
  v1 has no scheduler yet). ORDER 017 fix slice: the rule select tracks
  the pick (the shipped _on_pick; the placeholder row's value ``0`` is
  the oracle's own "no valid selection") and Enable/Disable/Delete run
  the shipped guards — the complete truthful behavior of the zero-rule
  world; the pipeline leg re-arms with the scheduler port.

Internal component ids are ``pf_*``/``diag_*``-prefixed subsystem-unique
tokens (K1 claims panel action_ids BARE and cross-subsystem — the #167
lesson); the shipped wire bytes ride ``custom_id_override``."""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    handler,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "diagnostic_hub_spec",
    "ensure_diagnostic_refs",
    "install_diagnostic_panels",
]

_TIER = "administrator"   # the shipped gate — every diagnostic surface

# --- the shipped option/field literals (goldens/diagnostic, verbatim) -----------

_RUNTIME_OPTIONS: tuple[dict, ...] = (
    {"label": 'health', "value": 'health',
     "description": 'Deterministic operational health snapshot (redacted)',
     "emoji": '🩺'},
    {"label": 'startup', "value": 'startup',
     "description": 'Settled-startup health report (extension load, gateway, DB)',
     "emoji": '🚀'},
    {"label": 'findings', "value": 'findings',
     "description": 'Persistent operational-health findings (open, redacted)',
     "emoji": '📋'},
    {"label": 'status', "value": 'status',
     "description": 'Uptime, cogs, guilds, scheduler, failed subsystems',
     "emoji": '🛠'},
    {"label": 'runtime', "value": 'runtime',
     "description": 'snapshot_all roll-up across every provider',
     "emoji": '🛰'},
    {"label": 'lifecycle', "value": 'lifecycle',
     "description": 'Lifecycle phase, pending requests, recent events',
     "emoji": '♻️'},
    {"label": 'caches', "value": 'caches',
     "description": 'F-1 guild_config + governance cache state',
     "emoji": '🧠'},
    {"label": 'media', "value": 'media',
     "description": 'Media (YouTube) cache health + provider outcomes',
     "emoji": '🎬'},
    {"label": 'locks', "value": 'locks',
     "description": 'scope_locks snapshot (no filter)',
     "emoji": '🔒'},
    {"label": 'tasks', "value": 'tasks',
     "description": 'Managed background-task snapshot',
     "emoji": '🔁'},
    {"label": 'views', "value": 'views',
     "description": 'Registered PersistentView classes by subsystem',
     "emoji": '🖼'},
    {"label": 'sessions', "value": 'sessions',
     "description": 'Active session counts by subsystem',
     "emoji": '🎫'},
    {"label": 'slow', "value": 'slow',
     "description": 'Slow-path log entries (latest 10)',
     "emoji": '🐢'},
    {"label": 'automation', "value": 'automation',
     "description": 'Scheduler status + per-guild rule management panel',
     "emoji": '🤖'},
)

_CATALOGUES_OPTIONS: tuple[dict, ...] = (
    {"label": 'schemas', "value": 'schemas',
     "description": 'Registered SubsystemSchema instances',
     "emoji": '📐'},
    {"label": 'settings-registry', "value": 'settings-registry',
     "description": 'Every declared SettingSpec',
     "emoji": '🗂️'},
    {"label": 'customization', "value": 'customization',
     "description": 'Customization catalogue across subsystems',
     "emoji": '🧭'},
    {"label": 'provisioning', "value": 'provisioning',
     "description": 'ResourceRequirement × BindingSpec catalogue',
     "emoji": '🧰'},
    {"label": 'participation-schemas', "value": 'participation-schemas',
     "description": 'Registered ParticipationSchema instances',
     "emoji": '🧑‍🤝‍🧑'},
    {"label": 'resource-requirements', "value": 'resource-requirements',
     "description": 'Declared ResourceRequirement entries',
     "emoji": '🧱'},
)

_RESOURCES_OPTIONS: tuple[dict, ...] = (
    {"label": 'resources', "value": 'resources',
     "description": 'Resource runtime taxonomy + status histogram',
     "emoji": '🧱'},
    {"label": 'bindings', "value": 'bindings',
     "description": 'Subsystem bindings taxonomy + per-guild counts',
     "emoji": '🔗'},
    {"label": 'flags', "value": 'flags',
     "description": 'Feature flag declarations + effective resolution',
     "emoji": '🚩'},
    {"label": 'migrations', "value": 'migrations',
     "description": 'Platform migration checkpoints',
     "emoji": '🛠'},
)

_VALIDATION_OPTIONS: tuple[dict, ...] = (
    {"label": 'identity', "value": 'identity',
     "description": 'Identity-contract validator findings',
     "emoji": '🪪'},
    {"label": 'consistency', "value": 'consistency',
     "description": 'Unified platform readiness diagnostic',
     "emoji": '🛡'},
    {"label": 'anchors', "value": 'anchors',
     "description": 'Panel anchor restoration + active counts',
     "emoji": '📌'},
    {"label": 'setup-readiness', "value": 'setup-readiness',
     "description": 'Per-guild setup-readiness inventory',
     "emoji": '✅'},
)

#: the capture world's flag declaration registry (pinned — see the module
#: docstring; sweep_platform_flag pins every option byte).
_FLAG_OPTIONS: tuple[dict, ...] = (
    {"label": '🛠 Settings menu (!settings)',
     "value": 'settings.manager_cog.enabled',
     "description": 'settings.manager_cog.enabled'},
    {"label": '🛠 YouTube context for AI replies',
     "value": 'youtube.context.enabled',
     "description": 'youtube.context.enabled'},
    {"label": '⚙ Bindings as primary source (internal rollout gate)',
     "value": 'bindings.primary',
     "description": 'bindings.primary'},
    {"label": '⚙ Feature-flag runtime gate (env-only, internal)',
     "value": 'feature_flag.primary',
     "description": 'feature_flag.primary · env-only'},
    {"label": '⚙ Participation runtime (internal rollout gate)',
     "value": 'participation.enabled',
     "description": 'participation.enabled'},
    {"label": '⚙ Resource provisioning pipeline primary (operator kill-switch)',
     "value": 'resource_provisioning.primary',
     "description": 'resource_provisioning.primary · inactive — no consumer'},
    {"label": '⚙ Unified resource discovery (internal rollout gate)',
     "value": 'resources.unified',
     "description": 'resources.unified · inactive — no consumer'},
    {"label": '⚙ Settings mutation pipeline primary (operator kill-switch)',
     "value": 'settings.mutation.primary',
     "description": 'settings.mutation.primary · inactive — no consumer'},
)

_HUB_FIELDS: tuple[tuple[str, str], ...] = (
    ('Runtime / status',
     '🩺 `health` — Deterministic operational health snapshot (redacted)\n'
     '🚀 `startup` — Settled-startup health report (extension load, gateway, DB)\n'
     '📋 `findings` — Persistent operational-health findings (open, redacted)\n'
     '🛠 `status` — Uptime, cogs, guilds, scheduler, failed subsystems\n'
     '🛰 `runtime` — snapshot_all roll-up across every provider\n'
     '♻️ `lifecycle` — Lifecycle phase, pending requests, recent events\n'
     '🧠 `caches` — F-1 guild_config + governance cache state\n'
     '🎬 `media` — Media (YouTube) cache health + provider outcomes\n'
     '🔒 `locks` — scope_locks snapshot (no filter)\n'
     '🔁 `tasks` — Managed background-task snapshot\n'
     '🖼 `views` — Registered PersistentView classes by subsystem\n'
     '🎫 `sessions` — Active session counts by subsystem\n'
     '🐢 `slow` — Slow-path log entries (latest 10)\n'
     '🤖 `automation` — Scheduler status + per-guild rule management panel'),
    ('Catalogues',
     '📐 `schemas` — Registered SubsystemSchema instances\n'
     '🗂️ `settings-registry` — Every declared SettingSpec\n'
     '🧭 `customization` — Customization catalogue across subsystems\n'
     '🧰 `provisioning` — ResourceRequirement × BindingSpec catalogue\n'
     '🧑‍🤝‍🧑 `participation-schemas` — Registered ParticipationSchema instances\n'
     '🧱 `resource-requirements` — Declared ResourceRequirement entries'),
    ('Resources / rollout',
     '🧱 `resources` — Resource runtime taxonomy + status histogram\n'
     '🔗 `bindings` — Subsystem bindings taxonomy + per-guild counts\n'
     '🚩 `flags` — Feature flag declarations + effective resolution\n'
     '🛠 `migrations` — Platform migration checkpoints'),
    ('Validation',
     '🪪 `identity` — Identity-contract validator findings\n'
     '🛡 `consistency` — Unified platform readiness diagnostic\n'
     '📌 `anchors` — Panel anchor restoration + active counts\n'
     '✅ `setup-readiness` — Per-guild setup-readiness inventory'),
    ('Mutations / managers',
     '🚩 Flag manager — Open the editable per-guild flag manager'),
)
_HUB_DESCRIPTION = ('Diagnostics + managers. Pick a surface from one of the '
                    'category dropdowns below — every entry maps to an '
                    'existing `!platform <subcommand>`. The four category '
                    'dropdowns are **read-only**; mutation surfaces live '
                    'under Mutations / managers.')
_HUB_FOOTER = ('Typed `!platform <name>` commands keep working with their '
               'filters/limits (e.g. `!platform locks counting`).')

_DIAG_FIELDS: tuple[tuple[str, str], ...] = (
    ('🤖 Bot Status', 'Health & performance metrics'),
    ('📡 Latency', 'WebSocket ping'),
    ('💻 System Info', 'OS, disk & Python version'),
    ('🗄️ Check Database', 'Verify all DB tables exist'),
    ('📄 Validate JSON', 'Check data file integrity'),
    ('📋 Command List', 'Paginated command overview'),
    ('🔍 Recent Errors', 'Last 10 error log entries'),
    ('🔔 Test Notify', 'Fire a test webhook ping'),
)
_DIAG_DESCRIPTION = ('Select a diagnostic tool below.\n'
                     'All tools require Administrator permission.')
_DIAG_FOOTER = 'Diagnostics Hub  •  Admin only'

_FLAG_DESCRIPTION = ('Pick a flag from the dropdown to view its current '
                     'state and enable/disable it for this guild. Every '
                     'mutation routes through the rollout pipeline '
                     '(validated + audited + cache invalidated).')
_FLAG_FOOTER = ('Read-only by default. Enable/Disable only mutate the '
                'per-guild override — global flag state and rollout percent '
                'are unchanged.')

_AUTOMATION_DESCRIPTION = ('⚠️ Scheduler snapshot: scheduler not registered '
                           '(services.automation_scheduler not started)')

# --- providers -------------------------------------------------------------------

_HUB_PROVIDERS = (
    ("diagnostic.hub_runtime_options", _RUNTIME_OPTIONS),
    ("diagnostic.hub_catalogues_options", _CATALOGUES_OPTIONS),
    ("diagnostic.hub_resources_options", _RESOURCES_OPTIONS),
    ("diagnostic.hub_validation_options", _VALIDATION_OPTIONS),
    ("diagnostic.flag_options", _FLAG_OPTIONS),
)


def _static_provider(rows: tuple[dict, ...]):
    async def _rows(ctx: object):
        return rows
    return _rows


async def _automation_rule_options(ctx: object):
    """The shipped rule dropdown — v1 has no automation-rule store, so the
    honest constant is the shipped no-rules placeholder option verbatim
    (sweep_platform_automation pins the bytes)."""
    return (
        {"label": '(no rules in this guild)', "value": '0',
         "description": "Create one via !automation or the wizard's "
                        "preset picker."},
    )


def _ensure_providers() -> None:
    for name, rows in _HUB_PROVIDERS:
        if not is_registered(ProviderRef(name)):
            provider(name)(_static_provider(rows))
    if not is_registered(ProviderRef("diagnostic.automation_rule_options")):
        provider("diagnostic.automation_rule_options")(
            _automation_rule_options)


# --- the specs -------------------------------------------------------------------

def diagnostic_hub_spec() -> PanelSpec:
    """The shipped 🔧 Diagnostics Hub (module docstring)."""
    def _btn(action_id: str, label: str, style: ActionStyle,
             route: HandlerRef) -> PanelActionSpec:
        return PanelActionSpec(
            action_id=action_id, label=label, style=style,
            audience_tier=_TIER, handler=route)

    return PanelSpec(
        panel_id="diagnostic.hub",
        subsystem="diagnostic",
        title="🔧 Diagnostics Hub",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        actions=(
            _btn("diag_status", "🤖 Bot Status", ActionStyle.PRIMARY,
                 HandlerRef("diagnostic.diag_status_view")),
            _btn("diag_latency", "📡 Latency", ActionStyle.PRIMARY,
                 HandlerRef("diagnostic.diag_latency")),
            _btn("diag_sysinfo", "💻 System Info", ActionStyle.PRIMARY,
                 HandlerRef("diagnostic.diag_sysinfo_view")),
            _btn("diag_database", "🗄️ Database", ActionStyle.SECONDARY,
                 HandlerRef("diagnostic.check_database_view")),
            _btn("diag_json", "📄 JSON Files", ActionStyle.SECONDARY,
                 HandlerRef("diagnostic.validate_json_view")),
            _btn("diag_commands", "📋 Commands", ActionStyle.SECONDARY,
                 PanelRef("diagnostic.command_list")),
            _btn("diag_errors", "🔍 Recent Errors", ActionStyle.DANGER,
                 HandlerRef("diagnostic.diag_errors_view")),
            _btn("diag_notify", "🔔 Test Notify", ActionStyle.SECONDARY,
                 HandlerRef("diagnostic.test_notification_view")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("diag_status", "diag_latency", "diag_sysinfo"),
            ("diag_database", "diag_json", "diag_commands"),
            ("diag_errors", "diag_notify"),
        )),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_hub"),
        justification=(
            "the shipped Diagnostics Hub embed carries eight INLINE tool "
            "fields plus the 'Diagnostics Hub  •  Admin only' footer "
            "literal — grammar FieldsBlock rows render inline=False and "
            "FooterMode has no such literal. The override delegates the "
            "COMPONENTS to render_panel (declared buttons untouched) and "
            "composes the EMBED only; "
            "goldens/diagnostic/sweep_diagnostics pins every byte."),
    )


def diagnostic_card_spec() -> PanelSpec:
    """The generic one-embed reply card (the shipped ``ctx.send(embed=…)``,
    the ai.card lane)."""
    return PanelSpec(
        panel_id="diagnostic.card",
        subsystem="diagnostic",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_card"),
        justification=(
            "the shipped `!platform <view>` / `!latency` replies are "
            "capture-world snapshot embeds built by "
            "sb/domain/diagnostic/platform_views.py (goldens/diagnostic "
            "pins the bytes). Zero components; the renderer presents the "
            "handler-built RenderedEmbed verbatim (the ai.card "
            "precedent)."),
    )


def command_list_spec() -> PanelSpec:
    """The shipped ``!list_commands_detailed`` paginator (module
    docstring)."""
    return PanelSpec(
        panel_id="diagnostic.command_list",
        subsystem="diagnostic",
        title="Command List",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        actions=(
            # the shipped _PaginatorView pair (ButtonStyle.secondary,
            # session auto-ids — the golden pins <cid:1>/<cid:2>; the
            # index-edge buttons render disabled via the renderer
            # override, the shipped _update_buttons).
            PanelActionSpec(
                action_id="cmdlist_prev", label="◀ Prev",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.cmdlist_prev")),
            PanelActionSpec(
                action_id="cmdlist_next", label="Next ▶",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.cmdlist_next")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("cmdlist_prev", "cmdlist_next"),
        )),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_command_list"),
        justification=(
            "the shipped command-list embed is page 1 of the capture "
            "registry paginator — four per-cog fields of shipped "
            "docstring/cooldown/alias lines with the shipped 1024-byte "
            "truncation, plus the 'Command List — Page 1/14' page title "
            "(capture literals, command_catalog.py) — and the first-page "
            "◀ Prev button renders disabled, outside the grammar's "
            "vocabulary (actions carry no disabled state; the admin "
            "cogmgr precedent). The override delegates the COMPONENTS to "
            "render_panel and composes the EMBED plus that one disabled "
            "bit only; goldens/diagnostic/sweep_list_commands_detailed "
            "pins every byte."),
    )


def platform_hub_spec() -> PanelSpec:
    """The shipped 🛰 Platform hub (module docstring)."""
    def _select(selector_id: str, override: str, placeholder: str,
                provider_name: str) -> SelectorSpec:
        return SelectorSpec(
            selector_id=selector_id, kind=SelectorKind.ENUM,
            on_select=HandlerRef("diagnostic.hub_open_view"),
            options_source=ProviderRef(provider_name),
            placeholder=placeholder, audience_tier=_TIER,
            custom_id_override=override)

    return PanelSpec(
        panel_id="diagnostic.platform_hub",
        subsystem="diagnostic",
        title="🛰 Platform hub",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        selectors=(
            _select("pf_runtime", "platform_hub.runtime",
                    "Runtime / status…",
                    "diagnostic.hub_runtime_options"),
            _select("pf_catalogues", "platform_hub.catalogues",
                    "Catalogues…",
                    "diagnostic.hub_catalogues_options"),
            _select("pf_resources", "platform_hub.resources",
                    "Resources / rollout…",
                    "diagnostic.hub_resources_options"),
            _select("pf_validation", "platform_hub.validation",
                    "Validation…",
                    "diagnostic.hub_validation_options"),
        ),
        actions=(
            PanelActionSpec(
                action_id="pf_overview", label="↩ Overview",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.hub_reopen"),
                custom_id_override="platform_hub.overview"),
            PanelActionSpec(
                action_id="pf_flag_manager", label="🚩 Flag manager",
                style=ActionStyle.PRIMARY, audience_tier=_TIER,
                handler=PanelRef("diagnostic.flag_manager"),
                custom_id_override="platform_hub.flag_manager"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pf_runtime",),
            ("pf_catalogues",),
            ("pf_resources",),
            ("pf_validation",),
            ("pf_overview", "pf_flag_manager"),
        )),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_platform_hub"),
        justification=(
            "the shipped Platform hub embed carries five catalogue fields "
            "whose lines mirror the select options plus the typed-commands "
            "footer literal — static shipped copy outside the grammar's "
            "FieldsBlock/FooterMode vocabulary. The override delegates the "
            "COMPONENTS to render_panel (declared selects/buttons with "
            "their verbatim custom_id_override pins untouched) and "
            "composes the EMBED only; goldens/diagnostic/sweep_platform + "
            "sweep_slash_platform pin every byte on both surfaces."),
    )


def flag_manager_spec() -> PanelSpec:
    """The shipped 🚩 Flag Manager (module docstring)."""
    return PanelSpec(
        panel_id="diagnostic.flag_manager",
        subsystem="diagnostic",
        title="🚩 Flag Manager",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="pf_flag_pick", kind=SelectorKind.ENUM,
                on_select=HandlerRef("diagnostic.flag_pick"),
                options_source=ProviderRef("diagnostic.flag_options"),
                placeholder="Choose a flag…", audience_tier=_TIER,
                custom_id_override="flag_manager:select"),
        ),
        actions=(
            PanelActionSpec(
                action_id="pf_flag_enable",
                label="✅ Enable for this guild",
                style=ActionStyle.SUCCESS, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.flag_enable"),
                custom_id_override="flag_manager:enable"),
            PanelActionSpec(
                action_id="pf_flag_disable",
                label="🛑 Disable for this guild",
                style=ActionStyle.DANGER, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.flag_disable"),
                custom_id_override="flag_manager:disable"),
            PanelActionSpec(
                action_id="pf_flag_refresh", label="🔄 Refresh",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.flag_reopen"),
                custom_id_override="flag_manager:refresh"),
            PanelActionSpec(
                action_id="pf_flag_back", label="↩ Back to Platform",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.hub_reopen"),
                custom_id_override="flag_manager:back"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pf_flag_pick",),
            ("pf_flag_enable", "pf_flag_disable", "pf_flag_refresh"),
            ("pf_flag_back",),
        )),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_flag_manager"),
        justification=(
            "the shipped Flag Manager embed is the static rollout-pipeline "
            "prose plus the read-only footer literal — outside FooterMode's "
            "vocabulary. The override delegates the COMPONENTS to "
            "render_panel (the verbatim flag_manager:* custom_id_override "
            "pins untouched) and composes the EMBED only; "
            "goldens/diagnostic/sweep_platform_flag pins every byte."),
    )


def automation_panel_spec() -> PanelSpec:
    """The shipped 🤖 Automation panel (module docstring)."""
    return PanelSpec(
        panel_id="diagnostic.automation_panel",
        subsystem="diagnostic",
        title="🤖 Automation panel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="orange",
                             footer_mode=FooterMode.NONE),
        selectors=(
            SelectorSpec(
                selector_id="pf_auto_rule", kind=SelectorKind.ENUM,
                on_select=HandlerRef("diagnostic.automation_rule_pick"),
                options_source=ProviderRef(
                    "diagnostic.automation_rule_options"),
                placeholder="Pick a rule…", audience_tier=_TIER),
        ),
        actions=(
            PanelActionSpec(
                action_id="pf_auto_enable", label="Enable",
                style=ActionStyle.SUCCESS, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.automation_enable")),
            PanelActionSpec(
                action_id="pf_auto_disable", label="Disable",
                style=ActionStyle.SECONDARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.automation_disable")),
            PanelActionSpec(
                action_id="pf_auto_delete", label="Delete",
                style=ActionStyle.DANGER, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.automation_delete")),
            PanelActionSpec(
                action_id="pf_auto_refresh", label="Refresh",
                style=ActionStyle.PRIMARY, audience_tier=_TIER,
                handler=HandlerRef("diagnostic.automation_reopen")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pf_auto_rule",),
            ("pf_auto_enable", "pf_auto_disable", "pf_auto_delete",
             "pf_auto_refresh"),
        )),)),
        session_lifecycle=True,
        renderer_override=HandlerRef("diagnostic.render_automation"),
        justification=(
            "the shipped Automation panel embed carries the "
            "scheduler-snapshot warning line and the no-rules Rules field "
            "— state-keyed shipped copy outside the grammar's vocabulary "
            "(true as a constant in both worlds: neither the capture "
            "harness nor v1 registers services.automation_scheduler). The "
            "override delegates the COMPONENTS to render_panel and "
            "composes the EMBED only; "
            "goldens/diagnostic/sweep_platform_automation pins every "
            "byte."),
    )


# --- renderer overrides ------------------------------------------------------------

async def _render_card(spec: PanelSpec, ctx) -> object:
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    embed = (ctx.params or {}).get("_card")
    if not isinstance(embed, RenderedEmbed):  # defensive: never a crash
        embed = RenderedEmbed(title="", description="")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


def _embed_override(title: str, description: str,
                    fields: tuple = (), footer: str = "",
                    style_token: str = "blurple", inline: bool = False):
    async def _render(spec: PanelSpec, ctx) -> object:
        from sb.kernel.panels.render import RenderedEmbed, render_panel

        base = await render_panel(spec, ctx)
        embed = RenderedEmbed(
            title=title, description=description,
            fields=tuple((n, v, inline) for n, v in fields),
            footer=footer, style_token=style_token)
        return _dc_replace(base, embed=embed)
    return _render


async def _render_command_list(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped adjustments (see the panel's
    justification): the requested capture-literal page (``cmdlist_page``
    in the panel args, default page 1 — the golden's bare open), and the
    shipped ``_update_buttons`` edge-disable (◀ Prev on the first page,
    Next ▶ on the last; the admin cogmgr override pattern)."""
    from sb.domain.diagnostic.command_catalog import COMMAND_LIST_PAGES
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    try:
        index = int((ctx.params or {}).get("cmdlist_page", 0) or 0)
    except (TypeError, ValueError):
        index = 0
    index = min(max(index, 0), len(COMMAND_LIST_PAGES) - 1)
    title, fields = COMMAND_LIST_PAGES[index]

    base = await render_panel(spec, ctx)

    def _edge(component):
        if component.custom_id == f"{spec.panel_id}.cmdlist_prev":
            return _dc_replace(component, disabled=(index == 0))
        if component.custom_id == f"{spec.panel_id}.cmdlist_next":
            return _dc_replace(
                component, disabled=(index == len(COMMAND_LIST_PAGES) - 1))
        return component

    components = tuple(_edge(c) for c in base.components)
    embed = RenderedEmbed(
        title=title, description="",
        fields=tuple((n, v, False) for n, v in fields),
        style_token="blue")
    return _dc_replace(base, components=components, embed=embed)


_render_hub = _embed_override(
    "🔧 Diagnostics Hub", _DIAG_DESCRIPTION, _DIAG_FIELDS,
    footer=_DIAG_FOOTER, style_token="blue", inline=True)

_render_platform_hub = _embed_override(
    "🛰 Platform hub", _HUB_DESCRIPTION, _HUB_FIELDS,
    footer=_HUB_FOOTER, style_token="blurple")

#: the Flag Manager detail footer — FINAL v1 copy (the oracle's footer
#: named RolloutMutationPipeline.set_flag_state, which does not exist in
#: this build; naming it would be false provenance).
_FLAG_DETAIL_FOOTER = ("Enable/Disable refuse while a flag has no consumer "
                       "in this build — no silent no-op writes.")

_render_flag_overview = _embed_override(
    "🚩 Flag Manager", _FLAG_DESCRIPTION,
    footer=_FLAG_FOOTER, style_token="red")


async def _render_flag_manager(spec: PanelSpec, ctx) -> object:
    """The shipped FlagManagerView render split: the overview embed until
    a flag is picked (goldens/diagnostic/sweep_platform_flag — no sweep
    clicks the select, so the golden's bare open always lands here), the
    flag DETAIL embed after (``build_flag_detail_embed`` shape verbatim;
    the pick memory lives in handlers.py, per guild+invoker)."""
    from sb.domain.diagnostic.flag_catalog import flag_details
    from sb.domain.diagnostic.handlers import flag_pick_for
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    picked = flag_pick_for(ctx.guild_id, getattr(ctx.actor, "user_id", 0))
    if not picked:
        return await _render_flag_overview(spec, ctx)

    details = flag_details(picked)
    fields = [
        ("Key", f"`{details['name']}`", True),
        ("Audience", f"`{details['audience']}`", True),
        ("Editable",
         "`per-guild`" if details["db_editable"] else "`env-only`", True),
        ("Default", f"`{details['default']}`", True),
        ("Effective", f"`{details['effective']}`", True),
        ("Source", f"`{details['source']}`", True),
        ("Owner", f"`{details['owner']}`", True),
        ("Guild override",
         "`yes`" if details["has_guild_override"] else "`none`", True),
    ]
    if details["removal_target"]:
        fields.append(("Removal target", details["removal_target"], True))
    # the oracle's plain-language Notes, kept where TRUE in this build
    # (its SUPERBOT_FF_* env-var pointers are dropped — nothing in v1
    # reads those variables).
    notes = []
    if details["no_consumer"]:
        notes.append("⚠️ **Inactive / no consumer** — declared but no "
                     "runtime code reads this flag in this build, so "
                     "toggling it changes nothing today.")
    if not details["db_editable"]:
        notes.append("🔒 **Env-only** — per-guild DB overrides are "
                     "ignored by the evaluator.")
    if notes:
        fields.append(("Notes", "\n".join(notes)[:1024], False))

    base = await render_panel(spec, ctx)
    embed = RenderedEmbed(
        title=f"🚩 {details['label'] or details['name']}",
        description=details["description"] or "_No description._",
        fields=tuple(fields),
        footer=_FLAG_DETAIL_FOOTER,
        style_token="red")
    return _dc_replace(base, embed=embed)

_render_automation = _embed_override(
    "🤖 Automation panel", _AUTOMATION_DESCRIPTION,
    (("Rules", "_No automation rules in this guild._"),),
    style_token="orange")

_RENDERERS = (
    ("diagnostic.render_card", _render_card),
    ("diagnostic.render_command_list", _render_command_list),
    ("diagnostic.render_hub", _render_hub),
    ("diagnostic.render_platform_hub", _render_platform_hub),
    ("diagnostic.render_flag_manager", _render_flag_manager),
    ("diagnostic.render_automation", _render_automation),
)


def _ensure_renderers() -> None:
    for name, fn in _RENDERERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


def _ensure_reopen_handlers() -> None:
    """The refresh/reopen click routes that live panel-side (the shipped
    edit-in-place refreshes land as fresh re-opens — the projmoon
    class)."""
    from sb.kernel.panels.engine import open_panel

    if not is_registered(HandlerRef("diagnostic.flag_reopen")):
        @handler("diagnostic.flag_reopen")
        async def flag_reopen(req) -> None:
            await open_panel(PanelRef("diagnostic.flag_manager"), req)

    if not is_registered(HandlerRef("diagnostic.automation_reopen")):
        @handler("diagnostic.automation_reopen")
        async def automation_reopen(req) -> None:
            await open_panel(PanelRef("diagnostic.automation_panel"), req)


# --- registration -------------------------------------------------------------------

_SPEC_FACTORIES = (
    ("diagnostic.hub", diagnostic_hub_spec),
    ("diagnostic.card", diagnostic_card_spec),
    ("diagnostic.command_list", command_list_spec),
    ("diagnostic.platform_hub", platform_hub_spec),
    ("diagnostic.flag_manager", flag_manager_spec),
    ("diagnostic.automation_panel", automation_panel_spec),
)


@panel("diagnostic.hub")
def _hub_factory() -> PanelSpec:
    return diagnostic_hub_spec()


@panel("diagnostic.card")
def _card_factory() -> PanelSpec:
    return diagnostic_card_spec()


@panel("diagnostic.command_list")
def _command_list_factory() -> PanelSpec:
    return command_list_spec()


@panel("diagnostic.platform_hub")
def _platform_hub_factory() -> PanelSpec:
    return platform_hub_spec()


@panel("diagnostic.flag_manager")
def _flag_manager_factory() -> PanelSpec:
    return flag_manager_spec()


@panel("diagnostic.automation_panel")
def _automation_factory() -> PanelSpec:
    return automation_panel_spec()


_FACTORY_TABLE = (
    ("diagnostic.hub", _hub_factory),
    ("diagnostic.card", _card_factory),
    ("diagnostic.command_list", _command_list_factory),
    ("diagnostic.platform_hub", _platform_hub_factory),
    ("diagnostic.flag_manager", _flag_manager_factory),
    ("diagnostic.automation_panel", _automation_factory),
)

_ensure_providers()
_ensure_renderers()
_ensure_reopen_handlers()


def all_panel_specs() -> tuple[PanelSpec, ...]:
    return tuple(factory() for _, factory in _SPEC_FACTORIES)


def install_diagnostic_panels() -> PanelSpec:
    """Register every diagnostic panel; returns the hub spec (the band-1
    signature the tests pin)."""
    out: list[PanelSpec] = []
    for _, factory in _SPEC_FACTORIES:
        spec = factory()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return out[0]


def ensure_diagnostic_refs() -> None:
    """Idempotent re-arm (the ENSURE_REFS pattern, D-0025)."""
    from sb.spec.refs import is_registered as _is, panel as _panel

    _ensure_providers()
    _ensure_renderers()
    _ensure_reopen_handlers()
    for panel_id, factory in _FACTORY_TABLE:
        if not _is(PanelRef(panel_id)):
            _panel(panel_id)(factory)
