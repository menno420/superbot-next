"""Blackjack panels + g1 session actions (band 6).

The hub is the shipped Games→Blackjack panel made declarative: Solo Free
Play / Solo Bet (G-10 modal) / Status. The SOLO TABLE (``!blackjack``)
is the shipped ``views/blackjack/solo_view.BlackjackView`` made a
session-lifecycle panel: the green game embed (Dealer/Your hand/Bet
fields — views/blackjack/embeds._game_embed) over Hit/Stand/Double
buttons on engine-minted 32-hex ids, refreshed IN PLACE per move
(goldens/blackjack pins the wire shape). The PVP panel
(``!blackjack @player [bet]``) is the shipped challenge →
accept/decline → per-player hit/stand → result loop on ONE public
message: its components ride the §3.4 ``g1:blackjack:`` scheme
(restart-safe — the checkpoint row is the authority; the old
``blackjack:solo:replay`` persistent id is retired — D-0042)."""

from __future__ import annotations

from sb.domain.games.session import register_session_actions
from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    AnchorPolicy,
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
    "PVP_PANEL_ID",
    "REGISTRATION_PANEL_ID",
    "RESULTS_PANEL_ID",
    "TABLE_PANEL_ID",
    "TOURN_TABLE_PANEL_ID",
    "blackjack_hub_spec",
    "blackjack_pvp_spec",
    "blackjack_registration_spec",
    "blackjack_results_spec",
    "blackjack_table_spec",
    "blackjack_tournament_table_spec",
    "ensure_panel_refs",
    "install_blackjack_panels",
    "register_blackjack_sessions",
]

TABLE_PANEL_ID = "blackjack.table"
PVP_PANEL_ID = "blackjack.pvp"
REGISTRATION_PANEL_ID = "blackjack.registration"
TOURN_TABLE_PANEL_ID = "blackjack.tournament_table"
RESULTS_PANEL_ID = "blackjack.tournament_results"

SOLO_BET_MODAL = ModalSpec(
    modal_id="blackjack.solo_bet_form",
    title="Blackjack — place your bet",
    fields=(
        ModalFieldSpec(field_id="bet", label="Bet (coins)",
                       placeholder="e.g. 25", required=True, max_length=9),
    ),
    on_submit=WorkflowRef("blackjack.solo_start"),
)


def _session_action(action_id: str, label: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    """A dispatcher-table action spec — dynamic-session only, never in a
    static panel layout (its custom_id is minted per session by g1:).
    Every PvP click routes through the ONE ``blackjack.pvp_click``
    handler (run the audited op, edit the match message in place);
    ``DeferMode.NONE`` so the refresh owns the deferred-update ack.
    The solo table does NOT ride g1 — it lives on engine-minted
    session-lifecycle ids (the #120 seam) — so the g1 table is
    PvP-only: the action tokens match what the PvP ops mint
    (accept/decline at challenge, hit/stand after the deal)."""
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           defer_mode=DeferMode.NONE,
                           handler=HandlerRef("blackjack.pvp_click"))


