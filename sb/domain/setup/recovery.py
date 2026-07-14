"""The SECTION-RECOVERY surface (ORDER 019 item 5b, half 1), ported from
the oracle (menno420/superbot @bbc524e4, ``disbot/views/setup/
recovery.py`` — Phase 7 of the setup-wizard plan):

when a wizard section's ``Apply Recommended`` flow errors out, the
wizard catches the exception, fills in a :class:`RecoveryContext`, and
mounts the recovery surface in place of the normal step embed (oracle
``LinearWizardView._mount_recovery_view`` — the ONLY shipped mount
site; hub-origin recovery is grammar the oracle carried but never
wired). The embed surfaces four operator-facing fields (What happened /
Why / Recommended / If skipped), gold accent, and five buttons:

* **Continue** — return to the wizard step without retrying (the
  oracle ``resume_callback`` → ``wizard._refresh_and_edit`` repaint);
* **Retry** — re-invoke the failing section's flow (oracle
  ``section.run``; here the section's registered
  ``setup.open_section_{slug}`` handler);
* **Skip section** — record the skip + drop the section's
  provenance-owned draft rows, then return to the wizard;
* **Customize** — jump to the section's manual detail view instead of
  re-triggering the failure (falls back to the Retry lane for
  sections without one — the oracle ``_on_customize`` fallback);
* **Cancel** — close the recovery surface, nothing applied or skipped.

Mutating buttons (Retry / Skip / Customize) re-check ``can_apply_setup``
per click with the recovery-specific gate copy — the oracle
``SectionRecoveryView._gate_apply``.

Kernel-idiom divergences, ledgered (the section_card.py doctrine):

* the oracle held the ``RecoveryContext`` on the view instance; here it
  is held per ``guild:user`` in memory (the wizard_nav step-index
  precedent — a restart forgets it the same way the oracle's dead view
  did; expired clicks answer the EXPIRED copy instead of Discord's
  dead-component failure);
* the oracle EDITED the anchor in place (``edit_message`` /
  ``safe_edit``); navigation here opens panels through ``open_panel``
  (the #295 precedent every setup lane rides);
* ``RecoveryContext.if_skipped`` falls through to the generic copy —
  the target ``WizardSectionSpec`` does not carry the oracle's
  ``description_if_skipped`` field (nothing in this build populates
  it; the generic fall-through is the oracle's own default);
* Customize's enablement (oracle: disabled unless the section declares
  a ``recommended_ops_builder`` or non-empty ``op_kinds``) rides the
  renderer's ``disabled`` flip (the wizard_step precedent for
  state-dependent controls).

NO GOLDEN drives any recovery component (the panels.py module pin) —
the oracle sources pin every byte.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sb.kernel.interaction.handler_kit import Reply
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "GATE_MSG_RECOVERY",
    "RecoveryContext",
    "SECTION_RECOVERY_PANEL_ID",
    "clear_recovery_context",
    "ensure_section_recovery_refs",
    "mount_section_recovery",
    "recovery_context",
    "recovery_context_from_exception",
    "reset_recovery_state_for_tests",
    "section_recovery_spec",
    "set_recovery_context",
]

logger = logging.getLogger("sb.domain.setup")

SECTION_RECOVERY_PANEL_ID = "setup.section_recovery"

#: shipped gate copy, verbatim (recovery.SectionRecoveryView._gate_apply).
GATE_MSG_RECOVERY = (
    "Only the server owner or a delegated setup admin can retry or skip "
    "a setup step.  Ask the owner to grant you `/setup-delegate`."
)

#: the restart-degrade copy (adaptation, ledgered above: the oracle's
#: dead view answered expired clicks with Discord's component failure).
_EXPIRED_MSG = ("This recovery prompt has expired — re-open the wizard "
                "with `/setup-advanced`.")

#: shipped field fallbacks, verbatim (recovery.build_recovery_embed).
_NO_DETAIL = "_(no detail captured)_"
_NO_SUGGESTION = "_(no suggestion available)_"
_NO_CONSEQUENCE = "_(no consequence documented)_"

#: shipped footer, verbatim.
_RECOVERY_FOOTER = (
    "Recovery only — Final Review still owns the apply path.  Nothing on "
    "this view stages or applies operations."
)

#: shipped generic-context copy, verbatim
#: (recovery.recovery_context_from_exception).
_GENERIC_RECOMMENDED = (
    "Press **Retry** to try the step again, or **Skip section** to move "
    "past it and revisit later."
)
_GENERIC_IF_SKIPPED = (
    "The wizard continues with the section's current state.  You can "
    "return to it any time via the hub."
)

#: shipped permission-hint ladder, verbatim.
_PERMISSION_HINTS = {
    "Forbidden": "SuperBot is missing a Discord permission for this step.",
    "HTTPException": "Discord refused the request (rate limit or API "
                     "failure).",
    "TimeoutError": "The operation timed out before Discord responded.",
}


@dataclass(frozen=True)
class RecoveryContext:
    """Structured payload for a section-failure recovery embed (the
    oracle dataclass; ``slug``/``label`` stand in for the oracle's
    whole ``SetupSection`` — the registry re-resolves the rest)."""

    slug: str
    label: str
    origin: str                 # "wizard" | "hub" — the return anchor
    step_index: int             # 0-based; -1 if origin is hub
    total_steps: int            # 0 if origin is hub
    what_happened: str
    why: str
    recommended: str
    if_skipped: str


# --- the per-operator context (the oracle view-instance state) ---------------------------

_RECOVERY: dict[str, RecoveryContext] = {}


def _key(guild_id: int, user_id: int) -> str:
    return f"{int(guild_id)}:{int(user_id)}"


def recovery_context(guild_id: int, user_id: int) -> RecoveryContext | None:
    return _RECOVERY.get(_key(guild_id, user_id))


def set_recovery_context(guild_id: int, user_id: int,
                         context: RecoveryContext) -> None:
    _RECOVERY[_key(guild_id, user_id)] = context


def clear_recovery_context(guild_id: int, user_id: int) -> None:
    _RECOVERY.pop(_key(guild_id, user_id), None)


def reset_recovery_state_for_tests() -> None:
    _RECOVERY.clear()


def recovery_context_from_exception(
    *,
    section,
    exc: BaseException,
    origin: str = "wizard",
    step_index: int = -1,
    total_steps: int = 0,
) -> RecoveryContext:
    """The oracle convenience helper: generic What happened / Why /
    Recommended / If skipped copy keyed to the section's metadata (the
    fall-through path for sections without custom messaging — every
    section in this build)."""
    exc_type = type(exc).__name__
    exc_msg = str(exc) or exc_type
    why = _PERMISSION_HINTS.get(exc_type, f"{exc_type}: {exc_msg}")
    return RecoveryContext(
        slug=str(section.slug),
        label=str(section.label),
        origin=origin,
        step_index=step_index,
        total_steps=total_steps,
        what_happened=(
            f"The wizard couldn't complete the **{section.label}** step "
            "without an error."
        ),
        why=why,
        recommended=_GENERIC_RECOMMENDED,
        if_skipped=_GENERIC_IF_SKIPPED,
    )


async def mount_section_recovery(req, *, section, exc: BaseException,
                                 origin: str = "wizard",
                                 step_index: int = -1,
                                 total_steps: int = 0) -> None:
    """The ``_mount_recovery_view`` twin: build + stash the context,
    then open the recovery panel over the failing step."""
    from sb.domain.setup.wizard import _open

    context = recovery_context_from_exception(
        section=section, exc=exc, origin=origin,
        step_index=step_index, total_steps=total_steps)
    set_recovery_context(int(req.guild_id or 0),
                         int(getattr(req.actor, "user_id", 0) or 0),
                         context)
    await _open(req, SECTION_RECOVERY_PANEL_ID)
    return None


# --- panel spec ---------------------------------------------------------------------------

def section_recovery_spec():
    """The SectionRecoveryView surface: Continue · Retry · Skip section
    on row 0, Customize · Cancel on row 1 (oracle labels/styles/rows/
    custom_ids verbatim — ``setup_recovery:*``)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=SECTION_RECOVERY_PANEL_ID,
        subsystem="setup",
        title="⚠️ Setup issue found",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="recovery_continue", label="Continue",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.section_recovery_continue"),
                custom_id_override="setup_recovery:continue"),
            PanelActionSpec(
                action_id="recovery_retry_step", label="Retry",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.section_recovery_retry"),
                custom_id_override="setup_recovery:retry"),
            PanelActionSpec(
                action_id="recovery_skip_section", label="Skip section",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.section_recovery_skip"),
                custom_id_override="setup_recovery:skip"),
            PanelActionSpec(
                action_id="recovery_customize", label="Customize",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.section_recovery_customize"),
                custom_id_override="setup_recovery:customize"),
            PanelActionSpec(
                action_id="recovery_cancel_view", label="Cancel",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.section_recovery_cancel"),
                custom_id_override="setup_recovery:cancel"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("recovery_continue", "recovery_retry_step",
             "recovery_skip_section"),
            ("recovery_customize", "recovery_cancel_view"))),)),
        renderer_override=HandlerRef("setup.section_recovery_render"),
        justification=(
            "the shipped recovery card is context-parameterized end to "
            "end (the Step i/N title, the section-label description, the "
            "What happened / Why / Recommended / If skipped fields — "
            "recovery.build_recovery_embed) and its Customize button is "
            "section-dependent (disabled unless the section declares a "
            "recommended builder or op_kinds — SectionRecoveryView."
            "_populate_buttons); both outside the static grammar "
            "vocabulary. The override renders through the grammar, "
            "composes the embed and flips the Customize disable (no "
            "golden pins this panel — the oracle source does)."),
        session_lifecycle=True,
    )


