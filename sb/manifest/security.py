"""SECURITY subsystem manifest (band 2) — raid detection + account-age
screening slice verbatim; decision cores are pure (sb/domain/security).
A-14 adjacency: the age screen + welcome entry-role gate are the join-
verification anchors."""

from __future__ import annotations

from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef
from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

_TITLE, _BLURB = "Security", ("Raid detection + account-age screening on "
                              "member join.")
ensure_hub("security", _TITLE, _BLURB)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="security_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Master security switch."),
    SettingSpec(name="raid_enabled", value_type=bool, default=False,
                settings_key="security_raid_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Raid-join detection."),
    SettingSpec(name="raid_join_count", value_type=int, default=10,
                settings_key="security_raid_join_count", bounds=(2, 100),
                hint="Joins inside the window that count as a raid."),
    SettingSpec(name="raid_window_seconds", value_type=int, default=60,
                settings_key="security_raid_window_seconds", bounds=(5, 3600),
                hint="Raid sliding-window length."),
    SettingSpec(name="raid_slowmode_seconds", value_type=int, default=10,
                settings_key="security_raid_slowmode_seconds", bounds=(0, 21600),
                hint="Slowmode applied during a raid (0 = none)."),
    SettingSpec(name="raid_lockdown_seconds", value_type=int, default=300,
                settings_key="security_raid_lockdown_seconds", bounds=(30, 86400),
                hint="How long a raid lockdown holds."),
    SettingSpec(name="age_enabled", value_type=bool, default=False,
                settings_key="security_age_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Screen accounts younger than the minimum age."),
    SettingSpec(name="age_min_days", value_type=int, default=7,
                settings_key="security_age_min_days", bounds=(0, 365),
                hint="Minimum account age in days."),
    SettingSpec(name="age_action", value_type=str, default="alert",
                settings_key="security_age_action",
                allowed_values=("alert", "kick", "ban"),
                hint="Action for under-age accounts."),
    BindingSpec(name="raid_slowmode_channel", kind=BindingKind.CHANNEL,
                hint="Channel slowmoded during a raid.",
                legacy_settings_key_aliases=("security_raid_slowmode_channel",)),
    BindingSpec(name="alert_channel", kind=BindingKind.CHANNEL,
                hint="Security alert channel.",
                legacy_settings_key_aliases=("security_alert_channel",)),
)

MANIFEST = SubsystemManifest(
    key="security",
    version=1,
    commands=(
        CommandSpec(name="security", kind=CommandKind.PREFIX,
                    route=PanelRef("security.hub"),
                    summary="Open the security menu.", capability="security"),
    ),
    panels=(hub_spec("security", _TITLE, _BLURB),),
    settings=_SETTINGS,
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("security", _TITLE, _BLURB)


ENSURE_REFS = _ensure_refs
