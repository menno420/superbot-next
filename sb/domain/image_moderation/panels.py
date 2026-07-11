"""The image-moderation status card (parity flip) — the shipped
``!imagemod`` policy embed (disbot cogs/image_moderation_cog.py at the
corpus sha 7f7628e1) as a component-less session-lifecycle card (the
welcome.status / automod.status / karma.card recipe: the shipped send
was a plain ``ctx.send(embed=...)``, never an anchored panel — zero
components, so the sim gate carries zero rows for it).

CAPTURE-SHA FIDELITY NOTE: checked as a mandatory pre-step (playbook
trap 24) — the oracle's current-head fragments match the imported
golden's seven lines exactly at the default state; NO post-capture
drift on this row (unlike automod's two extra rule lines). The shipped
cog additionally appends exempt-role/exempt-channel lines ONLY when the
guild configured non-empty exempt lists (``if policy.exempt_role_ids:``
/ ``if policy.exempt_channel_ids:``) — no imported golden reaches that
state, so the conditional tail is not ported here (the exempt keys stay
declared settings; the tail joins the card with a future corpus
re-import that pins its bytes).
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
    "install_image_moderation_panels",
    "status_spec",
]

STATUS_PANEL_ID = "image_moderation.status"


def status_spec() -> PanelSpec:
    """The shipped image-moderation policy summary
    (cogs/image_moderation_cog.py) — a per-read result card."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="image_moderation",
        title="🖼️ Image moderation",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="orange", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("image_moderation.status_render"),
        justification=(
            "the shipped status embed is state-parameterized end to end "
            "(the Master flag, the live action-threshold percentage, and "
            "each category line's live toggle flag) — grammar TextBlocks "
            "are static. The card declares no components; the renderer "
            "only composes the embed "
            "(goldens/image_moderation/sweep_imagemod pins the bytes)."),
        session_lifecycle=True,
    )


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/image_moderation_cog.py at the corpus
    sha: the Master flag, the action-threshold line, the four category
    lines (sexual/violence/harassment/hate), the MOD_COLOR orange
    accent, the two-sentence footer literal."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel
    from sb.kernel.settings import resolve

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)

    async def _flag_of(name: str, fallback: bool = False) -> bool:
        value = await resolve(guild_id, "image_moderation", name)
        if isinstance(value, bool):
            return value
        if value is None:
            return fallback
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    async def _int_of(name: str, fallback: int) -> int:
        try:
            return int(str(await resolve(
                guild_id, "image_moderation", name)).strip())
        except (TypeError, ValueError):
            return fallback

    def _flag(on: bool) -> str:
        return "🟢 on" if on else "⚫ off"

    enabled = await _flag_of("enabled")
    sexual_on = await _flag_of("sexual_enabled")
    violence_on = await _flag_of("violence_enabled")
    harassment_on = await _flag_of("harassment_enabled")
    hate_on = await _flag_of("hate_enabled")
    threshold = await _int_of("threshold_percent", 80)

    lines = [
        f"**Master:** {_flag(enabled)}",
        f"**Action threshold:** ≥ {threshold}% confidence",
        "",
        f"🔞 **Sexual** — {_flag(sexual_on)}",
        f"🔪 **Violence** — {_flag(violence_on)}",
        f"😠 **Harassment** — {_flag(harassment_on)}",
        f"🚫 **Hate** — {_flag(hate_on)}",
    ]
    embed = RenderedEmbed(
        title="🖼️ Image moderation",
        description="\n".join(lines),
        footer=("Configure in !settings → Image moderation. When on, "
                "flagged images are scanned via OpenAI; actions route "
                "through moderation."),
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


handler("image_moderation.status_render")(_render_status)


def install_image_moderation_panels() -> tuple[PanelSpec, ...]:
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
    if not is_registered(HandlerRef("image_moderation.status_render")):
        handler("image_moderation.status_render")(_render_status)
