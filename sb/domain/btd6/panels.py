"""BTD6 hub panel (band 7) — the shipped ``!btd6menu`` BTD6PanelView
declarative. Shipped buttons Ask / Live Events / Units / Rounds / Maps &
Modes / Strategy / Status become: Tower Lookup + Hero Lookup + Round
Lookup (G-10 modals over the reference views), Strategies (published
list), Grounding Check (the retrieval-diagnosis modal), and Live Events
(ingestion pending terminal). The Ask NL path arms with the K10 message
shell (slice 3) — until then grounding-check shows exactly what Ask
would ground."""

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

__all__ = ["btd6_hub_spec", "ensure_panel_refs", "install_btd6_panels"]

TOWER_MODAL = ModalSpec(
    modal_id="btd6.tower_form",
    title="Tower Lookup",
    fields=(
        ModalFieldSpec(field_id="name", label="Tower name",
                       required=True, max_length=60),
    ),
    on_submit=HandlerRef("btd6.ref_tower_view"),
)

HERO_MODAL = ModalSpec(
    modal_id="btd6.hero_form",
    title="Hero Lookup",
    fields=(
        ModalFieldSpec(field_id="name", label="Hero name",
                       required=True, max_length=60),
    ),
    on_submit=HandlerRef("btd6.ref_hero_view"),
)

ROUND_MODAL = ModalSpec(
    modal_id="btd6.round_form",
    title="Round Lookup",
    fields=(
        ModalFieldSpec(field_id="name",
                       label="Round number (add 'abr' for ABR)",
                       required=True, max_length=12),
    ),
    on_submit=HandlerRef("btd6.ref_round_view"),
)

GROUNDING_MODAL = ModalSpec(
    modal_id="btd6.grounding_form",
    title="Grounding Check",
    fields=(
        ModalFieldSpec(field_id="name", label="Your BTD6 question",
                       required=True, max_length=200),
    ),
    on_submit=HandlerRef("btd6.events_grounding_view"),
)


def btd6_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="btd6.hub",
        subsystem="btd6",
        title="🎈 BTD6 Assistant",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Deterministic BTD6 reference over the committed "
                      "game dataset — towers, heroes, rounds, bosses, "
                      "paragons — plus the community strategy memory. "
                      "Natural-language answers ride the grounded AI "
                      "path (mention the bot)."),
        ),
        actions=(
            PanelActionSpec(
                action_id="btd6_tower", label="Tower Lookup", emoji="🗼",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.ref_tower_view"),
                defer_mode=DeferMode.MODAL, modal=TOWER_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="btd6_hero", label="Hero Lookup", emoji="🦸",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.ref_hero_view"),
                defer_mode=DeferMode.MODAL, modal=HERO_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="btd6_round", label="Round Lookup", emoji="🎯",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("btd6.ref_round_view"),
                defer_mode=DeferMode.MODAL, modal=ROUND_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="btd6_strategies", label="Strategies",
                emoji="📚", audience_tier="user",
                handler=HandlerRef("btd6.strat_published_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="btd6_grounding", label="Grounding Check",
                emoji="🔎", audience_tier="user",
                handler=HandlerRef("btd6.events_grounding_view"),
                defer_mode=DeferMode.MODAL, modal=GROUNDING_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="btd6_events", label="Live Events", emoji="📡",
                audience_tier="user",
                handler=HandlerRef("btd6.events_pending"),
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("btd6_tower", "btd6_hero", "btd6_round"),
            ("btd6_strategies", "btd6_grounding", "btd6_events"),)),)),
    )


@panel("btd6.hub")
def _hub_factory() -> PanelSpec:
    return btd6_hub_spec()


def install_btd6_panels() -> PanelSpec:
    spec = btd6_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import panel as _panel

    if not is_registered(_P("btd6.hub")):
        _panel("btd6.hub")(_hub_factory)
