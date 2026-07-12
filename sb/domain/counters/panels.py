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
    "PRESETS_PANEL_ID",
    "STATUS_PANEL_ID",
    "ensure_panel_refs",
    "install_counters_panels",
    "presets_spec",
    "status_spec",
]

STATUS_PANEL_ID = "counters.status"
PRESETS_PANEL_ID = "counters.presets"


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


def presets_spec() -> PanelSpec:
    """The shipped ``!counterpreset`` (no name) preset-catalog embed
    (cogs/counters_cog.py ``counterpreset`` list branch: the 🎨 blurple
    card — one ``**`key`** — label`` line per curated preset with the
    ``-# e.g. `sample``` small-text TOTAL-template preview at count
    1,234, the apply-hint footer). A component-less per-read result card
    (the status-card recipe above); ``goldens/counters/
    sweep_counterpreset.json`` pins every byte.

    CAPTURE-SHA FIDELITY (trap 24, mandatory pre-step): the oracle's
    current-head ``counters_cog.py`` list branch + the
    ``counter_config.TEMPLATE_PRESETS`` catalog fragments compose to the
    golden's bytes exactly (title / labels / samples / footer / blurple)
    — NO post-capture drift on this surface."""
    return PanelSpec(
        panel_id=PRESETS_PANEL_ID,
        subsystem="counters",
        title="🎨 Counter name presets",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("counters.presets_render"),
        justification=(
            "the shipped preset lines interpolate the catalog's rendered "
            "TOTAL-template samples (render_counter_name at count 1,234 — "
            "counters_cog.py) and the footer is the shipped apply-hint "
            "literal, outside FooterMode's vocabulary — grammar "
            "TextBlocks are static. The card declares no components; the "
            "renderer only composes the embed "
            "(goldens/counters/sweep_counterpreset pins the bytes)."),
        session_lifecycle=True,
    )


async def _render_presets(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/counters_cog.py list branch, verbatim:
    ``**`{key}`** — {label}\\n-# e.g. `{sample}``` per preset, samples
    from the TOTAL template at 1,234, the apply-hint footer."""
    from sb.domain.counters import TEMPLATE_PRESETS, render_counter_name
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    lines = []
    for key, label, total_template in TEMPLATE_PRESETS:
        sample = render_counter_name(total_template, 1234)
        lines.append(f"**`{key}`** — {label}\n-# e.g. `{sample}`")

    embed = RenderedEmbed(
        title=spec.title,
        description="\n".join(lines),
        footer=("Apply one with !counterpreset <name> "
                "(sets all three name templates; admin only)."),
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _preset_view(req):
    """`!counterpreset [name]` — the shipped split (counters_cog.py): no
    name lists the catalog (the golden-pinned card above); a name APPLIED
    all three templates through the audited SettingsMutationPipeline +
    the rename loop — that write path is a successor slice, so the named
    branch lands on the declared + honest pending terminal (no golden
    drives it)."""
    import dataclasses as _dc

    from sb.domain.operator_spine import pending_handler
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import resolve as _resolve_ref

    argv = tuple(req.args.get("argv", ()) or ())
    if argv:
        # same copy as sb/manifest/counters.py's _PENDING declaration
        # (pending_handler is register-once — the first registration wins).
        ref = pending_handler(
            "counters.preset_pending",
            "Counter presets apply channel renames — armed with the "
            "channel-ops port slice.")
        return await _resolve_ref(ref)(req)
    await open_panel(PanelRef(PRESETS_PANEL_ID),
                     _dc.replace(req, args=dict(req.args)))
    return None


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_spec()


@panel(PRESETS_PANEL_ID)
def _presets_factory() -> PanelSpec:
    return presets_spec()


handler("counters.status_render")(_render_status)
handler("counters.presets_render")(_render_presets)
handler("counters.preset_view")(_preset_view)


def install_counters_panels() -> tuple[PanelSpec, ...]:
    specs = (status_spec(), presets_spec())
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
    if not is_registered(PanelRef(PRESETS_PANEL_ID)):
        panel(PRESETS_PANEL_ID)(_presets_factory)
    if not is_registered(HandlerRef("counters.presets_render")):
        handler("counters.presets_render")(_render_presets)
    if not is_registered(HandlerRef("counters.preset_view")):
        handler("counters.preset_view")(_preset_view)
