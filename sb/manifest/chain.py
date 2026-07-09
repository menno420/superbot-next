"""CHAIN subsystem manifest (band 6, message-game family) — the shipped
word-chain surface verbatim: the !chain group (create / delete /
setlimit / removelimit / list) + !chainmenu over chain_channels; the
per-message rule is ``sb.domain.chain.service.handle_message`` (the
MESSAGE FEED arms with the live adapter, order-20 auto-mod tier)."""

from __future__ import annotations

from sb.domain.chain import panels as _panels
from sb.domain.chain import service as _service
from sb.domain.chain.ops import register_ops
from sb.domain.chain.store import CHAIN_CHANNELS_STORE
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _sub(name: str, ref: str, summary: str,
         tier: str = "staff") -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX, group="chain",
                       route=HandlerRef(ref), audience_tier=tier,
                       capability="chain", summary=summary,
                       usage=f"!chain {name}")


MANIFEST = SubsystemManifest(
    key="chain",
    version=1,
    commands=(
        CommandSpec(name="chain", kind=CommandKind.PREFIX,
                    route=HandlerRef("chain.usage_view"),
                    audience_tier="user", capability="chain",
                    summary="Manage message chains and word limits.",
                    usage="!chain <create|delete|setlimit|removelimit"
                          "|list>"),
        _sub("create", "chain.create_route",
             "Lock a channel to one allowed word."),
        _sub("delete", "chain.delete_route",
             "Remove a channel's chain (word and limit)."),
        _sub("setlimit", "chain.setlimit_route",
             "Cap messages at N words (0 removes the cap)."),
        _sub("removelimit", "chain.removelimit_route",
             "Remove a channel's word limit."),
        _sub("list", "chain.list_view",
             "List every chain/limit in this server.", tier="user"),
        CommandSpec(name="chainmenu", kind=CommandKind.PREFIX,
                    route=PanelRef("chain.hub"), audience_tier="staff",
                    capability="chain",
                    summary="Open the chain management panel.",
                    usage="!chainmenu"),
    ),
    panels=(_panels.chain_hub_spec(),),
    settings=(),
    stores=(CHAIN_CHANNELS_STORE,),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.chain import ops as _ops
    from sb.domain.chain import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_handler_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