# --- renderer -----------------------------------------------------------------------------

async def _render_section_recovery(spec, ctx) -> object:
    """renderer_override — recovery.build_recovery_embed verbatim over
    the stashed context (a restart loses it — the oracle's
    view-instance state did too; the card degrades to the EXPIRED
    line)."""
    import dataclasses

    from sb.domain.setup import section_card
    from sb.domain.setup.sections import REGISTRY, register_shipped_sections
    from sb.kernel.panels.render import RenderedEmbed, render_panel

    base = await render_panel(spec, ctx)
    context = recovery_context(int(ctx.guild_id or 0),
                               int(getattr(ctx.actor, "user_id", 0) or 0))
    if context is None:
        embed = RenderedEmbed(
            title=spec.title,
            description=_EXPIRED_MSG,
            style_token="dark_grey")
        return dataclasses.replace(base, embed=embed)

    if context.step_index >= 0 and context.total_steps > 0:
        title = (f"⚠️ Setup issue found · Step "
                 f"{context.step_index + 1}/{context.total_steps}")
    else:
        title = "⚠️ Setup issue found"
    embed = RenderedEmbed(
        title=title,
        description=(
            f"While running **{context.label}** the wizard hit an "
            "error.  Nothing has changed yet — pick how to proceed from "
            "the buttons below."
        ),
        fields=(
            ("What happened", context.what_happened or _NO_DETAIL, False),
            ("Why", context.why or _NO_DETAIL, False),
            ("Recommended", context.recommended or _NO_SUGGESTION, False),
            ("If skipped", context.if_skipped or _NO_CONSEQUENCE, False),
        ),
        footer=_RECOVERY_FOOTER,
        style_token="gold")

    # the shipped Customize enablement: only sections with an actual
    # recommended builder OR non-empty op_kinds open a useful detail
    # view (SectionRecoveryView._populate_buttons).
    register_shipped_sections()
    section = REGISTRY.get(context.slug)
    customize_dead = (
        section_card.recommended_builder(context.slug) is None
        and not (section is not None and section.op_kinds))
    components = []
    for c in base.components:
        if c.custom_id == "setup_recovery:customize" and customize_dead:
            c = dataclasses.replace(c, disabled=True)
        components.append(c)
    return dataclasses.replace(base, embed=embed,
                               components=tuple(components))


