"""The SECTION-FLOW SPINE (the section-flows slice), ported from the
oracle (menno420/superbot, read from the LOCAL oracle clone):

* the SECTION CARD (views/setup/section_card.py ``build_section_card``
  + ``SectionCardView``) — the shared entry panel every staged
  section reuses: step counter, status badge, Detected / Recommended
  action / If-you-skip-this / Pending fields, and the four-button row
  **Apply Recommended** · **Customize** · **Skip** · **↩ Hub** (the
  shipped ``setup_card:{slug}:*`` persistent custom_ids, compat-pinned);
* the per-section STATUS vocabulary (services/setup_progress.py):
  not_started / recommended / customized / skipped / needs_attention /
  applied, the badge glyphs, and ``compute_section_status``'s decision
  order verbatim;
* the STAGING SEAMS (services/setup_draft.py, folded onto the K9
  draft store): ``replace_recommended_for_section`` — the sole writer
  of recommended rows: prior recommended rows for the section drop,
  non-recommended rows at a conflicting slot are PRESERVED (never
  overwritten) and surfaced as conflicts; ``stage_custom`` — the
  shipped append's replace-on-conflict slot semantics (a re-pick
  replaces the previous draft entry, it does not duplicate);
* the SKIP lane: ``mark_section_skipped`` through the K7
  ``setup.set_section_skip`` op + the wizard's provenance-aware
  delete (rows the section owns drop so Final Review never applies an
  op the operator skipped);
* the step marker: every card open / staging lane records
  ``current_step`` through the K7 ``setup.mark_in_progress`` op (the
  oracle ``setup_session.mark_in_progress``, best-effort).

Kernel-idiom divergences, ledgered (the final_review.py /
essential_steps.py adaptation doctrine — same copy, same labels, same
flow; only the seams differ):

* SECTION PROVENANCE rides the K9 ``DraftOperation.label`` as a
  parseable prefix — ``[recommended:<slug>] `` for recommended rows,
  ``[<slug>] `` for section-custom rows (the wizard.py
  ``[suggestions] `` precedent). The oracle carried ``section_slug`` +
  ``staging_kind`` as typed columns (migration 035) with cosmetic
  labels on top; the K9 row has no such columns, so the label IS the
  provenance seam. Rows with NO known prefix (the suggestions lane,
  preset-staged rows) fall back to the ``op.kind in section.op_kinds``
  match — exactly the oracle's null-provenance fallback
  (setup_progress's matching strategy);
* the oracle disabled dead buttons; the renderer here stamps
  ``disabled`` on the rendered component (the casino/creature
  disabled-patch precedent);
* the oracle's ephemeral confirmations answer as text replies carrying
  the copy verbatim; ↩ Hub answers the shipped
  "Returning to the setup hub above." (the hub message stays the
  operator's anchor — no view swap to undo);
* staged K9 rows carry no oracle metadata dict (source/confidence/
  risk) — the final_review.py ledger note's class.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "GATE_MSG_CARD",
    "SECTION_SKIP_DESCRIPTIONS",
    "SectionProgress",
    "StagedSectionOp",
    "badge_for",
    "build_section_card_embed",
    "compute_section_status",
    "delete_section_rows",
    "ensure_section_card_refs",
    "guild_ops",
    "mark_step_in_progress",
    "mark_section_skipped",
    "recommended_builder",
    "register_recommended_builder",
    "register_customize_panel",
    "register_section_card",
    "replace_recommended_for_section",
    "reset_section_card_state_for_tests",
    "stage_custom",
    "status_label",
]

logger = logging.getLogger("sb.domain.setup")

#: shipped gate refusal, verbatim (section_card.SectionCardView._gate_apply
#: — the "stage or skip" spelling; the hub's run-the-wizard gate copy is
#: wizard.GATE_MSG_WIZARD).
GATE_MSG_CARD = ("Only the server owner or a delegated setup admin can stage "
                 "or skip setup operations. Ask the server owner to grant "
                 "you `/setup-delegate`.")

#: the shipped per-section skip-impact copy, verbatim
#: (views/setup/sections/*.py ``description_if_skipped`` — carried as
#: data because the ported WizardSectionSpec deliberately has no
#: description facet, the SECTION_DEPTHS precedent). final_review
#: declared none.
SECTION_SKIP_DESCRIPTIONS: dict[str, str] = {
    "preset_select": (
        "No bundled preset is staged. Configure channels, cleanup, and "
        "routing one section at a time, or load a preset later."),
    "channels": (
        "SuperBot keeps the current command-channel rules and may not "
        "have a dedicated log channel. Configure these later in "
        "`!settings`."),
    "logging_presets": (
        "SuperBot keeps the existing channel routing.  You can "
        "still bind individual log channels via `!settings` or "
        "the Channels section."),
    "roles": (
        "No automatic role progression is configured — members keep "
        "whatever roles they have. You can set time / XP tiers later in "
        "`!roles` without re-running the wizard."),
    "role_templates": (
        "No template roles are created — the server keeps whatever roles it "
        "has. You can apply a role template later from `/setup` without "
        "re-running the whole wizard."),
    "cleanup": (
        "Cleanup stays at the current server default. Commands will not "
        "be aggressively deleted unless existing policies already say "
        "so. You can revisit cleanup later from `!settings`."),
    "moderation": (
        "Moderation keeps its current behaviour — no DM on action, reasons "
        "optional, warns escalate to a timeout at the threshold, and only "
        "Discord-permission holders can moderate. Configure later in "
        "`!settings → Moderation`."),
    "cog_routing": (
        "All loaded cogs stay enabled in every channel per the current "
        "default policy. You can tighten per-channel/category routing "
        "later in `!settings`."),
    "ticket": (
        "Tickets stay disabled — members can't open private support tickets "
        "until you enable them here or run `!ticketsetup`."),
}


# --- the status vocabulary (services/setup_progress.py, verbatim) ---------------------

NOT_STARTED = "not_started"
RECOMMENDED = "recommended"
CUSTOMIZED = "customized"
SKIPPED = "skipped"
NEEDS_ATTENTION = "needs_attention"
APPLIED = "applied"

_BADGE_BY_STATUS: dict[str, str] = {
    NOT_STARTED: "⬜",
    RECOMMENDED: "✅",
    CUSTOMIZED: "🟡",
    SKIPPED: "⚠️",
    NEEDS_ATTENTION: "❗",
    APPLIED: "✅",
}

#: section_card._STATUS_LABELS, verbatim.
_STATUS_LABELS: dict[str, str] = {
    NOT_STARTED: "Not started",
    RECOMMENDED: "Recommended selected",
    CUSTOMIZED: "Customized",
    SKIPPED: "Skipped",
    NEEDS_ATTENTION: "Needs attention",
    APPLIED: "Applied",
}


def badge_for(status: str) -> str:
    """setup_progress.badge_for, verbatim glyphs."""
    return _BADGE_BY_STATUS.get(status, "⬜")


def status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


@dataclass(frozen=True)
class SectionProgress:
    """setup_progress.SectionProgress, verbatim shape."""

    slug: str
    status: str
    pending_ops: int


# --- section provenance over K9 rows (the label micro-grammar) ------------------------

def _recommended_prefix(slug: str) -> str:
    return f"[recommended:{slug}] "


def _custom_prefix(slug: str) -> str:
    return f"[{slug}] "


def row_section(label: str) -> tuple[str | None, bool]:
    """Parse (section_slug | None, is_recommended) from a staged row's
    label — the ported ``section_slug`` / ``staging_kind`` provenance
    (module docstring). Unknown prefixes (``[suggestions] ``, preset
    labels) answer ``(None, False)`` — the op_kinds fallback's input."""
    from sb.domain.setup.sections import SECTIONS

    for section in SECTIONS:
        if label.startswith(_recommended_prefix(section.slug)):
            return section.slug, True
        if label.startswith(_custom_prefix(section.slug)):
            return section.slug, False
    return None, False