_SESSION_ACTIONS = {
    "accept": _session_action("bj_accept", "Accept",
                              ActionStyle.SUCCESS, "✅"),
    "decline": _session_action("bj_decline", "Decline",
                               ActionStyle.DANGER, "❌"),
    "hit": _session_action("bj_pvp_hit", "Hit",
                           ActionStyle.SUCCESS, "👊"),
    "stand": _session_action("bj_pvp_stand", "Stand",
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


def blackjack_pvp_spec() -> PanelSpec:
    """The shipped PvP loop (``!blackjack @player [bet]``) on ONE public
    message: the challenge embed (views/blackjack/pvp_view._ChallengeView)
    with Accept/Decline, edited through the dealt match (both public
    hands + per-player Hit/Stand — the shipped per-player tables were
    plain channel messages) to the `🃏 Blackjack PvP Result` embed.
    Components ride the restart-safe ``g1:`` scheme; the ops own every
    lock (peer, own-hand, hand-finished), so the panel carries NO
    invoker lock (audience PUBLIC)."""
    return PanelSpec(
        panel_id=PVP_PANEL_ID,
        subsystem="blackjack",
        title="🃏 Blackjack Challenge!",
        audience=Audience.PUBLIC,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("blackjack.render_pvp"),
        justification=(
            "the shipped challenge/match/result embeds are match-"
            "parameterized copy on every line (challenger/target "
            "mentions, bet line, per-player card reveals — views/"
            "blackjack/pvp_view.py); grammar TextBlocks are static, and "
            "the buttons are g1: dynamic-session components minted from "
            "the match's session id (never static panel ids). Authority "
            "stays on the g1 dispatcher table's declared specs; the "
            "renderer only composes the staged embed + buttons."),
        session_lifecycle=True,
    )


def blackjack_registration_spec() -> PanelSpec:
    """The shipped tournament-registration message (`!bjtournament` →
    ``ctx.send(embed=_tourn_embed(tourn), view=_TournRegistrationView)`` +
    the ✅ primer): the SUCCESS_COLOR embed with the Entry Fee / Rounds /
    Duration / Players / Pot inline fields, the `React ✅ or click Join to
    register.` footer, and the green 🃏 ``Join Tournament`` button —
    pinned byte-for-byte by the bjtournament golden. PUBLIC (anyone may
    join); session-lifecycle so the button rides a run-minted id, exactly
    the shipped auto-id view."""
    return PanelSpec(
        panel_id=REGISTRATION_PANEL_ID,
        subsystem="blackjack",
        title="🃏 Blackjack Tournament — Registration Open",
        audience=Audience.PUBLIC,
        timeout_s=310,             # the shipped duration_mins*60 + 10 grace
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="bj_join", label="Join Tournament", emoji="🃏",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("blackjack.tournament_join"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("bj_join",),)),)),
        renderer_override=HandlerRef("blackjack.render_registration"),
        justification=(
            "the shipped registration embed's five field values are "
            "request-parameterized copy (fee/rounds/mins arguments + the "
            "live player count and pot — views/blackjack/embeds."
            "_tourn_embed); grammar TextBlocks are static. The Join "
            "button and its authority stay declared on the spec; the "
            "renderer composes the embed + the declared button and asks "
            "for the shipped ✅ self-reaction primer."),
        session_lifecycle=True,
    )


def blackjack_tournament_table_spec() -> PanelSpec:
    """One entrant's tournament ROUND as a button view in the home channel
    — the DELIBERATE deviation from the shipped private per-player
    channels ("BJ Tournament" category; ledgered — the rps home-channel
    precedent). Hit/Stand play the shipped ``_TournBlackjackView`` hand
    for CHIPS (flat 200/round); the wallet never moves here.
    CHANNEL_ANCHOR: round N+1's view opens off round N's final click and
    must be a fresh channel message (the #130 presenter seam)."""
    return PanelSpec(
        panel_id=TOURN_TABLE_PANEL_ID,
        subsystem="blackjack",
        title="🃏 Blackjack Tournament",
        audience=Audience.PUBLIC,
        anchor_policy=AnchorPolicy.CHANNEL_ANCHOR,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="green",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="tourn_hit", label="Hit", emoji="👊",
                style=ActionStyle.SUCCESS, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("blackjack.tournament_click")),
            PanelActionSpec(
                action_id="tourn_stand", label="Stand", emoji="✋",
                style=ActionStyle.SECONDARY, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("blackjack.tournament_click")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("tourn_hit", "tourn_stand"),)),)),
        renderer_override=HandlerRef("blackjack.render_tournament_table"),
        justification=(
            "the shipped tournament round embed is game-state-"
            "parameterized copy (the _game_embed card fields plus the "
            "_finish_round `Chips: **N** | Rounds left: **N**` result "
            "field); grammar TextBlocks are static. Buttons and "
            "authority stay declared on the spec; the renderer only "
            "composes the embed + declared components with their "
            "state-derived disabled flags and the entrant's invoker "
            "lock."),
        session_lifecycle=True,
    )


