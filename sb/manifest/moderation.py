"""MODERATION subsystem manifest (band 2, operator spine) — shipped command
names verbatim (cogs/moderation_cog.py), the warn/timeout/kick/ban lanes as
K7 ops, the `moderation.action_taken` domain event, and the mod_logs +
warnings stores. Settings claim the shipped moderation keys slice
(sb/domain/settings/keys.py `moderation`)."""

from __future__ import annotations

from sb.domain.moderation import panels as _panels
from sb.domain.moderation import service as _service
from sb.domain.moderation.ops import EVT_MOD_ACTION, register_ops
from sb.domain.moderation.store import MOD_LOGS_STORE, WARNINGS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef
from sb.spec.settings import Activation, BindingKind, BindingSpec, SettingSpec

MOD_ACTION_EVENT = EventSpec(
    name=EVT_MOD_ACTION,                     # shipped verbatim
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("action", "str"),
        FieldSpec("target_id", "int"),
        FieldSpec("actor_id", "int"),
        FieldSpec("reason", "str", required=False),
    ),
    owner_subsystem="moderation",
    delivery=DeliveryClass.BEST_EFFORT,      # OD-1 v1: only the audit canary is ALO
)

_SETTINGS = (
    SettingSpec(name="warn_threshold", value_type=int, default=3,
                settings_key="warn_threshold", bounds=(1, 50),
                hint="Warnings before the escalation action runs."),
    SettingSpec(name="warn_timeout_minutes", value_type=int, default=10,
                settings_key="warn_timeout_minutes", bounds=(1, 40320),
                hint="Timeout length applied by the warn escalation."),
    SettingSpec(name="warn_escalation_action", value_type=str, default="timeout",
                settings_key="moderation_warn_escalation_action",
                allowed_values=_service.WARN_ESCALATION_ACTIONS,
                hint="Action at the warn threshold."),
    SettingSpec(name="dm_on_action", value_type=bool, default=False,
                settings_key="moderation_dm_on_action",
                activation=Activation.OFF_UNTIL_OPT_IN,
                external_side_effects=True,
                hint="DM the member when actioned."),
    SettingSpec(name="dm_actions", value_type=str,
                default=",".join(_service.DM_NOTIFY_ACTIONS),
                settings_key="moderation_dm_actions",
                hint="Comma list of actions that DM the member."),
    SettingSpec(name="dm_template", value_type=str, default="",
                settings_key="moderation_dm_template",
                hint="Custom DM template ({action}/{reason}/{guild})."),
    SettingSpec(name="require_reason", value_type=bool, default=False,
                settings_key="moderation_require_reason",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Refuse warn/kick/ban without a reason."),
    SettingSpec(name="ban_delete_message_days", value_type=int, default=0,
                settings_key="moderation_ban_delete_message_days",
                bounds=(0, 7),
                hint="Days of messages swept on ban."),
    SettingSpec(name="max_timeout_minutes", value_type=int, default=40320,
                settings_key="moderation_max_timeout_minutes",
                bounds=(1, 40320),
                hint="Ceiling for any timeout duration."),
    SettingSpec(name="post_action_cleanup", value_type=str, default="none",
                settings_key="moderation_post_action_cleanup",
                allowed_values=_service.POST_ACTION_CLEANUP_ACTIONS,
                hint="Sweep the actioned member's recent messages."),
    SettingSpec(name="post_action_cleanup_limit", value_type=int, default=100,
                settings_key="moderation_post_action_cleanup_limit",
                bounds=(1, 500),
                hint="Max messages scanned by the post-action sweep."),
    SettingSpec(name="public_log_actions", value_type=str, default="none",
                settings_key="moderation_public_log_actions",
                allowed_values=_service.PUBLIC_LOG_ACTIONS,
                hint="Which actions post to the public log channel."),
)

_BINDINGS = (
    BindingSpec(name="public_log", kind=BindingKind.CHANNEL,
                hint="Public moderation-log channel.",
                legacy_settings_key_aliases=("moderation_public_log_channel",)),
)


def _cmd(name: str, route, *, kind: CommandKind = CommandKind.PREFIX,
         summary: str = "", usage: str = "") -> CommandSpec:
    return CommandSpec(name=name, kind=kind, route=route, summary=summary,
                       usage=usage, capability="moderation")


MANIFEST = SubsystemManifest(
    key="moderation",
    version=1,
    commands=(
        _cmd("modmenu", PanelRef("moderation.hub"),
             summary="Open the moderation menu.", usage="!modmenu"),
        _cmd("moderation", PanelRef("moderation.hub"), kind=CommandKind.BOTH,
             summary="Open the moderation menu.", usage="/moderation"),
        _cmd("warn", WorkflowRef("moderation.warn"),
             summary="Warn a member (escalates at the threshold).",
             usage="!warn @member [reason]"),
        _cmd("timeout", WorkflowRef("moderation.timeout"),
             summary="Timeout a member.",
             usage="!timeout @member <minutes>"),
        _cmd("kick", WorkflowRef("moderation.kick"),
             summary="Kick a member.", usage="!kick @member [reason]"),
        _cmd("ban", WorkflowRef("moderation.ban"),
             summary="Ban a member.", usage="!ban @member [reason]"),
        _cmd("unban", WorkflowRef("moderation.unban"),
             summary="Unban a user id.", usage="!unban <user_id> [reason]"),
        _cmd("clearwarnings", WorkflowRef("moderation.clearwarnings"),
             summary="Clear a member's warnings.",
             usage="!clearwarnings @member"),
        _cmd("warnings", HandlerRef("moderation.warnings_view"),
             summary="Show a member's warning count.",
             usage="!warnings @member"),
        _cmd("modlogs", HandlerRef("moderation.modlogs_view"),
             summary="Show a member's moderation history.",
             usage="!modlogs @member"),
    ),
    panels=(_panels.moderation_hub_spec(),),
    settings=_SETTINGS + _BINDINGS,      # bindings ride the same facet tuple
    stores=(MOD_LOGS_STORE, WARNINGS_STORE),
    events=(MOD_ACTION_EVENT,),
    capabilities=(),
)

register_ops()
register_event_specs([MOD_ACTION_EVENT])


def _ensure_refs() -> None:
    from sb.domain.moderation import ops as _ops
    from sb.domain.moderation import service as _svc
    from sb.domain.moderation import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _svc.ensure_handler_refs()
    register_ops()
    register_event_specs([MOD_ACTION_EVENT])


ENSURE_REFS = _ensure_refs
