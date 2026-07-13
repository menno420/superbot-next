"""The LINEAR WIZARD STEPS (the section-flows slice) — the
one-step-at-a-time wizard behind the sections hub's ↩ Back to wizard,
ported from the oracle (menno420/superbot, read from the LOCAL oracle
clone: views/setup/wizard.py ``LinearWizardView`` +
``build_wizard_step_embed`` + ``_resolve_sections``/``_step_index_for``,
and views/setup/wizard_nav.py ``render_wizard_step`` — the shared
anchor-rebuild path the hub's Back button routes through):

* the STEP EMBED (``build_wizard_step_embed``, bytes verbatim): the
  ``🛰 SuperBot setup wizard · Step i/N`` title, the badge + status
  description line, the Current state / Recommended action /
  If-you-skip-this fields, the
  "Nothing changes until Final Review applies the staged operations."
  footer, the per-status accent;
* the BUTTON ROWS (``LinearWizardView._rebuild_buttons``, the shipped
  ``setup_wizard:*`` persistent custom_ids compat-pinned): ◀ Back ·
  Apply Recommended · Customize · Skip on row 0, Continue ▶ (the last
  step flips it to **Final Review**, primary) · Cancel on row 1, the
  Jump-to-section select on row 2, Apply all recommended on row 3
  (dropped when no depth-filtered section has a recommended builder —
  the shipped ``_build_apply_all_button`` None branch);
* the NAVIGATION lanes: Back/Continue/Jump mutate the step index and
  re-render; the last step's Continue opens FINAL REVIEW (the shipped
  ``_open_final_review`` destination); Cancel answers the shipped
  wizard-closed copy;
* the MUTATING lanes (gated per click on the shipped
  can-apply re-check): Apply Recommended stages the current section's
  builder output through the section-card spine's
  ``replace_recommended_for_section``; Apply all recommended sweeps
  every builder section (``stage_all_recommended``); Skip records the
  skip + drops the section's provenance-owned rows + advances.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the step index is held per ``guild:user`` in memory (the oracle held
  it on the view instance — restart forgets it the same way); entry
  through ↩ Back to wizard re-derives it from the persisted
  ``current_step`` (the shipped ``_step_index_for`` fallback ladder);
* the oracle edited the durable workspace anchor in place
  (``safe_edit``); navigation here re-renders the panel's own card via
  ``refresh_session_view`` and opens destinations through
  ``open_panel`` (the #295 precedent);
* the oracle's staged-notice ride (``push_setup_notice`` into the
  workspace channel) + the SectionRecoveryView mount are LIVE (the
  night-recovery-view slice: sb/domain/setup/notices.py +
  recovery.py) — Apply Recommended / Apply-all post the durable
  workspace notice AND keep the text reply as the click-level ack
  (the oracle's aggressive-ephemeral policy answered with a bare
  defer; this build's reply seam keeps the confirmation visible when
  the workspace is unreachable — ledgered); a builder/staging failure
  mounts the recovery panel instead of the flat error reply;
* the ``↩ Back to step`` button the oracle injected into detail views
  (wizard_nav._build_back_to_step_button, custom_id
  ``setup_wizard:back_to_step:{i}``) rides the detail panels as a
  declared run-minted button instead — the index suffix can't ride a
  static grammar id; the flow state carries the origin.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "WIZARD_STEP_PANEL_ID",
    "build_wizard_step_embed",
    "clear_detail_origin",
    "detail_from_wizard",
    "ensure_wizard_nav_refs",
    "mark_detail_from_wizard",
    "reset_wizard_nav_state_for_tests",
    "step_index",
    "wizard_step_spec",
]

logger = logging.getLogger("sb.domain.setup")

WIZARD_STEP_PANEL_ID = "setup.wizard_step"

#: shipped literals, verbatim (views/setup/wizard.py).
_WIZARD_TITLE = "🛰 SuperBot setup wizard"
_FOOTER_HINT = ("Nothing changes until Final Review applies the staged "
                "operations.")

_JUMP_OPTIONS_PROVIDER = "setup.wizard_jump_options"


# --- the per-operator step index (the oracle view-instance state) -----------------------

_WIZ_INDEX: dict[str, int] = {}
_DETAIL_FROM_WIZARD: set[str] = set()


def _key(guild_id: int, user_id: int) -> str:
    return f"{int(guild_id)}:{int(user_id)}"


def step_index(guild_id: int, user_id: int) -> int:
    return _WIZ_INDEX.get(_key(guild_id, user_id), 0)


def _set_step_index(guild_id: int, user_id: int, index: int) -> None:
    _WIZ_INDEX[_key(guild_id, user_id)] = max(0, int(index))


def mark_detail_from_wizard(guild_id: int, user_id: int) -> None:
    _DETAIL_FROM_WIZARD.add(_key(guild_id, user_id))


def clear_detail_origin(guild_id: int, user_id: int) -> None:
    _DETAIL_FROM_WIZARD.discard(_key(guild_id, user_id))


def detail_from_wizard(guild_id: int, user_id: int) -> bool:
    return _key(guild_id, user_id) in _DETAIL_FROM_WIZARD


def reset_wizard_nav_state_for_tests() -> None:
    _WIZ_INDEX.clear()
    _DETAIL_FROM_WIZARD.clear()


# --- session/sections resolution (wizard._resolve_sections / _step_index_for) -----------

async def _session_row(guild_id: int) -> dict | None:
    from sb.domain.setup import store

    try:
        return await store.get_session_row(int(guild_id))
    except Exception:  # noqa: BLE001 — the shipped resume soft-fail
        logger.exception("wizard_nav.render_wizard_step: resume failed")
        return None


def _sections_for(session: dict | None):
    from sb.domain.setup.wizard import sections_for_depth

    depth = (str(session["depth"]) if session and session.get("depth")
             else None)
    return sections_for_depth(depth)


def _step_index_for(session: dict | None, sections) -> int:
    """wizard._step_index_for, verbatim ladder: the recorded
    ``current_step`` slug's index, else 0."""
    current = str(session.get("current_step") or "") if session else ""
    if not current:
        return 0
    for idx, section in enumerate(sections):
        if section.slug == current:
            return idx
    return 0


