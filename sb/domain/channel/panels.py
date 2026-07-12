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

Deliberate under-port note (parity beyond the golden): the shipped
sub-panels (_CreateSubView / _DeleteSubView / _RestrictSubView /
_MoveSubView / _VisibilitySubView — disbot/views/channels/) are the
channel-ops Discord-mutation slice (D-0030, the named successor); every
action click lands on the declared + honest pending terminal (the
role/utility-band precedent), never a silent stub.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

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
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, is_registered, panel

__all__ = [
    "channel_hub_spec",
    "channel_info_card_spec",
    "channel_list_card_spec",
    "ensure_panel_refs",
    "install_channel_panels",
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
    """One shipped action button — separate-emoji wire shape; the
    sub-panels port with the channel-ops slice (D-0030), so every click
    lands on the polite pending terminal."""
    return PanelActionSpec(
        action_id=action_id, label=label, emoji=emoji, style=style,
        audience_tier="administrator",      # the shipped operator-hub gate
        handler=HandlerRef(f"channel.{action_id}_pending"))


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


# --- renderer override ------------------------------------------------------------

async def _render_hub(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed, footer=_FOOTER))


# --- the read-command result cards (list / channelinfo) --------------------------
# The shipped ``!list`` / ``!channelinfo`` replies were plain
# ``ctx.send(embed=...)`` sends (channel_cog.py) — no components, no
# panel_anchors rows: modeled as component-less session-lifecycle cards
# (the utility server_info / moderation modlogs_card recipe). The embed is
# fully data-parameterized (the guild channel enumeration / one channel's
# metadata), so a renderer_override composes it from the open params the
# command handler assembled (goldens/channel/sweep_list + sweep_channelinfo
# pin the bytes).

def _card_spec(panel_id: str, title: str, style_token: str) -> PanelSpec:
    return PanelSpec(
        panel_id=panel_id,
        subsystem="channel",
        title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token=style_token,
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef(f"{panel_id}_render"),
        justification=(
            "the shipped embed is data-parameterized (the guild channel "
            "enumeration / one channel's metadata read at send time — "
            "channel_cog.py); grammar TextBlocks are static. Zero "
            "components; the renderer composes only the embed "
            "(goldens/channel/sweep_list + sweep_channelinfo pin the "
            "bytes)."),
    )


def channel_list_card_spec() -> PanelSpec:
    # discord.Color.blue() = 3447003 (goldens/channel/sweep_list pins it).
    return _card_spec("channel.list_card", "Categories and Channels", "blue")


def channel_info_card_spec() -> PanelSpec:
    # discord.Color.yellow() = 16705372 (goldens/channel/sweep_channelinfo
    # pins it); the title interpolates the channel name, so it rides the
    # open params (card_title) rather than the static spec title.
    return _card_spec("channel.info_card", "", "yellow")


async def _render_param_card(spec: PanelSpec, ctx) -> object:
    """renderer_override — assemble the embed from the open params the
    command handler composed (card_title/card_fields), the shared
    param-card recipe (utility._render_param_card)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    fields = tuple(tuple(f) for f in params.get("card_fields", ()) or ())
    embed = RenderedEmbed(
        title=str(params.get("card_title", "") or spec.title or ""),
        description="",
        fields=fields,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- registration -----------------------------------------------------------------

def _register_refs() -> None:
    from sb.spec.refs import handler

    if not is_registered(PanelRef("channel.hub")):
        panel("channel.hub")(channel_hub_spec)
    if not is_registered(HandlerRef("channel.render_hub")):
        handler("channel.render_hub")(_render_hub)
    if not is_registered(PanelRef("channel.list_card")):
        panel("channel.list_card")(channel_list_card_spec)
    if not is_registered(PanelRef("channel.info_card")):
        panel("channel.info_card")(channel_info_card_spec)
    if not is_registered(HandlerRef("channel.list_card_render")):
        handler("channel.list_card_render")(_render_param_card)
    if not is_registered(HandlerRef("channel.info_card_render")):
        handler("channel.info_card_render")(_render_param_card)


_register_refs()


def _register_one(spec: PanelSpec) -> PanelSpec:
    try:
        return register_panel(spec)
    except ValueError as exc:
        if "already registered" in str(exc) or "duplicate" in str(exc):
            return spec
        raise


def install_channel_panels() -> tuple[PanelSpec, ...]:
    return (
        _register_one(channel_hub_spec()),
        _register_one(channel_list_card_spec()),
        _register_one(channel_info_card_spec()),
    )


def ensure_panel_refs() -> None:
    _register_refs()
