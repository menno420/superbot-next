"""The setup panels (parity flip) — the shipped wizard surface's four
golden-pinned cards, replacing the band-1 sections-index projection hub
(D-0065 oracle-wins: the projection was interim architecture; the shipped
bytes are the spec).

ORACLE @befc6d0d (search_code fragments; full-file reads stay denied):

* ``setup.hub`` — the DEPTH CHOOSER (disbot/views/setup/depth_panel.py
  ``build_depth_embed`` + the three static ``setup_depth:{slug}`` buttons).
  The shipped ``/setup-hub`` entry resolves a depth-less session to this
  chooser (cogs/setup/_helpers.resolve_hub_entry); the SAME view is the
  advanced wizard's workspace anchor (views/setup/wizard.py
  ``open_setup_workspace``) — one panel, two presentation surfaces
  (goldens/setup/sweep_slash_setup-hub pins the ephemeral type-4 render,
  sweep_slash_setup-advanced the workspace channel post).
* ``setup.essential_card`` — the Essential Setup Step-1 card
  (views/setup/essential_setup.py: the five-kind server select, the
  ✨ Save & continue / Skip pair, the "Step 1 of 8" footer) that
  ``!setup`` / ``/setup`` post into the workspace
  (goldens/setup/sweep_setup + goldens/quicksetup/sweep_slash_setup).
* ``setup.status_card`` — the read-only status snapshot
  (cogs/setup/_helpers.build_status_embed: ``**Status:** `{status}` ``
  description, the no-session field, blurple fallback color) that
  ``/setup-status`` posts into the workspace as a durable notice
  (goldens/setup/sweep_slash_setup-status pins the session-less bytes).
* ``setup.suggestions_card`` — the Smart-suggestions review panel
  (views/setup/ai_review/main_panel.py: the _REVIEW_HEADER description
  with the High/Medium/Low/Source counts, per-subsystem recommendation
  fields with the _CONFIDENCE_ICON glyphs, the Dropped list capped at 5,
  the four review buttons + Stage & open Final review) that
  ``/setup-describe`` sends as its ephemeral followup
  (goldens/setup/sweep_slash_setup-describe pins every byte).

The wizard INTERIOR (depth choice application, the essential flow's
Step-1 pick/save/skip, the review panel's accept/review/stage lanes) is
LIVE (the wizard-lifecycle slice — sb/domain/setup/wizard.py carries the
click handlers + the ported oracle data); no golden drives a click on
any of these components, so the oracle sources pin the click-path copy
while the goldens keep pinning every OPEN render byte. Two interior
panels ride along: ``setup.sections_hub`` (views/setup/hub.py — the
depth click's shipped destination) and ``setup.review_item``
(views/setup/ai_review/per_recommendation.py — the one-at-a-time
walkthrough). The FINAL-REVIEW APPLY LANE is live (final_review.py —
its three panels ride the manifest). Named successors stay honest
terminals: the essential steps 2–8, the remaining nine per-section
flows + the linear wizard steps, and the per-suggestion Edit lane (the
wizard.py module docstring routes them).
"""

from __future__ import annotations

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
    SelectorKind,
    SelectorSpec,
    TextBlock,
)
from sb.spec.refs import HandlerRef, PanelRef, ProviderRef, handler, is_registered, panel, provider

__all__ = [
    "ESSENTIAL_PANEL_ID",
    "HUB_PANEL_ID",
    "REVIEW_ITEM_PANEL_ID",
    "SECTIONS_HUB_PANEL_ID",
    "STATUS_PANEL_ID",
    "SUGGESTIONS_PANEL_ID",
    "ensure_setup_refs",
    "install_setup_panels",
    "setup_hub_spec",
]

HUB_PANEL_ID = "setup.hub"
ESSENTIAL_PANEL_ID = "setup.essential_card"
STATUS_PANEL_ID = "setup.status_card"
SUGGESTIONS_PANEL_ID = "setup.suggestions_card"
SECTIONS_HUB_PANEL_ID = "setup.sections_hub"
REVIEW_ITEM_PANEL_ID = "setup.review_item"

