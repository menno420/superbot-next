"""ROLE subsystem manifest (band 5) — the shipped role-management family
verbatim (cogs/role_cog.py + role_grants_cog.py + the reaction-roles
overhaul services): the 7-action Role Hub (persistent custom_ids
pinned), time/XP threshold automation, reaction roles (legacy emoji
surface + menus), automation exemptions, temp grants + the A-8
role:grants_expiry sweep task, and the settings slice
(sb/domain/settings/keys.py `role` module).

Importing this manifest FILLS the band-4 waiting port
sb.domain.xp.service.install_level_role_granter (the D-0031/D-0036
contract) via service.install_xp_ports().
"""

from __future__ import annotations

from sb.domain.role import handlers as _handlers
from sb.domain.role.ops import register_ops
from sb.domain.role.panels import install_role_panels, role_hub_spec
from sb.domain.role.service import install_xp_ports
from sb.domain.role.store import (
    REACTION_MODES_STORE,
    REACTION_ROLES_STORE,
    ROLE_EXEMPTIONS_STORE,
    ROLE_GRANTS_STORE,
    ROLE_MENU_OPTIONS_STORE,
    ROLE_MENUS_STORE,
    ROLE_PICKUP_STATS_STORE,
    ROLE_THRESHOLDS_STORE,
)
from sb.kernel.scheduler.due_queue import declare_task
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.scheduler import Interval, ManagedTaskSpec, TaskDurability
from sb.spec.settings import Activation, SettingSpec


def _cmd(name: str, route, *, aliases: tuple = (), tier: str = "administrator",
         summary: str = "", usage: str = "",
         kind: CommandKind = CommandKind.PREFIX) -> CommandSpec:
    return CommandSpec(name=name, kind=kind, route=route, aliases=aliases,
                       audience_tier=tier, capability="role",
                       summary=summary, usage=usage)


_COMMANDS = (
    _cmd("roles", PanelRef("role.hub"),
         summary="Open the Role Hub — create, manage, automate.",
         usage="!roles"),
    _cmd("rolesettings", HandlerRef("role.time_roles_view"),
         summary="Show the configured time-based role tiers.",
         usage="!rolesettings"),
    _cmd("roleinfo", HandlerRef("role.roleinfo_pending"), aliases=("ri",),
         summary="Inspect one role (live guild view).",
         usage="!roleinfo <role>"),
    # rolemenu opened the shipped RoleHubPanelView (role_cog.py) — the
    # golden (parity/goldens/role/sweep_rolemenu.json) captures the hub
    # embed + buttons, NOT a reaction-role listing (band-5 mis-map fix;
    # `!listreactroles` keeps the reaction_view text surface).
    _cmd("rolemenu", PanelRef("role.hub"),
         summary="Open the Role Hub — create, manage, automate.",
         usage="!rolemenu"),
    _cmd("rolecreator", HandlerRef("role.create_pending"),
         summary="Interactive role creation (live adapter).",
         usage="!rolecreator"),
    _cmd("assignroles", HandlerRef("role.assignroles_pending"),
         summary="Run the time-role reconciliation now.",
         usage="!assignroles"),
    _cmd("createrole", HandlerRef("role.create_pending"),
         summary="Create a server role (live adapter).",
         usage="!createrole <name> [color]"),
    _cmd("deleterole", HandlerRef("role.create_pending"),
         summary="Delete a server role (live adapter).",
         usage="!deleterole <role>"),
    _cmd("setrole", HandlerRef("role.setrole"),
         summary="Auto-assign a role after N days in the server.",
         usage="!setrole <days> <role name>"),
    _cmd("unsetrole", HandlerRef("role.unsetrole"),
         summary="Remove a time-based role tier.",
         usage="!unsetrole <role name>"),
    _cmd("debugroles", HandlerRef("role.debug_pending"),
         summary="Role automation diagnostics (live adapter).",
         usage="!debugroles"),
    _cmd("refreshmembers", HandlerRef("role.debug_pending"),
         summary="Refresh the member cache (live adapter).",
         usage="!refreshmembers"),
    _cmd("reactroles", HandlerRef("role.reactroles_bind"),
         aliases=("reaktionsrollen",),
         summary="Bind an emoji reaction on a message to a role.",
         usage="!reactroles <message_id> <emoji> <@role>"),
    _cmd("removereactrole", HandlerRef("role.reactroles_unbind"),
         summary="Remove a reaction-role binding.",
         usage="!removereactrole <message_id> <emoji>"),
    _cmd("listreactroles", HandlerRef("role.reaction_view"),
         summary="List reaction-role bindings.",
         usage="!listreactroles"),
    _cmd("temprole", HandlerRef("role.temprole"), tier="moderator",
         summary="Grant a role temporarily (auto-removed on expiry).",
         usage="!temprole @member <duration> <@role>"),
    _cmd("temproles", HandlerRef("role.temproles"), tier="user",
         summary="Show a member's active temporary roles.",
         usage="!temproles [@member]"),
)

_SETTINGS = (
    SettingSpec(name="skip_roles", value_type=str, default="",
                settings_key="skip_roles",
                hint="Comma-separated role names the automation engines "
                     "never touch (legacy skip list)."),
    SettingSpec(name="time_roles_stack", value_type=bool, default=False,
                settings_key="time_roles_stack",
                activation=Activation.OFF_UNTIL_OPT_IN,
                hint="Keep previously-earned tenure tiers on promotion "
                     "instead of removing them. Historical default: off."),
    SettingSpec(name="xp_roles_stack", value_type=bool, default=True,
                settings_key="xp_roles_stack",
                activation=Activation.ON_BY_DEFAULT,
                hint="Keep lower level roles when a higher tier is earned. "
                     "Historical default: on."),
    SettingSpec(name="reaction_roles_enabled", value_type=bool, default=True,
                settings_key="reaction_roles_enabled",
                activation=Activation.ON_BY_DEFAULT,
                hint="Master switch for the emoji reaction-role surface."),
)

#: A-8: the temp-grant expiry sweep (shipped RoleGrantsCog 5-minute loop).
GRANTS_EXPIRY_TASK = declare_task(ManagedTaskSpec(
    name="role:grants_expiry",
    trigger=Interval(seconds=300),
    handler=HandlerRef("role.grants_expiry_fire"),
    durability=TaskDurability.IN_MEMORY,
))

MANIFEST = SubsystemManifest(
    key="role",
    version=1,
    commands=_COMMANDS,
    panels=install_role_panels(),
    settings=_SETTINGS,
    stores=(ROLE_THRESHOLDS_STORE, REACTION_ROLES_STORE,
            REACTION_MODES_STORE, ROLE_MENUS_STORE, ROLE_MENU_OPTIONS_STORE,
            ROLE_GRANTS_STORE, ROLE_PICKUP_STATS_STORE,
            ROLE_EXEMPTIONS_STORE),
    events=(),
    capabilities=(),
)

register_ops()
install_xp_ports()


def _ensure_refs() -> None:
    from sb.domain.role import ops as _ops
    from sb.domain.role import panels as _panels
    from sb.domain.role import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _handlers.ensure_handler_refs()
    _panels.ensure_panel_refs()
    register_ops()
    install_role_panels()
    install_xp_ports()


ENSURE_REFS = _ensure_refs
