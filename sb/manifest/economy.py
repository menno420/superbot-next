"""ECONOMY subsystem manifest (band 3) — shipped command names verbatim
(cogs/economy_cog.py), the daily/work/pay/buy loops as K7 ops (CRIT-9: one
audited seam for every coin movement), the `economy.balance_changed` domain
event, the five economy stores (the money aggregate + THE hottest audit
ledger, NAME_STABLE), and the INV-F aggregate⊄ledger reconciliation
invariant. The settings slice claims the shipped economy key
(economy_log_channel → the binding lane, the P0-3 pointer-lane convergence
carried)."""

from __future__ import annotations

from sb.domain.economy import handlers as _handlers
from sb.domain.economy import panels as _panels
from sb.domain.economy.invariants import declare_economy_invariants
from sb.domain.economy.ops import EVT_BALANCE_CHANGED, register_ops
from sb.domain.economy.store import (
    ECONOMY_AUDIT_STORE,
    ECONOMY_BALANCES_STORE,
    ECONOMY_TRACK_STORE,
    INVENTORY_STORE,
    JOB_PROGRESS_STORE,
)
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.events import DeliveryClass, EventSpec, FieldSpec, register_event_specs
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef
from sb.spec.settings import (
    BindingKind,
    BindingSpec,
    ProvisioningHint,
    ProvisioningPriority,
    ResourceKind,
    ResourceRequirement,
)

BALANCE_CHANGED_EVENT = EventSpec(
    name=EVT_BALANCE_CHANGED,                # shipped verbatim
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("delta", "int"),
        FieldSpec("new_balance", "int"),
        FieldSpec("reason", "str"),
    ),
    owner_subsystem="economy",
    delivery=DeliveryClass.BEST_EFFORT,      # OD-1 v1 default; ALO rides the owner ruling
)

_SETTINGS = (
    # P0-3 pointer-lane convergence carried: the economy_log_channel scalar
    # was retired shipped-side; the pointer lives in the binding lane and the
    # legacy KV key is the alias.
    BindingSpec(name="log_channel", kind=BindingKind.CHANNEL,
                hint="Live feed of daily rewards, work earnings, transfers, "
                     "and shop purchases.",
                legacy_settings_key_aliases=("economy_log_channel",)),
    ResourceRequirement(
        kind=ResourceKind.CHANNEL, intent="log_channel",
        provisioning=ProvisioningHint(priority=ProvisioningPriority.RECOMMENDED,
                                      suggested_name="economy-log",
                                      suggested_category="Staff"),
        binding_name="log_channel",
        description="Operator-facing audit channel for economy mutations. "
                    "Recommended for any guild that runs the economy "
                    "actively.",
        offer_on_enable=True,
        audit_intent="economy_log_channel"),
)


def _cmd(name: str, route, *, kind: CommandKind = CommandKind.PREFIX,
         aliases: tuple[str, ...] = (), cooldown: CooldownSpec | None = None,
         tier: str = "user", summary: str = "", usage: str = "") -> CommandSpec:
    return CommandSpec(name=name, kind=kind, route=route, aliases=aliases,
                       cooldown=cooldown, audience_tier=tier, summary=summary,
                       usage=usage, capability="economy")


MANIFEST = SubsystemManifest(
    key="economy",
    version=1,
    commands=(
        _cmd("economymenu", PanelRef("economy.hub"),
             cooldown=CooldownSpec(rate=3, per_s=10),
             summary="Open the interactive economy control panel.",
             usage="!economymenu"),
        _cmd("economy", PanelRef("economy.hub"), kind=CommandKind.SLASH,
             summary="Open the Economy hub (daily, work, shop, balance).",
             usage="/economy"),
        _cmd("daily", WorkflowRef("economy.daily"),
             cooldown=CooldownSpec(rate=2, per_s=5),
             summary="Claim your daily reward. Higher streaks unlock "
                     "better odds!",
             usage="!daily"),
        _cmd("work", HandlerRef("economy.work_view"),
             cooldown=CooldownSpec(rate=2, per_s=5),
             summary="Work a job and earn coins + XP (1 h cooldown).",
             usage="!work [job]"),
        # panel-action slice: !shop opens the interactive shop panel (the
        # shipped _ShopView flow); the economy.shop_view text handler stays
        # registered as the NL/read fallback.
        _cmd("shop", PanelRef("economy.shop_panel"),
             summary="Browse and buy items from the shop.", usage="!shop"),
        _cmd("balance", HandlerRef("economy.balance_view"),
             aliases=("bal", "wallet"),
             summary="Show your (or another user's) current coin balance.",
             usage="!balance [@user]"),
        _cmd("pay", WorkflowRef("economy.pay"), aliases=("transfer",),
             cooldown=CooldownSpec(rate=3, per_s=10),
             summary="Send coins to another member.",
             usage="!pay @user <amount>"),
        _cmd("setlogchannel", HandlerRef("economy.setlogchannel"),
             tier="",                    # ADMIN floor (shipped @admin_or_owner)
             summary="Set the economy log channel.",
             usage="!setlogchannel #channel"),
        _cmd("joblist", HandlerRef("economy.joblist_view"), aliases=("jobs",),
             summary="Show all jobs, requirements, and your mastery.",
             usage="!joblist"),
    ),
    panels=(_panels.economy_hub_spec(), _panels.jobcenter_spec(),
            _panels.shop_panel_spec()),
    settings=_SETTINGS,
    stores=(ECONOMY_BALANCES_STORE, ECONOMY_AUDIT_STORE, ECONOMY_TRACK_STORE,
            JOB_PROGRESS_STORE, INVENTORY_STORE),
    events=(BALANCE_CHANGED_EVENT,),
    capabilities=(),
    data_invariants=(declare_economy_invariants(),),
)

register_ops()
register_event_specs([BALANCE_CHANGED_EVENT])


def _ensure_refs() -> None:
    from sb.domain.economy import invariants as _inv
    from sb.domain.economy import ops as _ops
    from sb.domain.economy import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()
    _inv.ensure_invariant_refs()
    register_ops()
    register_event_specs([BALANCE_CHANGED_EVENT])


ENSURE_REFS = _ensure_refs
