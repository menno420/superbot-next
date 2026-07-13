"""The CHANNEL management hub panel (parity flip) — the shipped
``_ChannelManagerView`` (disbot/views/channels/main_panel.py): the 🛠️
blurple embed (``CHANNEL_COLOR`` = discord.Color.blurple(); the shipped
four-line action legend, verbatim) over the shipped action rows — Create /
Delete / Manage Restrictions + Move-Reorder / Subsystem Visibility, each
button carrying its emoji as a SEPARATE component field (the shipped
``discord.ui.button(emoji=...)`` wire shape) — plus the shipped standard
nav row (``nav:help`` + ``nav:hub:admin`` "↩ Administration"; the channel
stack's shipped parent hub is ``admin`` — docs/help-command-surface-map.md
"hub child (Admin)"). ``parity/goldens/channel/sweep_channelmenu.json``
pins every byte.

The shipped view was a timeout-bound session view (``HubView`` family,
author-locked, the root of the channels navigation stack), so
``session_lifecycle=True``: the action buttons get run-minted custom_ids
(engine ``_mint_ephemeral`` → the Normalizer's ``<cid:N>``), no
``panel_anchors`` row — while the nav row keeps its literal ids (the
golden pins ``nav:help``/``nav:hub:admin`` next to five ``<cid:N>``s).

The shipped sub-panels (_CreateSubView / _DeleteSubView /
_RestrictSubView / _MoveSubView / _VisibilitySubView +
_SubsystemToggleView — disbot/views/channels/) are LIVE below
(2026-07-13 operator-hub edits B — the D-0030 named successor): each hub
click opens its sub-panel; commits run the audited command-twin lanes
(sb/domain/channel/handlers.py). Two oracle legs whose port verbs do not
exist yet answer honest declared refusals (Send to Top/Bottom — no
reorder verb; the create-NEW-category preset leg — no category-create
verb; existing categories are live).
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.confirmation import ConfirmationSpec
from sb.spec.panels import (
    ActionStyle,
    Audience,
    DeferMode,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    ModalFieldSpec,
    ModalSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "channel_hub_spec",
    "create_spec",
    "delete_spec",
    "ensure_panel_refs",
    "info_card_spec",
    "install_channel_panels",
    "list_card_spec",
    "move_spec",
    "restrict_spec",
    "visibility_grid_spec",
    "visibility_spec",
]

# the shipped panel copy (main_panel.build_embed — the golden pins every
# byte; description verbatim from the oracle, four legend lines for the
# five buttons: the shipped embed never listed Subsystem Visibility).
_DESCRIPTION = (
    "Select an action below to manage your server's channels.\n\n"
    "**➕ Create Channel** — interactive channel creator\n"
    "**🗑️ Delete Channel** — select and delete a channel\n"
    "**🔒 Manage Restrictions** — lock or unlock a channel\n"
    "**↔️ Move / Reorder** — bulk-move channels or send to top/bottom"
)

#: the shipped footer literal (main_panel.build_embed ``set_footer``) —
#: outside FooterMode's vocabulary, hence the renderer_override below
#: (the utility/ux_lab-panel precedent).
_FOOTER = "Only the command author can interact with this panel."


def _action(action_id: str, label: str, emoji: str, *,
            style: ActionStyle) -> PanelActionSpec:
    """One shipped action button — separate-emoji wire shape; each click
    opens its ported sub-panel (the D-0030 named successor landed —
    2026-07-13 operator-hub edits B)."""
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji, style=style,
        audience_tier="administrator",      # the shipped operator-hub gate
        handler=PanelRef(f"channel.{action_id}"))


def channel_hub_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="channel.hub",
        subsystem="channel",
        title="🛠️ Channel Management Panel",
        # the shipped view was author-locked to ctx.author (HubView).
        audience=Audience.INVOKER,
        # CHANNEL_COLOR = discord.Color.blurple() — the shipped accent.
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(_DESCRIPTION),),
        actions=(
            # row 0 — the shipped Create (green) / Delete (red) /
            # Restrictions (blurple) trio.
            _action("create", "Create Channel", "➕",
                    style=ActionStyle.SUCCESS),
            _action("delete", "Delete Channel", "🗑️",
                    style=ActionStyle.DANGER),
            _action("restrict", "Manage Restrictions", "🔒",
                    style=ActionStyle.PRIMARY),
            # row 1 — Move/Reorder (blurple) + Subsystem Visibility (grey).
            _action("move", "Move / Reorder", "↔️",
                    style=ActionStyle.PRIMARY),
            _action("visibility", "Subsystem Visibility", "🔍",
                    style=ActionStyle.SECONDARY),
        ),
        # the shipped _ChannelManagerView carried the standard nav row —
        # 📚 Help (nav:help) + ↩ Administration (nav:hub:admin; the
        # shipped parent hub is `admin`, pinned explicitly until the admin
        # hub's own band installs a resolver — the ux_lab precedent).
        navigation=NavigationSpec(home_hub="admin"),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.render_hub"),
        justification=(
            "the shipped panel footer is the literal author-lock notice "
            "'Only the command author can interact with this panel.' "
            "(main_panel.build_embed set_footer) — outside FooterMode's "
            "none/subsystem/provenance vocabulary "
            "(goldens/channel/sweep_channelmenu pins the byte; the "
            "utility/ux_lab-panel precedent). The override delegates to "
            "the grammar renderer and replaces ONLY the footer; body, "
            "actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("create", "delete", "restrict"),
            ("move", "visibility"),
        )),)),
    )


# --- the shipped read-only info embeds (the D-0030 batch re-home) -----------------
#
# The utility param-card pattern (#255): the shipped `!channelinfo` /
# `!list` embeds are composed at the command body from live gateway
# reads, so the handler owns every byte and the renderer only assembles.
# Zero components, timeout-free plain sends — modeled as zero-action
# session panels (never minted, never anchored).

def _info_card_spec(panel_id: str, style_token: str,
                    pinned_by: str) -> PanelSpec:
    return PanelSpec(
        panel_id=panel_id,
        subsystem="channel",
        title="",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token=style_token,
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef(f"{panel_id}_render"),
        justification=(
            "the shipped embed copy is live-data-parameterized (gateway "
            "channel/category reads at send time — cogs/channel_cog.py); "
            f"grammar TextBlocks are static ({pinned_by} pins the "
            "bytes). Zero components; the renderer composes only the "
            "embed."),
    )


def info_card_spec() -> PanelSpec:
    """The shipped ``!channelinfo`` embed (channel_cog.channel_info —
    WARNING_COLOR yellow; goldens/channel/sweep_channelinfo pins the
    bytes)."""
    return _info_card_spec("channel.info_card", "yellow",
                           "goldens/channel/sweep_channelinfo")


def list_card_spec() -> PanelSpec:
    """The shipped ``!list`` categories+channels embed
    (channel_cog.list_channels over views/channels/list_panel.py —
    INFO_COLOR blue; goldens/channel/sweep_list pins the bytes)."""
    return _info_card_spec("channel.list_card", "blue",
                           "goldens/channel/sweep_list")


# --- renderer overrides -----------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed, footer=_FOOTER))


async def _render_param_card(spec: PanelSpec, ctx) -> object:
    """The shared param-driven info card (the utility #255 pattern):
    title/description/fields arrive as open params; the accent rides the
    spec's style_token (WARNING_COLOR yellow / INFO_COLOR blue). Discord
    hard limits are enforced HERE because the override path bypasses the
    grammar renderer's budget clamps (render._clamp semantics mirrored:
    ellipsis truncation; 25-field cap) — a big guild's `!list` must not
    mint an invalid embed. The pinned goldens sit far under every limit,
    so the clamp is byte-inert for them."""
    from sb.kernel.panels.render import (
        DESCRIPTION_LIMIT,
        FIELD_NAME_LIMIT,
        FIELD_VALUE_LIMIT,
        TITLE_LIMIT,
        RenderedEmbed,
        RenderedPanel,
    )

    def _cl(text: object, limit: int) -> str:
        out = str(text)
        if len(out) <= limit:
            return out
        return out[: max(limit - 1, 0)] + "…"

    params = getattr(ctx, "params", {}) or {}
    raw = tuple(tuple(f) for f in params.get("card_fields", ()) or ())[:25]
    fields = tuple((_cl(f[0], FIELD_NAME_LIMIT),
                    _cl(f[1], FIELD_VALUE_LIMIT), *f[2:]) for f in raw)
    embed = RenderedEmbed(
        title=_cl(params.get("card_title", "") or "", TITLE_LIMIT),
        description=_cl(params.get("card_description", "") or "",
                        DESCRIPTION_LIMIT),
        fields=fields,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- the shipped sub-panels (operator-hub edits B — D-0030 successor) -------------
#
# disbot/views/channels/{create,delete,restrict,move,visibility}_panel.py
# as declared grammar. Session views (run-minted ids — no sub-panel was
# ever captured, so no custom-id pin exists to honor); the selects keep
# per-(guild,invoker) pick memory in sb/domain/channel/handlers.py (the
# diagnostic #331 precedent) and re-open fresh (the projmoon class); the
# state fields ("Selected channels: …") ride renderer overrides reading
# that pick memory. Copy is oracle-verbatim throughout.

#: the shipped ✏️ Custom Name modal (_CustomNameModal, verbatim).
CREATE_NAME_MODAL = ModalSpec(
    modal_id="channel.create_name_form", title="Custom Channel Name",
    fields=(ModalFieldSpec(field_id="channel_name", label="Channel name",
                           placeholder="e.g. my-channel", required=True,
                           max_length=100),),
    on_submit=HandlerRef("channel.create_name_form_submit"))

#: the shipped name presets (views/channels/_helpers.py, verbatim).
NAME_PRESETS: tuple[str, ...] = (
    "general", "gaming", "announcements", "events", "tournament",
    "support", "bot-commands", "vc-lounge")


async def _name_preset_options(ctx) -> tuple[dict, ...]:
    del ctx
    return tuple({"label": p, "value": p} for p in NAME_PRESETS)


async def _channel_options(ctx) -> tuple[dict, ...]:
    """The shipped `_build_channel_options` roster (text channels off the
    gateway cache — the ChannelDirectory port); an unarmed directory
    degrades to the selector's empty state, never a crash."""
    from sb.domain.channel import service

    try:
        snaps = await service.active_directory().list_channels(
            int(getattr(ctx, "guild_id", 0) or 0))
    except RuntimeError:
        return ()
    return tuple({"label": f"#{s.name}"[:100], "value": str(s.channel_id),
                  "description": f"ID: {s.channel_id}"}
                 for s in snaps if s.kind not in ("category",))


