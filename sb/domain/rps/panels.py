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
    AnchorPolicy,
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
    "BOTMATCH_PANEL_ID",
    "MATCH_PANEL_ID",
    "PVP_PANEL_ID",
    "QUICKPLAY_PANEL_ID",
    "REGISTRATION_PANEL_ID",
    "ensure_panel_refs",
    "install_rps_panels",
    "register_rps_sessions",
    "rps_botmatch_spec",
    "rps_hub_spec",
    "rps_match_spec",
    "rps_pvp_spec",
    "rps_quickplay_spec",
    "rps_registration_spec",
]

QUICKPLAY_PANEL_ID = "rps_tournament.quickplay"
PVP_PANEL_ID = "rps_tournament.pvp"
REGISTRATION_PANEL_ID = "rps_tournament.registration"
MATCH_PANEL_ID = "rps_tournament.match"
BOTMATCH_PANEL_ID = "rps_tournament.botmatch"

#: shipped button emoji (views/rps/solo_play.py — Rock 🪨 / Paper 📄 /
#: Scissors ✂️, grey style) + the mode families' first emoji alias
#: (cogs/rps_tournament/rules.py MOVE_ALIASES).
_QP_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️",
             "lizard": "🦎", "spock": "🖖",
             "pawn": "♟️", "knight": "♞", "queen": "♛",
             "fire": "🔥", "water": "💧", "grass": "🌿"}

#: every move any mode can render — the match panel DECLARES them all so
#: the engine can mint session ids for whichever subset the mode shows.
_ALL_MOVES = tuple(dict.fromkeys(
    move for moves in GAME_MODES.values() for move in moves))


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


def rps_registration_spec() -> PanelSpec:
    """The shipped tournament-registration message (`!rpsregister` →
    ``ctx.send(embed=embed, view=reg_view)`` + the ✅ primer): the
    INFO_COLOR embed with the Entry Fee / Game Mode fields and the green
    ``Join Tournament`` button (views/rps/registration._RpsRegistrationView)
    — pinned byte-for-byte by the rpsregister golden. PUBLIC (anyone may
    join); session-lifecycle so the button rides a run-minted id, exactly
    the shipped auto-id view; the window is the shipped 600 s."""
    return PanelSpec(
        panel_id=REGISTRATION_PANEL_ID,
        subsystem="rps_tournament",
        title="🎮 Rock Paper Scissors Tournament Registration 🎮",
        audience=Audience.PUBLIC,
        timeout_s=600,                    # the shipped registration_timer
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="join", label="Join Tournament", emoji="✅",
                style=ActionStyle.SUCCESS, audience_tier="user",
                handler=HandlerRef("rps.tournament_join"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(("join",),)),)),
        renderer_override=HandlerRef("rps.render_registration"),
        justification=(
            "the shipped registration embed's Entry Fee / Game Mode field "
            "values are request-parameterized copy (fee argument + the "
            "default_mode setting — cogs/rps_tournament_cog.rps_register); "
            "grammar TextBlocks are static. The Join button and its "
            "authority stay declared on the spec; the renderer composes "
            "the embed + the declared button and asks for the shipped ✅ "
            "self-reaction primer."),
        session_lifecycle=True,
    )


