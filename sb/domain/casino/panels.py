"""Casino hub panel (band 6) — the shipped views/casino/hub.py
navigation hub declarative: Poker (pending until the live table
arms), Hand Rankings, and the docking note for roulette-and-friends."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
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

__all__ = ["casino_hub_spec", "ensure_panel_refs",
           "install_casino_panels"]


def casino_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="casino.hub",
        subsystem="casino",
        title="🎰 Casino",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Group card games — every player gets their own "
                      "private table view. v1 seats multiplayer Texas "
                      "Hold'em; roulette and friends dock into this hub "
                      "as they land."),
        ),
        actions=(
            PanelActionSpec(
                action_id="casino_poker", label="Poker (Hold'em)",
                emoji="♠", style=ActionStyle.PRIMARY,
                audience_tier="user",
                handler=HandlerRef("casino.poker_pending"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="casino_hand_ranks", label="Hand Rankings",
                emoji="📜", audience_tier="user",
                handler=HandlerRef("casino.hand_rank_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.hub")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("casino_poker", "casino_hand_ranks"),)),)),
    )


@panel("casino.hub")
def _hub_factory() -> PanelSpec:
    return casino_hub_spec()


def install_casino_panels() -> PanelSpec:
    spec = casino_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("casino.hub")):
        _panel("casino.hub")(_hub_factory)
