"""Counting hub panel (band 6) — the shipped ``!countingmenu``
``_CountingHubView`` made declarative: a no-arg-mode ENUM selector
(Enable Here), the two toggles, Reset Count, Disable Here, plus the
Info / Top / Rules read views. ``multiples`` / ``custom`` stay on
``!start_match`` (the shipped NO_ARG_MODES split)."""

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
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, is_registered, panel

__all__ = [
    "NO_ARG_MODES",
    "counting_hub_spec",
    "ensure_panel_refs",
    "install_counting_panels",
]

# shipped _channel_manager.NO_ARG_MODES verbatim (panel-enable set);
# ordered for the selector.
NO_ARG_MODES = ("normal", "reverse", "skip", "random", "prime",
                "fibonacci", "squares", "cubes", "factorials")


def counting_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="counting.hub",
        subsystem="counting",
        title="🔢 Counting",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Run counting matches in this channel: pick a "
                      "mode below to enable counting HERE, or use "
                      "`!start_match <mode> [args]` (multiples/custom "
                      "modes take arguments). Wrong numbers are "
                      "removed; ✅ marks accepted counts."),
        ),
        actions=(
            PanelActionSpec(
                action_id="counting_info", label="Info", emoji="ℹ️",
                audience_tier="user",
                handler=HandlerRef("counting.info_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_top", label="Top", emoji="🏆",
                audience_tier="user",
                handler=HandlerRef("counting.top_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_rules", label="Rules", emoji="📜",
                audience_tier="user",
                handler=HandlerRef("counting.rules_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_toggle_turns", label="Toggle Turns",
                emoji="🔄", style=ActionStyle.PRIMARY,
                audience_tier="staff",
                handler=HandlerRef("counting.toggle_turns_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_toggle_reset", label="Toggle Reset",
                emoji="♻️", style=ActionStyle.PRIMARY,
                audience_tier="staff",
                handler=HandlerRef("counting.toggle_reset_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_reset", label="Reset Count",
                emoji="🔁", style=ActionStyle.DANGER,
                audience_tier="staff",
                handler=HandlerRef("counting.reset_route"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="counting_disable", label="Disable Here",
                emoji="🛑", style=ActionStyle.DANGER,
                audience_tier="staff",
                handler=HandlerRef("counting.end_match_route"),
                result_render=ResultRender.RESULT_CARD),
        ),
        selectors=(
            SelectorSpec(
                selector_id="counting_enable_mode",
                kind=SelectorKind.ENUM,
                placeholder="Enable Here — pick a counting mode",
                options_source=NO_ARG_MODES,
                on_select=HandlerRef("counting.enable_here_route"),
                audience_tier="staff"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("counting_enable_mode",),
            ("counting_info", "counting_top", "counting_rules"),
            ("counting_toggle_turns", "counting_toggle_reset"),
            ("counting_reset", "counting_disable"),)),)),
    )


@panel("counting.hub")
def _hub_factory() -> PanelSpec:
    return counting_hub_spec()


def install_counting_panels() -> PanelSpec:
    spec = counting_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("counting.hub")):
        _panel("counting.hub")(_hub_factory)