def _clamp(index: int, sections) -> int:
    if not sections:
        return 0
    return max(0, min(int(index), len(sections) - 1))


async def _guild_op_list(guild_id: int) -> list:
    from sb.domain.setup import section_card

    try:
        return [op for _d, op in await section_card.guild_ops(int(guild_id))]
    except Exception:  # noqa: BLE001 — the shipped list_rows soft-fail
        logger.exception("wizard_nav.render_wizard_step: list_rows failed")
        return []


# --- the step embed (build_wizard_step_embed, bytes verbatim) ----------------------------

def _short_state_for(section, ops) -> str:
    """wizard._short_state_for over the K9 rows (the ported provenance
    match — section_card.row_section)."""
    from sb.domain.setup import section_card

    matching = [op for op in ops
                if section_card._matches_section(op, section)]
    if not matching:
        return ""
    count = len(matching)
    noun = "operation" if count == 1 else "operations"
    if all(section_card._is_recommended(op) for op in matching):
        return f"{count} recommended {noun} staged"
    if all(not section_card._is_recommended(op) for op in matching):
        return f"{count} customised {noun} staged"
    return f"{count} {noun} staged ({count} mixed)"


def build_wizard_step_embed(*, session: dict | None, section,
                            step_index: int, total_steps: int, ops):
    from sb.domain.setup import section_card
    from sb.kernel.panels.render import RenderedEmbed

    progress = section_card.compute_section_status(
        section, session=session, ops=ops)
    glyph = section_card.badge_for(progress.status)
    skipped = bool(session) and section.slug in set(
        session.get("skipped_sections") or ())
    completed = bool(session) and section.slug in set(
        session.get("acknowledged_sections") or ())

    title = f"{_WIZARD_TITLE} · Step {step_index + 1}/{total_steps}"
    if skipped:
        token = "dark_grey"
    elif completed or progress.status == section_card.RECOMMENDED:
        token = "green"
    elif progress.status == section_card.CUSTOMIZED:
        token = "gold"
    else:
        token = "blurple"

    description = (f"{glyph} **{section.label}** "
                   f"({progress.status.replace('_', ' ')})")

    detected = _short_state_for(section, ops)
    fields: list[tuple] = [
        ("Current state",
         detected or "_(nothing staged for this step yet)_", False),
    ]
    if section_card.recommended_builder(section.slug) is not None:
        fields.append((
            "Recommended action",
            "Click **Apply Recommended** to stage this section's safe "
            "defaults.  Nothing applies until **Final Review** confirms.",
            False))
    else:
        fields.append((
            "Recommended action",
            "_(no recommended defaults — use Customize to open the "
            "section's detail view.)_",
            False))
    skip_note = section_card.SECTION_SKIP_DESCRIPTIONS.get(section.slug, "")
    if skip_note:
        fields.append(("If you skip this", skip_note, False))
    return RenderedEmbed(title=title, description=description,
                         fields=tuple(fields), footer=_FOOTER_HINT,
                         style_token=token)