#: shipped copy, verbatim (depth_panel.build_depth_embed — goldens/setup/
#: sweep_slash_setup-hub + sweep_slash_setup-advanced pin every byte).
_DEPTH_DESCRIPTION = (
    "How detailed do you want the wizard to be? You can change this later "
    "from the hub. Your selection only filters which sections appear — "
    "nothing applies until **Final review**."
)
_DEPTH_FIELDS = (
    ("⚡ Quick",
     "3 steps — server scan, choose a preset, apply. Best for small "
     "servers that just want safe defaults."),
    ("🛠 Standard",
     "5–6 steps — scan, channels & logging, cleanup, optional preset, "
     "review. Best for most communities."),
    ("🔬 Advanced",
     "Every section — identity, smart suggestions, cog routing, cleanup, "
     "channels, presets. Best for owners who want control."),
)
_DEPTH_FOOTER = "Recommended: Standard."

#: shipped essential Step-1 copy, verbatim (essential_setup.py —
#: goldens/setup/sweep_setup + goldens/quicksetup/sweep_slash_setup).
_ESSENTIAL_DESCRIPTION = (
    "Pick the closest match and we'll switch on a set of safe, sensible "
    "defaults right away — you can change any of it later. We won't "
    "create or delete anything; this just turns on a few settings to get "
    "you started.\n\nThen press **Save & continue**."
)
_ESSENTIAL_KINDS = (
    {"label": "Community", "value": "community", "emoji": "💬",
     "description": "balanced spam protection, members told why they're "
                    "actioned, steady XP"},
    {"label": "Gaming", "value": "gaming", "emoji": "🎮",
     "description": "spam & mass-ping protection (invite links allowed), "
                    "faster XP"},
    {"label": "Support / Help desk", "value": "support", "emoji": "🛟",
     "description": "strict protection on everything, members told why, "
                    "relaxed XP"},
    {"label": "Creator / Content", "value": "creator", "emoji": "🎨",
     "description": "balanced spam protection, members told why, steady XP"},
    {"label": "Just exploring", "value": "exploring", "emoji": "🧭",
     "description": "just basic spam protection — set everything else up "
                    "yourself"},
)

#: views/setup/ai_review/main_panel.py literals, verbatim.
_REVIEW_HEADER = "Smart suggestions are recommendations. Review before applying."
_CONFIDENCE_ICON = {"high": "🟢", "medium": "🟡", "low": "⚪"}

#: shipped hub copy, verbatim (views/setup/hub.py — the depth click's
#: destination; no golden drives it, the oracle source pins the bytes).
_SECTIONS_HUB_TITLE = "🛰 SuperBot setup wizard"
_SECTIONS_HUB_DESCRIPTION = (
    "Step through the sections to wire SuperBot up. Each section's "
    "actions go through audited mutation pipelines; nothing applies "
    "until **Final review** confirms it."
)
_SECTIONS_HUB_FOOTER = (
    "Owner-gated. No mutation runs until Final review confirms. "
    "Tip: /setup-status for a read-only peek · /setup-reset to "
    "clear staged ops."
)

#: the shipped section-status badges (services/setup_progress.py
#: ``_BADGE_BY_STATUS`` — the ported subset renders the states this
#: build can reach: skipped / applied-by-ack-or-complete / not started).
_BADGE_SKIPPED = "⚠️"
_BADGE_APPLIED = "✅"
_BADGE_NOT_STARTED = "⬜"

#: per-suggestion confidence accents (per_recommendation.py
#: ``_CONFIDENCE_COLOR``, mapped onto the ported style tokens).
_CONFIDENCE_TOKEN = {"high": "green", "medium": "gold", "low": "dark_grey"}


# --- providers ----------------------------------------------------------------------

_DEPTH_FIELDS_PROVIDER = "setup.depth_fields"
_ESSENTIAL_OPTIONS_PROVIDER = "setup.essential_kind_options"


