"""RPS panels + g1 session actions (band 6, subsystem rps_tournament).

The hub is the shipped `!rps` panel made declarative: a provider-free
move SELECTOR (quick play — on_select runs the audited rps.solo_play op
with args["values"], the D-0034 pattern) plus Rules and Settings views.
The QUICKPLAY picker is the shipped ``views/rps/solo_play._RpsView``
made a session-lifecycle panel (bare/bet `!rps` — embed + three move
buttons on engine-minted session ids; goldens/rps_tournament pins the
wire shape). The PVP panel (`!rps @player [bet]`) is the shipped
challenge → accept/decline → both-pick → result loop on ONE message:
Accept/Decline and the post-accept move buttons are dynamic-session
components on the ``g1:rps_tournament:`` prefix (restart-safe — the
checkpoint row is the authority), staged renders edited in place via
``refresh_session_view``."""

from __future__ import annotations

from sb.domain.games.session import register_session_actions
from sb.domain.rps.rules import GAME_MODES
from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import DeferMode
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
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, WorkflowRef, handler, is_registered, panel

__all__ = [
    "PVP_PANEL_ID",
    "QUICKPLAY_PANEL_ID",
    "ensure_panel_refs",
    "install_rps_panels",
    "register_rps_sessions",
    "rps_hub_spec",
    "rps_pvp_spec",
    "rps_quickplay_spec",
]

QUICKPLAY_PANEL_ID = "rps_tournament.quickplay"
PVP_PANEL_ID = "rps_tournament.pvp"

#: shipped button emoji (views/rps/solo_play.py — Rock 🪨 / Paper 📄 /
#: Scissors ✂️, grey style).
_QP_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}


def _session_action(action_id: str, label: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    """A dispatcher-table action spec — every PvP click routes through the
    ONE ``rps.pvp_click`` handler (run the audited op, then edit the
    challenge message in place); ``DeferMode.NONE`` so the refresh owns
    the deferred-update ack (the blackjack table_click precedent)."""
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           defer_mode=DeferMode.NONE,
                           handler=HandlerRef("rps.pvp_click"))


_SESSION_ACTIONS = {
    "accept": _session_action("rps_accept", "Accept",
                              ActionStyle.SUCCESS, "✅"),
    "decline": _session_action("rps_decline", "Decline",
                               ActionStyle.DANGER, "❌"),
    **{f"move_{m}": _session_action(f"rps_move_{m}", m.title())
       for m in GAME_MODES["classic"]},
}


def register_rps_sessions() -> None:
    register_session_actions("rps_tournament", _SESSION_ACTIONS)


def rps_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="rps_tournament.hub",
        subsystem="rps_tournament",
        title="✂️ Rock Paper Scissors",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Quick play vs the bot (pick a move below — free "
                      "play wins pay a fixed reward), challenge a player "
                      "with `!rps @player [bet]` (stakes escrowed at "
                      "accept), or run tournaments with `!rpsregister` / "
                      "`!rpsstart`."),
        ),
        actions=(
            PanelActionSpec(
                action_id="rps_rules", label="Rules", emoji="📜",
                audience_tier="user",
                handler=HandlerRef("rps.help_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="rps_settings_view", label="Settings",
                emoji="⚙️", audience_tier="user",
                handler=HandlerRef("rps.settings_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        selectors=(
            SelectorSpec(
                selector_id="rps_quick_move",
                kind=SelectorKind.ENUM,
                placeholder="Quick play — choose your move",
                options_source=tuple(GAME_MODES["classic"]),
                on_select=WorkflowRef("rps.solo_play"),
                audience_tier="user"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("rps_quick_move",),
            ("rps_rules", "rps_settings_view"),)),)),
    )


def rps_quickplay_spec() -> PanelSpec:
    """The shipped quick-play view (bare/bet `!rps`): embed + Rock/Paper/
    Scissors move buttons, invoker-locked, dying with the process — a
    session-lifecycle panel whose ids are engine-minted per open."""
    return PanelSpec(
        panel_id=QUICKPLAY_PANEL_ID,
        subsystem="rps_tournament",
        title="✂️ Rock · Paper · Scissors",
        audience=Audience.INVOKER,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        actions=tuple(
            PanelActionSpec(
                action_id=move, label=move.title(), emoji=_QP_EMOJI[move],
                style=ActionStyle.SECONDARY, audience_tier="user",
                handler=WorkflowRef("rps.solo_play"),
                result_render=ResultRender.RESULT_CARD)
            for move in GAME_MODES["classic"]),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(
            PageSpec(rows=(tuple(GAME_MODES["classic"]),)),)),
        renderer_override=HandlerRef("rps.render_quickplay"),
        justification=(
            "the shipped quick-play view's bet line is request-"
            "parameterized copy (Bet: **N** 🪙 / free play — views/rps/"
            "solo_play.py); grammar TextBlocks are static. Buttons and "
            "authority stay declared on the spec; the renderer only "
            "composes the embed + declared components."),
        session_lifecycle=True,
    )