def rps_match_spec() -> PanelSpec:
    """One tournament match as a BUTTON view in the tournament's home
    channel — the DELIBERATE deviation from the shipped private match
    channel + no-prefix message parsing (channel provisioning rides the
    resource-provision port; ledgered). Copy keeps the shipped match-
    channel announce lines verbatim. CHANNEL_ANCHOR: round-N views open
    off the round-(N-1) final click and must be fresh channel messages."""
    return PanelSpec(
        panel_id=MATCH_PANEL_ID,
        subsystem="rps_tournament",
        title="✂️ RPS Tournament Match",
        audience=Audience.PUBLIC,
        anchor_policy=AnchorPolicy.CHANNEL_ANCHOR,
        timeout_s=600,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        actions=tuple(
            PanelActionSpec(
                action_id=f"move_{move}", label=move.title(),
                emoji=_QP_EMOJI[move], style=ActionStyle.SECONDARY,
                audience_tier="user", defer_mode=DeferMode.NONE,
                handler=HandlerRef("rps.tournament_move"))
            for move in _ALL_MOVES),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            tuple(f"move_{m}" for m in _ALL_MOVES[:5]),
            tuple(f"move_{m}" for m in _ALL_MOVES[5:8]),
            tuple(f"move_{m}" for m in _ALL_MOVES[8:]),)),)),
        renderer_override=HandlerRef("rps.render_match"),
        justification=(
            "every line of the match view is match-parameterized copy "
            "(player mentions, mode/best-of, per-throw score reveals — the "
            "shipped match-channel sends); grammar TextBlocks are static. "
            "The mode decides WHICH declared move buttons render (classic "
            "3 / lizard_spock 5 / chess 3 / elemental 3) — declared "
            "actions and authority stay on the spec; the renderer only "
            "composes the staged embed + the mode's declared subset."),
        session_lifecycle=True,
    )


def rps_botmatch_spec() -> PanelSpec:
    """One ``!rpsbot`` match as a BUTTON view in the invoking channel —
    the tournament-match panel's DELIBERATE deviation carried to the bot
    lane (the shipped flow was a private per-player channel + no-prefix
    message parsing; channel provisioning rides the resource-provision
    port, ledgered in sb/domain/rps/bot_match.py). Copy keeps the shipped
    ``_bot_matches.py`` channel sends verbatim. CHANNEL_ANCHOR: `!rpsbot
    @a @b` opens one fresh channel message per player."""
    return PanelSpec(
        panel_id=BOTMATCH_PANEL_ID,
        subsystem="rps_tournament",
        title="✂️ RPS Bot Match",
        audience=Audience.PUBLIC,
        anchor_policy=AnchorPolicy.CHANNEL_ANCHOR,
        timeout_s=600,
        frame=EmbedFrameSpec(style_token="purple",
                             footer_mode=FooterMode.NONE),
        actions=tuple(
            PanelActionSpec(
                # `bot_move_` (not `move_`): custom_id claims are
                # SUBSYSTEM-scoped and the tournament match panel owns
                # `move_*` (manifest_compile namespace collision).
                action_id=f"bot_move_{move}", label=move.title(),
                emoji=_QP_EMOJI[move], style=ActionStyle.SECONDARY,
                audience_tier="user", defer_mode=DeferMode.NONE,
                handler=HandlerRef("rps.botmatch_move"))
            for move in _ALL_MOVES),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            tuple(f"bot_move_{m}" for m in _ALL_MOVES[:5]),
            tuple(f"bot_move_{m}" for m in _ALL_MOVES[5:8]),
            tuple(f"bot_move_{m}" for m in _ALL_MOVES[8:]),)),)),
        renderer_override=HandlerRef("rps.render_botmatch"),
        justification=(
            "every line of the bot-match view is match-parameterized copy "
            "(player mention, mode/best-of, the per-round `Bot played:` "
            "reveal + result line — the shipped _bot_matches.py channel "
            "sends); grammar TextBlocks are static. The mode decides "
            "WHICH declared move buttons render (classic 3 / lizard_spock "
            "5 / chess 3 / elemental 3) — declared actions and authority "
            "stay on the spec; the renderer only composes the staged "
            "embed + the mode's declared subset."),
        session_lifecycle=True,
    )


