"""The UTILITY panels (band 6 flip) — disbot/cogs/utility_cog.py's shipped
surfaces as PanelSpecs.

* ``utility.panel`` — the shipped ``_UtilityPanelView``: the 🔧 Utility
  Panel embed (discord.Color.blue(), the 6-line action legend, the
  ``More in Utility`` children field from the subsystem registry, footer
  ``Click an action below.``) over three action rows plus the
  child-forwarding row. The shipped view mixed discord.py AUTO-minted
  button ids (rows 0–2 — the parity Normalizer's ``<cid:N>``) with
  EXPLICIT persistent ids on the forwarding buttons
  (``custom_id=f"utility:open:{key}"`` — `_UtilityChildButton`, the
  consolidation-discoverability fix); ``custom_id_override`` carries those
  verbatim through the session mint.
  ``parity/goldens/utility/sweep_utilitymenu.json`` +
  ``sweep_slash_utility.json`` pin every byte.
* ``utility.pong`` / ``utility.avatar_card`` / ``utility.server_info`` /
  ``utility.user_info`` — the shipped plain info embeds (renderer_override:
  their copy is live-data-parameterized; grammar TextBlocks are static).
* ``utility.profile_card`` — the /myprofile hero-card send
  (sb/domain/utility/profile_card.py owns the attachment).

All read-only; the shipped views were timeout sessions (never anchored) —
``session_lifecycle=True`` throughout.
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    ActionStyle,
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelActionSpec,
    PanelSpec,
    ResultRender,
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
    "UTILITY_CHILDREN",
    "ensure_panel_refs",
    "install_utility_panels",
    "utility_panel_spec",
]

# --- the shipped children metadata (disbot/utils/subsystem_registry.py
# verbatim: display_name/emoji/description for parent_hub == "utility";
# roster + presentation also carried in sb/domain/help/categories.py).
# The shipped view DISCOVERED this row per render
# (discover_utility_children); the declarative spec pins today's roster —
# re-derivation from the manifest inventory is the follow-up when more
# utility children port.
UTILITY_CHILDREN: tuple[tuple[str, str, str, str], ...] = (
    ("general", "General", "💬", "General bot commands and information"),
    ("four_twenty", "420", "🍃",
     "A leafy little easter-egg panel — wisdom and number trivia"),
)

# the shipped overview legend (_UtilityPanelView embed description,
# verbatim — the goldens pin every byte).
_LEGEND = (
    "**🖥️ Server Info** — server statistics\n"
    "**👤 User Info** — your profile details\n"
    "**🖼️ Avatar** — display your avatar\n"
    "**📊 Poll** — create a reaction poll\n"
    "**🔔 Remind Me** — set a timed reminder\n"
    "**🔗 Invite** — generate a one-use server invite"
)

#: the shipped footer literal (utility_cog `set_footer(text=...)`) — outside
#: FooterMode's vocabulary, hence the renderer_override below.
_FOOTER = "Click an action below."


async def _children_field(ctx) -> tuple[tuple[str, str], ...]:
    """The shipped ``More in Utility`` embed field (one field, the shipped
    per-child line format verbatim)."""
    del ctx
    value = "\n".join(
        f"{emoji} **{name}** — {description}"
        for _key, name, emoji, description in UTILITY_CHILDREN)
    return (("More in Utility", value),)


def _child_action(key: str, name: str, emoji: str) -> PanelActionSpec:
    return PanelActionSpec(
        action_id=f"open_{key}",
        label=f"{emoji} {name}",                 # emoji IN the label (wire shape)
        style=ActionStyle.PRIMARY,               # the shipped blurple child row
        audience_tier="user",
        # general's panel is ported — forward straight to it; four_twenty is
        # a pending band, so its click lands on the polite pending terminal.
        handler=(PanelRef("general.menu") if key == "general"
                 else HandlerRef("utility.four_twenty_pending")),
        custom_id_override=f"utility:open:{key}",  # the shipped persistent id
    )


def utility_panel_spec() -> PanelSpec:
    return PanelSpec(
        panel_id="utility.panel",
        subsystem="utility",
        title="🔧 Utility Panel",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blue", footer_mode=FooterMode.NONE),
        body=(TextBlock(_LEGEND),
              FieldsBlock(provider=ProviderRef("utility.children_field"))),
        actions=(
            # row 0 — the shipped blurple info trio (emoji in-label).
            PanelActionSpec(
                action_id="server_info", label="🖥️ Server Info",
                style=ActionStyle.PRIMARY, audience_tier="user",
                capability_required="utility.info.server",
                handler=HandlerRef("utility.server_info_view")),
            PanelActionSpec(
                action_id="user_info", label="👤 User Info",
                style=ActionStyle.PRIMARY, audience_tier="user",
                capability_required="utility.info.user",
                handler=HandlerRef("utility.user_info_view")),
            PanelActionSpec(
                action_id="avatar", label="🖼️ Avatar",
                style=ActionStyle.PRIMARY, audience_tier="user",
                handler=HandlerRef("utility.avatar_view")),
            # row 1 — the shipped grey tool trio. Poll/Remind opened modals
            # and Invite created a one-use channel invite in the shipped
            # cog; their Discord effect ports (reaction egress, timed
            # delivery, invite mint) are not armed yet — the polite pending
            # terminal (the role-band precedent), never a silent stub.
            PanelActionSpec(
                action_id="poll", label="📊 Poll",
                audience_tier="user",
                handler=HandlerRef("utility.poll_pending")),
            PanelActionSpec(
                action_id="remind", label="🔔 Remind Me",
                audience_tier="user",
                handler=HandlerRef("utility.remind_pending")),
            PanelActionSpec(
                action_id="invite", label="🔗 Invite",
                audience_tier="user",
                handler=HandlerRef("utility.invite_pending")),
            # row 2 — the shipped grey re-render Overview.
            PanelActionSpec(
                action_id="utility_overview", label="↩ Overview",
                audience_tier="user",
                handler=PanelRef("utility.panel"),
                result_render=ResultRender.REFRESH_PANEL),
        ) + tuple(_child_action(key, name, emoji)
                  for key, name, emoji, _d in UTILITY_CHILDREN),
        # the shipped _UtilityPanelView carried only its own buttons (no nav
        # slots; timeout session view) — the goldens pin exactly four rows.
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef("utility.render_panel"),
        justification=(
            "the shipped panel footer is the literal 'Click an action "
            "below.' — outside FooterMode's none/subsystem/provenance "
            "vocabulary (goldens/utility pin the byte). The override "
            "delegates to the grammar renderer and replaces ONLY the "
            "footer; body, fields, actions and layout stay declared."),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("server_info", "user_info", "avatar"),
            ("poll", "remind", "invite"),
            ("utility_overview",),
            ("open_general", "open_four_twenty"),
        )),)),
    )


def _info_card_spec(panel_id: str, title: str, style_token: str) -> PanelSpec:
    """One shipped plain info embed (no components, timeout-free plain
    message — modeled as a zero-action session panel: never minted, never
    anchored; the shipped replies were not panel-manager panels)."""
    return PanelSpec(
        panel_id=panel_id,
        subsystem="utility",
        title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token=style_token, footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        session_lifecycle=True,
        renderer_override=HandlerRef(f"{panel_id}_render"),
        justification=(
            "the shipped embed copy is live-data-parameterized "
            "(guild/member/latency reads at send time — utility_cog.py); "
            "grammar TextBlocks are static. Zero components; the renderer "
            "composes only the embed."),
    )


def pong_spec() -> PanelSpec:
    return _info_card_spec("utility.pong", "🏓 Pong!", "blue")


def avatar_card_spec() -> PanelSpec:
    return _info_card_spec("utility.avatar_card", "", "blue")


def server_info_spec() -> PanelSpec:
    return _info_card_spec("utility.server_info", "", "blue")


def user_info_spec() -> PanelSpec:
    return _info_card_spec("utility.user_info", "", "green")


def profile_card_spec() -> PanelSpec:
    return _info_card_spec("utility.profile_card", "", "")


# --- renderer overrides ---------------------------------------------------------

async def _render_utility_panel(spec: PanelSpec, ctx) -> object:
    """Grammar render + the shipped footer literal (see justification)."""
    from sb.kernel.panels.render import render_panel

    rendered = await render_panel(spec, ctx)
    return _dc_replace(rendered, embed=_dc_replace(rendered.embed, footer=_FOOTER))


async def _render_pong(spec: PanelSpec, ctx) -> object:
    """The shipped !ping embed pair: bare '🏓 Pong!' on send; the edit
    carries Gateway/Round-trip fields (utility_cog.ping, verbatim
    ``f"{ms:.0f} ms"`` formatting — the capture world's no-heartbeat
    gateway reads 'nan ms')."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    fields: tuple = ()
    if "rtt_ms" in params:
        fields = (
            ("Gateway", f"{float(params['gateway_ms']):.0f} ms", True),
            ("Round-trip", f"{float(params['rtt_ms']):.0f} ms", True),
        )
    embed = RenderedEmbed(title=spec.title, description="", fields=fields,
                          style_token="blue")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_avatar_card(spec: PanelSpec, ctx) -> object:
    """The shipped !avatar embed: f"{member}'s Avatar", INFO_COLOR, the
    member's display avatar as the hero image (utility_cog.avatar)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    embed = RenderedEmbed(
        title=f"{params.get('tag', '')}'s Avatar", description="",
        style_token="blue", image_url=str(params.get("avatar_url", "")))
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_server_info(spec: PanelSpec, ctx) -> object:
    """The shipped `!info server` embed (utility_cog.info: title guild
    name, description 'Server Information', the six inline fields in the
    shipped order — goldens/utility/sweep_serverinfo pins the bytes)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    embed = RenderedEmbed(
        title=str(params.get("name", "")),
        description="Server Information",
        fields=(
            ("Owner", f"<@{params.get('owner_id')}>", True),
            ("Members", str(params.get("member_count")), True),
            ("Boost Level", str(params.get("premium_tier")), True),
            ("Created", str(params.get("created")), True),
            ("Text Channels", str(params.get("text_channels")), True),
            ("Voice Channels", str(params.get("voice_channels")), True),
        ),
        style_token="blue")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_user_info(spec: PanelSpec, ctx) -> object:
    """The shipped `!info user` embed (utility_cog.info: title
    f"User Info — {member}", SUCCESS_COLOR, Joined Discord / Joined Server
    date fields — no golden pins it; the panel button reaches it)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    embed = RenderedEmbed(
        title=f"User Info — {params.get('tag', '')}", description="",
        fields=(
            ("Joined Discord", str(params.get("created")), True),
            ("Joined Server", str(params.get("joined")), True),
        ),
        style_token="green")
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed,
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_profile_card(spec: PanelSpec, ctx) -> object:
    """The /myprofile hero-card send (profile_card.py owns the bytes; the
    goldens pin the multipart send shape — filenames only)."""
    from sb.domain.utility.profile_card import CARD_FILENAME, render_profile_card
    from sb.kernel.panels.render import (
        RenderedAttachment,
        RenderedEmbed,
        RenderedPanel,
    )

    png = render_profile_card(int(getattr(ctx.actor, "user_id", 0) or 0),
                              int(ctx.guild_id or 0))
    return RenderedPanel(
        panel_id=spec.panel_id,
        embed=RenderedEmbed(title="", description=""),
        attachments=(RenderedAttachment(filename=CARD_FILENAME, data=png),),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


# --- registration ----------------------------------------------------------------

_SPECS = {
    "utility.panel": utility_panel_spec,
    "utility.pong": pong_spec,
    "utility.avatar_card": avatar_card_spec,
    "utility.server_info": server_info_spec,
    "utility.user_info": user_info_spec,
    "utility.profile_card": profile_card_spec,
}

_RENDERERS = {
    "utility.render_panel": _render_utility_panel,
    "utility.pong_render": _render_pong,
    "utility.avatar_card_render": _render_avatar_card,
    "utility.server_info_render": _render_server_info,
    "utility.user_info_render": _render_user_info,
    "utility.profile_card_render": _render_profile_card,
}


def _register_refs() -> None:
    from sb.spec.refs import handler

    for pid, factory in _SPECS.items():
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)
    for name, fn in _RENDERERS.items():
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    if not is_registered(ProviderRef("utility.children_field")):
        provider("utility.children_field")(_children_field)


_register_refs()


def install_utility_panels() -> tuple[PanelSpec, ...]:
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