def _ensure_providers() -> None:
    if not is_registered(ProviderRef(_DEPTH_FIELDS_PROVIDER)):
        @provider(_DEPTH_FIELDS_PROVIDER)
        async def depth_fields(ctx: object):
            return _DEPTH_FIELDS

    if not is_registered(ProviderRef(_ESSENTIAL_OPTIONS_PROVIDER)):
        @provider(_ESSENTIAL_OPTIONS_PROVIDER)
        async def essential_kind_options(ctx: object):
            return _ESSENTIAL_KINDS


# --- specs --------------------------------------------------------------------------

def setup_hub_spec() -> PanelSpec:
    """The depth chooser — the shipped hub entry's first surface AND the
    advanced wizard's workspace anchor (module docstring)."""
    return PanelSpec(
        panel_id=HUB_PANEL_ID,
        subsystem="setup",
        title="🛰 Choose your setup depth",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        body=(TextBlock(_DEPTH_DESCRIPTION),
              FieldsBlock(provider=ProviderRef(_DEPTH_FIELDS_PROVIDER))),
        actions=(
            PanelActionSpec(
                action_id="depth_quick", label="⚡ Quick",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.depth_pick_quick"),
                custom_id_override="setup_depth:quick"),
            PanelActionSpec(
                action_id="depth_standard", label="🛠 Standard",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.depth_pick_standard"),
                custom_id_override="setup_depth:standard"),
            PanelActionSpec(
                action_id="depth_advanced", label="🔬 Advanced",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.depth_pick_advanced"),
                custom_id_override="setup_depth:advanced"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(
            rows=(("depth_quick", "depth_standard", "depth_advanced"),)),)),
        renderer_override=HandlerRef("setup.depth_render"),
        justification=(
            "the shipped depth chooser carries the footer literal "
            "'Recommended: Standard.' (depth_panel.build_depth_embed "
            "set_footer) — FooterMode has no literal lane; the override "
            "delegates the whole component/body render to the grammar and "
            "replaces ONLY the embed footer (goldens/setup/"
            "sweep_slash_setup-hub + sweep_slash_setup-advanced pin the "
            "byte)."),
        session_lifecycle=True,
    )


def essential_card_spec() -> PanelSpec:
    """The Essential Setup Step-1 card (the ``!setup`` / ``/setup``
    workspace post) — a fresh author-bound session view (the oracle's
    EssentialFlow: run-minted component ids, no session row, no anchor)."""
    return PanelSpec(
        panel_id=ESSENTIAL_PANEL_ID,
        subsystem="setup",
        title="✨ What kind of server is this?",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        body=(TextBlock(_ESSENTIAL_DESCRIPTION),),
        actions=(
            PanelActionSpec(
                action_id="essential_save", label="Save & continue",
                emoji="✨", style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.essential_save")),
            PanelActionSpec(
                action_id="essential_skip",
                label="Skip — set things up myself",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.essential_skip")),
        ),
        selectors=(
            SelectorSpec(
                selector_id="essential_kind", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.essential_pick"),
                options_source=ProviderRef(_ESSENTIAL_OPTIONS_PROVIDER),
                placeholder="What kind of server is this?"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("essential_kind",), ("essential_save",), ("essential_skip",))),)),
        renderer_override=HandlerRef("setup.essential_render"),
        justification=(
            "the shipped Step-1 card carries the footer literal "
            "'Step 1 of 8' and the 'Starter set' → '_pick one above_' "
            "field (essential_setup.py build; grammar fields are "
            "provider-fed and FooterMode has no literal lane) — the "
            "override delegates the component render to the grammar and "
            "replaces ONLY the embed footer + fields (goldens/setup/"
            "sweep_setup + goldens/quicksetup/sweep_slash_setup pin the "
            "bytes)."),
        session_lifecycle=True,
    )


