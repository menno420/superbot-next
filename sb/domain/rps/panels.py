"""RPS panels + g1 session actions (band 6, subsystem rps_tournament).

The hub is the shipped `!rps` panel made declarative: a provider-free
move SELECTOR (quick play — on_select runs the audited rps.solo_play op
with args["values"], the D-0034 pattern) plus Rules and Settings views.
PvP Accept/Decline and the post-accept move buttons are dynamic-session
components on the ``g1:rps_tournament:`` prefix."""

from __future__ import annotations

from sb.domain.games.session import register_session_actions
from sb.domain.rps.rules import GAME_MODES
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
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, WorkflowRef, is_registered, panel

__all__ = [
    "ensure_panel_refs",
    "install_rps_panels",
    "register_rps_sessions",
    "rps_hub_spec",
]


def _session_action(action_id: str, label: str, ref: str,
                    style: ActionStyle = ActionStyle.SECONDARY,
                    emoji: str = "") -> PanelActionSpec:
    return PanelActionSpec(action_id=action_id, label=label, emoji=emoji,
                           style=style, audience_tier="user",
                           handler=WorkflowRef(ref))


_SESSION_ACTIONS = {
    "accept": _session_action("rps_accept", "Accept", "rps.pvp_accept",
                              ActionStyle.SUCCESS, "✅"),
    "decline": _session_action("rps_decline", "Decline",
                               "rps.pvp_decline", ActionStyle.DANGER, "❌"),
    **{f"move_{m}": _session_action(f"rps_move_{m}", m.title(),
                                    "rps.pvp_move")
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


@panel("rps_tournament.hub")
def _hub_factory() -> PanelSpec:
    return rps_hub_spec()


def install_rps_panels() -> PanelSpec:
    spec = rps_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("rps_tournament.hub")):
        _panel("rps_tournament.hub")(_hub_factory)
    register_rps_sessions()
