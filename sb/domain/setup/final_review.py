"""The FINAL-REVIEW APPLY LANE (the final-review slice — the wizard's
sole apply gate), ported from the oracle (menno420/superbot,
disbot/views/setup/final_review.py @73aaf43, read from the LOCAL oracle
clone):

* the FINAL-REVIEW card (``build_final_review_embed`` — the three
  states: nothing-staged / pre-apply pending list + created-resources
  call-out + the no-rollback heads-up / post-apply summary) rendered
  from the K9 staged draft ops (the wizard-lifecycle slice's
  ``stage_accepted`` writer);
* the gated APPLY (``FinalReviewView._apply``): the ``can_apply_setup``
  re-check with the shipped apply refusal copy, the per-guild
  SINGLE-FLIGHT lock (``acquire_setup_apply_lock`` — check+add with no
  intervening await, race-free under asyncio), then the staged ops run
  through the audited kernel seams: the K9 ``DraftPipeline``
  (preview → accept gate → button confirmation → per-op K7 ``run()``,
  ONE central audit row per op, ``correlation_id = draft_id``) — the
  pipeline docstring's own mandate ("Final Review … THIN surfaces over
  this — none re-implements staging, preview, gate, or apply");
* the APPLY SUMMARY (``ApplySummary`` applied/failed/skipped) and the
  full-success branch: draft cleared by the kernel's APPLIED terminal
  status, the session marked complete through the K7
  ``setup.mark_complete`` op, the SetupCompleteView mounted;
* PARTIAL-APPLY RECOVERY (``PartialApplyRecoveryView``): Retry re-runs
  the apply lane, Cancel preserves the draft, Finish-anyway drops the
  remainder and marks setup complete (the partial-apply stickiness
  escape hatch, oracle docstring verbatim);
* the SETUP-COMPLETE view (``SetupCompleteView``): Delete-now runs the
  ported ``cleanup_setup_channel_after_completion`` guard ladder + the
  K7 ``setup.cleanup_workspace`` op; Keep closes without deletion.

Kernel-idiom divergences, ledgered (the wizard-lifecycle slice's
adaptation doctrine — same copy, same button labels, same flow; only
the seams differ):

* PER-OP ISOLATION vs SF-f: the oracle isolated failures per op ("one
  bad op does not abort the rest"); the K9 kernel STOPS at the first
  non-SUCCESS (apply.py SF-f) and partitions the rest as skipped. The
  oracle's summary vocabulary (applied/failed/skipped) carries both
  shapes; Retry covers the difference.
* K9 ``PARTIAL`` is a TERMINAL status, so "the draft is preserved" is
  honored by RE-STAGING the failed+skipped ops into a fresh OPEN draft
  (original ``dedup_token`` carried verbatim — none of them ever
  reached SUCCESS, so apply-idempotency is preserved across the retry);
  the PARTIAL draft row stays as the spine's correlation record.
* the oracle swapped views in place (``edit_message``); this
  architecture's navigation lane opens the destination panel through
  ``open_panel`` (the #295 precedent — the wizard.py ledger note), and
  ephemeral terminal states (Edit/Back/Cancel, the AI review, the
  cleanup outcomes) answer as text replies.
* the 🧠 Ask-AI-review lane rides the DETERMINISTIC advisor (the AI
  lane is key-gated OFF in this build — the shipped build_advisor
  fallback the /setup-describe entry already ledgers); copy verbatim
  from services/setup_advisor_review.py.
* staged K9 rows carry no oracle metadata dict, so the pending-line
  glyphs render the draft_render defaults (confidence ``medium`` ◐ ·
  risk ``low`` ·) — views/setup/draft_render.py ``_DEFAULT_METADATA``.

NO GOLDEN drives any of these components (the panels.py module pin);
the oracle SOURCES pin the copy, and every golden-pinned OPEN render
stays byte-identical.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = [
    "ApplySummary",
    "COMPLETE_PANEL_ID",
    "FINAL_REVIEW_PANEL_ID",
    "RECOVERY_PANEL_ID",
    "SetupApplyInProgressError",
    "acquire_setup_apply_lock",
    "build_final_review_embed",
    "ensure_final_review_refs",
    "last_summary",
    "reset_final_review_state_for_tests",
]

logger = logging.getLogger("sb.domain.setup")

FINAL_REVIEW_PANEL_ID = "setup.final_review"
RECOVERY_PANEL_ID = "setup.apply_recovery"
COMPLETE_PANEL_ID = "setup.complete_card"

#: shipped apply-gate refusal, verbatim (final_review._gate_apply).
GATE_MSG_APPLY = ("Only the server owner or a delegated setup admin can apply "
                  "staged setup operations. Ask the server owner to grant you "
                  "`/setup-delegate`.")

#: shipped single-flight refusal, verbatim (FinalReviewView._apply /
#: PartialApplyRecoveryView._retry).
IN_PROGRESS_MSG = ("Setup apply is already in progress — wait for the result "
                   "message before retrying.")


# --- the single-flight apply lock (setup_operations.py, ported verbatim) ---------------

class SetupApplyInProgressError(RuntimeError):
    """Raised by :func:`acquire_setup_apply_lock` when an apply batch
    for the same guild is already running."""

    def __init__(self, guild_id: int) -> None:
        super().__init__(
            f"setup apply already in progress for guild_id={guild_id}")
        self.guild_id = guild_id


_apply_inflight: set[int] = set()


@asynccontextmanager
async def acquire_setup_apply_lock(guild_id: int) -> AsyncIterator[None]:
    """The oracle single-flight guard: the check + add happen without an
    intervening ``await``, so under asyncio's cooperative scheduling the
    operation is atomic — a concurrent ``async with`` either sees the
    guild in the set and raises, or wins the slot and runs."""
    if guild_id in _apply_inflight:
        raise SetupApplyInProgressError(guild_id)
    _apply_inflight.add(guild_id)
    try:
        yield
    finally:
        _apply_inflight.discard(guild_id)


# --- the apply summary (final_review.ApplySummary, verbatim shape) --------------------

@dataclass
class ApplySummary:
    """Outcome of one apply batch — surfaced in the follow-up embed."""

    applied: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


#: the last apply outcome per guild (the oracle held it on the view
#: instance; the ported in-memory-state precedent is wizard.py's
#: _REVIEW dict — restart forgets it exactly like the oracle's view).
_SUMMARY: dict[int, ApplySummary] = {}


def last_summary(guild_id: int) -> ApplySummary | None:
    return _SUMMARY.get(int(guild_id))


def reset_final_review_state_for_tests() -> None:
    _SUMMARY.clear()
    _apply_inflight.clear()


# --- op-line rendering (views/setup/draft_render.py, the reachable subset) ------------

#: op kinds that CREATE a Discord resource (final_review._CREATE_OP_KINDS).
_CREATE_OP_KINDS: frozenset[str] = frozenset(
    {"create_channel", "create_role", "create_category"})


def _short_label(op: Any) -> str:
    """draft_render._short_label over a K9 ``DraftOperation`` — the
    staged rows are ``bind_channel`` payloads ({subsystem, name, kind,
    resource_id}); the other kind branches are carried for the section
    flows that will stage them later."""
    kind = str(getattr(op, "op_kind", "") or "")
    payload = dict(getattr(op, "payload", {}) or {})
    subsystem = str(payload.get("subsystem", getattr(op, "subsystem", "")))
    name = str(payload.get("name", "") or "")
    if kind == "set_setting" and name:
        value = payload.get("value")
        v = value if value is not None else "(default)"
        return f"{subsystem}.{name} = {v}"
    if kind == "clear_binding" and name:
        return f"{subsystem}.{name} ← clear"
    if kind == "set_cleanup_policy":
        # the shipped stored-label bytes (cleanup._stage_cleanup_policy's
        # ``cleanup.{scope}({name}) = {level}``) re-derived from the
        # payload's review ride-alongs (the settings-write slice).
        scope = str(payload.get("scope_type") or "?")
        target = str(payload.get("target_name") or "?")
        level = payload.get("level")
        return f"cleanup.{scope}({target}) = {level or '(default)'}"
    if kind == "set_role_threshold":
        # the shipped stored-label bytes (roles._stage_threshold's
        # ``role tier: @{role} after {N}d`` / ``at XP level {N}``)
        # re-derived from the payload's full-row columns (the
        # roles-family slice — time + XP fold onto ONE row, so a merged
        # row renders both halves).
        target = str(payload.get("target_name")
                     or payload.get("role_name") or "?")
        parts: list[str] = []
        days = payload.get("days_required")
        if days:
            parts.append(f"after {days}d")
        level = payload.get("level_required")
        if level is not None and payload.get("xp_auto_assign"):
            parts.append(f"at XP level {level}")
        tail = " + ".join(parts) if parts else "(no tier)"
        return f"role tier: @{target} {tail}"
    if kind == "create_managed_role":
        # the shipped stored-label bytes (role_templates._op_label's
        # ``create role @{name} +{N}d +L{N}``) re-derived from the
        # payload's resource_name + role_template spec ride.
        resource = str(payload.get("resource_name") or "?")
        spec = dict(payload.get("role_template") or {})
        label = f"create role @{resource}"
        if spec.get("time_days"):
            label += f" +{spec['time_days']}d"
        if spec.get("xp_level"):
            label += f" +L{spec['xp_level']}"
        return label
    if kind == "set_cog_routing":
        # the shipped stored-label bytes (cog_routing._stage_cog_routing's
        # ``cog_routing.{scope}({name}).{cog} = {enabled|disabled}``)
        # re-derived from the payload's set_policy params + target_name
        # ride (the routing-ticket slice).
        scope = str(payload.get("scope_type") or "?")
        target = str(payload.get("target_name") or "?")
        cog = str(payload.get("cog_name") or "?")
        state = "enabled" if payload.get("enabled") else "disabled"
        return f"cog_routing.{scope}({target}).{cog} = {state}"
    if kind.startswith("bind_") and name:
        target_id = payload.get("resource_id")
        target = (str(payload.get("target_name") or "")
                  or (f"<{target_id}>" if target_id else "?"))
        return f"{subsystem}.{name} → {target}"
    if kind.startswith("create_"):
        kind_label = kind[len("create_"):]
        resource = str(payload.get("resource_name") or "?")
        return f"create {kind_label} {resource!r}"
    return f"{kind} ({subsystem})"


def _pending_line(op: Any) -> str:
    """draft_render.render_op_line with the metadata DEFAULTS (staged K9
    rows carry no metadata dict): confidence ``medium`` → ``◐``, risk
    ``low`` → ``·``, no reason suffix."""
    return f"◐· `{_short_label(op)}`"


def _created_resource_names(ops: tuple[Any, ...] | list[Any]) -> list[str]:
    """final_review._created_resource_names over DraftOperations: names
    of resources a staged plan would CREATE (not just bind)."""
    names: list[str] = []
    for op in ops:
        if str(getattr(op, "op_kind", "")) in _CREATE_OP_KINDS:
            payload = dict(getattr(op, "payload", {}) or {})
            names.append(str(payload.get("resource_name") or "?"))
    return names


# --- the final-review embed (build_final_review_embed, bytes verbatim) ----------------

def build_final_review_embed(ops: list[Any] | tuple[Any, ...], *,
                             summary: ApplySummary | None = None):
    """The oracle three-state render: pre-apply (lists what will
    happen), post-apply (summary counts), or nothing-to-apply. Returns a
    ``RenderedEmbed`` — the ported embed carrier."""
    from sb.kernel.panels.render import RenderedEmbed

    ops = list(ops or ())
    if not ops and summary is None:
        return RenderedEmbed(
            title="🛰 Final review",
            description=(
                "No staged work yet. Visit a wizard section to stage "
                "the first change, then come back here to apply."),
            style_token="dark_grey")

    if summary is None:
        embed_fields: list[tuple] = []
        lines = [f"• {_pending_line(op)}" for op in ops[:10]]
        if len(ops) > 10:
            lines.append(f"_+{len(ops) - 10} more_")
        value = "\n".join(lines)
        if len(value) > 1000:
            value = value[:997] + "..."
        embed_fields.append(("Pending", value, False))
        created = _created_resource_names(ops)
        if created:
            shown = ", ".join(f"`{n}`" for n in created[:10])
            if len(created) > 10:
                shown += f" _+{len(created) - 10} more_"
            embed_fields.append((
                f"➕ {len(created)} new resource(s) will be created",
                f"Applying this plan **creates** these and binds them: "
                f"{shown}. Binding an existing resource is reversible; a "
                "created channel/role/category is new and must be deleted "
                "to undo.", False))
        embed_fields.append((
            "⚠️ Heads-up",
            "Apply has **no automatic rollback**. Each operation commits "
            "through its pipeline in order; if one fails partway, earlier "
            "ones stay applied and you'll be able to retry the rest.",
            False))
        return RenderedEmbed(
            title="🛰 Final review",
            description=(
                "Final review — **nothing has changed yet**.  "
                f"**{len(ops)}** operation(s) are staged and ready to "
                "apply.  Click **Apply staged setup** to route each "
                "through the audit pipelines."),
            fields=tuple(embed_fields),
            footer="Owner-gated. Nothing has applied yet.",
            style_token="blurple")

    partial = bool(summary.failed) or bool(summary.skipped)
    if partial:
        token = "gold"
        title = "🛰 Final review · partially applied"
        description = (
            "**Setup partially applied.**  Some changes succeeded, but "
            "setup is **not** complete.  Your remaining draft has been "
            "preserved so you can retry or cancel.\n\n"
            f"Applied **{len(summary.applied)}**, "
            f"failed **{len(summary.failed)}**, "
            f"skipped **{len(summary.skipped)}**.")
    else:
        token = "green"
        title = "🛰 Setup complete"
        description = (
            f"**Setup complete.**  Applied **{len(summary.applied)}** "
            "operation(s); nothing failed or was skipped.")
    embed_fields = []
    if summary.applied:
        embed_fields.append((
            "Applied",
            "\n".join(f"• {x}" for x in summary.applied[:10])
            + (f"\n_+{len(summary.applied) - 10} more_"
               if len(summary.applied) > 10 else ""), False))
    if summary.failed:
        embed_fields.append((
            "Failed", "\n".join(f"• {x}" for x in summary.failed[:10]),
            False))
    if summary.skipped:
        embed_fields.append((
            "Skipped", "\n".join(f"• {x}" for x in summary.skipped[:10]),
            False))
    footer = ""
    if partial:
        footer = ("Draft preserved. Retry re-runs the failed/skipped "
                  "operations; Cancel leaves the draft for later. Note: "
                  "Cancel does NOT undo operations that already applied.")
    return RenderedEmbed(title=title, description=description,
                         fields=tuple(embed_fields), footer=footer,
                         style_token=token)


# --- the apply engine drive (the K9 DraftPipeline thin surface) ------------------------

def _authority_request(req, *, authority_ref: str = ""):
    """ctx.actor → AuthorityRequest, the K7 engine._resolve_leg0 mapping."""
    from sb.kernel.authority.decision import AuthorityRequest

    actor = req.actor
    return AuthorityRequest(
        authority_ref=authority_ref,
        actor_type=getattr(actor, "actor_type", "user") or "user",
        user_id=getattr(actor, "user_id", None),
        guild_id=int(req.guild_id or 0) or None,
        is_member=bool(req.guild_id) and not getattr(actor, "is_dm", False),
        member_tier=getattr(actor, "member_tier", None),
        role_ids=tuple(getattr(actor, "role_ids", ()) or ()))


async def _restage_remainder(guild_id: int, remainder: list[Any]) -> None:
    """The K9-PARTIAL divergence (module docstring): re-stage the
    failed+skipped ops into a fresh OPEN draft so the oracle contract
    ("your remaining draft has been preserved") stays true against
    list_open readers (the hub pending count, ``/setup-reset``,
    Retry). Original ``dedup_token`` carried verbatim — none of these
    ops reached SUCCESS, so the K7 once() key stays correct."""
    from sb.domain.setup.wizard import _guild_scope
    from sb.kernel.draft.store import DraftStore
    from sb.spec.draft import DraftOperation, Producer

    if not remainder:
        return
    store = DraftStore()
    draft = await store.create(producer=Producer.HUMAN_SETUP,
                               owner_scope=_guild_scope(guild_id))
    for op in remainder:
        await store.add(draft.draft_id, DraftOperation(
            op_seq=0,  # append_operation assigns the real sequence
            op_kind=op.op_kind, subsystem=op.subsystem,
            authority_ref=op.authority_ref, payload=dict(op.payload),
            label=op.label, dedup_token=op.dedup_token))


async def _apply_open_drafts(req) -> ApplySummary:
    """Run every open guild draft through the K9 pipeline (preview →
    accept gate → BUTTON confirmation → per-op K7 run) and fold the
    results into the oracle ApplySummary partitions. Batch-level
    refusals (accept denial / confirmation mismatch / stale preview)
    land every op of that draft in ``failed`` — fail-closed, isolated
    per draft."""
    from sb.domain.setup import wizard
    from sb.kernel.draft.pipeline import DraftPipeline
    from sb.kernel.draft.preview import PreviewContext
    from sb.spec.draft import ConfirmationResponse

    guild_id = int(req.guild_id or 0)
    summary = ApplySummary()
    remainder: list[Any] = []
    pipeline = DraftPipeline()
    drafts = await wizard._open_guild_drafts(guild_id)
    for draft in drafts:
        labels = {op.op_seq: _short_label(op) for op in draft.operations}
        ops_by_seq = {op.op_seq: op for op in draft.operations}
        try:
            pctx = PreviewContext(
                actor=req.actor, guild_id=guild_id,
                member_tier=getattr(req.actor, "member_tier", None))
            preview = await pipeline.preview(draft.draft_id, pctx)
            result = await pipeline.confirm_and_apply(
                draft.draft_id, _authority_request(req), req.actor,
                preview_hash=preview.preview_hash,
                confirmation=ConfirmationResponse(
                    challenge=preview.confirmation.challenge))
        except Exception as exc:  # noqa: BLE001 — batch refusal, isolated per draft
            logger.exception("final review: apply refused for draft %s",
                             draft.draft_id)
            detail = str(exc) or type(exc).__name__
            for op in draft.operations:
                summary.failed.append(f"{labels[op.op_seq]}: {detail}")
                remainder.append(op)
            continue
        # map the DraftApplyResult partitions onto the oracle summary.
        # apply runs in op_seq order and stops at the first non-SUCCESS
        # (SF-f), so a failed op RAN iff it left an op_result behind
        # (len(op_results) > len(applied)); a binding-less kind never
        # ran — the oracle's not_yet_implemented partition, folded into
        # skipped (its own docstring).
        failed_ran = len(result.op_results) > len(result.applied)
        for seq in result.applied:
            summary.applied.append(labels.get(seq, f"op {seq}"))
        for seq in result.failed:
            label = labels.get(seq, f"op {seq}")
            if failed_ran:
                error = str(result.op_results[-1].user_message or "")
                summary.failed.append(f"{label}: {error}" if error
                                      else label)
            else:
                summary.skipped.append(f"{label} (not yet implemented)")
            remainder.append(ops_by_seq[seq])
        for seq in result.skipped:
            summary.skipped.append(labels.get(seq, f"op {seq}"))
            remainder.append(ops_by_seq[seq])
    if summary.failed or summary.skipped:
        try:
            await _restage_remainder(guild_id, remainder)
        except Exception:  # noqa: BLE001 — the summary still answers
            logger.exception("final review: re-staging the remainder failed")
    return summary


async def _mark_complete(req) -> None:
    """The oracle setup_session.mark_complete — through the K7
    ``setup.mark_complete`` op (best-effort, the oracle's own
    try/except posture)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    try:
        result = await engine.run(WorkflowRef("setup.mark_complete"),
                                  ctx_from_request(req, {}))
        if result.outcome != SUCCESS:
            logger.warning("final review: mark_complete → %s", result.outcome)
    except Exception:  # noqa: BLE001 — oracle: logged, never raised
        logger.exception("FinalReviewView: mark_complete failed")