def _matches_section(op, section) -> bool:
    """setup_progress._entry_matches_section: provenance first, the
    ``op.kind in section.op_kinds`` fallback for null-provenance rows."""
    slug, _rec = row_section(str(getattr(op, "label", "") or ""))
    if slug is not None:
        return slug == section.slug
    if not section.op_kinds:
        return False
    return str(getattr(op, "op_kind", "")) in section.op_kinds


def _is_recommended(op) -> bool:
    _slug, rec = row_section(str(getattr(op, "label", "") or ""))
    return rec


def compute_section_status(section, *, session: dict | None,
                           ops) -> SectionProgress:
    """setup_progress.compute_section_status — the decision order
    verbatim: SKIPPED → APPLIED (complete) → APPLIED (acknowledged,
    no staging) → NOT_STARTED → RECOMMENDED → CUSTOMIZED."""
    skipped = set(session.get("skipped_sections") or ()) if session else set()
    acked = (set(session.get("acknowledged_sections") or ())
             if session else set())
    if section.slug in skipped:
        return SectionProgress(slug=section.slug, status=SKIPPED,
                               pending_ops=0)
    matching = [op for op in ops if _matches_section(op, section)]
    pending = len(matching)
    if session is not None and str(session.get("setup_status")) == "complete":
        return SectionProgress(slug=section.slug, status=APPLIED,
                               pending_ops=pending)
    if not matching and section.slug in acked:
        return SectionProgress(slug=section.slug, status=APPLIED,
                               pending_ops=0)
    if not matching:
        return SectionProgress(slug=section.slug, status=NOT_STARTED,
                               pending_ops=0)
    if all(_is_recommended(op) for op in matching):
        return SectionProgress(slug=section.slug, status=RECOMMENDED,
                               pending_ops=pending)
    return SectionProgress(slug=section.slug, status=CUSTOMIZED,
                           pending_ops=pending)


