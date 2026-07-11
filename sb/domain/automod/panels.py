"""The automod status card (parity flip) — the shipped ``!automod``
policy embed (disbot cogs/automod_cog.py ``_policy_embed`` at the corpus
sha 7f7628e1) as a component-less session-lifecycle card (the
welcome.status / karma.card recipe: the shipped send was a plain
``ctx.send(embed=...)``, never an anchored panel — zero components, so
the sim gate carries zero rows for it).

CAPTURE-SHA FIDELITY NOTE: the oracle's CURRENT head renders two more
rule lines (🌐 Cross-channel spam, 🔁 Duplicate content) that the
imported golden does not carry — post-capture oracle drift. Parity pins
the corpus (@7f7628e1), so this card renders the capture-time four-rule
set; the two later rules stay declared settings (the manifest claimed
the shipped keys) and join the card if a future corpus re-import pins
them.
"""

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
    "install_automod_panels",
    "status_spec",
]

STATUS_PANEL_ID = "automod.status"


def status_spec() -> PanelSpec:
    """The shipped automod policy summary (cogs/automod_cog.py
    ``_policy_embed``) — a per-read result card."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="automod",
        title="🛡️ Automod",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="orange", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("automod.status_render"),
        justification=(
            "the shipped status embed is state-parameterized end to end "
            "(every rule line renders its live toggle flag AND its live "
            "numeric threshold — spam count/window, caps percent, "
            "mentions count) — grammar TextBlocks are static. The card "
            "declares no components; the renderer only composes the "
            "embed (goldens/automod/sweep_automod pins the bytes)."),
        session_lifecycle=True,
    )


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/automod_cog.py ``_policy_embed`` at the
    corpus sha: the Master flag, the four capture-time rule lines with
    their threshold parameterizations, the MOD_COLOR orange accent, the
    two-sentence footer literal."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel
    from sb.kernel.settings import resolve

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)

    async def _flag_of(name: str, fallback: bool = False) -> bool:
        value = await resolve(guild_id, "automod", name)
        if isinstance(value, bool):
            return value
        if value is None:
            return fallback
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    async def _int_of(name: str, fallback: int) -> int:
        try:
            return int(str(await resolve(guild_id, "automod", name)).strip())
        except (TypeError, ValueError):
            return fallback

    def _flag(on: bool) -> str:
        return "🟢 on" if on else "⚫ off"

    enabled = await _flag_of("enabled")
    spam_on = await _flag_of("spam_enabled")
    invites_on = await _flag_of("invites_enabled")
    caps_on = await _flag_of("caps_enabled")
    mentions_on = await _flag_of("mentions_enabled")
    spam_count = await _int_of("spam_count", 5)
    spam_window = await _int_of("spam_window_seconds", 7)
    caps_percent = await _int_of("caps_percent", 70)
    mentions_count = await _int_of("mentions_count", 4)

    lines = [
        f"**Master:** {_flag(enabled)}",
        "",
        f"🛑 **Spam** — {_flag(spam_on)} "
        f"(> {spam_count} msgs / {spam_window}s)",
        f"🔗 **Invite links** — {_flag(invites_on)}",
        f"🔠 **Excessive caps** — {_flag(caps_on)} "
        f"(>= {caps_percent}% uppercase)",
        f"📣 **Mass mentions** — {_flag(mentions_on)} "
        f"(>= {mentions_count} mentions)",
    ]
    embed = RenderedEmbed(
        title="🛡️ Automod",
        description="\n".join(lines),
        footer=("Configure in !settings → Automod. Actions route through "
                "moderation (warn → escalation)."),
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


handler("automod.status_render")(_render_status)


def install_automod_panels() -> tuple[PanelSpec, ...]:
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
    if not is_registered(HandlerRef("automod.status_render")):
        handler("automod.status_render")(_render_status)