def rps_pvp_spec() -> PanelSpec:
    """The shipped PvP loop (`!rps @player [bet]`) on ONE public message:
    the challenge embed (views/rps/pvp_challenge._RpsPvpChallengeView)
    with Accept/Decline, edited through accepted → both-pick → the
    `✂️ RPS PvP Result` embed (views/rps/pvp_play). Components ride the
    restart-safe ``g1:`` scheme — the checkpoint row is the authority
    (peer/turn locks live in the ops), so the panel carries NO invoker
    lock (audience PUBLIC)."""
    return PanelSpec(
        panel_id=PVP_PANEL_ID,
        subsystem="rps_tournament",
        title="✂️ RPS Challenge!",
        audience=Audience.PUBLIC,
        timeout_s=180,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("rps.render_pvp"),
        justification=(
            "the shipped challenge/result embeds are match-parameterized "
            "copy on every line (challenger/target mentions, bet line, "
            "per-player move reveals — views/rps/pvp_challenge.py + "
            "pvp_play.py); grammar TextBlocks are static, and the buttons "
            "are g1: dynamic-session components minted from the match's "
            "session id (never static panel ids). Authority stays on the "
            "g1 dispatcher table's declared specs; the renderer only "
            "composes the staged embed + buttons."),
        session_lifecycle=True,
    )


async def _render_pvp(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped PvP wire copy verbatim per stage:
    challenge (`✂️ RPS Challenge!` + Accept✅/Decline❌), accepted
    (`✅ Challenge accepted — both players, choose your move!` + move
    buttons), declined (`❌ <player> declined the challenge.`, controls
    disabled), result (`✂️ RPS PvP Result`, SUCCESS_COLOR on a win /
    GAME_COLOR on a tie — views/rps/pvp_play.py)."""
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
        return games_session.mint_custom_id("rps_tournament", sid, action)

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
        components = tuple(
            RenderedComponent(kind="button", custom_id=_g1(f"move_{m}"),
                              label=m.title(), row=0, style="secondary",
                              emoji=_QP_EMOJI[m], disabled=terminal)
            for m in GAME_MODES["classic"])
    title = spec.title
    style_token = "purple"                    # shipped GAME_COLOR
    if stage == "declined":
        description = (f"❌ <@{params.get('decliner')}> declined the "
                       "challenge.")
    elif stage == "result":
        title = "✂️ RPS PvP Result"
        p1 = int(params.get("p1") or 0)
        p2 = int(params.get("p2") or 0)
        moves = dict(params.get("moves") or {})
        m1 = str(moves.get(str(p1), ""))
        m2 = str(moves.get(str(p2), ""))
        if params.get("winner"):
            style_token = "green"             # shipped SUCCESS_COLOR
        description = (
            f"<@{p1}>: **{m1}** {_QP_EMOJI.get(m1, '')}\n"
            f"<@{p2}>: **{m2}** {_QP_EMOJI.get(m2, '')}\n\n"
            f"{params.get('result') or ''}")
    elif stage == "match":
        description = ("✅ Challenge accepted — both players, choose "
                       "your move!")
        if params.get("waiting"):
            description += ("\n⏳ One move is in — waiting for the other "
                            "player…")
    else:
        bet = int(params.get("bet", 0) or 0)
        bet_str = f"**{bet}** 🪙" if bet else "free play"
        description = (
            f"<@{params.get('challenger')}> challenges "
            f"<@{params.get('target')}> to Rock Paper Scissors "
            f"({bet_str}).\n<@{params.get('target')}>, do you accept?")
    embed = RenderedEmbed(title=title, description=description,
                          style_token=style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


async def _render_quickplay(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped embed shape verbatim (title,
    ``Bet: …\\nChoose your move!``, GAME_COLOR) over the DECLARED move
    buttons (canonical ids; the engine mints the session ids)."""
    from sb.domain.rps.ops import FREE_WIN
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    bet = params.get("bet")
    if bet is None:
        argv = tuple(params.get("argv", ()) or ())
        bet = next((int(str(t)) for t in argv if str(t).isdigit()), 0)
    bet = int(bet or 0)
    bet_str = f"**{bet}** 🪙" if bet else f"Free play (win = +{FREE_WIN} 🪙)"
    embed = RenderedEmbed(
        title=spec.title,
        description=f"Bet: {bet_str}\nChoose your move!",
        style_token=spec.frame.style_token)
    components = tuple(
        RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.{action.action_id}",
            label=action.label, row=0, style=action.style.value,
            emoji=action.emoji)
        for action in spec.actions)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel("rps_tournament.hub")
def _hub_factory() -> PanelSpec:
    return rps_hub_spec()


@panel(QUICKPLAY_PANEL_ID)
def _quickplay_factory() -> PanelSpec:
    return rps_quickplay_spec()


@panel(PVP_PANEL_ID)
def _pvp_factory() -> PanelSpec:
    return rps_pvp_spec()


handler("rps.render_quickplay")(_render_quickplay)
handler("rps.render_pvp")(_render_pvp)


def install_rps_panels() -> PanelSpec:
    spec = rps_hub_spec()
    for candidate in (spec, rps_quickplay_spec(), rps_pvp_spec()):
        try:
            register_panel(candidate)
        except ValueError as exc:
            if ("already registered" not in str(exc)
                    and "duplicate" not in str(exc)):
                raise
    return spec


def ensure_panel_refs() -> None:
    from sb.spec.refs import HandlerRef as _H, PanelRef as _P, panel as _panel

    if not is_registered(_P("rps_tournament.hub")):
        _panel("rps_tournament.hub")(_hub_factory)
    if not is_registered(_P(QUICKPLAY_PANEL_ID)):
        _panel(QUICKPLAY_PANEL_ID)(_quickplay_factory)
    if not is_registered(_P(PVP_PANEL_ID)):
        _panel(PVP_PANEL_ID)(_pvp_factory)
    if not is_registered(_H("rps.render_quickplay")):
        handler("rps.render_quickplay")(_render_quickplay)
    if not is_registered(_H("rps.render_pvp")):
        handler("rps.render_pvp")(_render_pvp)
    register_rps_sessions()
