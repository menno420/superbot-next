"""The XP panels (band 4) — the shipped `_XpHubView` declaratively:
the invoker's rank overview (provider-fed fields) + the admin action row
(Give XP / Reset XP as G-10 modals over the audited K7 ops; the shipped
`_GiveXpModal`/`_ResetXpModal` one-form flows), PLUS the shipped visual
card-engine H3 posture: the hub send carries the invoker's rank image
card ``rank.png`` (views/xp/main_panel.py build_response, PR #1413) and
``!rank`` sends the card directly (utils/rank_render.py, PR #1401) —
goldens/xp/sweep_xpmenu + xp_chat_award pin the multipart send shape.
The shipped Both/XP/Coins stat toggles are the `!rank <stat>` routes
(in-place attachment swapping is presentation the live adapter owns —
deviation ledgered).

Shipped XP-hub buttons carried no persistent custom_ids (view-local
decorators on an ephemeral, timeout-based view — views/xp/__init__.py),
so no `custom_id_override` pins are needed and the hub is a
session-lifecycle view: run-minted component ids, never anchored
(the goldens pin the no-panel_anchors-row delta).
"""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.outcomes import DeferMode
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    ProviderRef,
    WorkflowRef,
    is_registered,
    panel,
    provider,
)

__all__ = ["ensure_panel_refs", "install_xp_panels", "rank_card_spec",
           "xp_hub_spec"]

_HUB_PROVIDER = "xp.hub_overview"

GIVEXP_MODAL = ModalSpec(
    modal_id="xp.givexp_form",
    title="Give XP",                              # shipped modal title
    fields=(
        ModalFieldSpec(field_id="user", label="Member (mention or id)",
                       placeholder="@member or 123456789", required=True,
                       max_length=40),
        ModalFieldSpec(field_id="amount", label="Amount of XP",
                       placeholder="e.g. 100", required=True, max_length=10),
    ),
    on_submit=WorkflowRef("xp.award"),
)

RESETXP_MODAL = ModalSpec(
    modal_id="xp.resetxp_form",
    title="Reset a member's XP",                  # shipped modal title
    fields=(
        ModalFieldSpec(field_id="user", label="Member (mention or id)",
                       placeholder="@member or 123456789", required=True,
                       max_length=40),
    ),
    on_submit=WorkflowRef("xp.reset"),
)


def _ensure_hub_provider() -> ProviderRef:
    ref = ProviderRef(_HUB_PROVIDER)
    if not is_registered(ref):
        @provider(_HUB_PROVIDER)
        async def hub_overview(ctx: object):
            from sb.domain.xp import service, store
            from sb.domain.xp.levels import level_progress

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            user_id = int(getattr(getattr(ctx, "actor", None), "user_id", 0)
                          or 0)
            fields = []
            if user_id:
                row = await store.get_xp(user_id, guild_id)
                level, current, needed = level_progress(int(row["xp"]))
                fields.append(("Your rank",
                               f"Level **{level}** · {row['xp']} XP · "
                               f"{current}/{needed} into the next level"))
                fields.append(("Messages", str(row["messages"])))
            xp_min, xp_max, cooldown = await service.xp_config(guild_id)
            fields.append(("Chat awards",
                           f"{xp_min}–{xp_max} XP per message · "
                           f"{cooldown}s cooldown"))
            channel_id = await service.bound_announce_channel(guild_id)
            fields.append(("Level-up channel",
                           f"<#{channel_id}>" if channel_id
                           else "*(same channel as the message)*"))
            return tuple(fields)
    return ref


