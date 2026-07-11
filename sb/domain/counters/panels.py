"""The counters status card (parity flip) — the shipped ``!counters`` /
``/counters`` policy embed (disbot cogs/counters_cog.py at the corpus
sha 7f7628e1) as a component-less session-lifecycle card (the
welcome/automod/security/image_moderation recipe: the shipped send was
a plain ``ctx.send(embed=...)`` — zero components, so the sim gate
carries zero rows for it). The slash twin rides the SAME PanelRef:
slash+PanelRef resolves DeferMode.NONE (type-4 direct) and
``Audience.INVOKER`` panels present ephemeral on interaction surfaces
(flags 64) while staying public channel sends on prefix — exactly the
split the two goldens pin.

CAPTURE-SHA FIDELITY NOTE: checked as a mandatory pre-step (playbook
trap 24) — the oracle's current-head fragments compose to the imported
goldens' bytes exactly (Master line, blank, three
``**{Kind}** → {target}`` rows each with the ``-# → `{rendered}```
small-text preview, the ~10-min footer, blurple); NO post-capture drift
on this row.

Bound-channel rendering: the shipped cog resolved the bound channel
OBJECT from the gateway cache and rendered ``channel.mention`` (a
bound-but-deleted channel fell back to ``*(unbound)*``); the port
renders the mention from the binding id — channel liveness is a gateway
read the new bot takes when the channel-ops port arms (no golden pins
the bound state).
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
    "install_counters_panels",
    "status_spec",
]

STATUS_PANEL_ID = "counters.status"


def status_spec() -> PanelSpec:
    """The shipped counters policy summary (cogs/counters_cog.py) —
    a per-read result card."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="counters",
        title="📊 Server counters",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("counters.status_render"),
        justification=(
            "the shipped status embed is state-parameterized end to end "
            "(the Master flag, each counter row's live channel binding "
            "AND its live rendered name preview over the live member "
            "counts) — grammar TextBlocks are static. The card declares "
            "no components; the renderer only composes the embed "
            "(goldens/counters/sweep_counters + sweep_slash_counters "
            "pin the bytes)."),
        session_lifecycle=True,
    )


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/counters_cog.py at the corpus sha: the
    Master ``_flag`` line, one row per kind IN ORDER
    (``**{kind.capitalize()}** → {target}\\n-# → `{rendered}```), the
    blurple accent, the ~10-min footer literal."""
    from sb.domain.counters.service import KINDS, compute_counts, load_policy
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    guild_id = int(getattr(ctx, "guild_id", 0) or 0)
    policy = await load_policy(guild_id)
    counts = await compute_counts(guild_id)

    from sb.domain.counters import render_counter_name

    flag = "🟢 on" if policy.enabled else "⚫ off"
    lines = [f"**Master:** {flag}", ""]
    for kind in KINDS:
        channel_id = policy.channel_for(kind)
        target = f"<#{channel_id}>" if channel_id else "*(unbound)*"
        rendered = render_counter_name(
            policy.template_for(kind), counts.for_kind(kind))
        lines.append(f"**{kind.capitalize()}** → {target}\n-# → `{rendered}`")

    embed = RenderedEmbed(
        title="📊 Server counters",
        description="\n".join(lines),
        footer=("Configure in !settings → Counters. Channels refresh every "
                "~10 min (Discord rename rate limit)."),
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


handler("counters.status_render")(_render_status)


def install_counters_panels() -> tuple[PanelSpec, ...]:
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
    if not is_registered(HandlerRef("counters.status_render")):
        handler("counters.status_render")(_render_status)
