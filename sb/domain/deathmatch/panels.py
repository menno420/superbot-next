"""Deathmatch panel + g1 session actions (band 6) — the shipped
DeathmatchPanelView declarative (Fight Bot / My Stats / Leaderboard /
Help; PvP challenges are typed — `!deathmatch @user`), and the duel
session-action tables (Accept/Decline, Attack/Defend, bot twin)."""

from __future__ import annotations

from sb.domain.games.session import register_session_actions
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
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, is_registered, panel

__all__ = [
    "deathmatch_hub_spec",
    "ensure_panel_refs",
    "install_deathmatch_panels",
    "register_deathmatch_sessions",
]


def _session_action(action_id: str, label: str, ref: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           handler=WorkflowRef(ref))


_SESSION_ACTIONS = {
    "accept": _session_action("dm_accept", "Accept",
                              "deathmatch.accept", ActionStyle.SUCCESS,
                              "✅"),
    "decline": _session_action("dm_decline", "Decline",
                               "deathmatch.decline", ActionStyle.DANGER,
                               "❌"),
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


@panel("deathmatch.hub")
def _hub_factory() -> PanelSpec:
    return deathmatch_hub_spec()


def install_deathmatch_panels() -> PanelSpec:
    spec = deathmatch_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("deathmatch.hub")):
        _panel("deathmatch.hub")(_hub_factory)
    register_deathmatch_sessions()
