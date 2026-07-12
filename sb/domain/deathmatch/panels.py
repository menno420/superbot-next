"""Deathmatch panels + g1 session actions (band 6) — the shipped
DeathmatchPanelView declarative (Fight Bot / My Stats / Leaderboard /
Help; PvP challenges are typed — `!deathmatch @user`), the CHALLENGE
CARD (the shipped ``_ChallengeView``: red embed + ✅ Accept / ❌ Decline
on run-minted session ids, 30s timeout — goldens/deathmatch/
sweep_dm_challenge pins the wire bytes; the pre-accept challenge lives
in the session binding, NEVER a checkpoint row — the ops-module
D-0042-review note), the HELP CARD (the shipped ``dm_help`` blue embed,
pure grammar — sweep_dm_help pins it), and the duel session-action
table (Attack/Defend + bot twin; the accepted duel rides restart-safe
``g1:`` ids over its checkpoint row)."""

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
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, handler, is_registered, panel

__all__ = [
    "CHALLENGE_PANEL_ID",
    "HELP_PANEL_ID",
    "deathmatch_challenge_spec",
    "deathmatch_help_spec",
    "deathmatch_hub_spec",
    "ensure_panel_refs",
    "install_deathmatch_panels",
    "register_deathmatch_sessions",
]

CHALLENGE_PANEL_ID = "deathmatch.challenge_card"
HELP_PANEL_ID = "deathmatch.help_card"


def _session_action(action_id: str, label: str, ref: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           handler=WorkflowRef(ref))


# The g1 dispatcher table is DUEL-STAGE ONLY: Accept/Decline moved onto
# the challenge card's session-lifecycle binding (a pending challenge has
# no checkpoint row for g1 to recover — the ops-module D-0042-review
# note), so a stale g1 accept/decline id from an old message falls to the
# polite-expiry terminal.
_SESSION_ACTIONS = {
    "attack": _session_action("dm_attack", "Attack", "deathmatch.move",
                              ActionStyle.DANGER, "⚔️"),
    "defend": _session_action("dm_defend", "Defend", "deathmatch.move",
                              ActionStyle.PRIMARY, "🛡️"),
    "bot_attack": _session_action("dm_bot_attack", "Attack",
                                  "deathmatch.bot_move",
                                  ActionStyle.DANGER, "⚔️"),
    "bot_defend": _session_action("dm_bot_defend", "Defend",
                                  "deathmatch.bot_move",
                                  ActionStyle.PRIMARY, "🛡️"),
}


def register_deathmatch_sessions() -> None:
    register_session_actions("deathmatch", _SESSION_ACTIONS)


def deathmatch_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="deathmatch.hub",
        subsystem="deathmatch",
        title="⚔️ Deathmatch",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Turn-based duels: 100 HP each, attack for 15 "
                      "(30 on a crit), defend to halve the next hit. "
                      "Challenge a player with `!deathmatch @user` — "
                      "PvP wins count on the leaderboard. **Fight Bot** "
                      "starts an immediate duel vs the bot (results "
                      "stay off the leaderboard)."),
        ),
        actions=(
            PanelActionSpec(
                action_id="dm_fight_bot", label="Fight Bot", emoji="🤖",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=WorkflowRef("deathmatch.bot_start"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="dm_stats", label="My Stats", emoji="📊",
                audience_tier="user",
                handler=HandlerRef("deathmatch.stats_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="dm_top", label="Leaderboard", emoji="🏆",
                audience_tier="user",
                handler=HandlerRef("deathmatch.top_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="dm_help", label="Help", emoji="❓",
                audience_tier="user",
                handler=HandlerRef("deathmatch.help_view"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(parent=PanelRef("games.world")),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("dm_fight_bot", "dm_stats", "dm_top", "dm_help"),)),)),
    )


def deathmatch_challenge_spec() -> PanelSpec:
    """The shipped ``_ChallengeView`` (cogs/deathmatch_cog.py): the red
    challenge embed over ✅ Accept / ❌ Decline (glyphs IN the labels —
    the shipped decorator form ``label=\"✅ Accept\"``; sweep_dm_challenge
    pins the emoji-less wire shape) on run-minted session ids, dying at
    the shipped 30-second timeout. PUBLIC — only the TARGET may answer,
    and that lock is the accept/decline ops' own check (the shipped
    view checked the clicker, never an invoker lock)."""
    return PanelSpec(
        panel_id=CHALLENGE_PANEL_ID,
        subsystem="deathmatch",
        title="⚔️ Deathmatch Challenge",
        audience=Audience.PUBLIC,
        timeout_s=30,               # the shipped _ChallengeView timeout=30.0
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="dm_accept", label="✅ Accept",
                style=ActionStyle.SUCCESS, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("deathmatch.challenge_click")),
            PanelActionSpec(
                action_id="dm_decline", label="❌ Decline",
                style=ActionStyle.DANGER, audience_tier="user",
                defer_mode=DeferMode.NONE,
                handler=HandlerRef("deathmatch.challenge_click")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("dm_accept", "dm_decline"),)),)),
        renderer_override=HandlerRef("deathmatch.render_challenge"),
        justification=(
            "the shipped challenge/duel embeds are match-parameterized "
            "copy on every line (challenger/target mentions, HP lines, "
            "turn prompts — cogs/deathmatch_cog.py); grammar TextBlocks "
            "are static. The challenge-stage buttons stay DECLARED on the "
            "spec (authority + the session mint); the accepted-duel stage "
            "swaps them for g1: dynamic-session Attack/Defend minted from "
            "the duel's session id. The renderer only composes the staged "
            "embed + buttons."),
        session_lifecycle=True,
    )


