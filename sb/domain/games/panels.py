"""GAMES hub + world panels (band 6) — the shipped router-only games hub
(zero game logic; children discovered per band as their panels land) and
the federated Explore world hub's read mirror (the world card)."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "ensure_panel_refs",
    "games_hub_spec",
    "install_games_panels",
    "world_hub_spec",
]

_HUB_PROVIDER = "games.hub_overview"


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.games.session import registered_session_games

            games = registered_session_games()
            return (("Live session games",
                     ", ".join(sorted(games)) or "none yet"),)
    return ref


def games_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="games.hub",
        subsystem="games",
        title="🎮 Games",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Competitive games and channel activities. Wagered "
                      "games escrow stakes when a challenge is accepted; "
                      "your cross-game progress lives on the shared world "
                      "track (`!worldcard`)."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="games_blackjack", label="Blackjack", emoji="🃏",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=PanelRef("blackjack.hub")),
            PanelActionSpec(
                action_id="games_rps", label="Rock Paper Scissors",
                emoji="✂️", style=ActionStyle.PRIMARY,
                audience_tier="user",
                handler=PanelRef("rps_tournament.hub")),
            PanelActionSpec(
                action_id="games_world", label="World", emoji="🌍",
                audience_tier="user", handler=PanelRef("games.world")),
            PanelActionSpec(
                action_id="games_worldcard", label="My World Card",
                emoji="🪪", audience_tier="user",
                handler=HandlerRef("games.world_card_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("games_blackjack", "games_rps"),
            ("games_world", "games_worldcard"),)),)),
    )


def world_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="games.world",
        subsystem="games",
        title="🌍 Explore — the world",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("The open-world town square. Each game keeps its "
                      "own ladder; your shared world level derives from "
                      "the game-XP pool. Game worlds (Mine · Fish · Farm "
                      "· Creatures) dock here as their bands land."),
        ),
        actions=(
            PanelActionSpec(
                action_id="world_card", label="My World Card", emoji="🪪",
                audience_tier="user",
                handler=HandlerRef("games.world_card_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.hub")),
        layout=LayoutSpec(pages=(PageSpec(rows=(("world_card",),)),)),
    )


@panel("games.hub")
def _hub_factory() -> PanelSpec:
    return games_hub_spec()


@panel("games.world")
def _world_factory() -> PanelSpec:
    return world_hub_spec()


def install_games_panels() -> tuple[PanelSpec, ...]:
    specs = (games_hub_spec(), world_hub_spec())
    out = []
    for spec in specs:
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    _ensure_hub_provider()
    if not is_registered(_P("games.hub")):
        _panel("games.hub")(_hub_factory)
    if not is_registered(_P("games.world")):
        _panel("games.world")(_world_factory)