async def _render_botmatch(spec: PanelSpec, ctx) -> object:
    """renderer_override — one bot match, staged: open (the shipped
    match-channel announce lines) → per-round reveal (`Bot played: …` +
    the shipped result line + `Please enter your next move.`) → terminal
    (win/lose the match, buttons disabled). Shipped copy verbatim
    (oracle ``disbot/cogs/rps_tournament/_bot_matches.py``); the running
    score line is the home-channel deviation's addition (one edited
    embed carries no channel history)."""
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    stage = str(params.get("stage") or "open")
    player = int(params.get("player") or 0)
    mode = str(params.get("mode") or "classic")
    best_of = int(params.get("best_of") or 1)
    done = stage in ("match_won", "match_lost")
    # the shipped bot-match channel announce, verbatim lines
    lines = [f"<@{player}> vs **Bot**",
             f"Game mode: {mode.capitalize()}, Best of {best_of}",
             "Please enter your move."]
    score_line = (f"Score: <@{player}> **{int(params.get('wins') or 0)}** "
                  f"— **{int(params.get('bot_wins') or 0)}** Bot")
    if stage != "open":
        bot_move = str(params.get("bot_move") or "")
        result = str(params.get("result") or "")
        lines = lines[:2] + [f"Bot played: {bot_move.capitalize()}."]
        if result == "tie":
            lines.append("It's a tie!")                     # shipped
        elif result == "win":
            lines.append(f"<@{player}> wins this round!")   # shipped
        else:
            lines.append("Bot wins this round!")            # shipped
        if stage == "match_won":
            lines.append(f"<@{player}> wins the match against the bot!")
        elif stage == "match_lost":
            lines.append("Bot wins the match!")             # shipped
        else:
            lines.append("Please enter your next move.")    # shipped
        lines.append(score_line)
    embed = RenderedEmbed(
        title=spec.title,
        description="\n".join(lines),
        style_token="green" if stage == "match_won"
        else "red" if stage == "match_lost" else "purple")
    components = tuple(
        RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.bot_move_{move}",
            label=move.title(), row=0 if i < 5 else 1,
            style="secondary", emoji=_QP_EMOJI[move], disabled=done)
        for i, move in enumerate(GAME_MODES.get(mode, GAME_MODES["classic"])))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