async def _category_options(ctx) -> tuple[dict, ...]:
    """EXISTING categories ('— No category —' first). The shipped
    new-category presets ride the category-create port verb (named
    successor — flagged in the create sub-panel docstring)."""
    from sb.domain.channel import service

    out = [{"label": "— No category —", "value": "0"}]
    try:
        snaps = await service.active_directory().list_channels(
            int(getattr(ctx, "guild_id", 0) or 0))
    except RuntimeError:
        return tuple(out)
    out.extend({"label": s.name[:100], "value": str(s.channel_id),
                "description": "Existing category"}
               for s in snaps if s.kind == "category")
    return tuple(out)


def _channel_multi_selector(selector_id: str, handler_name: str,
                            placeholder: str) -> SelectorSpec:
    return SelectorSpec(
        selector_id=selector_id, kind=SelectorKind.ENUM,
        options_source=ProviderRef("channel.roster_options"),
        placeholder=placeholder, min_values=1, max_values=25,
        empty_state="No channels available (gateway directory unarmed).",
        audience_tier="administrator",
        on_select=HandlerRef(handler_name))


def create_spec() -> PanelSpec:
    """➕ Create Channel (_CreateSubView): preset multi-name picker +
    single category + ✏️ Custom Name modal + ✅ Create + ❌ Cancel."""
    return PanelSpec(
        panel_id="channel.create",
        subsystem="channel",
        title="➕ Create Channel",
        audience=Audience.INVOKER,
        # SUCCESS_COLOR green (the shipped create accent).
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        body=(TextBlock(
            # the shipped description, verbatim (_CreateSubView.build_embed)
            "Pick one or more names and a category, then press "
            "**Create Channel**.\n"
            "Click **Custom Name** to add your own name to the set."),),
        selectors=(
            SelectorSpec(
                selector_id="create_names", kind=SelectorKind.ENUM,
                options_source=ProviderRef("channel.name_preset_options"),
                placeholder="Pick one or more channel names…",
                min_values=0, max_values=len(NAME_PRESETS),
                audience_tier="administrator",
                on_select=HandlerRef("channel.create_pick_names")),
            SelectorSpec(
                selector_id="create_category", kind=SelectorKind.ENUM,
                options_source=ProviderRef("channel.category_options"),
                placeholder="Pick a category…",
                audience_tier="administrator",
                on_select=HandlerRef("channel.create_pick_category")),
        ),
        actions=(
            PanelActionSpec(
                action_id="create_custom", label="Custom Name", emoji="✏️",
                audience_tier="administrator",
                defer_mode=DeferMode.MODAL, modal=CREATE_NAME_MODAL,
                handler=HandlerRef("channel.create_name_form_submit")),
            PanelActionSpec(
                action_id="create_commit", label="Create Channel",
                emoji="✅", style=ActionStyle.SUCCESS,
                audience_tier="administrator",
                handler=HandlerRef("channel.create_commit"),
                audit="channel.audit_logged"),
            PanelActionSpec(
                action_id="create_cancel", label="Cancel", emoji="❌",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=PanelRef("channel.hub")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.create_render"),
        justification=(
            "the shipped sub-panel embed carries the live selection state "
            "('Selected names' / 'Selected category' fields off the "
            "operator's picks — _CreateSubView.build_embed); state-keyed "
            "fields are outside the grammar's static-block vocabulary "
            "(the diagnostic flag-manager pick-aware renderer precedent). "
            "The override delegates to the grammar renderer and adds ONLY "
            "those fields."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("create_names",),
            ("create_category",),
            ("create_custom", "create_commit", "create_cancel"),
        )),)),
    )


