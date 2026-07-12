"""MINING subsystem manifest (band 6, checkpoint family / parity flip) —
the FULL shipped command surface verbatim (37 commands): the core loop
(fastmine/chop/explore/sell/sellall/buy + reads + the admin reset) is
live over the audited K7 lanes with the shipped reply bytes
(goldens/mining/ pin them — see sb/domain/mining/service.py); `!mine`
carries the capture-pinned grid-navigator artifact copy; the deep
systems are honest pending terminals riding the D-0043 named successor
port. The hub panel is the shipped MiningHubView byte-for-byte
(sb/domain/mining/panels.py)."""

from __future__ import annotations

from sb.domain.mining import service as _service
from sb.domain.mining.ops import register_ops
from sb.domain.mining.panels import mining_hub_spec
from sb.domain.mining.store import (
    MINING_INVENTORY_STORE,
    MINING_PLAYER_STATE_STORE,
)
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef


def _cmd(name: str, route, summary: str, aliases: tuple[str, ...] = (),
         tier: str = "user") -> CommandSpec:
    return CommandSpec(name=name, kind=CommandKind.PREFIX,
                       aliases=aliases, route=route, audience_tier=tier,
                       capability="mining", summary=summary,
                       usage=f"!{name}")


def _pending(name: str, summary: str,
             aliases: tuple[str, ...] = ()) -> CommandSpec:
    return _cmd(name, HandlerRef(f"mining.{name}_pending"), summary,
                aliases)


_COMMANDS = (
    _cmd("minemenu", PanelRef("mining.hub"), "Open the mining hub."),
    _cmd("mine", HandlerRef("mining.mine_route"),
         "Open the grid Mine navigator — roam the world and dig."),
    _cmd("fastmine", HandlerRef("mining.fastmine_route"),
         "One quick mining swing — no buttons."),
    _cmd("chop", HandlerRef("mining.chop_route"), "Chop wood."),
    _cmd("explore", HandlerRef("mining.explore_route"),
         "Explore the caves for a random find."),
    _cmd("sell", HandlerRef("mining.sell_route"),
         "Sell a resource: !sell <item> [qty]."),
    _cmd("sellall", HandlerRef("mining.sellall_route"),
         "Sell every sellable resource in your pack."),
    _cmd("buy", HandlerRef("mining.buy_route"),
         "Buy gear from the shop: !buy <item>."),
    _cmd("market", HandlerRef("mining.market_view"),
         "Market prices — what sells for what."),
    _cmd("mineinv", HandlerRef("mining.inventory_view"),
         "Your mining pack.", ("mineinventory",)),
    _cmd("minestats", HandlerRef("mining.stats_view"),
         "Your mining stats."),
    # --- deep systems (the D-0043 named successor port) -------------------
    _pending("build", "Build a structure.", ("craft",)),
    _pending("buildlist", "List built structures."),
    _pending("buildable", "What you can build now."),
    _pending("use", "Use a consumable item."),
    _pending("cook", "Cook fish at a campfire."),
    _pending("equip", "Equip a tool or gear piece."),
    _pending("unequip", "Unequip a gear slot."),
    _pending("gear", "Your equipped gear."),
    _pending("loadout", "Gear loadout presets.", ("loadouts",)),
    _pending("character", "Your character sheet.", ("profile", "char")),
    _pending("descend", "Descend to a deeper mining band."),
    _pending("ascend", "Return toward the surface."),
    _pending("mineworld", "The shared mining world grid."),
    _pending("vault", "Your vault."),
    _pending("stash", "Stash resources in the vault."),
    _pending("unstash", "Withdraw from the vault."),
    _pending("vaultupgrade", "Upgrade vault capacity."),
    _pending("skills", "Your skill tree."),
    _pending("skill", "Spend a skill point."),
    _pending("titles", "Your earned titles."),
    _pending("forge", "The forge."),
    _pending("home", "Your home structure."),
    _pending("workshop", "The repair workshop."),
    _pending("repair", "Repair worn gear."),
    _pending("quickcraft", "Craft the best available recipe."),
    # shipped admin gate: member_has_perms_or_owner(administrator=True)
    # in-handler — the port home is the tier lane (deny copy is the
    # kernel's; unpinned — no golden drives the non-admin branch).
    _cmd("reset_inventory", HandlerRef("mining.reset_inventory_route"),
         "Admin: reset a member's mining inventory (this guild).",
         tier="administrator"),
)

MANIFEST = SubsystemManifest(
    key="mining",
    version=1,
    commands=_COMMANDS,
    panels=(mining_hub_spec(),),
    settings=(),
    stores=(MINING_INVENTORY_STORE, MINING_PLAYER_STATE_STORE),
    events=(),
    capabilities=(),
)

register_ops()
_service.install_inventory_source()


def _ensure_refs() -> None:
    from sb.domain.mining import ops as _ops
    from sb.domain.mining import panels as _panels
    from sb.domain.mining import store as _store

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    _panels.ensure_panel_refs()
    register_ops()


ENSURE_REFS = _ensure_refs