# --- the staged-row reads/writes over the K9 store -------------------------------------

@dataclass(frozen=True)
class StagedSectionOp:
    """One section-built op headed for the draft (the recommended
    builders' output shape — the oracle SetupOperation's reachable
    subset)."""

    op_kind: str
    subsystem: str
    payload: dict
    label_body: str = ""    # the oracle's cosmetic label tail

    @property
    def slot(self) -> tuple[str, str, str]:
        """The oracle slot key (op_kind, subsystem, name) — setting and
        binding names both ride the payload's ``name``."""
        return (self.op_kind, self.subsystem,
                str(self.payload.get("name") or ""))


def _op_slot(op) -> tuple[str, str, str]:
    payload = dict(getattr(op, "payload", {}) or {})
    return (str(getattr(op, "op_kind", "")), str(getattr(op, "subsystem", "")),
            str(payload.get("name") or ""))


async def guild_ops(guild_id: int) -> list:
    """Every staged op across the guild's open drafts (the oracle
    ``setup_draft.list_rows`` read)."""
    from sb.domain.setup import wizard

    drafts = await wizard._open_guild_drafts(int(guild_id))
    return [(draft, op) for draft in drafts for op in draft.operations]


async def _open_or_create_draft(guild_id: int):
    from sb.domain.setup.wizard import _guild_scope
    from sb.kernel.draft.store import DraftStore
    from sb.spec.draft import Producer

    store = DraftStore()
    drafts = await store.list_open(_guild_scope(int(guild_id)))
    if drafts:
        return store, drafts[0]
    draft = await store.create(producer=Producer.HUMAN_SETUP,
                               owner_scope=_guild_scope(int(guild_id)))
    return store, draft


@dataclass
class ReplaceRecommendedResult:
    """setup_draft.ReplaceRecommendedResult, the ported shape (conflicts
    carry the refused ops' labels)."""

    inserted: int = 0
    deleted: int = 0
    conflicts: list[str] = field(default_factory=list)