def delete_spec() -> PanelSpec:
    """🗑️ Delete Channel (_DeleteSubView): multi-select + the declared
    irreversible confirm (the kernel's confirm-as-second-dispatch stands
    in for the shipped _DeleteConfirmView's explicit step)."""
    return PanelSpec(
        panel_id="channel.delete",
        subsystem="channel",
        title="🗑️ Delete Channel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="red", footer_mode=FooterMode.NONE),
        body=(TextBlock(
            "Select one or more channels to delete, then press "
            "**Delete Selected**."),),
        selectors=(
            _channel_multi_selector(
                "delete_pick", "channel.delete_pick",
                "Select one or more channels to delete…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="delete_commit", label="Delete Selected",
                emoji="🗑️", style=ActionStyle.DANGER,
                audience_tier="administrator", destructive=True,
                confirm=ConfirmationSpec(reversibility="irreversible"),
                handler=HandlerRef("channel.delete_commit"),
                audit="channel.audit_logged"),
            PanelActionSpec(
                action_id="delete_cancel", label="↩️ Back",
                audience_tier="administrator",
                handler=PanelRef("channel.hub")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.delete_render"),
        justification=(
            "the shipped sub-panel embed carries the live selection state "
            "('Selected channels' field — _DeleteSubView.build_embed); "
            "state-keyed fields are outside the grammar's static-block "
            "vocabulary (the flag-manager precedent). The override "
            "delegates and adds ONLY that field."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("delete_pick",),
            ("delete_cancel", "delete_commit"),
        )),)),
    )


