"""Blackjack panels + g1 session actions (band 6).

The hub is the shipped Games→Blackjack panel made declarative: Solo Free
Play / Solo Bet (G-10 modal) / Status. In-hand table buttons (Hit / Stand
/ Double, PvP Accept/Decline) are DYNAMIC-session components — they ride
the §3.4 ``g1:blackjack:<session_id>:<action>`` scheme through the games
dispatcher, NOT the static table (the shipped per-view dynamic ids
replaced by design; the old ``blackjack:solo:replay`` persistent id is
retired with them — D-0042)."""

from __future__ import annotations

from sb.domain.games.session import register_session_actions
from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, is_registered, panel

__all__ = [
    "blackjack_hub_spec",
    "ensure_panel_refs",
    "install_blackjack_panels",
    "register_blackjack_sessions",
]

SOLO_BET_MODAL = ModalSpec(
    modal_id="blackjack.solo_bet_form",
    title="Blackjack — place your bet",
    fields=(
        ModalFieldSpec(field_id="bet", label="Bet (coins)",
                       placeholder="e.g. 25", required=True, max_length=9),
    ),
    on_submit=WorkflowRef("blackjack.solo_start"),
)


def _session_action(action_id: str, label: str, ref: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    """A dispatcher-table action spec — dynamic-session only, never in a
    static panel layout (its custom_id is minted per session by g1:)."""
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           handler=WorkflowRef(ref))


_SESSION_ACTIONS = {
    "hit": _session_action("bj_hit", "Hit", "blackjack.solo_hit",
                           ActionStyle.SUCCESS, "👊"),
    "stand": _session_action("bj_stand", "Stand", "blackjack.solo_stand",
                             ActionStyle.SECONDARY, "✋"),
    "double": _session_action("bj_double", "Double Down",
                              "blackjack.solo_double",
                              ActionStyle.PRIMARY, "✌️"),
    "accept": _session_action("bj_accept", "Accept",
                              "blackjack.pvp_accept",
                              ActionStyle.SUCCESS, "✅"),
    "decline": _session_action("bj_decline", "Decline",
                               "blackjack.pvp_decline",
                               ActionStyle.DANGER, "❌"),
    "pvp_hit": _session_action("bj_pvp_hit", "Hit", "blackjack.pvp_move",
                               ActionStyle.SUCCESS, "👊"),
    "pvp_stand": _session_action("bj_pvp_stand", "Stand",
                                 "blackjack.pvp_move",
                                 ActionStyle.SECONDARY, "✋"),
}


def register_blackjack_sessions() -> None:
    register_session_actions("blackjack", _SESSION_ACTIONS)


def blackjack_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="blackjack.hub",
        subsystem="blackjack",
        title="🃏 Blackjack",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Beat the dealer without going over 21. Free play "
                      "wins pay a fixed reward; bets pay 1:1 (naturals "
                      "3:2). Challenge a player with "
                      "`!blackjack @player [bet]` — stakes are escrowed "
                      "when the challenge is accepted."),
        ),
        actions=(
            PanelActionSpec(
                action_id="bj_solo_free", label="Solo Free Play",
                emoji="🃏", style=ActionStyle.SUCCESS,
                audience_tier="user",
                handler=WorkflowRef("blackjack.solo_start"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="bj_solo_bet", label="Solo Bet", emoji="🪙",
                style=ActionStyle.PRIMARY, audience_tier="user",
                defer_mode=DeferMode.MODAL, modal=SOLO_BET_MODAL,
                handler=WorkflowRef("blackjack.solo_start")),
            PanelActionSpec(
                action_id="bj_status", label="Tournament Status",
                emoji="🏆", audience_tier="user",
                handler=HandlerRef("blackjack.status_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("bj_solo_free", "bj_solo_bet", "bj_status"),)),)),
    )


@panel("blackjack.hub")
def _hub_factory() -> PanelSpec:
    return blackjack_hub_spec()


def install_blackjack_panels() -> PanelSpec:
    spec = blackjack_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("blackjack.hub")):
        _panel("blackjack.hub")(_hub_factory)
    register_blackjack_sessions()