async def replace_recommended_for_section(
        guild_id: int, slug: str,
        ops: list[StagedSectionOp]) -> ReplaceRecommendedResult:
    """setup_draft.replace_recommended_for_section semantics over the
    K9 store — the SOLE writer of recommended rows: drop the section's
    prior recommended rows, refuse (never overwrite) any slot a
    non-recommended row occupies, insert the rest."""
    from sb.kernel.draft.store import DraftStore
    from sb.spec.draft import DraftOperation

    if not slug:
        raise ValueError("section_slug must be non-empty")
    store = DraftStore()
    _store, draft = await _open_or_create_draft(guild_id)
    result = ReplaceRecommendedResult()

    # step 1 — delete prior recommended rows owned by this section.
    surviving = []
    for op in draft.operations:
        row_slug, rec = row_section(str(op.label or ""))
        if row_slug == slug and rec:
            await store.remove(draft.draft_id, op.op_seq)
            result.deleted += 1
        else:
            surviving.append(op)
    surviving_slots = {_op_slot(op): op for op in surviving}

    # step 2 — insert, preserving non-recommended rows at conflicting
    # slots (custom / preset / manual rows are never overwritten).
    prefix = _recommended_prefix(slug)
    for new in ops:
        conflict = surviving_slots.get(new.slot)
        if conflict is not None and not _is_recommended(conflict):
            result.conflicts.append(str(conflict.label or ""))
            continue
        await store.add(draft.draft_id, DraftOperation(
            op_seq=0,           # append_operation assigns the real sequence
            op_kind=new.op_kind, subsystem=new.subsystem,
            authority_ref="",   # the ADMIN floor (the staged ops' own)
            payload=dict(new.payload),
            label=f"{prefix}{new.label_body or new.op_kind}"))
        result.inserted += 1
    return result


async def stage_custom(guild_id: int, slug: str,
                       op: StagedSectionOp) -> None:
    """The shipped ``setup_draft.append`` replace-on-conflict slot
    semantics (its own docstring: "a re-edit replaces the previous
    draft entry; it does not duplicate") — any prior row at the same
    slot drops, then the custom row lands with the section's
    provenance prefix."""
    from sb.kernel.draft.store import DraftStore
    from sb.spec.draft import DraftOperation

    store = DraftStore()
    _store, draft = await _open_or_create_draft(guild_id)
    for prior in draft.operations:
        if _op_slot(prior) == op.slot:
            await store.remove(draft.draft_id, prior.op_seq)
    await store.add(draft.draft_id, DraftOperation(
        op_seq=0,
        op_kind=op.op_kind, subsystem=op.subsystem,
        authority_ref="",
        payload=dict(op.payload),
        label=f"{_custom_prefix(slug)}{op.label_body or op.op_kind}"))


async def delete_section_rows(guild_id: int, slug: str) -> int:
    """The wizard skip's provenance-aware delete (wizard._on_skip →
    setup_draft.list_by_section + delete_by_ids): drop every row this
    section OWNS (label-provenance match only — null-provenance rows
    are never guessed at)."""
    from sb.kernel.draft.store import DraftStore

    store = DraftStore()
    deleted = 0
    pairs = await guild_ops(guild_id)
    for draft, op in pairs:
        row_slug, _rec = row_section(str(op.label or ""))
        if row_slug == slug:
            await store.remove(draft.draft_id, op.op_seq)
            deleted += 1
    return deleted


# --- the K7 session writes --------------------------------------------------------------

async def mark_step_in_progress(req, step: str) -> None:
    """The oracle ``setup_session.mark_in_progress`` — best-effort (a
    DB hiccup never breaks the flow, the persist_progress posture)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    try:
        await engine.run(WorkflowRef("setup.mark_in_progress"),
                         ctx_from_request(req, {"step": step}))
    except Exception:  # noqa: BLE001 — the oracle's own posture
        logger.exception("section card: mark_in_progress failed (step=%s)",
                         step)


async def mark_section_skipped(req, slug: str, *, skipped: bool) -> bool:
    """The card/wizard Skip's session write through the K7
    ``setup.set_section_skip`` op; False on any failure (the caller
    surfaces the shipped error copy)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    try:
        result = await engine.run(
            WorkflowRef("setup.set_section_skip"),
            ctx_from_request(req, {"section": slug, "skipped": skipped}))
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception("section card: set_section_skip failed (%s)", slug)
        return False
    return result.outcome == SUCCESS


# --- the per-section plug points (builders / customize destinations) --------------------

