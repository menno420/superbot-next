"""MINING subsystem manifest (band 6, checkpoint family) — the FULL
shipped command surface verbatim (37 commands): the core loop
(mine/chop/explore/sell/sellall/buy + reads) is live over the audited K7
lanes; the deep systems are honest pending terminals riding the D-0043
named successor port."""

from __future__ import annotations

from sb.domain.mining import service as _service
from sb.domain.mining.ops import register_ops
from sb.domain.mining.store import (
    MINING_INVENTORY_STORE,
    MINING_PLAYER_STATE_STORE,
)
from sb.kernel.panels.registry import register_panel
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel


def mining_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="mining.hub",
        subsystem="mining",
        title="⛏️ Mining",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock("Dig for ore, chop wood, explore — then sell "
                        "your haul at the market. Deeper bands hold "
                        "richer ore."),),
        actions=(
            PanelActionSpec(action_id="mining_mine", label="Mine",
                            emoji="⛏️", style=ActionStyle.SUCCESS,
                            audience_tier="user",
                            handler=HandlerRef("mining.mine_route"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="mining_chop", label="Chop",
                            emoji="🪓", audience_tier="user",
                            handler=HandlerRef("mining.chop_route"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="mining_explore", label="Explore",
                            emoji="🧭", audience_tier="user",
                            handler=HandlerRef("mining.explore_route"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="mining_sell_all", label="Sell All",
                            emoji="💰", style=ActionStyle.PRIMARY,
                            audience_tier="user",
                            handler=HandlerRef("mining.sellall_route"),
                            result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.world")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("mining_mine", "mining_chop", "mining_explore",
             "mining_sell_all"),)),)),
    )


@panel("mining.hub")
def _hub_factory() -> PanelSpec:
    return mining_hub_spec()


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
         "One mining swing — roll ore loot."),
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
    _pending("fastmine", "Grid dig (fast mine)."),
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
    _pending("reset_inventory", "Admin: reset a mining inventory."),
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
    from sb.domain.mining import store as _store
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    if not is_registered(_P("mining.hub")):
        _panel("mining.hub")(_hub_factory)
    register_ops()


ENSURE_REFS = _ensure_refs