# --- handlers -----------------------------------------------------------------------------

def _ids(req) -> tuple[int, int]:
    return (int(req.guild_id or 0),
            int(getattr(req.actor, "user_id", 0) or 0))


async def _reopen_host(req, context: RecoveryContext | None) -> None:
    """The ``resume_callback`` twin: repaint the host anchor — the
    wizard step for wizard-origin recovery (at the mount's step index),
    the sections hub for hub-origin (the oracle's "return the operator
    to the right anchor" OriginTag contract)."""
    from sb.domain.setup.wizard import _open

    if context is not None and context.origin == "hub":
        from sb.domain.setup.panels import SECTIONS_HUB_PANEL_ID

        await _open(req, SECTIONS_HUB_PANEL_ID)
        return
    from sb.domain.setup import wizard_nav

    if context is not None and context.step_index >= 0:
        wizard_nav._set_step_index(*_ids(req), context.step_index)
    await _open(req, wizard_nav.WIZARD_STEP_PANEL_ID)


async def _run_section_flow(req, context: RecoveryContext) -> Reply | None:
    """Re-invoke the section's own flow (the oracle ``section.run``):
    the registered ``setup.open_section_{slug}`` route re-opens the
    section UI; any failure answers the shipped retry-failed copy."""
    from sb.spec.refs import HandlerRef, resolve

    try:
        section_open = resolve(HandlerRef(f"setup.open_section_"
                                          f"{context.slug}"))
        return await section_open(req)
    except Exception:  # noqa: BLE001 — the shipped retry-failed posture
        logger.exception("recovery._on_retry: section %s raised",
                         context.slug)
        # shipped copy, verbatim (SectionRecoveryView._on_retry).
        return Reply(BLOCKED,
                     f"Retry of **{context.label}** failed again — see "
                     "logs.  Use Skip section to move on.")


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.section_recovery_continue")):
        return

    @handler("setup.section_recovery_continue")
    async def recovery_continue(req) -> None:
        """Continue — past the failing step without retrying: close the
        recovery surface and hand control back to the host (the oracle
        ``_on_continue`` → resume callback; ungated — navigation
        only)."""
        guild_id, user_id = _ids(req)
        context = recovery_context(guild_id, user_id)
        clear_recovery_context(guild_id, user_id)
        await _reopen_host(req, context)
        return None

    @handler("setup.section_recovery_retry")
    async def recovery_retry(req) -> Reply | None:
        """Retry — re-invoke the failing section path (gated per click,
        the oracle ``_on_retry``)."""
        from sb.domain.setup import wizard

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_RECOVERY)
        guild_id, user_id = _ids(req)
        context = recovery_context(guild_id, user_id)
        if context is None:
            return Reply(BLOCKED, _EXPIRED_MSG)
        clear_recovery_context(guild_id, user_id)
        return await _run_section_flow(req, context)

    @handler("setup.section_recovery_skip")
    async def recovery_skip(req) -> Reply | None:
        """Skip section — record the skip, drop the section's
        provenance-owned draft rows (so Final Review never applies an op
        the operator just skipped — the oracle ``_on_skip``), then
        return to the host anchor with the shipped confirmation."""
        from sb.domain.setup import section_card, wizard

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_RECOVERY)
        guild_id, user_id = _ids(req)
        context = recovery_context(guild_id, user_id)
        if context is None:
            return Reply(BLOCKED, _EXPIRED_MSG)
        if not await section_card.mark_section_skipped(
                req, context.slug, skipped=True):
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Could not record the skip — see logs.")
        try:
            await section_card.delete_section_rows(guild_id, context.slug)
        except Exception:  # noqa: BLE001 — the shipped best-effort delete
            logger.exception(
                "recovery._on_skip: provenance delete failed (section=%s)",
                context.slug)
        clear_recovery_context(guild_id, user_id)
        await _reopen_host(req, context)
        # shipped copy, verbatim.
        return Reply(SUCCESS, f"⏭ Skipped **{context.label}**.")

    @handler("setup.section_recovery_customize")
    async def recovery_customize(req) -> Reply | None:
        """Customize — jump straight to the section's manual detail
        view instead of re-triggering the failure (the oracle
        ``_on_customize``); sections without one fall back to the Retry
        lane (their ``run`` is the only manual entry)."""
        from sb.domain.setup import section_card, wizard, wizard_nav
        from sb.domain.setup.wizard import _open

        if not await wizard.can_apply_setup(req):
            return Reply(BLOCKED, GATE_MSG_RECOVERY)
        guild_id, user_id = _ids(req)
        context = recovery_context(guild_id, user_id)
        if context is None:
            return Reply(BLOCKED, _EXPIRED_MSG)
        panel_id = section_card.customize_panel(context.slug)
        clear_recovery_context(guild_id, user_id)
        if panel_id is None:
            return await _run_section_flow(req, context)
        if context.step_index >= 0:
            wizard_nav._set_step_index(guild_id, user_id,
                                       context.step_index)
        wizard_nav.mark_detail_from_wizard(guild_id, user_id)
        try:
            await _open(req, panel_id)
        except Exception:  # noqa: BLE001 — the shipped failure copy answers
            logger.exception(
                "recovery._on_customize: render_step_detail failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         f"Could not open the detail view for "
                         f"**{context.label}** — see logs.")
        return None

    @handler("setup.section_recovery_cancel")
    async def recovery_cancel(req) -> Reply:
        """Cancel — close the recovery surface; nothing applied or
        skipped (the oracle ``_on_cancel``; the disabled-view swap is
        the ledgered text-reply seam)."""
        guild_id, user_id = _ids(req)
        clear_recovery_context(guild_id, user_id)
        # shipped copy, verbatim.
        return Reply(SUCCESS,
                     "Recovery cancelled — your wizard / hub anchor above "
                     "is unchanged.  Nothing was applied or skipped.")


# --- registration -------------------------------------------------------------------------

def _register_panel() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    if not is_registered(HandlerRef("setup.section_recovery_render")):
        handler("setup.section_recovery_render")(_render_section_recovery)
    if not is_registered(PanelRef(SECTION_RECOVERY_PANEL_ID)):
        panel(SECTION_RECOVERY_PANEL_ID)(section_recovery_spec)


_register()
_register_panel()


def ensure_section_recovery_refs() -> None:
    _register()
    _register_panel()
