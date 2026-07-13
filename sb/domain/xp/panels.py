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

__all__ = ["ensure_panel_refs", "install_xp_panels", "import_scan_spec",
           "rank_card_spec", "xp_config_spec", "xp_hub_spec"]

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


_CONFIG_PROVIDER = "xp.config_overview"

# The shipped config buttons open settings modals (_XpRangeModal /
# _XpCooldownModal / _XpChannelModal, disbot/views/xp/modals.py); the
# 2026-07-13 curation rework (backlog slice 1) arms them as G-10 modal
# ingresses over the live K7 lanes — settings.set_scalar for the two
# scalar keys, settings.bind/unbind for the announce-channel pointer
# (P0-3 binding lane) — the cleanup-words / moderation.hub.warn
# modal-ingress precedent. The import button's shipped target is the
# select-driven XpImportSetupView picker (disbot/views/xp/
# import_panel.py); its modal collects the SAME source/channel/limit
# args the `!xpimport` front door walks and delegates to that live
# flow — the picker's preview/apply half stays the import-preview
# slice's port (the scan's honest BLOCKED boundaries are unchanged).
# No golden clicks these buttons (handler refs are not wire bytes).

XP_RANGE_MODAL = ModalSpec(
    modal_id="xp.range_form",
    title="Set XP Range",                         # shipped modal title
    fields=(
        ModalFieldSpec(field_id="xp_min", label="Min XP per message",
                       placeholder="15", required=True, max_length=4),
        ModalFieldSpec(field_id="xp_max", label="Max XP per message",
                       placeholder="25", required=True, max_length=4),
    ),
    on_submit=HandlerRef("xp.config_range_submit"),
)

XP_COOLDOWN_MODAL = ModalSpec(
    modal_id="xp.cooldown_form",
    title="Set XP Cooldown",                      # shipped modal title
    fields=(
        ModalFieldSpec(field_id="seconds", label="Cooldown in seconds",
                       placeholder="60", required=True, max_length=5),
    ),
    on_submit=HandlerRef("xp.config_cooldown_submit"),
)

XP_CHANNEL_MODAL = ModalSpec(
    modal_id="xp.channel_form",
    title="Level-up Announcement Channel",        # shipped modal title
    fields=(
        ModalFieldSpec(field_id="channel_id",
                       label="Channel ID (leave blank = same channel)",
                       required=False, max_length=25),
    ),
    on_submit=HandlerRef("xp.config_channel_submit"),
)

XP_IMPORT_MODAL = ModalSpec(
    modal_id="xp.import_form",
    title="📥 Import XP from another bot",        # shipped picker title
    fields=(
        # the same three args the `!xpimport` front door walks
        # (usage: !xpimport [source] [#channel] [limit]).
        ModalFieldSpec(field_id="source",
                       label="Which bot posted them? (default: arcane)",
                       placeholder="arcane", required=False,
                       max_length=20),
        ModalFieldSpec(field_id="channel",
                       label="Level-up channel (ID; blank = here)",
                       placeholder="123456789", required=False,
                       max_length=25),
        ModalFieldSpec(field_id="limit",
                       label="Max messages to scan (blank = all)",
                       placeholder="1000", required=False, max_length=6),
    ),
    on_submit=HandlerRef("xp.import_setup_submit"),
)


def _ensure_config_provider() -> ProviderRef:
    """The declared config-field reads (the same service seams the
    override renders inline — the grammar consumer sees real data)."""
    ref = ProviderRef(_CONFIG_PROVIDER)
    if not is_registered(ref):
        @provider(_CONFIG_PROVIDER)
        async def config_overview(ctx: object):
            from sb.domain.xp import service

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            xp_min, xp_max, cooldown = await service.xp_config(guild_id)
            channel_id = await service.bound_announce_channel(guild_id)
            channel_str = (f"<#{channel_id}>" if channel_id
                           else "Same channel as message")
            return (
                ("XP per message", f"{xp_min}–{xp_max}"),
                ("Cooldown", f"{cooldown}s"),
                ("Level-up channel", channel_str),
            )
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