def blackjack_results_spec() -> PanelSpec:
    """The shipped end-of-tournament results embed (`🏆 Blackjack
    Tournament Results`, ECONOMY_COLOR, medal-ranked chip lines, the
    Winner's payout field on paid tournaments) — a render-only terminal
    frame; CHANNEL_ANCHOR because it opens off the final round's click."""
    return PanelSpec(
        panel_id=RESULTS_PANEL_ID,
        subsystem="blackjack",
        title="🏆 Blackjack Tournament Results",
        audience=Audience.PUBLIC,
        anchor_policy=AnchorPolicy.CHANNEL_ANCHOR,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="gold",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("blackjack.render_results"),
        justification=(
            "every line of the shipped results embed is tournament-"
            "parameterized copy (medal icons, member names, chip counts, "
            "the payout amount/balance field — views/blackjack/"
            "tournament_views._check_tourn_done); grammar TextBlocks are "
            "static, and the frame carries zero components."),
        session_lifecycle=True,
    )


def _pvp_hand_line(uid_s: str, hand: dict) -> str:
    """One player's public hand line — cards, value, done marker."""
    value = int(hand.get("value") or 0)
    marker = ""
    if value > 21:
        marker = "  💥"
    elif hand.get("done"):
        marker = "  ✅"
    return (f"<@{uid_s}>: {'  '.join(hand.get('cards') or ())} "
            f"(**{value}**){marker}")


