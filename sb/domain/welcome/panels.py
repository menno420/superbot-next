"""The welcome status card (parity flip) — the shipped ``!welcome``
policy embed (disbot cogs/welcome_cog.py ``_policy_embed`` +
``welcome_status``) as a component-less session-lifecycle card (the
karma.card / logging status-card precedent: the shipped send was a plain
``ctx.send(embed=...)``, never an anchored panel — zero components, so
the sim gate carries zero rows for it)."""

from __future__ import annotations

from sb.kernel.panels.registry import register_panel
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FooterMode,
    LayoutSpec,
    NavigationSpec,
    PageSpec,
    PanelSpec,
)
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

__all__ = [
    "STATUS_PANEL_ID",
    "ensure_panel_refs",
    "install_welcome_panels",
    "status_spec",
]

STATUS_PANEL_ID = "welcome.status"


def status_spec() -> PanelSpec:
    """The shipped welcome policy summary (cogs/welcome_cog.py
    ``_policy_embed``) — a per-read result card."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="welcome",
        title="👋 Welcome",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("welcome.status_render"),
        justification=(
            "the shipped status embed is state-parameterized end to end "
            "(the flag lines read the effective policy, the channel/"
            "entry-role lines render live binding mentions, the message-"
            "preview fields render the stored templates through the "
            "shipped variant splitter with the live guild name and "
            "member count, and the conditional leave/DM/auto-delete "
            "surfaces appear only when their toggles are set) — grammar "
            "TextBlocks are static. The card declares no components; the "
            "renderer only composes the embed "
            "(goldens/welcome/sweep_welcome pins the bytes)."),
        session_lifecycle=True,
    )


async def _guild_view(guild_id: int) -> tuple[str, int]:
    """(guild name, member count) through the utility guild-directory
    read port — the shipped ``guild.name`` / ``guild.member_count`` pair
    (the karma/economy renderer posture: degrade, never invent — with no
    directory armed the previews render an empty server name and the
    shipped ``max(count or 1, 1)`` floor)."""
    try:
        from sb.domain.utility.service import guild_directory

        info = await guild_directory().guild_info(guild_id)
    except Exception:  # noqa: BLE001 — headless ⇒ degraded previews
        return "", 1
    return info.name, max(int(info.member_count or 1), 1)


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/welcome_cog.py ``_policy_embed``
    verbatim: the flag lines, the channel/entry-role mentions, the
    always-on join preview plus the toggle-gated leave/DM previews (each
    through the shipped variant splitter with its shipped sample name),
    the auto-delete line, the footer literal, the GENERAL_COLOR green
    accent."""
    from sb.domain.welcome import render_message, service
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    policy = await service.load_policy(guild_id)
    channel_id = await service.bound_channel(guild_id)
    role_id = await service.bound_entry_role(guild_id)
    guild_name, sample_count = await _guild_view(guild_id)

    def _flag(on: bool) -> str:
        return "🟢 on" if on else "⚫ off"

    def _preview(template: str, sample_name: str) -> tuple[str, str]:
        variants = service.split_message_variants(template) or [template]
        rendered = render_message(
            variants[0], user=sample_name, server=guild_name,
            count=sample_count)
        suffix = (f" (1 of {len(variants)} random variants)"
                  if len(variants) > 1 else "")
        return rendered, suffix

    channel_str = f"<#{channel_id}>" if channel_id else "*(unset)*"
    role_str = f"<@&{role_id}>" if role_id else "*(none)*"
    lines = [
        f"**Master:** {_flag(policy.enabled)}",
        "",
        f"👋 **Greet on join** — {_flag(policy.join_enabled)}",
        f"🚪 **Farewell on leave** — {_flag(policy.leave_enabled)}",
        f"✉️ **DM on join** — {_flag(policy.dm_enabled)}",
        f"📢 **Channel:** {channel_str}",
        f"🎟️ **Entry role:** {role_str}",
    ]
    if policy.delete_after_seconds:
        lines.append(
            f"🧹 **Auto-delete greeting after:** "
            f"{policy.delete_after_seconds}s")

    fields = []
    join_preview, join_suffix = _preview(policy.join_message, "@NewMember")
    fields.append((f"Join message preview{join_suffix}", join_preview, False))
    if policy.leave_enabled:
        leave_preview, leave_suffix = _preview(policy.leave_message,
                                               "NewMember")
        fields.append((f"Leave message preview{leave_suffix}",
                       leave_preview, False))
    if policy.dm_enabled:
        dm_preview, dm_suffix = _preview(policy.dm_message, "@NewMember")
        fields.append((f"DM message preview{dm_suffix}", dm_preview, False))

    embed = RenderedEmbed(
        title="👋 Welcome",
        description="\n".join(lines),
        fields=tuple(fields),
        footer="Configure in !settings → Welcome.",
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


handler("welcome.status_render")(_render_status)


def install_welcome_panels() -> tuple[PanelSpec, ...]:
    specs = (status_spec(),)
    out = []
    for spec in specs:
        try:
            out.append(register_panel(spec))
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                out.append(spec)
            else:
                raise
    return tuple(out)


def ensure_panel_refs() -> None:
    if not is_registered(PanelRef(STATUS_PANEL_ID)):
        panel(STATUS_PANEL_ID)(_status_factory)
    if not is_registered(HandlerRef("welcome.status_render")):
        handler("welcome.status_render")(_render_status)