def restrict_spec() -> PanelSpec:
    """🔒 Manage Restrictions (_RestrictSubView): multi-select + the
    Lock/Unlock pair over the lock/unlock twins' overwrite masks."""
    return PanelSpec(
        panel_id="channel.restrict",
        subsystem="channel",
        title="🔒 Manage Restrictions",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            # shipped verbatim (_RestrictSubView.build_embed)
            "Select one or more channels, then choose a restriction "
            "action.\n\n"
            "**🔒 Lock** — disable send messages for @everyone\n"
            "**🔓 Unlock** — restore send messages for @everyone"),),
        selectors=(
            _channel_multi_selector(
                "restrict_pick", "channel.restrict_pick",
                "Select one or more channels to manage…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="restrict_lock", label="Lock", emoji="🔒",
                style=ActionStyle.DANGER, audience_tier="administrator",
                handler=HandlerRef("channel.restrict_lock"),
                audit="channel.audit_logged"),
            PanelActionSpec(
                action_id="restrict_unlock", label="Unlock", emoji="🔓",
                style=ActionStyle.SUCCESS, audience_tier="administrator",
                handler=HandlerRef("channel.restrict_unlock"),
                audit="channel.audit_logged"),
            PanelActionSpec(
                action_id="restrict_back", label="↩️ Back",
                audience_tier="administrator",
                handler=PanelRef("channel.hub")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.restrict_render"),
        justification=(
            "the shipped sub-panel embed carries the live selection state "
            "('Selected channels' field — _RestrictSubView.build_embed); "
            "state-keyed fields are outside the grammar's static-block "
            "vocabulary (the flag-manager precedent). The override "
            "delegates and adds ONLY that field."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("restrict_pick",),
            ("restrict_lock", "restrict_unlock"),
            ("restrict_back",),
        )),)),
    )