def status_card_spec() -> PanelSpec:
    """The read-only ``/setup-status`` snapshot — a component-less durable
    workspace notice (never anchored, never refreshed)."""
    return PanelSpec(
        panel_id=STATUS_PANEL_ID,
        subsystem="setup",
        title="🛰 Setup status",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=()),)),
        renderer_override=HandlerRef("setup.status_render"),
        justification=(
            "the shipped status snapshot is state-parameterized in both "
            "its description ('**Status:** `{status}`' — "
            "cogs/setup/_helpers.build_status_embed) and its field set "
            "(the no-session explainer renders only when no session row "
            "exists); grammar TextBlocks are static. Zero components; the "
            "renderer only composes the embed (goldens/setup/"
            "sweep_slash_setup-status pins the session-less bytes)."),
        session_lifecycle=True,
    )


def suggestions_card_spec() -> PanelSpec:
    """The Smart-suggestions review panel (the ``/setup-describe``
    ephemeral followup)."""
    return PanelSpec(
        panel_id=SUGGESTIONS_PANEL_ID,
        subsystem="setup",
        title="🤖 Smart suggestions",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="accept_high_confidence",
                label="Accept all high-confidence",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.review_accept_high")),
            PanelActionSpec(
                action_id="review_one_by_one", label="Review one-by-one",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.review_one_by_one")),
            PanelActionSpec(
                action_id="reject_ai_suggestions",
                label="Reject all AI suggestions",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.review_reject_ai")),
            PanelActionSpec(
                action_id="rerun_deterministic",
                label="Rerun deterministic-only",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.review_rerun")),
            PanelActionSpec(
                action_id="stage_final_review",
                label="Stage & open Final review",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.review_stage")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("accept_high_confidence", "review_one_by_one",
             "reject_ai_suggestions", "rerun_deterministic"),
            ("stage_final_review",))),)),
        renderer_override=HandlerRef("setup.suggestions_render"),
        justification=(
            "the shipped review panel is draft-parameterized in its "
            "description (the _REVIEW_HEADER + High/Medium/Low/Source "
            "count line), its per-subsystem recommendation fields, its "
            "Dropped list (capped at 5 with the '+N more not shown' "
            "tail), and it rides the deterministic-note CONTENT line "
            "next to the embed (main_panel.py _DETERMINISTIC_NOTE) — all "
            "outside the static grammar vocabulary. The override "
            "delegates the component render to the grammar and composes "
            "embed + content (goldens/setup/sweep_slash_setup-describe "
            "pins every byte)."),
        session_lifecycle=True,
    )


def sections_hub_spec() -> PanelSpec:
    """The SECTIONS HUB (views/setup/hub.py ``SetupHubView`` +
    ``build_hub_embed``) — the depth click's shipped destination: one
    button per registered section (filtered to the persisted depth by
    the renderer override), plus Change depth + ↩ Back to wizard on the
    nav row. Section buttons hold the honest section-flows terminal;
    Change depth re-opens the chooser (live)."""
    from sb.domain.setup.sections import SECTIONS

    section_actions = tuple(
        PanelActionSpec(
            action_id=f"section_{s.slug}", label=s.label,
            emoji=s.emoji,
            style=(ActionStyle.SUCCESS if s.slug == "preset_select"
                   else ActionStyle.SECONDARY),
            handler=HandlerRef(f"setup.open_section_{s.slug}"),
            custom_id_override=f"setup_section:{s.slug}")
        for s in SECTIONS)
    slugs = tuple(f"section_{s.slug}" for s in SECTIONS)
    return PanelSpec(
        panel_id=SECTIONS_HUB_PANEL_ID,
        subsystem="setup",
        title=_SECTIONS_HUB_TITLE,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        actions=section_actions + (
            PanelActionSpec(
                action_id="change_depth", label="Change depth",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.change_depth"),
                custom_id_override="setup_hub:change_depth"),
            PanelActionSpec(
                action_id="back_to_wizard", label="↩ Back to wizard",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.back_to_wizard"),
                custom_id_override="setup_hub:back_to_wizard"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            slugs[:5], slugs[5:],
            ("change_depth", "back_to_wizard"))),)),
        renderer_override=HandlerRef("setup.sections_hub_render"),
        justification=(
            "the shipped hub embed is state-parameterized end to end "
            "(the Status/depth/current-step/readiness description line, "
            "the badge-prefixed Sections list, the Next-step hint — "
            "hub.build_hub_embed) and its BUTTON SET is depth-filtered "
            "at render (SetupHubView.__init__ REGISTRY.for_depth) — "
            "both outside the static grammar vocabulary; the override "
            "renders through the grammar then composes the embed and "
            "filters/repacks the section rows (no golden pins this "
            "panel — the oracle source does)."),
        session_lifecycle=True,
    )