#: slug → async (guild_id) -> list[StagedSectionOp] — the oracle
#: ``SetupSection.recommended_ops_builder`` registration slot.
_RECOMMENDED_BUILDERS: dict[str, object] = {}

#: slug → the detail panel id the card's Customize opens — the oracle
#: ``on_customize`` callback slot (the open_panel navigation lane).
_CUSTOMIZE_PANELS: dict[str, str] = {}

#: slug → the card's Detected field copy (the section modules supply
#: ``detected_state`` exactly like the oracle ``show`` callers).
_DETECTED_STATE: dict[str, str] = {}


def register_recommended_builder(slug: str, builder) -> None:
    _RECOMMENDED_BUILDERS[slug] = builder


def register_customize_panel(slug: str, panel_id: str) -> None:
    _CUSTOMIZE_PANELS[slug] = panel_id


def recommended_builder(slug: str):
    return _RECOMMENDED_BUILDERS.get(slug)


def customize_panel(slug: str) -> str | None:
    return _CUSTOMIZE_PANELS.get(slug)


def reset_section_card_state_for_tests() -> None:
    """Plug-point registries survive (module-import registrations);
    nothing else is held here."""


# --- the card embed (section_card.build_section_card, bytes verbatim) -------------------

def _all_sections():
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections

    register_shipped_sections()
    return REGISTRY.ordered()


def _step_index(section, sections) -> int:
    for idx, s in enumerate(sections, start=1):
        if s.slug == section.slug:
            return idx
    return 0


_STATUS_TOKEN = {RECOMMENDED: "green", APPLIED: "green",
                 SKIPPED: "dark_grey", NEEDS_ATTENTION: "gold"}


def build_section_card_embed(*, section, progress: SectionProgress,
                             detected_state: str, has_recommended: bool,
                             has_customize: bool):
    """build_section_card, verbatim bytes over the ported carrier."""
    from sb.kernel.panels.render import RenderedEmbed

    sections = _all_sections()
    total = len(sections)
    step = _step_index(section, sections)
    glyph = badge_for(progress.status)
    label = status_label(progress.status)

    title_emoji = section.emoji or "🛰"
    title = f"{title_emoji} {section.label}"
    description = (f"**Step {step} of {total}** · {glyph} *{label}*"
                   if step else f"{glyph} *{label}*")

    fields: list[tuple] = [
        ("Detected", detected_state or "_(no state detected)_", False),
        ("Recommended action",
         ("Click **Apply Recommended** to stage the section's safe defaults."
          if has_recommended
          else "_(this section has no recommended defaults — use "
               "Customize.)_"),
         False),
    ]
    skip_note = SECTION_SKIP_DESCRIPTIONS.get(section.slug, "")
    if skip_note:
        fields.append(("If you skip this", skip_note, False))
    if progress.pending_ops:
        suffix = "operation" if progress.pending_ops == 1 else "operations"
        fields.append(("Pending",
                       f"{progress.pending_ops} {suffix} staged for Final "
                       "review.",
                       False))
    footer_bits = []
    if has_customize:
        footer_bits.append("Customize to open the detailed picker")
    footer_bits.append("Final Review applies all staged ops")
    return RenderedEmbed(
        title=title, description=description, fields=tuple(fields),
        footer=" · ".join(footer_bits),
        style_token=_STATUS_TOKEN.get(progress.status, "blurple"))


# --- the card panel factory + handlers ---------------------------------------------------

def card_panel_id(slug: str) -> str:
    return f"setup.section_{slug}"


