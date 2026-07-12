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
save/skip steps, the review panel's accept/stage lanes) stays a named
successor: every component routes to the declared honest-refusal terminal
(the D-0030 pending posture) until the wizard-lifecycle slice ports it —
no golden drives a click on any of these components.
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

#: the wizard-interior pending terminal (D-0030 posture — declared surface,
#: honest BLOCKED refusal, never silent; the wizard-lifecycle slice retires
#: it when the section flows port).
_PENDING_MSG = ("The setup wizard's interactive steps aren't armed in this "
                "build yet — they land with the wizard-lifecycle slice.")


def _pending() -> HandlerRef:
    from sb.domain.operator_spine import pending_handler

    return pending_handler("setup.wizard_pending", _PENDING_MSG)


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
                style=ActionStyle.SECONDARY, handler=_pending(),
                custom_id_override="setup_depth:quick"),
            PanelActionSpec(
                action_id="depth_standard", label="🛠 Standard",
                style=ActionStyle.SECONDARY, handler=_pending(),
                custom_id_override="setup_depth:standard"),
            PanelActionSpec(
                action_id="depth_advanced", label="🔬 Advanced",
                style=ActionStyle.SECONDARY, handler=_pending(),
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
                emoji="✨", style=ActionStyle.SUCCESS, handler=_pending()),
            PanelActionSpec(
                action_id="essential_skip",
                label="Skip — set things up myself",
                style=ActionStyle.SECONDARY, handler=_pending()),
        ),
        selectors=(
            SelectorSpec(
                selector_id="essential_kind", kind=SelectorKind.ENUM,
                on_select=_pending(),
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
                style=ActionStyle.SUCCESS, handler=_pending()),
            PanelActionSpec(
                action_id="review_one_by_one", label="Review one-by-one",
                style=ActionStyle.PRIMARY, handler=_pending()),
            PanelActionSpec(
                action_id="reject_ai_suggestions",
                label="Reject all AI suggestions",
                style=ActionStyle.DANGER, handler=_pending()),
            PanelActionSpec(
                action_id="rerun_deterministic",
                label="Rerun deterministic-only",
                style=ActionStyle.SECONDARY, handler=_pending()),
            PanelActionSpec(
                action_id="stage_final_review",
                label="Stage & open Final review",
                style=ActionStyle.SUCCESS, handler=_pending()),
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
    literals (essential_setup.py Step 1)."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    embed = dataclasses.replace(
        base.embed,
        fields=(("Starter set", "_pick one above_", False),),
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
    embed = RenderedEmbed(
        title=spec.title,
        description=description,
        fields=tuple(fields),
        style_token=spec.frame.style_token)
    return dataclasses.replace(
        base, embed=embed, content=str(params.get("advisor_note") or "") or None)


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


handler("setup.depth_render")(_render_depth)
handler("setup.essential_render")(_render_essential)
handler("setup.status_render")(_render_status)
handler("setup.suggestions_render")(_render_suggestions)

_ensure_providers()


def install_setup_panels() -> PanelSpec:
    """Register the four panels; returns the hub spec (the band-1 test
    contract — tests/unit/setup_band/test_band1_setup.py)."""
    out: PanelSpec | None = None
    for spec in (setup_hub_spec(), essential_card_spec(),
                 status_card_spec(), suggestions_card_spec()):
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
    _pending()
    from sb.spec.refs import handler as _handler
    from sb.spec.refs import is_registered as _is

    for name, fn in (("setup.depth_render", _render_depth),
                     ("setup.essential_render", _render_essential),
                     ("setup.status_render", _render_status),
                     ("setup.suggestions_render", _render_suggestions)):
        if not _is(HandlerRef(name)):
            _handler(name)(fn)
    for pid, factory in ((HUB_PANEL_ID, _hub_factory),
                         (ESSENTIAL_PANEL_ID, _essential_factory),
                         (STATUS_PANEL_ID, _status_factory),
                         (SUGGESTIONS_PANEL_ID, _suggestions_factory)):
        if not _is(PanelRef(pid)):
            panel(pid)(factory)