def move_spec() -> PanelSpec:
    """↔️ Move / Reorder (_MoveSubView): channel multi-select +
    destination category + Move / Send to Top / Send to Bottom."""
    return PanelSpec(
        panel_id="channel.move",
        subsystem="channel",
        title="↔️ Move / Reorder Channels",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            # shipped verbatim (_MoveSubView.build_embed)
            "Select channels, then **Move to Category** (pick a "
            "destination above) or **Send to Top / Bottom**."),),
        selectors=(
            _channel_multi_selector(
                "move_pick", "channel.move_pick_channels",
                "Select channels to move / reorder…"),
            SelectorSpec(
                selector_id="move_category", kind=SelectorKind.ENUM,
                options_source=ProviderRef("channel.move_category_options"),
                placeholder="Destination category (for Move)…",
                audience_tier="administrator",
                on_select=HandlerRef("channel.move_pick_category")),
        ),
        actions=(
            PanelActionSpec(
                action_id="move_commit", label="Move to Category",
                emoji="📁", style=ActionStyle.PRIMARY,
                audience_tier="administrator",
                handler=HandlerRef("channel.move_commit"),
                audit="channel.audit_logged"),
            PanelActionSpec(
                action_id="move_top", label="Send to Top", emoji="⬆️",
                audience_tier="administrator",
                handler=HandlerRef("channel.move_reorder")),
            PanelActionSpec(
                action_id="move_bottom", label="Send to Bottom", emoji="⬇️",
                audience_tier="administrator",
                handler=HandlerRef("channel.move_reorder")),
            PanelActionSpec(
                action_id="move_back", label="↩️ Back",
                audience_tier="administrator",
                handler=PanelRef("channel.hub")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.move_render"),
        justification=(
            "the shipped sub-panel embed carries the live selection state "
            "('Selected channels' + 'Move destination' fields — "
            "_MoveSubView.build_embed); state-keyed fields are outside "
            "the grammar's static-block vocabulary (the flag-manager "
            "precedent). The override delegates and adds ONLY those "
            "fields."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("move_pick",),
            ("move_category",),
            ("move_commit", "move_top", "move_bottom"),
            ("move_back",),
        )),)),
    )


def visibility_spec() -> PanelSpec:
    """🔍 Subsystem Visibility stage 1 (_VisibilitySubView): channel
    multi-select + ⚙️ Configure Selected → the toggle grid."""
    return PanelSpec(
        panel_id="channel.visibility",
        subsystem="channel",
        title="🔍 Subsystem Visibility",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            # shipped verbatim (_VisibilitySubView.build_embed)
            "Select one or more channels, then press **Configure "
            "Selected** to set which subsystems are visible there.\n\n"
            "**Green** = enabled  •  **Red** = disabled  •  **Grey** = "
            "inherit  •  **Blue** = mixed across the selection\n\n"
            "_Use ◀/▶ to page through channels. Category and guild-scope "
            "controls coming soon._"),),
        selectors=(
            _channel_multi_selector(
                "visibility_pick", "channel.visibility_pick",
                "Select one or more channels to configure…"),
        ),
        actions=(
            PanelActionSpec(
                action_id="visibility_configure", label="Configure Selected",
                emoji="⚙️", style=ActionStyle.PRIMARY,
                audience_tier="administrator",
                handler=HandlerRef("channel.visibility_configure")),
            PanelActionSpec(
                action_id="visibility_back", label="↩ Back",
                audience_tier="administrator",
                handler=PanelRef("channel.hub")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.hub")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.visibility_render"),
        justification=(
            "the shipped sub-panel embed carries the live selection state "
            "('Selected channels' field — _VisibilitySubView.build_embed); "
            "state-keyed fields are outside the grammar's static-block "
            "vocabulary (the flag-manager precedent). The override "
            "delegates and adds ONLY that field."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("visibility_pick",),
            ("visibility_configure", "visibility_back"),
        )),)),
    )


