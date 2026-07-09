"""Project Moon browse panel (band 7) — the shipped LimbusBrowseView
declarative: one button per entity kind + Origins + the lookup modal
(the shipped overview embed's category browse)."""

from __future__ import annotations

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
from sb.spec.refs import HandlerRef, is_registered, panel

__all__ = ["ensure_panel_refs", "install_projmoon_panels", "projmoon_hub_spec"]

LOOKUP_MODAL = ModalSpec(
    modal_id="projmoon.lookup_form",
    title="Limbus Lookup",
    fields=(
        ModalFieldSpec(field_id="name", label="Name or term",
                       required=True, max_length=60),
    ),
    on_submit=HandlerRef("projmoon.lookup_view"),
)


def _kind_action(action_id: str, label: str, emoji: str,
                 ref: str) -> PanelActionSpec:
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji,
        audience_tier="user", handler=HandlerRef(ref),
        result_render=ResultRender.RESULT_CARD)


def projmoon_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="projmoon.hub",
        subsystem="projmoon",
        title="🌑 Project Moon — Limbus Company",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Read-only Limbus Company reference over committed "
                      "structural facts: the 12 Sinners, 7 Sins, 3 damage "
                      "types, 5 E.G.O grades, statuses, and combat "
                      "mechanics. Lookup resolves any name or term."),
        ),
        actions=(
            PanelActionSpec(
                action_id="pm_lookup", label="Lookup", emoji="🔎",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("projmoon.lookup_view"),
                defer_mode=DeferMode.MODAL, modal=LOOKUP_MODAL,
                result_render=ResultRender.RESULT_CARD),
            _kind_action("pm_sinners", "Sinners", "🧑‍🤝‍🧑",
                         "projmoon.sinner_view"),
            _kind_action("pm_sins", "Sins", "🎨", "projmoon.sin_view"),
            _kind_action("pm_grades", "E.G.O Grades", "🎖️",
                         "projmoon.ego_view"),
            _kind_action("pm_statuses", "Statuses", "🔥",
                         "projmoon.status_view"),
            _kind_action("pm_mechanics", "Mechanics", "⚙️",
                         "projmoon.mechanic_view"),
            _kind_action("pm_origins", "Origins", "📖",
                         "projmoon.origins_view"),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("pm_lookup", "pm_sinners", "pm_sins"),
            ("pm_grades", "pm_statuses", "pm_mechanics", "pm_origins"),)),)),
    )


@panel("projmoon.hub")
def _hub_factory() -> PanelSpec:
    return projmoon_hub_spec()


def install_projmoon_panels() -> PanelSpec:
    spec = projmoon_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import panel as _panel

    if not is_registered(_P("projmoon.hub")):
        _panel("projmoon.hub")(_hub_factory)