def deathmatch_help_spec() -> PanelSpec:
    """The shipped ``!dm_help`` embed (blue, no footer, no components —
    goldens/deathmatch/sweep_dm_help pins every byte): static copy, so
    the pure grammar renders it with no override."""
    return PanelSpec(
        panel_id=HELP_PANEL_ID,
        subsystem="deathmatch",
        title="Deathmatch Help",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(
            TextBlock("**Commands:**\n"
                      "`!deathmatch @User` — Challenge a user to a duel.\n"
                      "`!leaderboard deathmatch` — View the top duelists."
                      "\n\n**During a Duel:**\n"
                      "Use the **⚔️ Attack** and **🛡️ Defend** buttons "
                      "in the duel message."),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        session_lifecycle=True,
    )


async def _render_challenge(spec: PanelSpec, ctx) -> object:
    """renderer_override — the shipped wire copy per stage: challenge
    (`⚔️ Deathmatch Challenge`, red, the 30-seconds footer, ✅ Accept /
    ❌ Decline — pinned by sweep_dm_challenge), declined (controls
    disabled, the decline line), the accepted duel (HP lines + turn
    prompt over g1 Attack/Defend), result (terminal, no components)."""
    from sb.domain.games import session as games_session
    from sb.kernel.panels.render import (
        RenderedComponent,
        RenderedEmbed,
        RenderedPanel,
    )

    params = getattr(ctx, "params", {}) or {}
    stage = str(params.get("stage") or "challenge")
    if stage in ("challenge", "declined"):
        components = tuple(
            RenderedComponent(
                kind="button",
                custom_id=f"{spec.panel_id}.{action.action_id}",
                label=action.label, row=0, style=action.style.value,
                emoji="", disabled=stage == "declined")
            for action in spec.actions)
    elif stage == "result":
        components = ()
    else:                                     # the accepted duel
        sid = str(params.get("session_id") or "")

        def _g1(action: str) -> str:
            return games_session.mint_custom_id("deathmatch", sid, action)

        components = (
            RenderedComponent(kind="button", custom_id=_g1("attack"),
                              label="Attack", row=0, style="danger",
                              emoji="⚔️", disabled=False),
            RenderedComponent(kind="button", custom_id=_g1("defend"),
                              label="Defend", row=0, style="primary",
                              emoji="🛡️", disabled=False),
        )
    if stage == "challenge":
        description = (f"<@{params.get('challenger')}> has challenged "
                       f"<@{params.get('target')}> to a duel!\n\n"
                       "Press **Accept** or **Decline** below.")
        footer = "You have 30 seconds to respond."
    else:
        description = str(params.get("message") or "")
        footer = ""
    embed = RenderedEmbed(title=spec.title, description=description,
                          footer=footer, style_token="red")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=components,
        invoker_lock=None, timeout_s=spec.timeout_s,
        audience=spec.audience.value, anchor_policy=spec.anchor_policy.value)


@panel("deathmatch.hub")
def _hub_factory() -> PanelSpec:
    return deathmatch_hub_spec()


@panel(CHALLENGE_PANEL_ID)
def _challenge_factory() -> PanelSpec:
    return deathmatch_challenge_spec()


@panel(HELP_PANEL_ID)
def _help_factory() -> PanelSpec:
    return deathmatch_help_spec()


handler("deathmatch.render_challenge")(_render_challenge)


def install_deathmatch_panels() -> PanelSpec:
    spec = deathmatch_hub_spec()
    for candidate in (spec, deathmatch_challenge_spec(),
                      deathmatch_help_spec()):
        try:
            register_panel(candidate)
        except ValueError as exc:
            if ("already registered" not in str(exc)
                    and "duplicate" not in str(exc)):
                raise
    return spec


def ensure_panel_refs() -> None:
    from sb.spec.refs import (
        HandlerRef as _H,
        PanelRef as _P,
        handler as _handler,
        panel as _panel,
    )

    if not is_registered(_P("deathmatch.hub")):
        _panel("deathmatch.hub")(_hub_factory)
    if not is_registered(_P(CHALLENGE_PANEL_ID)):
        _panel(CHALLENGE_PANEL_ID)(_challenge_factory)
    if not is_registered(_P(HELP_PANEL_ID)):
        _panel(HELP_PANEL_ID)(_help_factory)
    if not is_registered(_H("deathmatch.render_challenge")):
        _handler("deathmatch.render_challenge")(_render_challenge)
    register_deathmatch_sessions()
