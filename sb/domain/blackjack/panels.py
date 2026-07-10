"""Blackjack panels + g1 session actions (band 6).

The hub is the shipped Games→Blackjack panel made declarative: Solo Free
Play / Solo Bet (G-10 modal) / Status. The SOLO TABLE (``!blackjack``)
is the shipped ``views/blackjack/solo_view.BlackjackView`` made a
session-lifecycle panel: the green game embed (Dealer/Your hand/Bet
fields — views/blackjack/embeds._game_embed) over Hit/Stand/Double
buttons on engine-minted 32-hex ids, refreshed IN PLACE per move
(goldens/blackjack pins the wire shape). PvP Accept/Decline stay
DYNAMIC-session components on the §3.4 ``g1:blackjack:`` scheme (the
old ``blackjack:solo:replay`` persistent id is retired — D-0042)."""

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
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, handler, is_registered, panel

__all__ = [
    "TABLE_PANEL_ID",
    "blackjack_hub_spec",
    "blackjack_table_spec",
    "ensure_panel_refs",
    "install_blackjack_panels",
    "register_blackjack_sessions",
]

TABLE_PANEL_ID = "blackjack.table"

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


def blackjack_table_spec() -> PanelSpec:
    """The shipped solo table view (`!blackjack [bet]`): the green game
    embed + Hit/Stand/Double, invoker-locked, refreshed in place per move,
    dying with the process — a session-lifecycle panel whose ids are
    engine-minted per deal (goldens/blackjack pins the wire shape)."""
    return PanelSpec(
        panel_id=TABLE_PANEL_ID,
        subsystem="blackjack",
        title="🃏 Blackjack",
        audience=Audience.INVOKER,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="hit", label="Hit", emoji="👊",
                style=ActionStyle.SUCCESS, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("blackjack.table_click")),
            PanelActionSpec(
                action_id="stand", label="Stand", emoji="✋",
                style=ActionStyle.SECONDARY, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("blackjack.table_click")),
            PanelActionSpec(
                action_id="double", label="Double Down", emoji="✌️",
                style=ActionStyle.PRIMARY, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("blackjack.table_click")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("hit", "stand", "double"),)),)),
        renderer_override=HandlerRef("blackjack.render_table"),
        justification=(
            "the shipped table embed is game-state-parameterized copy "
            "(Dealer (N+?)/Your hand (N)/Bet fields with a mixed inline "
            "layout and a result-keyed accent color — views/blackjack/"
            "embeds._game_embed); grammar TextBlocks are static. Buttons "
            "and authority stay declared on the spec; the renderer only "
            "composes the embed + declared components with their "
            "state-derived disabled flags."),
        session_lifecycle=True,
    )


async def _render_table(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped ``_game_embed`` verbatim over the
    DECLARED buttons (canonical ids; the engine mints/remints nothing on
    refresh — ids are remapped onto the original mint)."""
    from sb.domain.blackjack import engine as bj
    from sb.domain.blackjack.ops import FREE_WIN_COINS
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    player = [str(c) for c in (params.get("player") or ())]
    dealer = [str(c) for c in (params.get("dealer") or ())]
    bet = int(params.get("bet", 0) or 0)
    terminal = bool(params.get("terminal"))
    if terminal:
        dealer_label = f"Dealer ({params.get('dealer_value')})"
        dealer_str = "  ".join(dealer)
    else:
        # the shipped hidden-card line: first card + ||?||, visible value
        # in the field name (embeds.py hide_second branch).
        dealer_label = f"Dealer ({bj.rank_value(dealer[0].split()[0])}+?)"
        dealer_str = f"{dealer[0]}  ||?||"
    bet_str = (f"**{bet}** 🪙" if bet
               else f"Free (win = +{FREE_WIN_COINS} 🪙)")
    fields = [
        (dealer_label, dealer_str, False),
        (f"Your hand ({params.get('player_value')})",
         "  ".join(player), False),
        ("Bet", bet_str, True),
    ]
    style_token = "green"
    if terminal:
        result = str(params.get("result") or "")
        delta = int(params.get("delta", 0) or 0)
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        fields.append((result,
                       f"{delta_str} 🪙  |  "
                       f"Balance: **{params.get('balance', '?')}** 🪙",
                       False))
        # the shipped result colors: SUCCESS on a win, GAME on a push,
        # ERROR on a loss/bust (solo_view._resolve).
        style_token = ("green" if result.startswith("🎉")
                       else "purple" if result.startswith("🤝") else "red")
    can_double = (bet > 0 and len(player) == 2
                  and not params.get("doubled") and not terminal)
    disabled = {"hit": terminal, "stand": terminal,
                "double": not can_double}
    embed = RenderedEmbed(title=spec.title, description="",
                          fields=tuple(fields), style_token=style_token)
    components = tuple(
        RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.{action.action_id}",
            label=action.label, row=0, style=action.style.value,
            emoji=action.emoji,
            disabled=bool(disabled.get(action.action_id, terminal)))
        for action in spec.actions)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel("blackjack.hub")
def _hub_factory() -> PanelSpec:
    return blackjack_hub_spec()


@panel(TABLE_PANEL_ID)
def _table_factory() -> PanelSpec:
    return blackjack_table_spec()


handler("blackjack.render_table")(_render_table)


def install_blackjack_panels() -> PanelSpec:
    spec = blackjack_hub_spec()
    for candidate in (spec, blackjack_table_spec()):
        try:
            register_panel(candidate)
        except ValueError as exc:
            if ("already registered" not in str(exc)
                    and "duplicate" not in str(exc)):
                raise
    return spec


def ensure_panel_refs() -> None:
    from sb.spec.refs import HandlerRef as _H, PanelRef as _P, panel as _panel

    if not is_registered(_P("blackjack.hub")):
        _panel("blackjack.hub")(_hub_factory)
    if not is_registered(_P(TABLE_PANEL_ID)):
        _panel(TABLE_PANEL_ID)(_table_factory)
    if not is_registered(_H("blackjack.render_table")):
        handler("blackjack.render_table")(_render_table)
    register_blackjack_sessions()
