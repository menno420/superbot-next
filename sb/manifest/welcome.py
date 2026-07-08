"""WELCOME subsystem manifest (band 2) — greetings/farewells slice
verbatim + the A-14 join-verification anchors (entry_role binding = the
deny-until-role gate's role source; min_account_age_days = the screening
input). The member-join feed arms with the member band."""

from __future__ import annotations

from sb.domain.operator_spine import ensure_hub, hub_spec
from sb.domain.welcome import DEFAULT_JOIN_MESSAGE, DEFAULT_LEAVE_MESSAGE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import PanelRef
from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

_TITLE, _BLURB = "Welcome", ("Member greetings, farewells, and the optional "
                             "entry role (the A-14 join gate anchor).")
ensure_hub("welcome", _TITLE, _BLURB)

_SETTINGS = (
    SettingSpec(name="enabled", value_type=bool, default=False,
                settings_key="welcome_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Master welcome switch."),
    SettingSpec(name="join_enabled", value_type=bool, default=True,
                settings_key="welcome_join_enabled",
                activation=Activation.ON_BY_DEFAULT,
                hint="Post a greeting on member join."),
    SettingSpec(name="leave_enabled", value_type=bool, default=False,
                settings_key="welcome_leave_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Post a farewell on member leave."),
    SettingSpec(name="join_message", value_type=str,
                default=DEFAULT_JOIN_MESSAGE,
                settings_key="welcome_join_message",
                hint="Greeting template ({user}/{server}/{count})."),
    SettingSpec(name="leave_message", value_type=str,
                default=DEFAULT_LEAVE_MESSAGE,
                settings_key="welcome_leave_message",
                hint="Farewell template ({user}/{server}/{count})."),
    SettingSpec(name="dm_enabled", value_type=bool, default=False,
                settings_key="welcome_dm_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                external_side_effects=True,
                hint="DM new members a welcome message."),
    SettingSpec(name="dm_message", value_type=str, default="",
                settings_key="welcome_dm_message",
                hint="DM template (empty = built-in copy)."),
    SettingSpec(name="card_enabled", value_type=bool, default=False,
                settings_key="welcome_card_enabled",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Render the welcome card image."),
    SettingSpec(name="min_account_age_days", value_type=int, default=0,
                settings_key="welcome_min_account_age_days", bounds=(0, 365),
                hint="A-14 screening input: minimum account age."),
    SettingSpec(name="delete_after_seconds", value_type=int, default=0,
                settings_key="welcome_delete_after_seconds", bounds=(0, 86400),
                hint="Auto-delete the greeting after N seconds (0 = keep)."),
    BindingSpec(name="channel", kind=BindingKind.CHANNEL,
                hint="Greeting/farewell channel.",
                legacy_settings_key_aliases=("welcome_channel",)),
    BindingSpec(name="entry_role", kind=BindingKind.ROLE,
                hint="Role granted on join — the A-14 deny-until-role "
                     "gate's role source.",
                legacy_settings_key_aliases=("welcome_entry_role",)),
)

MANIFEST = SubsystemManifest(
    key="welcome",
    version=1,
    commands=(
        CommandSpec(name="welcome", kind=CommandKind.PREFIX,
                    route=PanelRef("welcome.hub"),
                    summary="Open the welcome menu.", capability="welcome"),
    ),
    panels=(hub_spec("welcome", _TITLE, _BLURB),),
    settings=_SETTINGS,
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    ensure_hub("welcome", _TITLE, _BLURB)


ENSURE_REFS = _ensure_refs