def visibility_grid_spec() -> PanelSpec:
    """🔍 Subsystem Visibility stage 2 (_SubsystemToggleView): the
    20-toggle tri-state grid over the oracle-extracted capture roster
    (sb/domain/channel/visibility.py GRID_SUBSYSTEMS); the live
    aggregate glyphs/styles ride the renderer override."""
    from sb.domain.channel.visibility import GRID_SUBSYSTEMS

    actions = tuple(
        PanelActionSpec(
            action_id=f"vis_{sub}", label=display,
            audience_tier="administrator",
            handler=HandlerRef(f"channel.vis_toggle_{sub}"),
            audit="channel.audit_logged")
        for sub, display in GRID_SUBSYSTEMS)
    keys = [f"vis_{sub}" for sub, _ in GRID_SUBSYSTEMS]
    rows = tuple(tuple(keys[i:i + 5]) for i in range(0, len(keys), 5))
    return PanelSpec(
        panel_id="channel.visibility_grid",
        subsystem="channel",
        title="🔍 Subsystem Visibility",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        body=(TextBlock(
            # shipped verbatim (_SubsystemToggleView.build_embed legend)
            "**✓ Green** = force enabled  •  **✗ Red** = force disabled  "
            "•  **~ Grey** = inherit  •  **± Blue** = mixed across "
            "channels\n_Clicking forces every selected channel to the "
            "next state._"),),
        actions=actions + (
            PanelActionSpec(
                action_id="vis_grid_back", label="↩ Back",
                audience_tier="administrator",
                handler=PanelRef("channel.visibility")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False,
                                  parent=PanelRef("channel.visibility")),
        session_lifecycle=True,
        renderer_override=HandlerRef("channel.visibility_grid_render"),
        justification=(
            "the shipped toggle grid renders each button's label/style "
            "off the LIVE per-channel aggregate (✓/✗/~/± glyph + "
            "green/red/grey/blurple style — _SubsystemToggleView."
            "_rebuild_buttons) and titles off the picked channel count — "
            "state-keyed presentation outside the grammar's static "
            "vocabulary (the cogmgr footer/disabled precedent). The "
            "override delegates to the grammar renderer and adjusts ONLY "
            "those surfaces."),
        layout=LayoutSpec(pages=(PageSpec(
            rows=rows + (("vis_grid_back",),)),)),
    )


# --- the sub-panel renderer overrides (state fields off the pick memory) ----------

def _selected_field(names: list[str]) -> tuple[str, str]:
    """The shipped 'Selected channel(s)' field (every sub-view's
    build_embed, verbatim byte shape)."""
    return (f"Selected channel{'s' if len(names) != 1 else ''}",
            (", ".join(f"`{n}`" for n in names) if names else "*(none)*"))


async def _pick_names(ctx, panel: str) -> list[str]:
    from sb.domain.channel import handlers, service

    pick = handlers.picks_for(getattr(ctx, "guild_id", 0),
                              getattr(ctx.actor, "user_id", 0), panel)
    ids = list(pick.get("ids", ()))
    if not ids:
        return []
    try:
        snaps = {int(s.channel_id): f"#{s.name}"
                 for s in await service.active_directory().list_channels(
                     int(getattr(ctx, "guild_id", 0) or 0))}
    except RuntimeError:
        snaps = {}
    return [snaps.get(int(cid), str(cid)) for cid in ids]


def _make_picker_renderer(panel_key: str):
    async def _render(spec: PanelSpec, ctx) -> object:
        from sb.kernel.panels.render import render_panel

        rendered = await render_panel(spec, ctx)
        fields = rendered.embed.fields + (_selected_field(
            await _pick_names(ctx, panel_key)),)
        return _dc_replace(rendered,
                           embed=_dc_replace(rendered.embed, fields=fields))
    return _render


async def _render_create(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped 'Selected name(s)' / 'Selected
    category' state fields (_CreateSubView.build_embed)."""
    from sb.domain.channel import handlers
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    pick = handlers.picks_for(getattr(ctx, "guild_id", 0),
                              getattr(ctx.actor, "user_id", 0), "create")
    names: list[str] = []
    for n in [*pick.get("presets", ()), *pick.get("customs", ())]:
        if n not in names:
            names.append(n)
    fields = rendered.embed.fields + (
        (f"Selected name{'s' if len(names) != 1 else ''}",
         (", ".join(f"`{n}`" for n in names) if names else "*(none)*")),
        ("Selected category",
         (f"`{pick['category_name']}`" if pick.get("category_name")
          else "*(none)*"), True),
    )
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, fields=fields))