async def _render_pvp(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped PvP wire copy per stage: challenge
    (`🃏 Blackjack Challenge!`, SUCCESS_COLOR, Accept✅/Decline❌ —
    cogs/blackjack_cog.py), declined (`❌ <player> declined the
    challenge.`, controls disabled), the dealt match (both public hands
    + Hit👊/Stand✋ playing the CLICKER's own hand), result
    (`🃏 Blackjack PvP Result`, ECONOMY_COLOR on a win / GAME_COLOR on a
    tie — views/blackjack/pvp_view._resolve_pvp)."""
    from sb.domain.games import session as games_session
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    stage = str(params.get("stage") or "challenge")
    sid = str(params.get("session_id") or "")

    def _g1(action: str) -> str:
        return games_session.mint_custom_id("blackjack", sid, action)

    terminal = stage in ("declined", "result")
    if stage in ("challenge", "declined"):
        components = (
            RenderedComponent(kind="button", custom_id=_g1("accept"),
                              label="Accept", row=0, style="success",
                              emoji="✅", disabled=terminal),
            RenderedComponent(kind="button", custom_id=_g1("decline"),
                              label="Decline", row=0, style="danger",
                              emoji="❌", disabled=terminal),
        )
    else:
        components = (
            RenderedComponent(kind="button", custom_id=_g1("hit"),
                              label="Hit", row=0, style="success",
                              emoji="👊", disabled=terminal),
            RenderedComponent(kind="button", custom_id=_g1("stand"),
                              label="Stand", row=0, style="secondary",
                              emoji="✋", disabled=terminal),
        )
    title = spec.title
    style_token = "green"                     # shipped SUCCESS_COLOR
    bet = int(params.get("bet", 0) or 0)
    p1 = str(params.get("p1") or "")
    p2 = str(params.get("p2") or "")
    hands = dict(params.get("hands") or {})
    hand_lines = "\n".join(
        _pvp_hand_line(u, hands.get(u) or {}) for u in (p1, p2) if u)
    if stage == "declined":
        description = (f"❌ <@{params.get('decliner')}> declined the "
                       "challenge.")
    elif stage == "result":
        title = "🃏 Blackjack PvP Result"
        # shipped result accents: ECONOMY_COLOR (gold) on a win,
        # GAME_COLOR (purple) on a tie.
        style_token = "gold" if params.get("winner") else "purple"
        description = f"{hand_lines}\n\n{params.get('result') or ''}"
    elif stage == "match":
        title = "🃏 Blackjack PvP"
        bet_line = (f"Bet: **{bet}** 🪙 each" if bet else "Free play")
        description = (f"{hand_lines}\n\n{bet_line}\n"
                       "Your buttons play YOUR hand.")
    else:
        bet_str = f"**{bet}** 🪙" if bet else "free play"
        description = (
            f"<@{params.get('challenger')}> challenges "
            f"<@{params.get('target')}> to Blackjack "
            f"({bet_str}).\n<@{params.get('target')}>, do you accept?")
    embed = RenderedEmbed(title=title, description=description,
                          style_token=style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


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


async def _render_registration(spec: PanelSpec, ctx) -> object:
    """renderer_override — the golden-pinned registration embed verbatim:
    SUCCESS_COLOR, the five inline fields (Entry Fee / Rounds / Duration /
    Players / Pot), the `React ✅ or click Join to register.` footer, the
    green 🃏 Join button, and the shipped ✅ self-reaction primer."""
    from sb.domain.blackjack.tournament import REGISTRATION_EMOJI
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    fee = int(params.get("entry_fee", 0) or 0)
    rounds = int(params.get("rounds", 5) or 5)
    mins = int(params.get("duration_mins", 5) or 5)
    players = int(params.get("players", 0) or 0)
    # the shipped _tourn_embed field values, verbatim
    fee_str = f"**{fee}** 🪙" if fee else "Free"
    closed = bool(params.get("closed"))
    embed = RenderedEmbed(
        title=spec.title,
        description="",
        fields=(("Entry Fee", fee_str, True),
                ("Rounds", str(rounds), True),
                ("Duration", f"{mins} min", True),
                ("Players", str(players), True),
                ("Pot", f"{fee * players} 🪙", True)),
        footer="React ✅ or click Join to register.",
        style_token=spec.frame.style_token)
    action = spec.actions[0]
    components = (RenderedComponent(
        kind="button", custom_id=f"{spec.panel_id}.{action.action_id}",
        label=action.label, row=0, style=action.style.value,
        emoji=action.emoji, disabled=closed),)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value,
        self_reactions=() if closed else (REGISTRATION_EMOJI,))


async def _render_tournament_table(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped ``_game_embed`` card frame in CHIPS
    space over the declared Hit/Stand: Dealer/Your hand fields, the flat
    200-chip bet line, and on a finished round the shipped
    ``_finish_round`` result field (`Chips: **N** | Rounds left: **N**`).
    The INVOKER LOCK is the entrant (params), never the opener — round
    views open off the launch command or another player's click."""
    from sb.domain.blackjack import engine as bj
    from sb.domain.blackjack.ops import TOURN_BET_PER_ROUND
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    uid = int(params.get("uid", 0) or 0)
    player = [str(c) for c in (params.get("player") or ())]
    dealer = [str(c) for c in (params.get("dealer") or ())]
    terminal = bool(params.get("terminal"))
    if terminal:
        dealer_label = f"Dealer ({params.get('dealer_value')})"
        dealer_str = "  ".join(dealer)
    else:
        dealer_label = f"Dealer ({bj.rank_value(dealer[0].split()[0])}+?)"
        dealer_str = f"{dealer[0]}  ||?||"
    round_no = int(params.get("round_no", 1) or 1)
    fields = [
        (dealer_label, dealer_str, False),
        (f"Your hand ({params.get('player_value')})",
         "  ".join(player), False),
        ("Bet", f"**{TOURN_BET_PER_ROUND}** chips", True),
    ]
    style_token = "green"
    if terminal:
        result = str(params.get("result") or "")
        # the shipped _finish_round field, verbatim bytes
        fields.append((result,
                       f"Chips: **{params.get('chips')}** | Rounds left: "
                       f"**{params.get('rounds_left')}**", False))
        style_token = ("green" if result.startswith("🎉")
                       else "purple" if result.startswith("🤝") else "red")
    embed = RenderedEmbed(
        title=f"{spec.title} — <@{uid}> · Round {round_no}",
        description="", fields=tuple(fields), style_token=style_token)
    components = tuple(
        RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.{action.action_id}",
            label=action.label, row=0, style=action.style.value,
            emoji=action.emoji, disabled=terminal)
        for action in spec.actions)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=uid or None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


async def _render_results(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped ``_check_tourn_done`` results embed:
    medal-ranked `{icon} **{name}** — {chips} chips` lines, ECONOMY_COLOR,
    and the `Winner's payout` field when a paid pot settled."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    names = {str(k): str(v)
             for k, v in dict(params.get("names") or {}).items()}
    medals = ["🥇", "🥈", "🥉"]           # shipped, verbatim
    lines = []
    ranked = [(int(u), int(c)) for u, c in (params.get("ranking") or ())]
    for i, (uid, chips) in enumerate(ranked):
        icon = medals[i] if i < 3 else f"#{i + 1}"
        name = names.get(str(uid)) or f"<@{uid}>"
        lines.append(f"{icon} **{name}** — {chips} chips")
    fields = ()
    if params.get("paid") and int(params.get("entry_fee", 0) or 0) > 0:
        winner = int(params.get("winner", 0) or 0)
        fields = (("Winner's payout",
                   f"<@{winner}> receives **{params.get('amount')}** 🪙 "
                   f"(Balance: {params.get('balance')} 🪙)", True),)
    embed = RenderedEmbed(title=spec.title, description="\n".join(lines),
                          fields=fields,
                          style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


@panel("blackjack.hub")
def _hub_factory() -> PanelSpec:
    return blackjack_hub_spec()


@panel(TABLE_PANEL_ID)
def _table_factory() -> PanelSpec:
    return blackjack_table_spec()


@panel(PVP_PANEL_ID)
def _pvp_factory() -> PanelSpec:
    return blackjack_pvp_spec()


@panel(REGISTRATION_PANEL_ID)
def _registration_factory() -> PanelSpec:
    return blackjack_registration_spec()


@panel(TOURN_TABLE_PANEL_ID)
def _tournament_table_factory() -> PanelSpec:
    return blackjack_tournament_table_spec()


@panel(RESULTS_PANEL_ID)
def _results_factory() -> PanelSpec:
    return blackjack_results_spec()


handler("blackjack.render_table")(_render_table)
handler("blackjack.render_pvp")(_render_pvp)
handler("blackjack.render_registration")(_render_registration)
handler("blackjack.render_tournament_table")(_render_tournament_table)
handler("blackjack.render_results")(_render_results)


def install_blackjack_panels() -> PanelSpec:
    spec = blackjack_hub_spec()
    for candidate in (spec, blackjack_table_spec(), blackjack_pvp_spec(),
                      blackjack_registration_spec(),
                      blackjack_tournament_table_spec(),
                      blackjack_results_spec()):
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
    if not is_registered(_P(PVP_PANEL_ID)):
        _panel(PVP_PANEL_ID)(_pvp_factory)
    if not is_registered(_P(REGISTRATION_PANEL_ID)):
        _panel(REGISTRATION_PANEL_ID)(_registration_factory)
    if not is_registered(_P(TOURN_TABLE_PANEL_ID)):
        _panel(TOURN_TABLE_PANEL_ID)(_tournament_table_factory)
    if not is_registered(_P(RESULTS_PANEL_ID)):
        _panel(RESULTS_PANEL_ID)(_results_factory)
    if not is_registered(_H("blackjack.render_table")):
        handler("blackjack.render_table")(_render_table)
    if not is_registered(_H("blackjack.render_pvp")):
        handler("blackjack.render_pvp")(_render_pvp)
    if not is_registered(_H("blackjack.render_registration")):
        handler("blackjack.render_registration")(_render_registration)
    if not is_registered(_H("blackjack.render_tournament_table")):
        handler("blackjack.render_tournament_table")(_render_tournament_table)
    if not is_registered(_H("blackjack.render_results")):
        handler("blackjack.render_results")(_render_results)
    register_blackjack_sessions()