def xp_config_spec() -> PanelSpec:
    """The shipped ``!xpconfig`` panel (disbot/views/xp/config_panel.py
    ``XpConfigView`` + ``build_embed``) — an ephemeral timeout-based admin
    view (run-minted ids, never anchored; goldens/xp/sweep_xpconfig.json
    pins the send: the three blurple setting buttons on row 0, the grey
    import button on row 1, the three inline config fields and the
    "Click a button below…" footer)."""
    return PanelSpec(
        panel_id="xp.config",
        subsystem="xp",
        title="⚙️ XP Configuration",                 # shipped embed title
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue",     # UTILITY_COLOR 3447003
                             footer_mode=FooterMode.NONE),
        body=(FieldsBlock(provider=_ensure_config_provider()),),
        actions=(
            # shipped labels/styles verbatim (@discord.ui.button decorators,
            # config_panel.py). Action ids are subsystem-prefixed — K1
            # claims panel action_ids BARE and cross-subsystem (trap 19);
            # the wire never sees them (session mint => <cid:N>).
            PanelActionSpec(
                action_id="xp_range", label="XP Range",
                style=ActionStyle.PRIMARY,           # ButtonStyle.blurple
                audience_tier="",                    # ADMIN floor (shipped)
                defer_mode=DeferMode.MODAL,
                modal=XP_RANGE_MODAL,
                handler=HandlerRef("xp.config_range_submit")),
            PanelActionSpec(
                action_id="xp_cooldown", label="Cooldown",
                style=ActionStyle.PRIMARY,
                audience_tier="",
                defer_mode=DeferMode.MODAL,
                modal=XP_COOLDOWN_MODAL,
                handler=HandlerRef("xp.config_cooldown_submit")),
            PanelActionSpec(
                action_id="xp_levelup_channel", label="Level-up Channel",
                style=ActionStyle.PRIMARY,
                audience_tier="",
                defer_mode=DeferMode.MODAL,
                modal=XP_CHANNEL_MODAL,
                handler=HandlerRef("xp.config_channel_submit")),
            PanelActionSpec(
                action_id="xp_import", label="📥 Import from another bot",
                style=ActionStyle.SECONDARY,         # ButtonStyle.grey;
                audience_tier="",                    # glyph IN-LABEL (15a)
                defer_mode=DeferMode.MODAL,
                modal=XP_IMPORT_MODAL,
                handler=HandlerRef("xp.import_setup_submit")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        # views/xp/__init__.py: "all views here are ephemeral,
        # timeout-based" — session lifecycle, no panel_anchors row
        # (goldens/xp/sweep_xpconfig pins the anchor-less delta).
        session_lifecycle=True,
        renderer_override=HandlerRef("xp.render_config"),
        justification=(
            "the shipped build_embed renders its three config fields "
            "INLINE and a literal footer (\"Click a button below to "
            "change a setting.\" — disbot/views/xp/config_panel.py); the "
            "grammar's FieldsBlock renders block fields non-inline and "
            "FooterMode has no literal form. The override delegates to "
            "the grammar renderer for every component byte and replaces "
            "ONLY the embed (title/color kept, fields re-rendered inline, "
            "the footer literal added) — the economy wallet-card "
            "delegation shape (#152). goldens/xp/sweep_xpconfig.json pins "
            "the bytes."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("xp_range", "xp_cooldown", "xp_levelup_channel"),   # row 0
            ("xp_import",),                                      # row 1
        )),)),
    )