async def _render_move(spec: PanelSpec, ctx) -> object:
    from sb.domain.channel import handlers
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    pick = handlers.picks_for(getattr(ctx, "guild_id", 0),
                              getattr(ctx.actor, "user_id", 0), "move")
    fields = rendered.embed.fields + (_selected_field(
        await _pick_names(ctx, "move")),)
    if pick.get("category_chosen"):
        fields += (("Move destination",
                    f"`{pick.get('category_name') or pick.get('category_id')}`"),)
    return _dc_replace(rendered,
                       embed=_dc_replace(rendered.embed, fields=fields))


async def _render_visibility_grid(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped live-aggregate glyphs/styles and the
    picked-channel title/description (_SubsystemToggleView)."""
    from sb.domain.channel import handlers
    from sb.domain.channel.visibility import (
        GRID_SUBSYSTEMS,
        aggregate_state,
        channel_visibility_rows,
        grid_label,
    )
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    gid = int(getattr(ctx, "guild_id", 0) or 0)
    pick = handlers.picks_for(gid, getattr(ctx.actor, "user_id", 0),
                              "visibility")
    ids = list(pick.get("ids", ()))
    rows = await channel_visibility_rows(gid, ids)
    display_by_key = dict(GRID_SUBSYSTEMS)
    components = []
    for c in rendered.components:
        leaf = c.custom_id.rsplit(".", 1)[-1]
        if leaf.startswith("vis_") and leaf != "vis_grid_back":
            sub = leaf[len("vis_"):]
            if sub in display_by_key:
                label, style = grid_label(
                    display_by_key[sub], aggregate_state(rows, sub))
                c = _dc_replace(c, label=label, style=style)
        components.append(c)
    names = await _pick_names(ctx, "visibility")
    count = len(ids)
    title = (f"🔍 Subsystem Visibility — {count} "
             f"channel{'s' if count != 1 else ''}")
    description = (
        f"Toggling applies to: "
        f"{', '.join(f'`{n}`' for n in names) if names else '*(none)*'}\n\n"
        + rendered.embed.description)
    return _dc_replace(
        rendered, components=tuple(components),
        embed=_dc_replace(rendered.embed, title=title,
                          description=description))


# --- registration -----------------------------------------------------------------

_SPECS = {
    "channel.hub": channel_hub_spec,
    "channel.info_card": info_card_spec,
    "channel.list_card": list_card_spec,
    "channel.create": create_spec,
    "channel.delete": delete_spec,
    "channel.restrict": restrict_spec,
    "channel.move": move_spec,
    "channel.visibility": visibility_spec,
    "channel.visibility_grid": visibility_grid_spec,
}

_PROVIDERS = {
    "channel.name_preset_options": _name_preset_options,
    "channel.roster_options": _channel_options,
    "channel.category_options": _category_options,
    "channel.move_category_options": _category_options,
}

_RENDERERS = {
    "channel.render_hub": _render_hub,
    "channel.info_card_render": _render_param_card,
    "channel.list_card_render": _render_param_card,
    "channel.create_render": _render_create,
    "channel.delete_render": _make_picker_renderer("delete"),
    "channel.restrict_render": _make_picker_renderer("restrict"),
    "channel.move_render": _render_move,
    "channel.visibility_render": _make_picker_renderer("visibility"),
    "channel.visibility_grid_render": _render_visibility_grid,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _PROVIDERS.items():
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)


_register_refs()


def install_channel_panels() -> tuple[PanelSpec, ...]:
    out = []
    for factory in _SPECS.values():
        spec = factory()
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    _register_refs()