# --- the panel spec ----------------------------------------------------------------------

def wizard_step_spec():
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec, SelectorKind,
        SelectorSpec,
    )
    from sb.spec.refs import HandlerRef, ProviderRef

    return PanelSpec(
        panel_id=WIZARD_STEP_PANEL_ID,
        subsystem="setup",
        title=_WIZARD_TITLE,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple",
                             footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="wiz_back", label="◀ Back",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_back"),
                custom_id_override="setup_wizard:back"),
            PanelActionSpec(
                action_id="wiz_apply_recommended", label="Apply Recommended",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.wizard_apply_recommended"),
                custom_id_override="setup_wizard:apply_recommended"),
            PanelActionSpec(
                action_id="wiz_customize", label="Customize",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.wizard_customize"),
                custom_id_override="setup_wizard:customize"),
            PanelActionSpec(
                action_id="wiz_skip", label="Skip",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_skip"),
                custom_id_override="setup_wizard:skip"),
            PanelActionSpec(
                action_id="wiz_continue", label="Continue ▶",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.wizard_continue"),
                custom_id_override="setup_wizard:continue"),
            PanelActionSpec(
                action_id="wiz_cancel", label="Cancel",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.wizard_cancel"),
                custom_id_override="setup_wizard:cancel"),
            PanelActionSpec(
                action_id="wiz_apply_all", label="Apply all recommended",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.wizard_apply_all"),
                custom_id_override="setup_wizard:apply_all_recommended"),
        ),
        selectors=(
            SelectorSpec(
                selector_id="wiz_jump", kind=SelectorKind.ENUM,
                on_select=HandlerRef("setup.wizard_jump"),
                options_source=ProviderRef(_JUMP_OPTIONS_PROVIDER),
                placeholder="Jump to section…",
                custom_id_override="setup_wizard:jump"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("wiz_back", "wiz_apply_recommended", "wiz_customize",
             "wiz_skip"),
            ("wiz_continue", "wiz_cancel"),
            ("wiz_jump",),
            ("wiz_apply_all",))),)),
        renderer_override=HandlerRef("setup.wizard_step_render"),
        justification=(
            "the shipped linear wizard anchor is session/draft/index-"
            "parameterized end to end (the Step i/N title, the badge + "
            "status line, the Current-state field, the per-status accent "
            "— wizard.build_wizard_step_embed), its Continue button flips "
            "label/style on the last step, its dead buttons render "
            "disabled and the Apply-all row drops when no depth section "
            "has a builder (LinearWizardView._rebuild_buttons) — all "
            "outside the static grammar vocabulary; the override renders "
            "through the grammar and composes embed + component patches "
            "(no golden pins it — the oracle source does)."),
        session_lifecycle=True,
    )


# --- providers ---------------------------------------------------------------------------

def _ensure_providers() -> None:
    from sb.spec.refs import ProviderRef, is_registered, provider

    if is_registered(ProviderRef(_JUMP_OPTIONS_PROVIDER)):
        return

    @provider(_JUMP_OPTIONS_PROVIDER)
    async def jump_options(ctx):
        """The _JumpToSectionSelect option list (labels verbatim; the
        current step pre-selected)."""
        guild_id = int(ctx.guild_id or 0)
        user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
        session = await _session_row(guild_id)
        sections = _sections_for(session)
        current = _clamp(step_index(guild_id, user_id), sections)
        return tuple(
            {"label": section.label[:100], "value": str(idx),
             "default": idx == current}
            for idx, section in enumerate(sections[:25]))


# --- the renderer ------------------------------------------------------------------------