def import_scan_spec() -> PanelSpec:
    """The shipped ``!xpimport`` scan status message (disbot/cogs/
    xp_cog.py xpimport: the "📥 Scanning…" ctx.send, then the in-place
    ``status.edit`` to the result embed) — a zero-component session panel
    driven send-then-edit like utility.pong; goldens/xp/
    sweep_xpimport.json pins both embeds and the edit wire shape."""
    return PanelSpec(
        panel_id="xp.import_scan",
        subsystem="xp",
        title="📥 Scanning…",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("xp.render_import_scan"),
        justification=(
            "the shipped scan status embed is STATE-DEPENDENT (the "
            "scanning line, then the nothing-to-import / preview result "
            "written over it by status.edit — disbot/cogs/xp_cog.py); "
            "grammar TextBlocks are static, so the override renders the "
            "phase-keyed title/description (the cleanup/proof_channel "
            "state-dependent-description precedent, #145 12c). Zero "
            "components; goldens/xp/sweep_xpimport.json pins both "
            "phases' bytes."),
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


async def _render_config(spec: PanelSpec, ctx: object) -> object:
    """Grammar render for the components; the shipped build_embed bytes
    for the embed (see the spec's justification) — disbot/views/xp/
    config_panel.py verbatim; goldens/xp/sweep_xpconfig.json."""
    from dataclasses import replace as _dc_replace

    from sb.domain.xp import service
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    rendered = await render_panel(spec, ctx)
    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    xp_min, xp_max, cooldown = await service.xp_config(guild_id)
    channel_id = await service.bound_announce_channel(guild_id)
    channel_str = (f"<#{channel_id}>" if channel_id
                   else "Same channel as message")
    embed = RenderedEmbed(
        title="⚙️ XP Configuration",
        description="",
        fields=(
            ("XP per message", f"{xp_min}–{xp_max}", True),
            ("Cooldown", f"{cooldown}s", True),
            ("Level-up channel", channel_str, True),
        ),
        footer="Click a button below to change a setting.",
        style_token="blue")
    return _dc_replace(rendered, embed=embed)


async def _render_import_scan(spec: PanelSpec, ctx: object) -> object:
    """The phase-keyed scan status embed (disbot/cogs/xp_cog.py xpimport
    — the "📥 Scanning…" send, then the status.edit result; goldens/xp/
    sweep_xpimport.json pins both). Zero components by design."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    channel_id = int(params.get("scan_channel_id", 0) or 0)
    label = str(params.get("scan_fmt_label", "") or "")
    if str(params.get("scan_phase", "scanning")) == "empty":
        embed = RenderedEmbed(
            title="Nothing to import",
            description=(
                f"Scanned **{int(params.get('scan_scanned', 0) or 0)}** "
                f"message(s) in <#{channel_id}> but found no **{label}** "
                "level-up announcements. Try a different `source` or "
                "`#channel` — `!xpimport help` lists the formats."),
            style_token="blue")
    else:
        embed = RenderedEmbed(
            title="📥 Scanning…",
            description=f"Reading <#{channel_id}> for **{label}** "
                        "level-ups…",
            style_token="blue")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(getattr(ctx, "actor", None), "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel("xp.hub")
def _hub_factory() -> PanelSpec:
    return xp_hub_spec()


@panel("xp.rank_card")
def _rank_card_factory() -> PanelSpec:
    return rank_card_spec()


@panel("xp.config")
def _config_factory() -> PanelSpec:
    return xp_config_spec()


@panel("xp.import_scan")
def _import_scan_factory() -> PanelSpec:
    return import_scan_spec()


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
    if not is_registered(HandlerRef("xp.render_config")):
        _handler("xp.render_config")(_render_config)
    if not is_registered(HandlerRef("xp.render_import_scan")):
        _handler("xp.render_import_scan")(_render_import_scan)


_register_renderers()


def ensure_panel_refs() -> None:
    from sb.spec.refs import PanelRef as _P
    from sb.spec.refs import is_registered as _is
    from sb.spec.refs import panel as _panel

    _ensure_hub_provider()
    _ensure_config_provider()
    _register_renderers()
    if not _is(_P("xp.hub")):
        _panel("xp.hub")(_hub_factory)
    if not _is(_P("xp.rank_card")):
        _panel("xp.rank_card")(_rank_card_factory)
    if not _is(_P("xp.config")):
        _panel("xp.config")(_config_factory)
    if not _is(_P("xp.import_scan")):
        _panel("xp.import_scan")(_import_scan_factory)
