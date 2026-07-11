"""XP subsystem manifest (band 4) — shipped command names verbatim
(cogs/xp_cog.py), the award/reset/import loops as K7 ops (INV-G: one
audited seam for every XP mutation), the shipped event vocabulary
(xp.awarded / xp.level_up / xp.reset — the level_up→community_spotlight
wiring is now a DECLARED event), the `xp` store (RENAME complement of
band 3's coins extraction, REVERSE_IMPORTABLE), and the level-consistency
invariant. The settings slice claims the shipped xp keys (xp_min/xp_max/
xp_cooldown; xp_announce_channel is the P0-3 binding-lane pointer,
carried as the BindingSpec legacy alias).

IMPORTING THIS MANIFEST FILLS THE BAND-3 WAITING PORTS:
sb.domain.xp.service.install_economy_ports() installs the real level
reader + xp awarder into sb.domain.economy.service (D-0031 boundary).
"""

from __future__ import annotations

from sb.domain.xp import handlers as _handlers
from sb.domain.xp import panels as _panels
from sb.domain.xp import service as _service
from sb.domain.xp.invariants import declare_xp_invariants
from sb.domain.xp.ops import (
    EVT_LEVEL_UP,
    EVT_XP_AWARDED,
    EVT_XP_RESET,
    register_ops,
)
from sb.domain.xp.store import XP_STORE
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.settings import (
    BindingKind,
    BindingSpec,
    ProvisioningHint,
    ProvisioningPriority,
    ResourceKind,
    ResourceRequirement,
    SettingSpec,
)

# shipped payload keys verbatim (services/xp_service.py bus.emit calls)
XP_AWARDED_EVENT = EventSpec(
    name=EVT_XP_AWARDED,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("delta", "int"),
        FieldSpec("new_xp", "int"),
        FieldSpec("new_level", "int"),
        FieldSpec("source", "str"),
    ),
    owner_subsystem="xp",
    delivery=DeliveryClass.BEST_EFFORT,   # OD-1 v1 default; ALO rides the ruling
)
LEVEL_UP_EVENT = EventSpec(
    name=EVT_LEVEL_UP,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("new_level", "int"),
        FieldSpec("source", "str"),
    ),
    owner_subsystem="xp",
    delivery=DeliveryClass.BEST_EFFORT,
)
XP_RESET_EVENT = EventSpec(
    name=EVT_XP_RESET,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("actor_id", "int", required=False),
        FieldSpec("source", "str"),
    ),
    owner_subsystem="xp",
    delivery=DeliveryClass.BEST_EFFORT,
)

_EVENTS = (XP_AWARDED_EVENT, LEVEL_UP_EVENT, XP_RESET_EVENT)


_SETTINGS = (
    SettingSpec(name="xp_min", value_type=int, default=15,
                settings_key="xp_min",
                hint="Minimum XP awarded per qualifying message.",
                bounds=(1, 10_000)),
    SettingSpec(name="xp_max", value_type=int, default=25,
                settings_key="xp_max",
                hint="Maximum XP awarded per qualifying message.",
                bounds=(1, 10_000)),
    SettingSpec(name="xp_cooldown", value_type=int, default=60,
                settings_key="xp_cooldown",
                hint="Seconds between XP awards per user. Zero disables "
                     "the cooldown (not recommended in active guilds).",
                bounds=(0, 86_400),
                input_hint="numeric_presets",
                presets=(0, 15, 30, 60, 120, 300)),
    # P0-3 pointer-lane convergence carried: the xp_announce_channel
    # scalar was retired shipped-side; the pointer lives in the binding
    # lane and the legacy KV key is the alias.
    BindingSpec(name="announce_channel", kind=BindingKind.CHANNEL,
                hint="Channel where level-up announcements post. Leave "
                     "unbound to announce where the level-up happened.",
                legacy_settings_key_aliases=("xp_announce_channel",)),
    ResourceRequirement(
        kind=ResourceKind.CHANNEL, intent="announce_channel",
        provisioning=ProvisioningHint(priority=ProvisioningPriority.OPTIONAL,
                                      suggested_name="level-ups",
                                      suggested_category="Community"),
        binding_name="announce_channel",
        description="Dedicated channel for level-up announcements. "
                    "Optional — XP announces in-place when unset."),
)


def _cmd(name: str, route, *, kind: CommandKind = CommandKind.PREFIX,
         aliases: tuple[str, ...] = (), cooldown: CooldownSpec | None = None,
         tier: str = "user", summary: str = "", usage: str = "") -> CommandSpec:
    return CommandSpec(name=name, kind=kind, route=route, aliases=aliases,
                       cooldown=cooldown, audience_tier=tier, summary=summary,
                       usage=usage, capability="xp")


MANIFEST = SubsystemManifest(
    key="xp",
    version=1,
    commands=(
        _cmd("xpmenu", PanelRef("xp.hub"),
             summary="Open the XP panel showing your rank and quick "
                     "admin actions.",
             usage="!xpmenu"),
        _cmd("rank", HandlerRef("xp.rank_view"),
             summary="Show rank in a category (xp/coins/both or any "
                     "leaderboard category).",
             usage="!rank [@user] [xp|coins|both|<category>]"),
        _cmd("givexp", HandlerRef("xp.givexp"),
             tier="",                    # ADMIN floor (shipped @admin_or_owner)
             summary="Give XP to a user (admin only).",
             usage="!givexp @user <amount>"),
        _cmd("resetxp", HandlerRef("xp.resetxp"),
             tier="",                    # ADMIN floor (shipped @admin_or_owner)
             summary="Reset a user's XP to zero (admin only).",
             usage="!resetxp @user"),
        _cmd("xpconfig", HandlerRef("xp.xpconfig_view"),
             tier="",                    # ADMIN floor (shipped @admin_or_owner)
             summary="Show the XP configuration.",
             usage="!xpconfig"),
        _cmd("xpimport", HandlerRef("xp.xpimport"),
             tier="",                    # ADMIN floor (shipped @admin_or_owner)
             summary="Import XP/levels from another bot's level-up "
                     "channel (raise-only, preview first).",
             usage="!xpimport [source] [#channel] [limit]"),
    ),
    panels=(_panels.xp_hub_spec(), _panels.rank_card_spec(),
            _panels.xp_config_spec(), _panels.import_scan_spec()),
    settings=_SETTINGS,
    stores=(XP_STORE,),
    events=_EVENTS,
    capabilities=(),
    data_invariants=(declare_xp_invariants(),),
)

register_ops()
register_event_specs(list(_EVENTS))
_service.install_economy_ports()          # the D-0031 waiting ports, FILLED


def _ensure_refs() -> None:
    from sb.domain.xp import invariants as _inv
    from sb.domain.xp import ops as _ops
    from sb.domain.xp import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _inv.ensure_invariant_refs()
    register_ops()
    register_event_specs(list(_EVENTS))
    _service.install_economy_ports()


ENSURE_REFS = _ensure_refs
