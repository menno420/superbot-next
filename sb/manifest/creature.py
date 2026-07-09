"""CREATURE subsystem manifest (band 6, checkpoint family) — catch +
collection (the shipped creature-game v1, Q-0187) with the shipped
command names verbatim; battle RECORD lane live, interactive battles
pending (live adapter)."""

from __future__ import annotations

from sb.domain.creature import service as _service
from sb.domain.creature.ops import register_ops
from sb.domain.creature.store import (
    CREATURE_BATTLE_STORE,
    CREATURE_COLLECTION_STORE,
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


def creature_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="creature.hub",
        subsystem="creature",
        title="🐾 Creatures",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock("Hunt wild creatures — rarity drives both how "
                        "often they appear and how hard they are to "
                        "catch. Your creature level (shared game XP) "
                        "nudges the odds."),),
        actions=(
            PanelActionSpec(action_id="creature_catch", label="Catch",
                            emoji="🐾", style=ActionStyle.SUCCESS,
                            audience_tier="user",
                            handler=HandlerRef("creature.catch_route"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="creature_dex", label="My Dex",
                            emoji="📖", audience_tier="user",
                            handler=HandlerRef("creature.dex_view"),
                            result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(action_id="creature_top", label="Top Catchers",
                            emoji="🏆", audience_tier="user",
                            handler=HandlerRef("creature.dextop_view"),
                            result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.world")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("creature_catch", "creature_dex", "creature_top"),)),)),
    )


@panel("creature.hub")
def _hub_factory() -> PanelSpec:
    return creature_hub_spec()


MANIFEST = SubsystemManifest(
    key="creature",
    version=1,
    commands=(
        CommandSpec(name="catch", kind=CommandKind.PREFIX,
                    aliases=("hunt",),
                    route=HandlerRef("creature.catch_route"),
                    audience_tier="user", capability="creature",
                    summary="Hunt a wild creature — rarity-weighted "
                            "encounter, level-nudged catch roll.",
                    usage="!catch"),
        CommandSpec(name="creatures", kind=CommandKind.PREFIX,
                    aliases=("creaturemenu", "pets"),
                    route=PanelRef("creature.hub"),
                    audience_tier="user", capability="creature",
                    summary="Open the creatures menu.",
                    usage="!creatures"),
        CommandSpec(name="dex", kind=CommandKind.PREFIX,
                    aliases=("collection",),
                    route=HandlerRef("creature.dex_view"),
                    audience_tier="user", capability="creature",
                    summary="Your creature collection log.",
                    usage="!dex"),
        CommandSpec(name="dextop", kind=CommandKind.PREFIX,
                    aliases=("topcatchers",),
                    route=HandlerRef("creature.dextop_view"),
                    audience_tier="user", capability="creature",
                    summary="Top catchers by species collected.",
                    usage="!dextop"),
        CommandSpec(name="cbattle", kind=CommandKind.PREFIX,
                    aliases=("creaturebattle",),
                    route=HandlerRef("creature.battle_pending"),
                    audience_tier="user", capability="creature",
                    summary="Battle another player's creatures.",
                    usage="!cbattle @player"),
        CommandSpec(name="cbrecord", kind=CommandKind.PREFIX,
                    aliases=("battlerecord",),
                    route=HandlerRef("creature.battle_record_view"),
                    audience_tier="user", capability="creature",
                    summary="Your creature battle record.",
                    usage="!cbrecord"),
        CommandSpec(name="cbattletop", kind=CommandKind.PREFIX,
                    aliases=("pvptop", "battletop"),
                    route=HandlerRef("creature.battletop_view"),
                    audience_tier="user", capability="creature",
                    summary="The creature battle leaderboard.",
                    usage="!cbattletop"),
    ),
    panels=(creature_hub_spec(),),
    settings=(),
    stores=(CREATURE_COLLECTION_STORE, CREATURE_BATTLE_STORE),
    events=(),
    capabilities=(),
)

register_ops()


def _ensure_refs() -> None:
    from sb.domain.creature import ops as _ops
    from sb.domain.creature import store as _store
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _store.ensure_refs()
    _ops.ensure_ops_refs()
    _service.ensure_handler_refs()
    if not is_registered(_P("creature.hub")):
        _panel("creature.hub")(_hub_factory)
    register_ops()


ENSURE_REFS = _ensure_refs
