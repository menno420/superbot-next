"""Chain hub panel (band 6) — the shipped ``!chainmenu``
``_ChainMenuView`` made declarative: the four G-10 modals
(Create / Delete / Set Limit / Clear Limit, each with the shipped
'Channel (mention/ID, blank = current)' field) + the List view."""

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

__all__ = ["chain_hub_spec", "ensure_panel_refs", "install_chain_panels"]

_CHANNEL_FIELD = ModalFieldSpec(
    field_id="channel", label="Channel (mention/ID, blank = current)",
    required=False, max_length=32)

CREATE_MODAL = ModalSpec(
    modal_id="chain.create_form",
    title="Create Chain",
    fields=(
        _CHANNEL_FIELD,
        ModalFieldSpec(field_id="word", label="Allowed word",
                       required=True, max_length=100),
    ),
    on_submit=HandlerRef("chain.create_route"),
)

DELETE_MODAL = ModalSpec(
    modal_id="chain.delete_form",
    title="Delete Chain",
    fields=(_CHANNEL_FIELD,),
    on_submit=HandlerRef("chain.delete_route"),
)

SET_LIMIT_MODAL = ModalSpec(
    modal_id="chain.set_limit_form",
    title="Set Word Limit",
    fields=(
        _CHANNEL_FIELD,
        ModalFieldSpec(field_id="limit",
                       label="Word limit (0 = remove limit)",
                       required=True, max_length=6),
    ),
    on_submit=HandlerRef("chain.setlimit_route"),
)

CLEAR_LIMIT_MODAL = ModalSpec(
    modal_id="chain.clear_limit_form",
    title="Clear Word Limit",
    fields=(_CHANNEL_FIELD,),
    on_submit=HandlerRef("chain.removelimit_route"),
)


def chain_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="chain.hub",
        subsystem="chain",
        title="🔗 Chain Manager",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Message chains: lock a channel to one allowed "
                      "word, cap message length, and watch the chain "
                      "count climb. All other messages are removed."),
        ),
        actions=(
            PanelActionSpec(
                action_id="chain_list", label="List", emoji="📋",
                audience_tier="user",
                handler=HandlerRef("chain.list_view"),
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_create", label="Create Chain",
                emoji="➕", style=ActionStyle.SUCCESS,
                audience_tier="staff",
                handler=HandlerRef("chain.create_route"),
                defer_mode=DeferMode.MODAL, modal=CREATE_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_set_limit", label="Set Limit",
                emoji="📏", style=ActionStyle.PRIMARY,
                audience_tier="staff",
                handler=HandlerRef("chain.setlimit_route"),
                defer_mode=DeferMode.MODAL, modal=SET_LIMIT_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_clear_limit", label="Clear Limit",
                emoji="🧹", style=ActionStyle.SECONDARY,
                audience_tier="staff",
                handler=HandlerRef("chain.removelimit_route"),
                defer_mode=DeferMode.MODAL, modal=CLEAR_LIMIT_MODAL,
                result_render=ResultRender.RESULT_CARD),
            PanelActionSpec(
                action_id="chain_delete", label="Delete Chain",
                emoji="🗑️", style=ActionStyle.DANGER,
                audience_tier="staff",
                handler=HandlerRef("chain.delete_route"),
                defer_mode=DeferMode.MODAL, modal=DELETE_MODAL,
                result_render=ResultRender.RESULT_CARD),
        ),
        navigation=NavigationSpec(),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("chain_list",),
            ("chain_create", "chain_set_limit", "chain_clear_limit"),
            ("chain_delete",),)),)),
    )


@panel("chain.hub")
def _hub_factory() -> PanelSpec:
    return chain_hub_spec()


def install_chain_panels() -> PanelSpec:
    spec = chain_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P, panel as _panel

    if not is_registered(_P("chain.hub")):
        _panel("chain.hub")(_hub_factory)