async def _render_registration(spec: PanelSpec, ctx) -> object:
    """renderer_override — the golden-pinned registration embed verbatim:
    INFO_COLOR, `React ✅ or click **Join** to sign up!` + the window line,
    inline Entry Fee / Game Mode fields, the green Join button, and the
    shipped ✅ self-reaction primer."""
    from sb.domain.rps.tournament import (
        REGISTRATION_EMOJI,
        REGISTRATION_WINDOW_S,
    )
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    fee = int(params.get("entry_fee", 0) or 0)
    fee_str = f"{fee} 🪙" if fee > 0 else "Free"
    mode_label = str(params.get("mode_label") or "Classic")
    closed = bool(params.get("closed"))
    embed = RenderedEmbed(
        title=spec.title,
        description=("React ✅ or click **Join** to sign up!\n"
                     f"Registration ends in "
                     f"{REGISTRATION_WINDOW_S // 60} minutes."),
        fields=(("Entry Fee", fee_str, True), ("Game Mode", mode_label, True)),
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


async def _render_match(spec: PanelSpec, ctx) -> object:
    """renderer_override — one tournament match, staged: open (the shipped
    match-channel announce lines) → waiting → per-throw reveal (tie /
    scored) → done (winner line, buttons disabled)."""
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    stage = str(params.get("stage") or "open")
    p1 = int(params.get("p1") or 0)
    p2 = int(params.get("p2") or 0)
    mode = str(params.get("mode") or "classic")
    best_of = int(params.get("best_of") or 1)
    round_num = int(params.get("round") or 1)
    done = stage == "done"
    # the shipped match-channel announce, verbatim lines
    lines = [f"<@{p1}> vs <@{p2}>",
             f"Game mode: {mode.capitalize()}, Best of {best_of}",
             "Please enter your move."]
    moves = {str(k): str(v) for k, v in dict(params.get("moves") or {}).items()}
    m1, m2 = moves.get(str(p1), ""), moves.get(str(p2), "")

    def _reveal() -> str:
        return (f"<@{p1}>: **{m1}** {_QP_EMOJI.get(m1, '')}  ·  "
                f"<@{p2}>: **{m2}** {_QP_EMOJI.get(m2, '')}")

    scores = {str(k): int(v)
              for k, v in dict(params.get("scores") or {}).items()}
    score_line = (f"Score: <@{p1}> **{scores.get(str(p1), 0)}** — "
                  f"**{scores.get(str(p2), 0)}** <@{p2}>")
    if stage == "waiting":
        lines.append("⏳ One move is in — waiting for the other player…")
    elif stage == "throw_tie":
        lines += [_reveal(), "🤝 Tie — throw again!", score_line]
    elif stage == "throw_scored":
        lines += [_reveal(),
                  f"<@{int(params.get('throw_winner') or 0)}> takes the "
                  "throw!", score_line]
    elif done:
        lines = lines[:2] + [_reveal(),
                             f"🏆 <@{int(params.get('winner') or 0)}> wins "
                             "the match!"]
    embed = RenderedEmbed(
        title=f"✂️ RPS Tournament — Round {round_num}",
        description="\n".join(lines),
        style_token="green" if done else "purple")
    components = tuple(
        RenderedComponent(
            kind="button", custom_id=f"{spec.panel_id}.move_{move}",
            label=move.title(), row=0 if i < 5 else 1,
            style="secondary", emoji=_QP_EMOJI[move], disabled=done)
        for i, move in enumerate(GAME_MODES.get(mode, GAME_MODES["classic"])))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


@panel("rps_tournament.hub")
def _hub_factory() -> PanelSpec:
    return rps_hub_spec()


@panel(QUICKPLAY_PANEL_ID)
def _quickplay_factory() -> PanelSpec:
    return rps_quickplay_spec()


@panel(PVP_PANEL_ID)
def _pvp_factory() -> PanelSpec:
    return rps_pvp_spec()


@panel(REGISTRATION_PANEL_ID)
def _registration_factory() -> PanelSpec:
    return rps_registration_spec()


@panel(MATCH_PANEL_ID)
def _match_factory() -> PanelSpec:
    return rps_match_spec()


@panel(BOTMATCH_PANEL_ID)
def _botmatch_factory() -> PanelSpec:
    return rps_botmatch_spec()


handler("rps.render_quickplay")(_render_quickplay)
handler("rps.render_pvp")(_render_pvp)
handler("rps.render_registration")(_render_registration)
handler("rps.render_match")(_render_match)
handler("rps.render_botmatch")(_render_botmatch)


def install_rps_panels() -> PanelSpec:
    spec = rps_hub_spec()
    for candidate in (spec, rps_quickplay_spec(), rps_pvp_spec(),
                      rps_registration_spec(), rps_match_spec(),
                      rps_botmatch_spec()):
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
    if not is_registered(_P(REGISTRATION_PANEL_ID)):
        _panel(REGISTRATION_PANEL_ID)(_registration_factory)
    if not is_registered(_P(MATCH_PANEL_ID)):
        _panel(MATCH_PANEL_ID)(_match_factory)
    if not is_registered(_P(BOTMATCH_PANEL_ID)):
        _panel(BOTMATCH_PANEL_ID)(_botmatch_factory)
    if not is_registered(_H("rps.render_quickplay")):
        handler("rps.render_quickplay")(_render_quickplay)
    if not is_registered(_H("rps.render_pvp")):
        handler("rps.render_pvp")(_render_pvp)
    if not is_registered(_H("rps.render_registration")):
        handler("rps.render_registration")(_render_registration)
    if not is_registered(_H("rps.render_match")):
        handler("rps.render_match")(_render_match)
    if not is_registered(_H("rps.render_botmatch")):
        handler("rps.render_botmatch")(_render_botmatch)
    register_rps_sessions()