def review_item_spec() -> PanelSpec:
    """The per-suggestion walkthrough card (views/setup/ai_review/
    per_recommendation.py): Accept · Deny · Edit / Skip · Back to
    overview over one recommendation at a time."""
    return PanelSpec(
        panel_id=REVIEW_ITEM_PANEL_ID,
        subsystem="setup",
        title="🤖 Smart suggestions",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="item_accept", label="Accept",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.review_item_accept")),
            PanelActionSpec(
                action_id="item_deny", label="Deny",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.review_item_deny")),
            PanelActionSpec(
                action_id="item_edit", label="Edit",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.review_item_edit_pending")),
            PanelActionSpec(
                action_id="item_skip", label="Skip",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.review_item_skip")),
            PanelActionSpec(
                action_id="item_back", label="Back to overview",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.review_item_back")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("item_accept", "item_deny", "item_edit"),
            ("item_skip", "item_back"))),)),
        renderer_override=HandlerRef("setup.review_item_render"),
        justification=(
            "the shipped walkthrough card is index-parameterized in "
            "title (Suggestion i/N · accepted/pending), description "
            "(the per-recommendation lines), footer (the accepted "
            "count) and COLOR (the per-confidence accent — "
            "per_recommendation._CONFIDENCE_COLOR); all outside the "
            "static grammar vocabulary, so the override composes the "
            "embed (no golden pins it — the oracle source does)."),
        session_lifecycle=True,
    )


# --- renderer overrides ---------------------------------------------------------------

async def _render_depth(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped footer literal."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    return dataclasses.replace(
        base, embed=dataclasses.replace(base.embed, footer=_DEPTH_FOOTER))


