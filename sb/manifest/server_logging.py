"""LOGGING subsystem manifest (band 2, operator spine) — manifest key
`logging` (module named server_logging: stdlib-shadow discipline, S15
precedent). Shipped `!logging` group verbatim (cogs/logging_cog.py) via
CommandSpec.group; settings claim the shipped logging keys slice; channel
pointers are BindingSpecs with the legacy KV aliases (decision 3)."""

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

_BINDINGS = (
    BindingSpec(name="mod", kind=BindingKind.CHANNEL,
                hint="Moderation log channel (default name bot-mod-log).",
                legacy_settings_key_aliases=("logging_mod_channel",)),
    BindingSpec(name="cleanup", kind=BindingKind.CHANNEL,
                hint="Cleanup log channel (falls back to mod).",
                legacy_settings_key_aliases=("logging_cleanup_channel",)),
    BindingSpec(name="events", kind=BindingKind.CHANNEL,
                hint="Combined event-log channel."),
    BindingSpec(name="messages", kind=BindingKind.CHANNEL,
                hint="Per-category: message events."),
    BindingSpec(name="members", kind=BindingKind.CHANNEL,
                hint="Per-category: member events."),
    BindingSpec(name="roles", kind=BindingKind.CHANNEL,
                hint="Per-category: role events."),
)


def _sub(name: str, ref: str, summary: str) -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="logging",
                       route=HandlerRef(ref), summary=summary,
                       usage=f"!logging {name}", capability="logging")


MANIFEST = SubsystemManifest(
    key="logging",
    version=1,
    commands=(
        CommandSpec(name="logging", kind=CommandKind.PREFIX,
                    route=PanelRef("logging.hub"),
                    summary="Open the server-logging menu.",
                    usage="!logging", capability="logging"),
        _sub("status", "logging.status_view",
             "Show the logging config + counters."),
        _sub("enable", "logging.enable", "Enable server logging."),
        _sub("disable", "logging.disable", "Disable server logging."),
        _sub("set", "logging.set_channel",
             "Bind a log slot to a channel."),
        _sub("create", "logging.create_channels",
             "Provision missing log channels."),
        _sub("routes", "logging.routes_view",
             "Show per-category routing."),
        _sub("test", "logging.test_send", "Send a test log line."),
    ),
    panels=(_panels.logging_hub_spec(),),
    settings=_SETTINGS + _BINDINGS,
    stores=(),                      # KV/bindings rows live in the settings stores
    events=(),
    capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