def _card_spec(slug: str, section):
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=card_panel_id(slug),
        subsystem="setup",
        title=f"{section.emoji or '🛰'} {section.label}",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id=f"{slug}_apply_recommended",
                label="Apply Recommended", style=ActionStyle.SUCCESS,
                handler=HandlerRef(f"setup.section_apply_{slug}"),
                custom_id_override=f"setup_card:{slug}:apply_recommended"),
            PanelActionSpec(
                action_id=f"{slug}_customize", label="Customize",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef(f"setup.section_customize_{slug}"),
                custom_id_override=f"setup_card:{slug}:customize"),
            PanelActionSpec(
                action_id=f"{slug}_skip", label="Skip",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef(f"setup.section_skip_{slug}"),
                custom_id_override=f"setup_card:{slug}:skip"),
            PanelActionSpec(
                action_id=f"{slug}_hub", label="↩ Hub",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef(f"setup.section_hub_{slug}"),
                custom_id_override=f"setup_card:{slug}:hub"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            (f"{slug}_apply_recommended", f"{slug}_customize",
             f"{slug}_skip", f"{slug}_hub"),)),)),
        renderer_override=HandlerRef(f"setup.section_card_render_{slug}"),
        justification=(
            "the shipped section card is session/draft-parameterized end "
            "to end (the Step-X-of-N + status-badge description, the "
            "Detected / Pending fields, the per-status accent — "
            "section_card.build_section_card) and its dead buttons render "
            "disabled (SectionCardView.__init__) — outside the static "
            "grammar vocabulary; the override renders through the grammar "
            "and composes the embed (no golden pins it — the oracle "
            "source does)."),
        session_lifecycle=True,
    )


def _card_renderer(slug: str, section):
    async def _render(spec, ctx):
        import dataclasses

        from sb.domain.setup import store

        guild_id = int(ctx.guild_id or 0)
        try:
            session = await store.get_session_row(guild_id)
        except Exception:  # noqa: BLE001 — the shipped resume soft-fail
            logger.exception("section_card.show: resume_session failed")
            session = None
        try:
            ops = [op for _d, op in await guild_ops(guild_id)]
        except Exception:  # noqa: BLE001 — the shipped list_rows soft-fail
            logger.exception("section_card.show: list_rows failed")
            ops = []
        progress = compute_section_status(section, session=session, ops=ops)
        has_recommended = recommended_builder(slug) is not None
        has_customize = customize_panel(slug) is not None
        embed = build_section_card_embed(
            section=section, progress=progress,
            detected_state=_DETECTED_STATE.get(slug, ""),
            has_recommended=has_recommended, has_customize=has_customize)

        from sb.kernel.panels.render import render_panel

        base = await render_panel(spec, ctx)
        components = []
        for c in base.components:
            if (c.custom_id == f"setup_card:{slug}:apply_recommended"
                    and not has_recommended):
                c = dataclasses.replace(c, disabled=True)
            if (c.custom_id == f"setup_card:{slug}:customize"
                    and not has_customize):
                c = dataclasses.replace(c, disabled=True)
            components.append(c)
        return dataclasses.replace(base, embed=embed,
                                   components=tuple(components))
    return _render


async def _gated_card(req) -> bool:
    """The card's per-button re-check (SectionCardView._gate_apply —
    the ported can_apply_setup ladder; a delegated admin who lost
    delegation between opening the card and pressing a button cannot
    mutate the draft)."""
    from sb.domain.setup import wizard

    return await wizard.can_apply_setup(req)


async def apply_recommended_flow(req, slug: str, section) -> Reply:
    """The shared Apply-Recommended body (SectionCardView.
    _apply_recommended — the wizard's button routes here too)."""
    if not await _gated_card(req):
        return Reply(BLOCKED, GATE_MSG_CARD)
    builder = recommended_builder(slug)
    if builder is None:
        # shipped copy, verbatim.
        return Reply(BLOCKED, "This section has no recommended defaults.")
    guild_id = int(req.guild_id or 0)
    try:
        ops = list(await builder(guild_id))
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception(
            "section_card._apply_recommended: builder failed (section=%s)",
            slug)
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "Could not build the recommended defaults. See logs.")
    if not ops:
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "No recommended operations were generated for this "
                     "section.")
    try:
        result = await replace_recommended_for_section(guild_id, slug, ops)
    except Exception:  # noqa: BLE001 — the shipped error copy answers
        logger.exception(
            "section_card._apply_recommended: replace_recommended failed")
        # shipped copy, verbatim.
        return Reply(BLOCKED,
                     "Could not stage the recommended operations. See logs.")
    if not await mark_section_skipped(req, slug, skipped=False):
        logger.warning("section_card: unmark skip failed (%s)", slug)
    word = "operation" if result.inserted == 1 else "operations"
    msg = (f"Staged **{result.inserted} recommended {word}** for "
           f"{section.label}. Open Final review to apply.")
    if result.conflicts:
        conflict_word = ("operation" if len(result.conflicts) == 1
                         else "operations")
        msg += (f"\n\n⚠️ Preserved **{len(result.conflicts)} custom / preset "
                f"{conflict_word}** at the same slot(s) — no overwrite. "
                "Edit Final review if you want to swap them out.")
    return Reply(SUCCESS, msg)


