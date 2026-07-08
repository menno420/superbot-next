"""AUTOMOD subsystem manifest (band 2) — the shipped settings slice
verbatim + the pure decision engine (sb/domain/automod/engine.py); the
on_message feed arms with the message band."""

from __future__ import annotations

from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef
from sb.spec.settings import Activation, SettingSpec

_TITLE, _BLURB = "Automod", ("Spam / invite / caps / mention / duplicate "
                             "filtering — decisions are pure engine rules.")
ensure_hub("automod", _TITLE, _BLURB)

_TOGGLES = tuple(
    SettingSpec(name=f"{rule}_enabled", value_type=bool, default=False,
                settings_key=f"automod_{rule}_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint=f"Enable the {rule.replace('_', ' ')} rule.")
    for rule in ("spam", "invites", "caps", "mentions",
                 "cross_channel_spam", "duplicate")
)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="automod_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Master automod switch."),
) + _TOGGLES + (
    SettingSpec(name="spam_count", value_type=int, default=5,
                settings_key="automod_spam_count", bounds=(2, 50),
                hint="Messages inside the window that count as spam."),
    SettingSpec(name="spam_window_seconds", value_type=int, default=7,
                settings_key="automod_spam_window_seconds", bounds=(1, 300),
                hint="Spam sliding-window length."),
    SettingSpec(name="caps_percent", value_type=int, default=70,
                settings_key="automod_caps_percent", bounds=(10, 100),
                hint="Uppercase percentage threshold."),
    SettingSpec(name="mentions_count", value_type=int, default=4,
                settings_key="automod_mentions_count", bounds=(2, 50),
                hint="Mentions per message threshold."),
    SettingSpec(name="cross_channel_spam_count", value_type=int, default=4,
                settings_key="automod_cross_channel_spam_count", bounds=(2, 20),
                hint="Distinct channels inside the window."),
    SettingSpec(name="duplicate_count", value_type=int, default=3,
                settings_key="automod_duplicate_count", bounds=(2, 20),
                hint="Identical messages inside the window."),
    SettingSpec(name="exempt_roles", value_type=str, default="",
                settings_key="automod_exempt_roles",
                hint="Comma list of exempt role ids."),
    SettingSpec(name="exempt_channels", value_type=str, default="",
                settings_key="automod_exempt_channels",
                hint="Comma list of exempt channel ids."),
)

MANIFEST = SubsystemManifest(
    key="automod",
    version=1,
    commands=(
        CommandSpec(name="automod", kind=CommandKind.PREFIX,
                    route=PanelRef("automod.hub"),
                    summary="Open the automod menu.", capability="automod"),
    ),
    panels=(hub_spec("automod", _TITLE, _BLURB),),
    settings=_SETTINGS,
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("automod", _TITLE, _BLURB)


ENSURE_REFS = _ensure_refs