async def _render_wizard_step(spec, ctx):
    import dataclasses

    from sb.domain.setup import section_card
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    guild_id = int(ctx.guild_id or 0)
    user_id = int(getattr(ctx.actor, "user_id", 0) or 0)
    session = await _session_row(guild_id)
    sections = _sections_for(session)
    index = _clamp(step_index(guild_id, user_id), sections)
    ops = await _guild_op_list(guild_id)
    base = await render_panel(spec, ctx)

    if sections:
        section = sections[index]
        embed = build_wizard_step_embed(
            session=session, section=section, step_index=index,
            total_steps=len(sections), ops=ops)
        has_builder = (section_card.recommended_builder(section.slug)
                       is not None)
        has_detail = section_card.customize_panel(section.slug) is not None
    else:
        # the shipped no-sections branch (wizard_nav.render_wizard_step).
        section = None
        embed = RenderedEmbed(
            title=_WIZARD_TITLE,
            description=(
                "No setup sections are available for this depth. "
                "Pick a different depth via `/setup-depth`."),
            style_token="dark_grey")
        has_builder = False
        has_detail = False

    is_last = not sections or index >= len(sections) - 1
    any_builder = any(
        section_card.recommended_builder(s.slug) is not None
        for s in sections)

    components = []
    for c in base.components:
        cid = c.custom_id
        if cid == "setup_wizard:back":
            c = dataclasses.replace(c, disabled=index <= 0)
        elif cid == "setup_wizard:apply_recommended":
            c = dataclasses.replace(
                c, disabled=(section is None or not has_builder))
        elif cid == "setup_wizard:customize":
            c = dataclasses.replace(
                c, disabled=(section is None or not has_detail))
        elif cid == "setup_wizard:skip":
            c = dataclasses.replace(c, disabled=section is None)
        elif cid == "setup_wizard:continue":
            c = dataclasses.replace(
                c,
                label="Final Review" if is_last else "Continue ▶",
                style="primary" if is_last else "secondary")
        elif cid == "setup_wizard:apply_all_recommended" and not any_builder:
            continue    # the shipped None branch — never a no-op button
        elif cid == "setup_wizard:jump" and not sections:
            continue    # the shipped None branch
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers ----------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.wizard_back")):
        return

    def _ids(req) -> tuple[int, int]:
        return (int(req.guild_id or 0),
                int(getattr(req.actor, "user_id", 0) or 0))

    async def _refresh_or_open(req) -> None:
        from sb.domain.setup.wizard import _open, _refresh_own_panel

        if not await _refresh_own_panel(req, {}):
            await _open(req, WIZARD_STEP_PANEL_ID)

    async def _current(req):
        guild_id, user_id = _ids(req)
        session = await _session_row(guild_id)
        sections = _sections_for(session)
        index = _clamp(step_index(guild_id, user_id), sections)
        section = sections[index] if sections else None
        return session, sections, index, section

    @handler("setup.back_to_wizard")
    async def back_to_wizard(req) -> Reply | None:
        """The hub's ↩ Back to wizard — the shared anchor-rebuild path
        (wizard_nav.render_wizard_step at ``session.current_step``,
        the hub button's shipped destination), gate first (the hub
        button's existing gate)."""
        from sb.domain.setup import wizard
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        guild_id, user_id = _ids(req)
        session = await _session_row(guild_id)
        sections = _sections_for(session)
        _set_step_index(guild_id, user_id,
                        _clamp(_step_index_for(session, sections), sections))
        await _open(req, WIZARD_STEP_PANEL_ID)
        return None

    @handler("setup.wizard_back")
    async def wizard_back(req) -> None:
        guild_id, user_id = _ids(req)
        if step_index(guild_id, user_id) > 0:
            _set_step_index(guild_id, user_id,
                            step_index(guild_id, user_id) - 1)
        await _refresh_or_open(req)
        return None

    @handler("setup.wizard_continue")
    async def wizard_continue(req) -> None:
        _session, sections, index, _section = await _current(req)
        guild_id, user_id = _ids(req)
        if sections and index < len(sections) - 1:
            _set_step_index(guild_id, user_id, index + 1)
            await _refresh_or_open(req)
            return None
        # last step → open Final Review (the shipped destination).
        from sb.domain.setup.final_review import FINAL_REVIEW_PANEL_ID
        from sb.domain.setup.wizard import _open

        await _open(req, FINAL_REVIEW_PANEL_ID)
        return None

    @handler("setup.wizard_jump")
    async def wizard_jump(req) -> None:
        _session, sections, index, _section = await _current(req)
        values = tuple(req.args.get("values", ()) or ())
        try:
            target = int(str(values[0]))
        except (ValueError, IndexError):
            target = index
        guild_id, user_id = _ids(req)
        _set_step_index(guild_id, user_id, _clamp(target, sections))
        await _refresh_or_open(req)
        return None

    @handler("setup.wizard_cancel")
    async def wizard_cancel(req) -> Reply:
        # shipped copy, verbatim (LinearWizardView._on_cancel's embed
        # description — the disabled-view swap is the ledgered
        # text-reply seam).
        return Reply(SUCCESS,
                     "Wizard closed.  Re-open with `/setup` or `!setup`; "
                     "your draft is preserved.")

    @handler("setup.wizard_apply_recommended")
    async def wizard_apply_recommended(req) -> Reply | None:
        from sb.domain.setup import section_card
        from sb.domain.setup.wizard import _refresh_own_panel

        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        _session, sections, index, section = await _current(req)
        if section is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "No section selected.")
        builder = section_card.recommended_builder(section.slug)
        if builder is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "This step has no recommended defaults — use "
                         "Customize to open the detail view.")
        guild_id, _user_id = _ids(req)
        try:
            ops = list(await builder(guild_id))
        except Exception as exc:  # noqa: BLE001 — the shipped recovery
            # mount (wizard._on_apply_recommended's builder catch).
            logger.exception(
                "wizard._on_apply_recommended: builder failed (%s)",
                section.slug)
            from sb.domain.setup import recovery

            return await recovery.mount_section_recovery(
                req, section=section, exc=exc, origin="wizard",
                step_index=index, total_steps=len(sections))
        if not ops:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No recommended operations were generated for "
                         "this step.")
        try:
            result = await section_card.replace_recommended_for_section(
                guild_id, section.slug, ops)
        except Exception as exc:  # noqa: BLE001 — the shipped recovery
            # mount (the replace_recommended catch).
            logger.exception(
                "wizard._on_apply_recommended: replace_recommended failed")
            from sb.domain.setup import recovery

            return await recovery.mount_section_recovery(
                req, section=section, exc=exc, origin="wizard",
                step_index=index, total_steps=len(sections))
        if not await section_card.mark_section_skipped(
                req, section.slug, skipped=False):
            logger.warning("wizard._on_apply_recommended: unmark skip "
                           "failed")
        count = result.inserted
        noun = "operation" if count == 1 else "operations"
        conflict_text = ""
        if result.conflicts:
            cn = len(result.conflicts)
            conflict_word = "row" if cn == 1 else "rows"
            conflict_text = (
                f"\n\n⚠️ Preserved **{cn} custom / preset {conflict_word}** "
                "at conflicting slot(s); no overwrite.")
        await _refresh_own_panel(req, {})
        # the shipped apply-recommended record, posted as a durable
        # workspace notice (wizard._on_apply_recommended's
        # push_setup_notice ride — the aggressive-ephemeral policy);
        # failure only logs, the oracle posture.
        from sb.domain.setup import notices

        await notices.push_setup_notice(
            req,
            title=f"✅ Recommended staged · {section.label}",
            description=f"Staged **{count} {noun}**.{conflict_text}")
        # the same copy answers as the click-level text ack (the
        # ledgered reply seam — module docstring).
        return Reply(SUCCESS,
                     f"✅ Recommended staged · {section.label} — "
                     f"Staged **{count} {noun}**.{conflict_text}")

    @handler("setup.wizard_apply_all")
    async def wizard_apply_all(req) -> Reply | None:
        from sb.domain.setup import section_card
        from sb.domain.setup.wizard import _refresh_own_panel

        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        _session, sections, _index, _section = await _current(req)
        builder_sections = [
            s for s in sections
            if section_card.recommended_builder(s.slug) is not None]
        if not builder_sections:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No section in the current depth has a recommended "
                         "default — use **Customize** on individual steps "
                         "instead.")
        guild_id, _user_id = _ids(req)
        section_totals: dict[str, int] = {}
        conflicts_total = 0
        for section in builder_sections:
            builder = section_card.recommended_builder(section.slug)
            try:
                ops = list(await builder(guild_id))
            except Exception:  # noqa: BLE001 — per-section isolation
                logger.exception(
                    "stage_all_recommended: builder failed (slug=%s)",
                    section.slug)
                continue
            if not ops:
                continue
            try:
                result = await section_card.replace_recommended_for_section(
                    guild_id, section.slug, ops)
            except Exception:  # noqa: BLE001 — per-section isolation
                logger.exception(
                    "stage_all_recommended: replace_recommended_for_section "
                    "failed (slug=%s)", section.slug)
                continue
            if result.inserted:
                section_totals[section.slug] = result.inserted
            conflicts_total += len(result.conflicts)
        total = sum(section_totals.values())
        word = "operation" if total == 1 else "operations"
        if not total and not conflicts_total:
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "No recommended operations were generated — the "
                         "server may already cover these, or no channels "
                         "matched the rules.")
        await _refresh_own_panel(req, {})
        # the shipped apply-all record, posted as a durable workspace
        # notice (wizard._on_apply_all_recommended's push_setup_notice
        # ride) — per-section lines + the conflicts tail, verbatim.
        lines = "\n".join(
            f"• `{slug}`: **{count}** op(s)"
            for slug, count in section_totals.items())
        description = (
            f"Staged **{total} {word}** across {len(section_totals)} "
            "section(s). Continue to **Final Review** to apply.")
        if lines:
            description += f"\n\n{lines}"
        if conflicts_total:
            conflict_word = "row" if conflicts_total == 1 else "rows"
            description += (
                f"\n\n⚠️ Preserved **{conflicts_total} custom / preset "
                f"{conflict_word}** at conflicting slot(s); no overwrite.")
        from sb.domain.setup import notices

        await notices.push_setup_notice(
            req,
            title=f"✅ Apply all recommended — {total} {word}",
            description=description)
        # the shipped immediate click-level confirmation, verbatim.
        return Reply(SUCCESS,
                     f"✅ Staged **{total} {word}** across "
                     f"{len(section_totals)} section(s).")

    @handler("setup.wizard_skip")
    async def wizard_skip(req) -> Reply | None:
        from sb.domain.setup import section_card
        from sb.domain.setup.wizard import _refresh_own_panel

        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        _session, sections, index, section = await _current(req)
        if section is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "No step to skip.")
        if not await section_card.mark_section_skipped(
                req, section.slug, skipped=True):
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Could not record the skip — see logs.")
        # provenance-aware delete: Final Review never applies an op the
        # operator skipped (wizard._on_skip, best-effort).
        deleted = 0
        try:
            deleted = await section_card.delete_section_rows(
                int(req.guild_id or 0), section.slug)
        except Exception:  # noqa: BLE001 — the shipped soft-fail
            logger.exception(
                "wizard._on_skip: provenance delete failed (%s)",
                section.slug)
        guild_id, user_id = _ids(req)
        if index < len(sections) - 1:
            _set_step_index(guild_id, user_id, index + 1)
        followup = (f"\n\nRemoved {deleted} staged op(s) for this section."
                    if deleted else "")
        await _refresh_own_panel(req, {})
        # shipped copy, verbatim.
        return Reply(SUCCESS, f"⏭ Skipped **{section.label}**.{followup}")

    @handler("setup.wizard_customize")
    async def wizard_customize(req) -> Reply | None:
        from sb.domain.setup import section_card
        from sb.domain.setup.wizard import _open

        _session, _sections, _index, section = await _current(req)
        panel_id = (section_card.customize_panel(section.slug)
                    if section is not None else None)
        if section is None or panel_id is None:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "This step has no detail view.")
        # gate before opening — detail views can stage draft operations
        # (the shipped order).
        if not await section_card._gated_card(req):
            return Reply(BLOCKED, section_card.GATE_MSG_CARD)
        guild_id, user_id = _ids(req)
        mark_detail_from_wizard(guild_id, user_id)
        await _open(req, panel_id)
        return None

    @handler("setup.wizard_back_to_step")
    async def wizard_back_to_step(req) -> None:
        """The injected ↩ Back to step button's callback
        (wizard_nav._build_back_to_step_button): restore the wizard
        view at the originating step (the flow state carries it)."""
        from sb.domain.setup.wizard import _open

        guild_id, user_id = _ids(req)
        clear_detail_origin(guild_id, user_id)
        await _open(req, WIZARD_STEP_PANEL_ID)
        return None


# --- registration ------------------------------------------------------------------------

def _register_panel() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.wizard_step_render")):
        handler("setup.wizard_step_render")(_render_wizard_step)
    if not is_registered(PanelRef(WIZARD_STEP_PANEL_ID)):
        panel(WIZARD_STEP_PANEL_ID)(wizard_step_spec)


_ensure_providers()
_register()
_register_panel()


def ensure_wizard_nav_refs() -> None:
    _ensure_providers()
    _register()
    _register_panel()