def _card_handlers(slug: str, section) -> None:
    from sb.spec.refs import handler

    @handler(f"setup.section_apply_{slug}")
    async def apply_recommended(req) -> Reply | None:
        reply = await apply_recommended_flow(req, slug, section)
        if reply.outcome == SUCCESS:
            # refresh the card so the status badge / Pending field
            # reflect the freshly staged rows (the shipped anchor
            # refresh), then answer the shipped confirmation.
            from sb.domain.setup.wizard import _refresh_own_panel

            await _refresh_own_panel(req, {})
        return reply

    @handler(f"setup.section_customize_{slug}")
    async def customize(req) -> Reply | None:
        panel_id = customize_panel(slug)
        if panel_id is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "This section has no detail view yet.")
        # the card path is NOT wizard-native — the detail's ↩ Back to
        # step button rides only the wizard origin (wizard_nav's
        # injection ledger note).
        from sb.domain.setup import wizard_nav

        wizard_nav.clear_detail_origin(
            int(req.guild_id or 0),
            int(getattr(req.actor, "user_id", 0) or 0))
        from sb.domain.setup.wizard import _open

        try:
            await _open(req, panel_id)
        except Exception:  # noqa: BLE001 — the shipped error copy answers
            logger.exception(
                "section_card._customize: handler failed (section=%s)", slug)
            return Reply(BLOCKED, "Could not open the detail view. See logs.")
        return None

    @handler(f"setup.section_skip_{slug}")
    async def skip(req) -> Reply:
        if not await _gated_card(req):
            return Reply(BLOCKED, GATE_MSG_CARD)
        if not await mark_section_skipped(req, slug, skipped=True):
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Could not record the skip. See logs.")
        # shipped copy, verbatim.
        return Reply(SUCCESS,
                     f"Marked **{section.label}** as skipped. "
                     "Reopen the section any time to change your mind.")

    @handler(f"setup.section_hub_{slug}")
    async def return_to_hub(req) -> Reply:
        # shipped copy, verbatim (the hub message stays the anchor).
        return Reply(SUCCESS, "Returning to the setup hub above.")


_REGISTERED_CARDS: dict[str, object] = {}


def register_section_card(slug: str, *, detected_state: str = "") -> None:
    """Mint + register the section's card panel, renderer and the four
    button handlers (idempotent). Flow modules call this once at
    import, after registering their builder / customize panel."""
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    register_shipped_sections()
    section = REGISTRY.get(slug)
    if section is None:
        raise ValueError(f"unknown wizard section {slug!r}")
    _DETECTED_STATE[slug] = detected_state
    _REGISTERED_CARDS[slug] = section
    render_ref = f"setup.section_card_render_{slug}"
    if not is_registered(HandlerRef(render_ref)):
        handler(render_ref)(_card_renderer(slug, section))
    if not is_registered(HandlerRef(f"setup.section_apply_{slug}")):
        _card_handlers(slug, section)
    if not is_registered(PanelRef(card_panel_id(slug))):
        panel(card_panel_id(slug))(lambda s=slug, sec=section: _card_spec(s, sec))


def card_spec_for(slug: str):
    """The registered card's PanelSpec (the manifest declaration read)."""
    section = _REGISTERED_CARDS.get(slug)
    if section is None:
        raise ValueError(f"section card {slug!r} not registered")
    return _card_spec(slug, section)


def ensure_section_card_refs() -> None:
    for slug in list(_REGISTERED_CARDS):
        register_section_card(slug, detected_state=_DETECTED_STATE.get(slug, ""))