async def _render_essential(spec: PanelSpec, ctx) -> object:
    """renderer_override — grammar render + the shipped footer/field
    literals (essential_setup.py Step 1). A recorded pick renders the
    shipped Starter-set field byte (``ServerTypeStep.render``'s
    picked branch); the fresh OPEN stays the golden-pinned
    '_pick one above_' placeholder."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    params = getattr(ctx, "params", {}) or {}
    starter = "_pick one above_"
    kind = str(params.get("essential_kind", "") or "")
    if kind:
        from sb.domain.setup.wizard import server_type

        preset = server_type(kind)
        if preset is not None:
            starter = f"{preset.emoji} **{preset.label}** — {preset.blurb}"
    embed = dataclasses.replace(
        base.embed,
        fields=(("Starter set", starter, False),),
        footer="Step 1 of 8")
    return dataclasses.replace(base, embed=embed)


async def _render_status(spec: PanelSpec, ctx) -> object:
    """renderer_override — cogs/setup/_helpers.build_status_embed, the
    session-less slice verbatim; a session-bearing row renders the bare
    status line (the fuller pending-ops/readiness fields land with the
    wizard-lifecycle slice — no golden drives them)."""
    from sb.kernel.panels.render import RenderedEmbed, RenderedPanel

    params = getattr(ctx, "params", {}) or {}
    session = params.get("setup_session")
    status = (str(session.get("setup_status"))
              if isinstance(session, dict) else "no session")
    fields: tuple = ()
    if session is None:
        fields = (
            ("No session row",
             "The bot has not recorded any setup session for this guild. "
             "Run `!setup` or `/setup` to start.", False),
        )
    embed = RenderedEmbed(
        title=spec.title,
        description=f"**Status:** `{status}`",
        fields=fields,
        style_token=spec.frame.style_token)
    return RenderedPanel(
        panel_id=spec.panel_id, embed=embed, components=(),
        invoker_lock=getattr(ctx.actor, "user_id", None),
        timeout_s=spec.timeout_s, audience=spec.audience.value,
        anchor_policy=spec.anchor_policy.value)


async def _render_suggestions(spec: PanelSpec, ctx) -> object:
    """renderer_override — views/setup/ai_review/main_panel.py verbatim:
    the header + count description, per-subsystem recommendation fields
    (first-appearance subsystem order, one icon-prefixed line per rec),
    the Dropped list capped at 5, the deterministic-note content line."""
    import dataclasses

    from sb.kernel.panels.render import RenderedEmbed, render_panel

    params = getattr(ctx, "params", {}) or {}
    draft = params.get("setup_plan_draft")
    recommendations = tuple(getattr(draft, "recommendations", ()) or ())
    dropped = tuple(getattr(draft, "dropped", ()) or ())
    source = str(getattr(draft, "source", "deterministic"))
    counts = {c: sum(1 for r in recommendations if r.confidence == c)
              for c in ("high", "medium", "low")}
    description = (
        f"_{_REVIEW_HEADER}_\n\n"
        f"**High:** {counts['high']} · **Medium:** {counts['medium']} · "
        f"**Low:** {counts['low']} · **Source:** `{source}`")
    grouped: dict[str, list[str]] = {}
    for rec in recommendations:
        icon = _CONFIDENCE_ICON.get(rec.confidence, "⚪")
        grouped.setdefault(rec.subsystem, []).append(
            f"{icon} `{rec.binding_name}` → `{rec.target_name}` — "
            f"{rec.reason}")
    fields = [(subsystem, "\n".join(lines), False)
              for subsystem, lines in grouped.items()]
    if dropped:
        dropped_value = "\n".join(f"• {d}" for d in dropped[:5])
        if len(dropped) > 5:
            dropped_value += f"\n_+{len(dropped) - 5} more not shown_"
        fields.append(("Dropped", dropped_value, False))
    base = await render_panel(spec, ctx)
    # the shipped confidence accent (main_panel.build_ai_review_embed:
    # green if high else gold if medium else dark_grey) + the last-action
    # footer the click lanes stamp (AIReviewPanelView._refresh_embed).
    token = ("green" if counts["high"] else
             "gold" if counts["medium"] else "dark_grey")
    embed = RenderedEmbed(
        title=spec.title,
        description=description,
        fields=tuple(fields),
        footer=str(params.get("review_status") or ""),
        style_token=token)
    return dataclasses.replace(
        base, embed=embed, content=str(params.get("advisor_note") or "") or None)


async def _render_sections_hub(spec: PanelSpec, ctx) -> object:
    """renderer_override — hub.build_hub_embed verbatim over the ported
    state reads: the session row (status/depth/current-step/readiness
    description line), the K9 staged-op count, the badge-prefixed
    Sections list at the persisted depth, the Next-step hint subset this
    build can reach, the shipped footer; components filter to the
    depth's sections and repack five-per-row (the shipped add_item
    flow)."""
    import dataclasses

    from sb.domain.setup import store, wizard
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    guild_id = int(ctx.guild_id or 0)
    session = await store.get_session_row(guild_id)
    try:
        pending_ops = await wizard.staged_ops_count(guild_id)
    except Exception:  # noqa: BLE001 — the shipped list_ops soft-fail
        pending_ops = 0

    status = str(session.get("setup_status") or "") if session else ""
    depth = (str(session["depth"]) if session and session.get("depth")
             else None)
    complete = status == "complete"

    description = _SECTIONS_HUB_DESCRIPTION
    if session is not None:
        description = (f"{_SECTIONS_HUB_DESCRIPTION}\n\n"
                       f"**Status:** `{status}`")
        if depth:
            description += f" · depth: `{depth}`"
        if session.get("current_step"):
            description += f" · current step: `{session['current_step']}`"
        if session.get("last_readiness_score") is not None:
            description += (f" · readiness "
                            f"`{session['last_readiness_score']}%`")
    prefix = (description + "\n\n" if "**Status:**" not in description
              else description + " · ")
    description = f"{prefix}**Pending operations:** `{pending_ops}`"

    sections = wizard.sections_for_depth(depth)
    skipped = set(session.get("skipped_sections") or ()) if session else set()
    acked = (set(session.get("acknowledged_sections") or ())
             if session else set())
    lines = []
    not_started = 0
    for idx, section in enumerate(sections, start=1):
        if section.slug in skipped:
            glyph = _BADGE_SKIPPED
        elif complete or section.slug in acked:
            glyph = _BADGE_APPLIED
        else:
            glyph = _BADGE_NOT_STARTED
            not_started += 1
        lines.append(f"{glyph} {idx}. {section.label}")
    fields = [("Sections",
               "\n".join(lines) if lines else "_No sections registered._",
               False)]

    # the shipped next-step hint ladder, the reachable subset (the
    # recommended-path branch needs the section builders — section-flows
    # slice): complete → the summary pointer; staged ops → the Final-
    # review pointers; else the pick prompt.
    if complete:
        hint = "✅ Setup is complete. Click **View Summary** for the digest."
    elif pending_ops and not not_started:
        hint = ("🚀 Every section has staged ops. Open **Final Review** "
                "to apply.")
    elif pending_ops:
        hint = (f"📝 **{pending_ops}** op(s) staged. Either open more "
                f"sections or go to **Final Review**.")
    else:
        hint = "👉 Pick a section to begin."
    fields.append(("Next step", hint, False))

    base = await render_panel(spec, ctx)
    allowed = {f"setup_section:{s.slug}" for s in sections}
    allowed |= {"setup_hub:change_depth", "setup_hub:back_to_wizard"}
    kept = [c for c in base.components if c.custom_id in allowed]
    repacked = []
    nav_row = (len([c for c in kept
                    if c.custom_id.startswith("setup_section:")]) - 1) // 5 + 1
    section_i = 0
    for component in kept:
        if component.custom_id.startswith("setup_section:"):
            row = section_i // 5
            section_i += 1
        else:
            row = nav_row
        repacked.append(dataclasses.replace(component, row=row))

    embed = RenderedEmbed(
        title=spec.title,
        description=description,
        fields=tuple(fields),
        footer=_SECTIONS_HUB_FOOTER,
        style_token="green" if complete else "blurple")
    return dataclasses.replace(base, embed=embed,
                               components=tuple(repacked))


async def _render_review_item(spec: PanelSpec, ctx) -> object:
    """renderer_override — per_recommendation.build_per_recommendation_
    embed verbatim: one recommendation at the walkthrough index, the
    accepted/pending title state, the per-confidence accent, the
    accepted-count footer."""
    import dataclasses

    from sb.domain.setup import wizard
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    state = await wizard.review_state(
        int(ctx.guild_id or 0), int(getattr(ctx.actor, "user_id", 0) or 0))
    recs = tuple(state.draft.recommendations)
    base = await render_panel(spec, ctx)
    if not recs:
        embed = RenderedEmbed(
            title="🤖 Smart suggestions",
            description="No recommendations to review.",
            style_token="dark_grey")
        return dataclasses.replace(base, embed=embed)
    index = max(0, min(state.index, len(recs) - 1))
    rec = recs[index]
    accepted = state.contains(rec)
    state_label = "✅ accepted" if accepted else "⬜ pending"
    # the deterministic advisor's recommendations are all ``bind`` mode
    # (the shipped mode default) — the bind target line renders.
    target_line = f"**Target:** `{rec.target_name}` (id `{rec.target_id}`)\n"
    source = getattr(rec, "source", None) or str(
        getattr(state.draft, "source", "deterministic"))
    embed = RenderedEmbed(
        title=f"🤖 Suggestion {index + 1} / {len(recs)} · {state_label}",
        description=(
            f"**Subsystem:** `{rec.subsystem}`\n"
            f"**Binding:** `{rec.binding_name}` (`{rec.target_kind}`)\n"
            f"{target_line}"
            f"**Confidence:** `{rec.confidence}`\n"
            f"**Source:** `{source}`\n\n"
            f"_{rec.reason}_"),
        footer=(f"Accepted set: {state.count} · Accept / Deny / Edit"
                f" · Skip to defer, Back to return."),
        style_token=_CONFIDENCE_TOKEN.get(rec.confidence, "blurple"))
    return dataclasses.replace(base, embed=embed)


# --- registration ---------------------------------------------------------------------

@panel(HUB_PANEL_ID)
def _hub_factory() -> PanelSpec:
    return setup_hub_spec()


@panel(ESSENTIAL_PANEL_ID)
def _essential_factory() -> PanelSpec:
    return essential_card_spec()


@panel(STATUS_PANEL_ID)
def _status_factory() -> PanelSpec:
    return status_card_spec()


@panel(SUGGESTIONS_PANEL_ID)
def _suggestions_factory() -> PanelSpec:
    return suggestions_card_spec()


@panel(SECTIONS_HUB_PANEL_ID)
def _sections_hub_factory() -> PanelSpec:
    return sections_hub_spec()


@panel(REVIEW_ITEM_PANEL_ID)
def _review_item_factory() -> PanelSpec:
    return review_item_spec()


handler("setup.depth_render")(_render_depth)
handler("setup.essential_render")(_render_essential)
handler("setup.status_render")(_render_status)
handler("setup.suggestions_render")(_render_suggestions)
handler("setup.sections_hub_render")(_render_sections_hub)
handler("setup.review_item_render")(_render_review_item)

_ensure_providers()


def install_setup_panels() -> PanelSpec:
    """Register the six panels; returns the hub spec (the band-1 test
    contract — tests/unit/setup_band/test_band1_setup.py)."""
    out: PanelSpec | None = None
    for spec in (setup_hub_spec(), essential_card_spec(),
                 status_card_spec(), suggestions_card_spec(),
                 sections_hub_spec(), review_item_spec()):
        try:
            registered = register_panel(spec)
        except ValueError as exc:
            if "already registered" in str(exc) or "duplicate" in str(exc):
                registered = spec
            else:
                raise
        if spec.panel_id == HUB_PANEL_ID:
            out = registered
    assert out is not None
    return out


def ensure_setup_refs() -> None:
    _ensure_providers()
    from sb.domain.setup.wizard import ensure_wizard_refs

    ensure_wizard_refs()
    from sb.spec.refs import handler as _handler
    from sb.spec.refs import is_registered as _is

    for name, fn in (("setup.depth_render", _render_depth),
                     ("setup.essential_render", _render_essential),
                     ("setup.status_render", _render_status),
                     ("setup.suggestions_render", _render_suggestions),
                     ("setup.sections_hub_render", _render_sections_hub),
                     ("setup.review_item_render", _render_review_item)):
        if not _is(HandlerRef(name)):
            _handler(name)(fn)
    for pid, factory in ((HUB_PANEL_ID, _hub_factory),
                         (ESSENTIAL_PANEL_ID, _essential_factory),
                         (STATUS_PANEL_ID, _status_factory),
                         (SUGGESTIONS_PANEL_ID, _suggestions_factory),
                         (SECTIONS_HUB_PANEL_ID, _sections_hub_factory),
                         (REVIEW_ITEM_PANEL_ID, _review_item_factory)):
        if not _is(PanelRef(pid)):
            panel(pid)(factory)
