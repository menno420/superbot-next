"""LOGGING subsystem manifest (band 2, operator spine) — manifest key
`logging` (module named server_logging: stdlib-shadow discipline, S15
precedent). FLIPPED to the shipped surface (disbot cogs/logging_cog.py +
cogs/logging/{panel,select_view,routes_panel,schemas}.py @58040c6):

* the shipped `!logging` group VERBATIM — bare group opens the panel
  (invoke_without_command: an unknown token like the D-0029-era `enable`
  falls through to the SAME panel; goldens/logging pin it), plus the five
  real subcommands status/set/create/routes/test. The D-0029 `enable` /
  `disable` subcommands were NEVER shipped commands (zero oracle
  hits; no sweep golden exists for either) — retired at the flip, the
  moderation-`!warnings` D-0065(3) precedent. The master switch lives on
  the settings surface (`logging_enabled` — §4.1 one-write-path).
* the shipped 11-slot route/binding table (select_view._ROUTE_BINDING)
  replaces D-0029's 6 interim BindingSpecs — binding NAMES are the
  shipped ones (mod_channel/…); the two legacy KV aliases carry.
* four panels: the LoggingPanelView hub (8 static logging_panel.* ids),
  the zero-component status card, the Routes panel (logging_routes.*),
  and the LogChannelSelectView channel picker (session-minted ids).
"""

from __future__ import annotations

from sb.domain.server_logging import handlers as _handlers
from sb.domain.server_logging import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

_CATEGORY_SETTINGS = tuple(
    SettingSpec(name=f"{category}_enabled", value_type=bool, default=False,
                settings_key=f"logging_{category}_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint=f"Log the {category} event family.")
    for category in ("messages", "members", "roles", "moderation",
                     "channels", "server", "voice")
)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="logging_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Master switch for server logging."),
    SettingSpec(name="auto_create_channels", value_type=bool, default=False,
                settings_key="logging_auto_create_channels",
                activation=Activation.OFF_UNTIL_OPT_IN,
                external_side_effects=True,
                hint="Provision missing log channels automatically."),
    SettingSpec(name="event_routing", value_type=str, default="combined",
                settings_key="logging_event_routing",
                allowed_values=("combined", "per_category"),
                hint="One combined events channel, or one per category."),
    SettingSpec(name="ignored_channels", value_type=str, default="",
                settings_key="logging_ignored_channels",
                hint="Comma list of channel ids never logged."),
    SettingSpec(name="ignored_users", value_type=str, default="",
                settings_key="logging_ignored_users",
                hint="Comma list of user ids never logged."),
) + _CATEGORY_SETTINGS

#: the shipped 11 route bindings (cogs/logging/schemas.py BindingSpecs;
#: names verbatim). The two legacy KV pointer aliases carry from the
#: pre-flip manifest (decision 3).
_BINDINGS = (
    BindingSpec(name="mod_channel", kind=BindingKind.CHANNEL,
                hint="Moderation log channel (default name bot-mod-log).",
                legacy_settings_key_aliases=("logging_mod_channel",)),
    BindingSpec(name="events_channel", kind=BindingKind.CHANNEL,
                hint="Combined event-log channel (default bot-event-log)."),
    BindingSpec(name="cleanup_channel", kind=BindingKind.CHANNEL,
                hint="Cleanup log channel (falls back to mod).",
                legacy_settings_key_aliases=("logging_cleanup_channel",)),
    BindingSpec(name="debug_channel", kind=BindingKind.CHANNEL,
                hint="Debug severity route (falls back to mod)."),
    BindingSpec(name="info_channel", kind=BindingKind.CHANNEL,
                hint="Info severity route (falls back to mod)."),
    BindingSpec(name="warning_channel", kind=BindingKind.CHANNEL,
                hint="Warning severity route (falls back to mod)."),
    BindingSpec(name="error_channel", kind=BindingKind.CHANNEL,
                hint="Error severity route (falls back to mod)."),
    BindingSpec(name="audit_channel", kind=BindingKind.CHANNEL,
                hint="Audit-feed route (falls back to mod)."),
    BindingSpec(name="message_channel", kind=BindingKind.CHANNEL,
                hint="Per-category: message events (falls back to events)."),
    BindingSpec(name="member_channel", kind=BindingKind.CHANNEL,
                hint="Per-category: member events (falls back to events)."),
    BindingSpec(name="role_channel", kind=BindingKind.CHANNEL,
                hint="Per-category: role events (falls back to events)."),
)


def _sub(name: str, ref: str, summary: str, usage: str | None = None) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="logging",
                       route=HandlerRef(ref), summary=summary,
                       usage=usage or f"!logging {name}",
                       capability="logging")


MANIFEST = SubsystemManifest(
    key="logging",
    version=1,
    commands=(
        CommandSpec(name="logging", kind=CommandKind.PREFIX,
                    route=PanelRef("logging.hub"),
                    summary="Open the server-logging panel.",
                    usage="!logging", capability="logging"),
        CommandSpec(name="status", kind=CommandKind.PREFIX, group="logging",
                    route=PanelRef("logging.status_card"),
                    summary="Show the logging config + counters.",
                    usage="!logging status", capability="logging"),
        _sub("set", "logging.set_channel",
             "Open the channel selector for a log binding.",
             usage="!logging set <route>"),
        _sub("create", "logging.create_channels",
             "Provision a missing log channel.",
             usage="!logging create <route>"),
        _sub("routes", "logging.routes_view",
             "Show per-route bindings + fallbacks."),
        _sub("test", "logging.test_send", "Send a test log line."),
    ),
    panels=(_panels.logging_hub_spec(), _panels.status_card_spec(),
            _panels.routes_panel_spec(), _panels.bind_picker_spec()),
    settings=_SETTINGS + _BINDINGS,
    stores=(),                      # KV/bindings rows live in the settings stores
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