async def _run_apply_flow(req) -> Reply | None:
    """The shared _run_apply body (FinalReviewView._run_apply +
    PartialApplyRecoveryView._retry both route here): apply, stash the
    summary, then mount the outcome surface — SetupCompleteView on full
    success, PartialApplyRecoveryView otherwise."""
    from sb.domain.setup.wizard import _open as _open_panel

    guild_id = int(req.guild_id or 0)
    summary = await _apply_open_drafts(req)
    _SUMMARY[guild_id] = summary
    full_success = not summary.failed and not summary.skipped
    if full_success:
        await _mark_complete(req)
        await _open_panel(req, COMPLETE_PANEL_ID)
        return None
    await _open_panel(req, RECOVERY_PANEL_ID)
    return None


# --- staged-ops reads -------------------------------------------------------------------

async def _staged_ops(guild_id: int) -> list[Any]:
    from sb.domain.setup import wizard

    drafts = await wizard._open_guild_drafts(int(guild_id))
    return [op for draft in drafts for op in draft.operations]


# --- panel specs -------------------------------------------------------------------------

def final_review_spec():
    """The FinalReviewView surface: Apply staged setup · 🧠 Ask AI to
    review · Edit setup · Back · Cancel (oracle button labels/styles/
    custom_ids verbatim; discord.ui packed all five onto one row)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=FINAL_REVIEW_PANEL_ID,
        subsystem="setup",
        title="🛰 Final review",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="blurple", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="final_apply", label="Apply staged setup",
                style=ActionStyle.SUCCESS,
                handler=HandlerRef("setup.final_apply"),
                custom_id_override="setup_final_review:apply"),
            PanelActionSpec(
                action_id="final_ai_review", label="🧠 Ask AI to review",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.final_ai_review"),
                custom_id_override="setup_final_review:ai_review"),
            PanelActionSpec(
                action_id="final_edit", label="Edit setup",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.final_edit"),
                custom_id_override="setup_final_review:edit"),
            PanelActionSpec(
                action_id="final_back", label="Back",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.final_back"),
                custom_id_override="setup_final_review:back"),
            PanelActionSpec(
                action_id="final_cancel", label="Cancel",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.final_cancel"),
                custom_id_override="setup_final_review:cancel"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("final_apply", "final_ai_review", "final_edit", "final_back",
             "final_cancel"),)),)),
        renderer_override=HandlerRef("setup.final_review_render"),
        justification=(
            "the shipped final-review card is draft-parameterized end to "
            "end (the staged-op count description, the Pending list, the "
            "created-resources call-out, the heads-up field — "
            "final_review.build_final_review_embed) — outside the static "
            "grammar vocabulary; the override renders through the grammar "
            "and composes the embed (no golden pins this panel — the "
            "oracle source does)."),
        session_lifecycle=True,
    )


def recovery_spec():
    """The PartialApplyRecoveryView surface: Retry · Finish anyway ·
    Cancel (oracle labels/styles verbatim; run-minted component ids —
    the oracle buttons carried no custom_id)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=RECOVERY_PANEL_ID,
        subsystem="setup",
        title="🛰 Final review · partially applied",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="gold", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="recovery_retry", label="Retry",
                style=ActionStyle.PRIMARY,
                handler=HandlerRef("setup.recovery_retry")),
            PanelActionSpec(
                action_id="recovery_finish", label="Finish anyway",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.recovery_finish")),
            PanelActionSpec(
                action_id="recovery_cancel", label="Cancel",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.recovery_cancel")),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("recovery_retry", "recovery_finish", "recovery_cancel"),)),)),
        renderer_override=HandlerRef("setup.recovery_render"),
        justification=(
            "the shipped partial-apply card is summary-parameterized "
            "(applied/failed/skipped counts + lists — "
            "build_final_review_embed's partial branch); the override "
            "composes the embed (no golden pins it — the oracle source "
            "does)."),
        session_lifecycle=True,
    )


def complete_spec():
    """The SetupCompleteView surface: Delete now · Keep setup channel
    (oracle labels/styles/custom_ids verbatim)."""
    from sb.spec.panels import (
        ActionStyle, Audience, EmbedFrameSpec, FooterMode, LayoutSpec,
        NavigationSpec, PageSpec, PanelActionSpec, PanelSpec,
    )
    from sb.spec.refs import HandlerRef

    return PanelSpec(
        panel_id=COMPLETE_PANEL_ID,
        subsystem="setup",
        title="🛰 Setup complete",
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(style_token="green", footer_mode=FooterMode.NONE),
        actions=(
            PanelActionSpec(
                action_id="complete_delete", label="Delete now",
                style=ActionStyle.DANGER,
                handler=HandlerRef("setup.complete_delete"),
                custom_id_override="setup_complete:delete"),
            PanelActionSpec(
                action_id="complete_keep", label="Keep setup channel",
                style=ActionStyle.SECONDARY,
                handler=HandlerRef("setup.complete_keep"),
                custom_id_override="setup_complete:keep"),
        ),
        navigation=NavigationSpec(show_help=False, show_home=False),
        layout=LayoutSpec(pages=(PageSpec(rows=(
            ("complete_delete", "complete_keep"),)),)),
        renderer_override=HandlerRef("setup.complete_render"),
        justification=(
            "the shipped setup-complete card is summary-parameterized "
            "(the applied count — build_final_review_embed's full-success "
            "branch); the override composes the embed (no golden pins it "
            "— the oracle source does)."),
        session_lifecycle=True,
    )


# --- renderer overrides -------------------------------------------------------------------

async def _render_final_review(spec, ctx) -> object:
    """renderer_override — build_final_review_embed's pre-apply/empty
    states over the LIVE staged-draft read; the empty state drops the
    Apply button (the oracle disabled it — component-model adaptation:
    the ported RenderedComponent carries no disabled facet, so the
    honest twin is not offering the dead button)."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    try:
        ops = await _staged_ops(int(ctx.guild_id or 0))
    except Exception:  # noqa: BLE001 — the shipped list_ops soft-fail
        logger.exception("final review: staged-ops read failed")
        ops = []
    embed = build_final_review_embed(ops)
    components = base.components
    if not ops:
        components = tuple(c for c in components
                           if c.custom_id != "setup_final_review:apply")
    return dataclasses.replace(base, embed=embed, components=components)


async def _render_recovery(spec, ctx) -> object:
    """renderer_override — build_final_review_embed's partial branch
    over the stashed summary (a restart loses it — the oracle's
    view-instance state did too; the card degrades to the preserved
    draft's pre-apply render)."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    summary = last_summary(int(ctx.guild_id or 0))
    if summary is None:
        try:
            ops = await _staged_ops(int(ctx.guild_id or 0))
        except Exception:  # noqa: BLE001
            ops = []
        embed = build_final_review_embed(ops)
    else:
        ops = []
        embed = build_final_review_embed(ops, summary=summary)
    return dataclasses.replace(base, embed=embed)


async def _render_complete(spec, ctx) -> object:
    """renderer_override — build_final_review_embed's full-success
    branch over the stashed summary."""
    import dataclasses

    from sb.kernel.panels.render import render_panel

    base = await render_panel(spec, ctx)
    summary = last_summary(int(ctx.guild_id or 0)) or ApplySummary()
    embed = build_final_review_embed([], summary=summary)
    return dataclasses.replace(base, embed=embed)


# --- handlers -------------------------------------------------------------------------------

def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("setup.open_section_final_review")):
        return

    async def _gated(req) -> bool:
        """The dynamic module-attribute gate read (the test seam the
        wizard-interior suite monkeypatches — never a from-import
        binding)."""
        from sb.domain.setup import wizard

        return await wizard.can_apply_setup(req)

    @handler("setup.open_section_final_review")
    async def open_section_final_review(req) -> Reply | None:
        """The hub's Final-review section button — gate exactly like the
        shipped hub button, then land on the final-review card (the
        oracle hub read setup_draft.list_ops and passed
        ``FinalReviewView(ops=...)``; the ported renderer does the same
        read)."""
        from sb.domain.setup import wizard
        from sb.domain.setup.wizard import _open as _open_panel

        if not await _gated(req):
            return Reply(BLOCKED, wizard.GATE_MSG_WIZARD)
        await _open_panel(req, FINAL_REVIEW_PANEL_ID)
        return None

    @handler("setup.final_apply")
    async def final_apply(req) -> Reply | None:
        """Apply staged setup (FinalReviewView._apply): the
        nothing-to-apply guard, the shipped apply gate, the
        single-flight lock, then the K9 pipeline drive."""
        guild_id = int(req.guild_id or 0)
        try:
            ops = await _staged_ops(guild_id)
        except Exception:  # noqa: BLE001 — fail closed on an unreadable draft
            logger.exception("final review: staged-ops read failed in apply")
            return Reply(BLOCKED,
                         "Could not read the staged draft — see logs.")
        if not ops:
            # shipped copy, verbatim.
            return Reply(BLOCKED, "Nothing to apply.")
        if not await _gated(req):
            return Reply(BLOCKED, GATE_MSG_APPLY)
        try:
            async with acquire_setup_apply_lock(guild_id):
                return await _run_apply_flow(req)
        except SetupApplyInProgressError:
            # shipped copy, verbatim.
            return Reply(BLOCKED, IN_PROGRESS_MSG)

    @handler("setup.final_ai_review")
    async def final_ai_review(req) -> Reply:
        """🧠 Ask AI to review (FinalReviewView._ai_review →
        setup_advisor_review.review_draft): advisory-only, never
        stages/applies/mutates, never blocks — every failure degrades
        to the friendly notice (oracle copy verbatim). The provider is
        the deterministic advisor (the AI lane is key-gated OFF in this
        build — the shipped build_advisor fallback)."""
        from sb.domain.setup import plan

        provider = "DeterministicAdvisor"
        try:
            draft = await plan.suggest(int(req.guild_id or 0))
        except Exception:  # noqa: BLE001 — advisory only; never raise
            logger.warning("setup_advisor_review: advisor.suggest failed",
                           exc_info=True)
            # shipped copy, verbatim (review_draft's advisor-raise branch).
            return Reply(SUCCESS,
                         "🧠 AI setup review — The AI advisor couldn't "
                         "produce a review right now.")
        recommendations = tuple(draft.recommendations or ())
        footer = (f"Advisory only ({provider}) — nothing has been staged "
                  "or applied. Use the wizard to make any changes "
                  "yourself.")
        if not recommendations:
            # shipped copy, verbatim (review_draft's empty branch).
            summary = ("No additional changes recommended — your setup "
                       "looks good.")
            return Reply(SUCCESS, f"🧠 AI setup review — {summary}\n{footer}")
        lines = []
        for rec in recommendations[:10]:
            # setup_advisor_review._format_recommendation verbatim (the
            # oracle read ``rationale``, a field SetupRecommendation
            # never carried — the suffix is empty there too).
            conf = (f" ({rec.confidence})" if rec.confidence else "")
            lines.append(f"• `{rec.subsystem}.{rec.binding_name}`{conf}")
        extra = len(recommendations) - min(len(recommendations), 10)
        if extra > 0:
            lines.append(f"_+{extra} more_")
        summary = (f"{len(recommendations)} suggestion(s) from the advisor "
                   "(advisory only — nothing has been staged or applied):")
        return Reply(SUCCESS,
                     "🧠 AI setup review — " + summary + "\n"
                     + "\n".join(lines) + "\n" + footer)

    @handler("setup.final_edit")
    async def final_edit(req) -> Reply:
        """Edit setup (FinalReviewView._edit) — close and return to the
        anchor; no side effect. Shipped copy, verbatim."""
        return Reply(SUCCESS,
                     "Closed Final review — open the wizard or hub above to "
                     "edit your staged operations.  Nothing has been "
                     "applied.")

    @handler("setup.final_back")
    async def final_back(req) -> Reply:
        """Back (FinalReviewView._back) — the navigation alias for Edit.
        Shipped copy, verbatim."""
        return Reply(SUCCESS,
                     "Closed Final review — your wizard / hub anchor is "
                     "still open above.  Nothing has been applied.")

    @handler("setup.final_cancel")
    async def final_cancel(req) -> Reply:
        """Cancel (FinalReviewView._cancel). Shipped copy, verbatim."""
        return Reply(SUCCESS,
                     "Final review cancelled — nothing was applied.")

    # ---- partial-apply recovery (PartialApplyRecoveryView) ----

    @handler("setup.recovery_retry")
    async def recovery_retry(req) -> Reply | None:
        """Retry — re-run the apply path: same gate, same single-flight
        lock, same draft-clear / mark-complete guarding, same partial
        recovery branch on second failure (the oracle rebuilt a
        FinalReviewView and re-ran _run_apply)."""
        guild_id = int(req.guild_id or 0)
        if not await _gated(req):
            return Reply(BLOCKED, GATE_MSG_APPLY)
        try:
            ops = await _staged_ops(guild_id)
        except Exception:  # noqa: BLE001
            logger.exception("recovery retry: staged-ops read failed")
            return Reply(BLOCKED,
                         "Could not read the staged draft — see logs.")
        if not ops:
            return Reply(BLOCKED, "Nothing to apply.")
        try:
            async with acquire_setup_apply_lock(guild_id):
                return await _run_apply_flow(req)
        except SetupApplyInProgressError:
            # shipped copy, verbatim.
            return Reply(BLOCKED, IN_PROGRESS_MSG)

    @handler("setup.recovery_finish")
    async def recovery_finish(req) -> Reply:
        """Finish anyway — drop the remaining staged ops and mark setup
        complete (the partial-apply stickiness escape hatch; already-
        applied ops stay applied). Shipped copy, verbatim (the embed
        description; the '🛰 Setup finished (with skips)' title is embed
        chrome — the ledgered text-reply seam)."""
        from sb.domain.setup import wizard

        guild_id = int(req.guild_id or 0)
        if not await _gated(req):
            return Reply(BLOCKED, GATE_MSG_APPLY)
        try:
            await wizard.clear_guild_drafts(guild_id)
        except Exception:  # noqa: BLE001 — oracle: logged, never raised
            logger.exception(
                "PartialApplyRecoveryView._finish_anyway: clear failed")
        await _mark_complete(req)
        summary = last_summary(guild_id) or ApplySummary()
        dropped = len(summary.failed) + len(summary.skipped)
        noun = "operation" if dropped == 1 else "operations"
        return Reply(SUCCESS,
                     "🛰 Setup finished (with skips) — "
                     f"Applied **{len(summary.applied)}** operation(s). "
                     f"Dropped **{dropped}** un-appliable {noun} from the "
                     "draft. Re-run `/setup` any time to revisit them.")

    @handler("setup.recovery_cancel")
    async def recovery_cancel(req) -> Reply:
        """Cancel (PartialApplyRecoveryView._cancel). Shipped copy,
        verbatim."""
        return Reply(SUCCESS,
                     "Recovery cancelled — your draft is preserved. Re-open "
                     "Final review when you're ready to retry.")

    # ---- setup complete (SetupCompleteView) ----

    @handler("setup.complete_delete")
    async def complete_delete(req) -> Reply:
        """Delete now — the ported cleanup_setup_channel_after_completion
        guard ladder (order verbatim), then the K7
        ``setup.cleanup_workspace`` op (Discord delete + pointer nulls).
        Every refusal is the shipped ⚠️-prefixed ephemeral detail."""
        from sb.domain.setup import store, wizard

        guild_id = int(req.guild_id or 0)
        if not await _gated(req):
            return Reply(BLOCKED, GATE_MSG_APPLY)
        try:
            session = await store.get_session_row(guild_id)
        except Exception:  # noqa: BLE001 — oracle: resume failed branch
            logger.exception("SetupCompleteView._on_delete: resume failed")
            return Reply(BLOCKED,
                         "Couldn't read the setup session — see logs.")
        if session is None or str(session.get("setup_status")) != "complete":
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "⚠️ Setup isn't complete yet — finish a Final "
                         "Review apply before deleting the setup channel.")
        try:
            pending = await wizard.staged_ops_count(guild_id)
        except Exception:  # noqa: BLE001 — shipped count-failed branch
            logger.exception(
                "cleanup_setup_channel: setup_draft.count failed (guild=%d)",
                guild_id)
            return Reply(BLOCKED,
                         "⚠️ Couldn't read the staged-ops count — see "
                         "logs.  Re-run Final Review or try again later.")
        if pending > 0:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         f"⚠️ There are still **{pending}** staged "
                         "operation(s) — Final Review left them in the "
                         "draft for recovery.  Apply them (or run "
                         "`/setup-reset`) before deleting the channel.")
        channel_id = (int(session["setup_channel_id"])
                      if session.get("setup_channel_id") else 0)
        if not channel_id:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "⚠️ No setup channel is recorded for this guild — "
                         "nothing to delete.")
        # the shipped id/name guard pair, adapted to the gateway-cache
        # NAME lookup this architecture carries (module docstring): the
        # canonical-name resolve returning nothing ⇒ the channel is gone
        # or operator-renamed — either way NEVER deleted; a resolve that
        # disagrees with the session pointer refuses (belt-and-braces).
        from sb.domain.channel import service as channel_service
        from sb.domain.setup.service import SETUP_CHANNEL_NAME

        try:
            resolved = await channel_service.resolve_channel(
                guild_id, SETUP_CHANNEL_NAME)
        except Exception:  # noqa: BLE001 — an unreadable cache never deletes
            logger.exception("cleanup_setup_channel: channel resolve failed")
            resolved = None
        if resolved is None:
            # the shipped already-gone branch: null the pointer, answer
            # the non-error reason (copy verbatim).
            await _clear_workspace_pointers(req)
            return Reply(SUCCESS,
                         "⚠️ The setup channel is already gone — cleared "
                         "the session pointer for you.")
        if int(resolved) != channel_id:
            # shipped guard copy, verbatim.
            return Reply(BLOCKED,
                         "⚠️ The session's setup_channel_id doesn't match "
                         "the resolved channel; refusing to delete.")
        # the Discord-side delete rides the channel-state port directly
        # (the channel domain's `!del` precedent — no K7 leg wraps a
        # pure Discord effect); the shipped delete reason, verbatim
        # (delete_setup_channel's default). NotFound-as-success rides
        # the port contract (already-gone IS the goal state).
        from sb.domain.channel.service import active_actions

        try:
            await active_actions().delete_channel(
                channel_id,
                reason="Setup complete — operator confirmed auto-cleanup")
        except Exception:  # noqa: BLE001 — the shipped delete-failed branch
            logger.exception("cleanup_setup_channel: delete failed")
            # shipped copy, verbatim.
            return Reply(BLOCKED,
                         "⚠️ Discord refused the delete — check the bot's "
                         "Manage Channels permission and see logs.")
        # null both pointers so the next /setup re-creates a fresh
        # channel (oracle order: delete, THEN null — best-effort).
        await _clear_workspace_pointers(req)
        summary = last_summary(guild_id) or ApplySummary()
        # shipped confirmation copy, verbatim.
        return Reply(SUCCESS,
                     "✅ Setup channel deleted.  "
                     f"Applied **{len(summary.applied)}** operation(s); "
                     "re-run `/setup` later to recreate it.")

    @handler("setup.complete_keep")
    async def complete_keep(req) -> Reply:
        """Keep setup channel (SetupCompleteView._on_keep). Shipped
        copy, verbatim."""
        if not await _gated(req):
            return Reply(BLOCKED, GATE_MSG_APPLY)
        return Reply(SUCCESS,
                     "✅ Setup channel kept.  Re-run `/setup` any time to "
                     "revisit the wizard.")


async def _clear_workspace_pointers(req) -> None:
    """The oracle's null-the-pointers write, through the K7
    ``setup.clear_workspace_pointer`` op (best-effort — the oracle
    logged and continued)."""
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    try:
        await engine.run(WorkflowRef("setup.clear_workspace_pointer"),
                         ctx_from_request(req, {}))
    except Exception:  # noqa: BLE001
        logger.exception("cleanup_setup_channel: nulling channel id failed")


# --- registration ----------------------------------------------------------------------

def _register_panels() -> None:
    from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered, panel

    for name, fn in (("setup.final_review_render", _render_final_review),
                     ("setup.recovery_render", _render_recovery),
                     ("setup.complete_render", _render_complete)):
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for pid, factory in ((FINAL_REVIEW_PANEL_ID, final_review_spec),
                         (RECOVERY_PANEL_ID, recovery_spec),
                         (COMPLETE_PANEL_ID, complete_spec)):
        if not is_registered(PanelRef(pid)):
            panel(pid)(factory)


_register()
_register_panels()


def ensure_final_review_refs() -> None:
    _register()
    _register_panels()