def xp_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="xp.hub",
        subsystem="xp",
        title="🏆 XP Panel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(
            TextBlock("Chat to earn XP and level up. `!rank` shows your "
                      "card; admins configure via the settings hub."),
            FieldsBlock(provider=_ensure_hub_provider()),
        ),
        actions=(
            PanelActionSpec(
                action_id="rank", label="My Rank", emoji="📊",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("xp.rank_view")),
            PanelActionSpec(
                action_id="config", label="Configure", emoji="⚙️",
                audience_tier="",                 # ADMIN floor (shipped)
                handler=HandlerRef("xp.xpconfig_view")),
            PanelActionSpec(
                action_id="givexp", label="Give XP", emoji="🎁",
                audience_tier="",                 # ADMIN floor (shipped)
                defer_mode=DeferMode.MODAL,
                modal=GIVEXP_MODAL,
                handler=WorkflowRef("xp.award"),
                audit="xp.awarded"),
            PanelActionSpec(
                action_id="resetxp", label="Reset XP", emoji="🔄",
                style=ActionStyle.DANGER, audience_tier="",
                destructive=True,
                defer_mode=DeferMode.MODAL,
                modal=RESETXP_MODAL,
                confirm=ConfirmationSpec(reversibility="irreversible",
                                         challenge=Challenge.TYPED_PHRASE),
                handler=WorkflowRef("xp.reset"),
                audit="xp.reset"),
        ),
        navigation=NavigationSpec(),
        # the shipped `_XpHubView` is an ephemeral timeout view (views/xp/
        # __init__.py: "all views here are ephemeral, timeout-based") —
        # session lifecycle: run-minted ids, never in panel_anchors
        # (goldens/xp/sweep_xpmenu pins the no-anchor-row delta).
        session_lifecycle=True,
        renderer_override=HandlerRef("xp.render_hub"),
        justification=(
            "the shipped hub send carries the invoker's rank image card "
            "as the message attachment `rank.png` (views/xp/main_panel.py "
            "build_response — the visual card-engine H3 surface, oracle "
            "PR #1413) — attachments are outside the grammar's block "
            "vocabulary; goldens/xp/sweep_xpmenu.json pins the multipart "
            "send shape ({\"_files\": [\"rank.png\"]}) and the preceding "
            "avatar `get_from_cdn` read. The override delegates to the "
            "grammar renderer and adds ONLY the attachment (avatar fetch "
            "+ placeholder card bytes — rank_card.py); embed, fields, "
            "actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("rank", "config"),
            ("givexp", "resetxp"),                # danger never row 0
        )),)),
    )


def rank_card_spec() -> PanelSpec:
    """The `!rank` image-card send (utils/rank_render.py, oracle PR
    #1401) — a zero-action session panel: the shipped reply was a plain
    channel message carrying the `rank.png` attachment (no view, no
    anchor row); goldens/xp/xp_chat_award.json pins the send shape."""
    return PanelSpec(
        panel_id="xp.rank_card",
        subsystem="xp",
        title="",
        audience=Audience.INVOKER,
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("xp.rank_card_render"),
        justification=(
            "the shipped `!rank` reply is the rank image card sent as "
            "the message attachment `rank.png` (utils/rank_render.py "
            "over services/xp_helpers.build_rank_response) — attachments "
            "are outside the grammar's block vocabulary; goldens/xp/"
            "xp_chat_award.json pins the multipart send shape "
            "({\"_files\": [\"rank.png\"]}) and the preceding avatar "
            "`get_from_cdn` read. Zero components; the renderer composes "
            "only the attachment (the utility.profile_card precedent)."),
    )


# --- renderer overrides (see the specs' justifications) --------------------------

async def _attach_rank_card(rendered: object, ctx: object) -> object:
    """Fetch the avatar (the goldens' ``get_from_cdn`` read) and ride the
    rank card on the rendered panel — the shipped H3 attachment seam."""
    from dataclasses import replace as _dc_replace

    from sb.domain.xp import service
    from sb.domain.xp.rank_card import RANK_CARD_FILENAME, render_rank_card
    from sb.kernel.panels.render import RenderedAttachment

    params = getattr(ctx, "params", {}) or {}
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    user_id = int(params.get("rank_target")
                  or getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    avatar = await service.fetch_avatar_png(user_id, guild_id)
    png = render_rank_card(user_id, guild_id,
                           stat=str(params.get("rank_stat", "both")),
                           avatar_png=avatar)
    return _dc_replace(
        rendered,
        attachments=(RenderedAttachment(filename=RANK_CARD_FILENAME,
                                        data=png),))


async def _render_hub(spec: PanelSpec, ctx: object) -> object:
    """Grammar render + the shipped rank-card attachment (justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return await _attach_rank_card(rendered, ctx)


async def _render_rank_card(spec: PanelSpec, ctx: object) -> object:
    """The bare card send — empty embed + the attachment (the multipart
    collapse leaves only the filename on the wire; profile_card
    precedent)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    rendered = RenderedPanel(
        panel_id=spec.panel_id,
        embed=RenderedEmbed(title="", description=""),
        invoker_lock=getattr(getattr(ctx, "actor", None), "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)
    return await _attach_rank_card(rendered, ctx)


@panel("xp.hub")
def _hub_factory() -> PanelSpec:
    return xp_hub_spec()


@panel("xp.rank_card")
def _rank_card_factory() -> PanelSpec:
    return rank_card_spec()


def install_xp_panels() -> PanelSpec:
    spec = xp_hub_spec()
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def _register_renderers() -> None:
    from sb.spec.refs import handler as _handler

    if not is_registered(HandlerRef("xp.render_hub")):
        _handler("xp.render_hub")(_render_hub)
    if not is_registered(HandlerRef("xp.rank_card_render")):
        _handler("xp.rank_card_render")(_render_rank_card)


_register_renderers()


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_provider()
    _register_renderers()
    if not _is(_P("xp.hub")):
        _panel("xp.hub")(_hub_factory)
    if not _is(_P("xp.rank_card")):
        _panel("xp.rank_card")(_rank_card_factory)
