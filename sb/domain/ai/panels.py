"""AI hub panel (band 7) — the shipped ``!aimenu`` made declarative:
operator read-views over K10 (status/readiness/routing/diagnostics) +
the review backlog."""

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
from sb.spec.refs import HandlerRef, is_registered, panel

__all__ = ["ai_hub_spec", "ensure_panel_refs", "install_ai_panels"]


def _action(action_id: str, label: str, emoji: str, ref: str,
            style: ActionStyle = ActionStyle.SECONDARY) -> PanelActionSpec:
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji, style=style,
        audience_tier="staff", handler=HandlerRef(ref),
        result_render=ResultRender.RESULT_CARD)


def ai_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="ai.hub",
        subsystem="ai",
        title="🤖 AI Platform",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Operator views over the AI invocation kernel: "
                      "gateway status, task readiness, model routing, "
                      "diagnostics, and the answer review loop. All AI "
                      "settings ride the declared `ai.*` settings."),
        ),
        actions=(
            _action("ai_status", "Status", "📊", "ai.status_view",
                    ActionStyle.PRIMARY),
            _action("ai_readiness", "Readiness", "🩺", "ai.readiness_view"),
            _action("ai_routing", "Routing", "🧭", "ai.routing_view"),
            _action("ai_diagnostics", "Diagnostics", "🔬",
                    "ai.diagnostics_view"),
            _action("ai_review_list", "Review Backlog", "📝",
                    "ai.review_list_view"),
            _action("ai_providers", "Providers", "🔌", "ai.providers_view"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("ai_status", "ai_readiness", "ai_routing"),
            ("ai_diagnostics", "ai_review_list", "ai_providers"),)),)),
    )


@panel("ai.hub")
def _hub_factory() -> PanelSpec:
    return ai_hub_spec()


def install_ai_panels() -> PanelSpec:
    spec = ai_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import panel as _panel

    if not is_registered(_P("ai.hub")):
        _panel("ai.hub")(_hub_factory)
