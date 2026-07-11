"""The security status card (parity flip) — the shipped ``!security``
policy embed (disbot cogs/security_cog.py ``_policy_embed``) as a
component-less session-lifecycle card (the welcome.status / automod.status
recipe: the shipped send was a plain ``ctx.send(embed=...)``, never an
anchored panel — zero components, so the sim gate carries zero rows for
it). The reconstructed fragments match the imported golden byte-for-byte
(no capture-sha drift on this row — unlike automod)."""

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
    "install_security_panels",
    "status_spec",
]

STATUS_PANEL_ID = "security.status"


def status_spec() -> PanelSpec:
    """The shipped security policy summary (cogs/security_cog.py
    ``_policy_embed``) — a per-read result card."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="security",
        title="🛡️ Server security",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("security.status_render"),
        justification=(
            "the shipped status embed is state-parameterized end to end "
            "(the Master flag, the live alert-channel binding mention, "
            "and two per-tier fields whose NAMES carry live toggle flags "
            "and whose values carry live thresholds plus the "
            "slowmode-vs-alert-only lockdown branch keyed on the "
            "raid_slowmode_channel binding) — grammar TextBlocks are "
            "static and grammar field names cannot carry state. The card "
            "declares no components; the renderer only composes the "
            "embed (goldens/security/sweep_security pins the bytes)."),
        session_lifecycle=True,
    )


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/security_cog.py ``_policy_embed``
    verbatim: the Master/Alert-channel description lines, the
    ``🚨 Raid detection`` field (Trigger line + the shipped
    ``applies_raid_slowmode`` branch: slowmode channel bound AND
    slowmode seconds > 0 ⇒ the slowmode sentence, else the alert-only
    literal), the ``⚠️ Account-age filter`` field (Threshold/Action),
    the footer literal, the GENERAL_COLOR green accent."""
    from sb.kernel.db.settings import get_binding
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel
    from sb.kernel.settings import resolve

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)

    async def _flag_of(name: str, fallback: bool = False) -> bool:
        value = await resolve(guild_id, "security", name)
        if isinstance(value, bool):
            return value
        if value is None:
            return fallback
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    async def _int_of(name: str, fallback: int) -> int:
        try:
            return int(str(await resolve(guild_id, "security", name)).strip())
        except (TypeError, ValueError):
            return fallback

    async def _bound(name: str) -> int | None:
        try:
            return await get_binding(guild_id, "security", name)
        except Exception:  # noqa: BLE001 — headless reads as unbound
            return None

    def _flag(on: bool) -> str:
        return "🟢 on" if on else "⚫ off"

    enabled = await _flag_of("enabled")
    raid_enabled = await _flag_of("raid_enabled")
    age_enabled = await _flag_of("age_enabled")
    raid_join_count = await _int_of("raid_join_count", 10)
    raid_window_seconds = await _int_of("raid_window_seconds", 60)
    raid_slowmode_seconds = await _int_of("raid_slowmode_seconds", 10)
    raid_lockdown_seconds = await _int_of("raid_lockdown_seconds", 300)
    age_min_days = await _int_of("age_min_days", 7)
    age_action = str(await resolve(guild_id, "security", "age_action")
                     or "alert")
    alert_channel = await _bound("alert_channel")
    slowmode_channel = await _bound("raid_slowmode_channel")

    alert_str = f"<#{alert_channel}>" if alert_channel else "*(unset)*"
    # shipped security_config.applies_raid_slowmode verbatim
    applies_raid_slowmode = (slowmode_channel is not None
                             and raid_slowmode_seconds > 0)
    lines = [
        f"**Master:** {_flag(enabled)}",
        f"📢 **Alert channel:** {alert_str}",
    ]
    fields = (
        (f"🚨 Raid detection — {_flag(raid_enabled)}",
         (f"Trigger: **{raid_join_count}** joins / "
          f"**{raid_window_seconds}s**\n"
          + (f"Lockdown: slowmode **{raid_slowmode_seconds}s** for "
             f"**{raid_lockdown_seconds}s**"
             if applies_raid_slowmode
             else "Lockdown: alert-only (no slowmode channel set)")),
         False),
        (f"⚠️ Account-age filter — {_flag(age_enabled)}",
         f"Threshold: **{age_min_days}** days\nAction: **{age_action}**",
         False),
    )
    embed = RenderedEmbed(
        title="🛡️ Server security",
        description="\n".join(lines),
        fields=fields,
        footer="Configure in !settings → Security.",
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


handler("security.status_render")(_render_status)


def install_security_panels() -> tuple[PanelSpec, ...]:
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
    if not is_registered(HandlerRef("security.status_render")):
        handler("security.status_render")(_render_status)
