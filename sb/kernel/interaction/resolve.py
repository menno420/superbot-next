"""`resolve(ResolveRequest) -> Result` — THE chokepoint (frozen L0 spec 02
§3.2, post-absorption). Fixed order:

    admission → authority (K6) → validate → cooldown → [ACK] → audit →
    dispatch → render

Absorption edits applied (the explicit S9 L0 task):
  RC-2/3  — consumes 04's 10-field `AuthorityDecision` + `Lane`; DERIVES
            `override_applied = owner_override ∧ lane_would_deny` and
            `base_allowed = ¬lane_would_deny` onto the dispatch trace;
  RC-4    — threads `decision.owner_override` into `resolve_channel_access`
            (the L-12 owner deny stays closed);
  RC-5/15 — names `build_transparency_audit` + the `TransparencySink` port at
            step 4 (installable; default `LoggingTransparencySink`);
  RC-12   — reads `actor.member_tier`/`actor.role_ids` into the
            `AuthorityRequest`;
  RC-14   — the step-1 denial copy IS `decision.denial_message`.

Policy reads ride installable ports (command-access policy, subsystem
visibility) — armed by their bands; defaults are unconfigured-allow.
`OPEN_PANEL` dispatches through the installable panel-engine port (the
panel/presentation runtime is S9b).
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from sb.kernel.authority.channel_access import CommandAccessSnapshot, resolve_channel_access
from sb.kernel.authority.decision import AuthorityDecision, AuthorityRequest
from sb.kernel.authority.resolve import resolve_authority
from sb.kernel.authority.transparency import (
    LoggingTransparencySink,
    TransparencySink,
    build_transparency_audit,
)
from sb.kernel.interaction import cooldown as cooldown_mod
from sb.kernel.interaction.errors import ValidatorError, from_exception
from sb.kernel.interaction.predicates import EvalContext, evaluate
from sb.kernel.interaction.request import ConfirmPrompt, ResolveRequest, Surface
from sb.kernel.interaction.result import Result, lane_default, resolve_reply_visibility
from sb.kernel.interaction.trace import emit_dispatch_trace
from sb.kernel.lifecycle import can_accept_commands
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.namespace.bootstrap import is_bootstrap_command
from sb.spec.confirmation import Challenge
from sb.spec.outcomes import (
    BLOCKED,
    DECLINED,
    SUCCESS,
    DeferMode,
    DenialReason,
    ErrorClass,
    ReplyVisibility,
)
from sb.spec.refs import HandlerRef, PanelRef, WorkflowRef, resolve as resolve_ref

logger = logging.getLogger("sb.kernel.interaction.resolve")

__all__ = [
    "cancel_pending_confirm",
    "install_access_policy_reader",
    "install_panel_engine",
    "install_transparency_sink",
    "install_visibility_reader",
    "reset_resolver_ports_for_tests",
    "resolve",
]

# --- installable ports -------------------------------------------------------

AccessPolicyReader = Callable[[int], Awaitable[CommandAccessSnapshot | None]]
VisibilityReader = Callable[[int, str], Awaitable[bool]]     # subsystem visible?
PanelEngine = Callable[[PanelRef, ResolveRequest], Awaitable[None]]


async def _no_policy(guild_id: int) -> CommandAccessSnapshot | None:
    return None


async def _all_visible(guild_id: int, subsystem: str) -> bool:
    return True


async def _no_panel_engine(ref: PanelRef, req: ResolveRequest) -> None:
    raise NotImplementedError(
        f"panel engine not installed (S9b): cannot OPEN_PANEL {ref.name!r}")


_policy_reader: AccessPolicyReader = _no_policy
_visibility_reader: VisibilityReader = _all_visible
_panel_engine: PanelEngine = _no_panel_engine
_transparency_sink: TransparencySink = LoggingTransparencySink()
_seen_request_ids: dict[str, None] = {}   # confirm re-entry dedup (in-memory, §④.2)
_pending_confirm_args: dict[str, dict] = {}   # request_id -> original args
                                              # (v1 confirm re-entry carry)
_cancelled_request_ids: dict[str, None] = {}  # confirm-cancel terminal (S9b view)
_SEEN_MAX = 4096


def install_access_policy_reader(reader: AccessPolicyReader) -> None:
    global _policy_reader
    _policy_reader = reader


def install_visibility_reader(reader: VisibilityReader) -> None:
    global _visibility_reader
    _visibility_reader = reader


def install_panel_engine(engine: PanelEngine) -> None:
    global _panel_engine
    _panel_engine = engine


def install_transparency_sink(sink: TransparencySink) -> None:
    global _transparency_sink
    _transparency_sink = sink


def reset_resolver_ports_for_tests() -> None:
    global _policy_reader, _visibility_reader, _panel_engine, _transparency_sink
    _policy_reader = _no_policy
    _visibility_reader = _all_visible
    _panel_engine = _no_panel_engine
    _transparency_sink = LoggingTransparencySink()
    _seen_request_ids.clear()
    _pending_confirm_args.clear()
    _cancelled_request_ids.clear()


def cancel_pending_confirm(request_id: str) -> bool:
    """The confirm-terminal's kernel leg (02 §3.2 step 3 — decline/timeout):
    drop the stashed args and remember the cancellation so a late confirm
    click gets the DECLINED terminal, not a dispatch. Returns True when a
    pending confirm existed (an idle cancel is not an error — the surface
    may cancel twice or after expiry). Same in-memory posture as the maps
    above."""
    had_pending = _pending_confirm_args.pop(request_id, None) is not None
    _cancelled_request_ids[request_id] = None
    while len(_cancelled_request_ids) > _SEEN_MAX:
        _cancelled_request_ids.pop(next(iter(_cancelled_request_ids)))
    return had_pending


# --- helpers ------------------------------------------------------------------

async def _declined(req: ResolveRequest, user_message: str) -> Result:
    """The confirm DECLINED terminal (§2.7 vocab), RENDERED — a clicked
    Confirm must answer even when it dispatches nothing."""
    result = _result(req, outcome=DECLINED, reason=DenialReason.CONFIRM_DECLINED,
                     error_class=ErrorClass.NONE, retryable=False,
                     visibility=ReplyVisibility.EPHEMERAL,
                     user_message=user_message)
    try:
        await req.responder.render(result)
    except Exception:  # noqa: BLE001 — render failure is logged, never raised
        logger.warning("responder.render failed (confirm terminal)", exc_info=True)
    return result


def _spec_field(req: ResolveRequest, name: str, default=None):
    return getattr(req.target.spec, name, default)


def _routable_ref(req: ResolveRequest):
    spec = req.target.spec
    return (getattr(spec, "route", None) or getattr(spec, "handler", None)
            or getattr(spec, "on_select", None))


def _op_confirmation(route) -> object | None:
    """The op's own ConfirmationSpec for WorkflowRef routes. CommandSpec
    carries no confirm field ([S]-pinned), so without this read a
    confirmation-fenced op behind a command (moderation.kick, §2.7) never
    reached the interactive confirm gate — every dispatch dead-ended in the
    engine's HEADLESS backstop refusal (band-2 finding, D-0052)."""
    if not isinstance(route, WorkflowRef):
        return None
    from sb.kernel.workflow.registry import REGISTRY

    try:
        spec = REGISTRY.resolve(route)
    except Exception:  # noqa: BLE001 — not a registered op => no confirm
        return None
    return getattr(spec, "confirmation", None)


def _result(req: ResolveRequest, *, outcome: str, reason: DenialReason,
            error_class: ErrorClass, retryable: bool, visibility: ReplyVisibility,
            user_message: str | None, workflow=None, audit_emitted=False) -> Result:
    return Result(outcome=outcome, reason=reason, error_class=error_class,
                  retryable=retryable, reply_visibility=visibility,
                  user_message=user_message, surface=req.surface,
                  workflow=workflow, audit_emitted=audit_emitted,
                  request_id=req.request_id)


async def _deny(req: ResolveRequest, *, reason: DenialReason,
                error_class: ErrorClass, user_message: str | None,
                retryable: bool = False, silent: bool = False) -> Result:
    """Pre-ack denial: the denial IS its own ack (always ephemeral;
    DRAINING is silent — no ack at all)."""
    visibility = ReplyVisibility.SILENT if silent else ReplyVisibility.EPHEMERAL
    if not silent and user_message:
        try:
            await req.responder.deny(user_message, ephemeral=True)
        except Exception:  # noqa: BLE001 — a failed denial render never raises out
            logger.warning("responder.deny failed", exc_info=True)
    return _result(req, outcome=BLOCKED, reason=reason, error_class=error_class,
                   retryable=retryable, visibility=visibility,
                   user_message=user_message)


def _surface_default_defer(req: ResolveRequest) -> DeferMode:
    route = _routable_ref(req)
    if req.surface is Surface.SLASH:
        return DeferMode.NONE if isinstance(route, PanelRef) else DeferMode.AUTO
    if req.surface is Surface.COMPONENT:
        return DeferMode.AUTO
    # PREFIX / MODAL-submit / NL / message surfaces
    return DeferMode.NONE


# --- the chokepoint -----------------------------------------------------------

async def resolve(req: ResolveRequest) -> Result:  # noqa: PLR0911, PLR0912, PLR0915
    spec = req.target.spec
    actor = req.actor

    # 0. admission — draining stops EVERY surface, silent (no ack).
    if not can_accept_commands():
        return await _deny(req, reason=DenialReason.DRAINING,
                           error_class=ErrorClass.NONE, user_message=None,
                           silent=True)

    # 1. authority (K6) — ONE authority_ref; override applied once inside.
    decision: AuthorityDecision = await resolve_authority(AuthorityRequest(
        authority_ref=_spec_field(req, "authority_ref", "") or "",
        actor_type=getattr(actor, "actor_type", "user") or "user",
        user_id=actor.user_id,
        guild_id=req.guild_id,
        is_member=req.guild_id is not None and not actor.is_dm,
        member_tier=getattr(actor, "member_tier", None),
        role_ids=getattr(actor, "role_ids", frozenset()) or frozenset(),
    ))
    if not decision.allowed:
        return await _deny(req, reason=DenialReason.AUTHORITY,
                           error_class=ErrorClass.DENIED,
                           user_message=decision.denial_message)

    # 2. validate.
    eval_ctx = EvalContext(guild_id=req.guild_id or 0, channel_id=req.channel_id,
                           actor=actor)
    # (a) per-guild enablement + visibility + the channel-access lane.
    if not await evaluate(_spec_field(req, "enabled_when", "") or "", eval_ctx):
        return await _deny(req, reason=DenialReason.DISABLED,
                           error_class=ErrorClass.DENIED,
                           user_message="This feature is disabled in this server.")
    subsystem = getattr(spec, "owner_subsystem", None) or req.target.key.split(".")[0]
    if req.guild_id is not None and not await _visibility_reader(req.guild_id, subsystem):
        return await _deny(req, reason=DenialReason.VISIBILITY,
                           error_class=ErrorClass.DENIED,
                           user_message="This feature isn't available here.")
    if req.surface is Surface.COMPONENT:
        # defense-in-depth stale/replayed-custom_id guard: re-evaluate the
        # component's render gate at dispatch (02 §3.0).
        if not await evaluate(_spec_field(req, "visible_when", "") or "", eval_ctx):
            return await _deny(req, reason=DenialReason.DISABLED,
                               error_class=ErrorClass.DENIED,
                               user_message="This control is no longer available.")
    channel = None
    if req.guild_id is not None:
        policy = await _policy_reader(req.guild_id)
        channel = await resolve_channel_access(
            policy, req.channel_id,
            owner_override=decision.owner_override,                 # RC-4
            is_bootstrap=is_bootstrap_command(req.target.key),
            is_operator=actor.is_guild_operator,
            is_owner=actor.is_bot_owner,
            actor_role_ids=getattr(actor, "role_ids", frozenset()) or frozenset(),
        )
        if not channel.allowed:
            return await _deny(req, reason=channel.reason,
                               error_class=ErrorClass.DENIED,
                               user_message=channel.denial_message)
    # (b) argument validation against the spec's ParamSpecs (duck-typed:
    # a spec-supplied validator callable; ValidatorError => user_error).
    validator = getattr(spec, "validate_args", None)
    if callable(validator):
        try:
            validator(req.args)
        except ValidatorError as exc:
            envelope = from_exception(exc, surface=req.surface, target=req.target)
            return await _deny(req, reason=envelope.reason,
                               error_class=envelope.error_class,
                               user_message=envelope.user_message, retryable=True)

    # 3. cooldown (charge BEFORE the ack, refunded on transient/bug).
    cooldown_spec = _spec_field(req, "cooldown", None)
    ai_axis = req.surface in (Surface.NL_INTENT, Surface.NL_ORCHESTRATION)
    allowed, retry_after = cooldown_mod.charge(
        cooldown_spec, target_key=req.target.key, guild_id=req.guild_id,
        channel_id=req.channel_id, user_id=actor.user_id, ai_axis=ai_axis)
    if not allowed:
        reason = DenialReason.AI_THROTTLE if ai_axis else DenialReason.COOLDOWN
        return await _deny(req, reason=reason, error_class=ErrorClass.DENIED,
                           retryable=True,
                           user_message=f"Slow down — try again in {retry_after:.0f}s.")

    # --- ACK boundary: resolve defer_mode; a defer COMMITS the visibility V.
    declared = _spec_field(req, "reply_visibility", None)
    committed_v = declared or lane_default(decision.lane)
    defer_mode = _spec_field(req, "defer_mode", None) or _surface_default_defer(req)
    modal_issued = False
    try:
        if defer_mode is DeferMode.AUTO:
            await req.responder.ack(ephemeral=committed_v is ReplyVisibility.EPHEMERAL)
        elif defer_mode is DeferMode.MODAL:
            if req.surface is Surface.MODAL:
                # the SUBMIT re-entry (G-10): the form is already collected —
                # ack like AUTO and fall through to dispatch with the fields.
                await req.responder.ack(
                    ephemeral=committed_v is ReplyVisibility.EPHEMERAL)
            else:
                # the OPENING click: issue the declared form and stop — the
                # handler runs on submit, never on open (G-10; terminal
                # below, mirroring the confirm-issued pattern).
                await req.responder.open_modal(getattr(spec, "modal", None))
                modal_issued = True
    except Exception:  # noqa: BLE001 — a failed ack is a transient render issue
        logger.warning("responder ack/open_modal failed", exc_info=True)

    # 4. audit — the dispatch trace skeleton (outcome back-filled at render);
    # the transparency audit fires when the override carried the dispatch.
    override_applied = decision.owner_override and decision.lane_would_deny  # RC-2
    base_allowed = not decision.lane_would_deny
    audit = build_transparency_audit(
        decision, channel, actor_id=actor.user_id or 0,
        guild_id=req.guild_id or 0, target_key=req.target.key,
        surface=req.surface.value, )
    if audit is not None:
        try:
            await _transparency_sink.emit(audit)                    # RC-15
        except Exception:  # noqa: BLE001 — the sink never blocks dispatch
            logger.warning("transparency sink emit failed", exc_info=True)

    # 5. dispatch.
    if modal_issued:
        # G-10 terminal: the modal IS the response; dispatch happens on the
        # submit re-entry (surface=MODAL) with args = the field values.
        result = _result(req, outcome=SUCCESS, reason=DenialReason.ALLOWED,
                         error_class=ErrorClass.NONE, retryable=False,
                         visibility=ReplyVisibility.EPHEMERAL,
                         user_message=None, audit_emitted=True)
        emit_dispatch_trace(req, decision, override_applied=override_applied,
                            base_allowed=base_allowed, outcome=SUCCESS,
                            reason=DenialReason.ALLOWED, note="modal-issued")
        return result
    workflow_result = None
    confirm = (_spec_field(req, "confirm", None)
               or _spec_field(req, "confirmation", None)
               or _op_confirmation(_routable_ref(req)))
    if confirm is not None and not req.confirmed:
        prompt = ConfirmPrompt(
            target_key=req.target.key, request_id=req.request_id,
            challenge=getattr(confirm, "challenge", Challenge.BUTTON),
            timeout_s=getattr(confirm, "timeout_s", 60),
        )
        # stash the ORIGINAL args for the re-entry: the confirm control
        # carries only (target_key, request_id), so without this the
        # confirmed dispatch lost the command's own arguments (`!kick @m r`
        # re-entered arg-less and died in a member-missing user_error —
        # band-2 finding, D-0052). Same in-memory posture as the dedup map.
        _pending_confirm_args[req.request_id] = dict(req.args)
        while len(_pending_confirm_args) > _SEEN_MAX:
            _pending_confirm_args.pop(next(iter(_pending_confirm_args)))
        try:
            await req.responder.open_confirm(prompt)
        except Exception:  # noqa: BLE001
            logger.warning("responder.open_confirm failed", exc_info=True)
        result = _result(req, outcome=SUCCESS, reason=DenialReason.ALLOWED,
                         error_class=ErrorClass.NONE, retryable=False,
                         visibility=ReplyVisibility.EPHEMERAL,
                         user_message=None, audit_emitted=True)
        emit_dispatch_trace(req, decision, override_applied=override_applied,
                            base_allowed=base_allowed, outcome=SUCCESS,
                            reason=DenialReason.CONFIRM_DECLINED, note="confirm-issued")
        return result
    if req.confirmed:
        # a cancelled confirm's late click gets the §2.7 DECLINED terminal —
        # never a dispatch (the S9b cancel control, 02 §3.2 step 3).
        if req.request_id in _cancelled_request_ids:
            return await _declined(req, "This action was cancelled.")
        # the re-entry idempotency checkpoint: request_id is the dedup key —
        # a double-clicked confirm runs once (in-memory, vocab §④.2).
        if req.request_id in _seen_request_ids:
            return await _declined(req, "This action was already confirmed.")
        _seen_request_ids[req.request_id] = None
        while len(_seen_request_ids) > _SEEN_MAX:
            _seen_request_ids.pop(next(iter(_seen_request_ids)))

    # the confirmed re-entry restores the original command args (stashed at
    # prompt time); the re-entry's own args (interaction_id, ...) win ties.
    dispatch_args = dict(req.args)
    if req.confirmed:
        stashed = _pending_confirm_args.pop(req.request_id, None)
        if stashed:
            dispatch_args = {**stashed, **dispatch_args}

    route = _routable_ref(req)
    outcome = SUCCESS
    reason = DenialReason.ALLOWED
    error_class = ErrorClass.NONE
    retryable = False
    user_message = None
    try:
        if isinstance(route, PanelRef):
            await _panel_engine(route, req)                 # OPEN_PANEL — terminal render
        elif isinstance(route, WorkflowRef):
            ctx = WorkflowContext(
                actor=actor, guild_id=req.guild_id or 0,
                request_id=req.request_id, confirmed=req.confirmed,
                params=dispatch_args,
            )
            workflow_result = await workflow_engine.run(route, ctx)
            outcome = workflow_result.outcome                # copied through UNCHANGED
            user_message = workflow_result.user_message
        elif isinstance(route, HandlerRef):
            handler = resolve_ref(route)
            workflow_result = await handler(req)
            if workflow_result is not None:
                outcome = workflow_result.outcome
                user_message = getattr(workflow_result, "user_message", None)
        else:
            raise ValidatorError("route", f"target {req.target.key!r} has no routable ref")
    except Exception as exc:  # noqa: BLE001 — the envelope, not a crash
        envelope = from_exception(exc, surface=req.surface, target=req.target)
        outcome = envelope.outcome
        reason = envelope.reason
        error_class = envelope.error_class
        retryable = envelope.retryable
        user_message = envelope.user_message
        if error_class in (ErrorClass.TRANSIENT, ErrorClass.BUG):
            cooldown_mod.refund(cooldown_spec, target_key=req.target.key,
                                guild_id=req.guild_id, channel_id=req.channel_id,
                                user_id=actor.user_id)          # fork D

    # 6. render.
    visibility = resolve_reply_visibility(
        outcome=outcome, reason=reason, lane=decision.lane, declared=declared,
        committed=req.responder.committed_visibility(),
    )
    result = _result(req, outcome=outcome, reason=reason, error_class=error_class,
                     retryable=retryable, visibility=visibility,
                     user_message=user_message, workflow=workflow_result,
                     audit_emitted=True)
    try:
        await req.responder.render(result)
    except Exception:  # noqa: BLE001 — render failure is logged, never raised
        logger.warning("responder.render failed", exc_info=True)
    emit_dispatch_trace(req, decision, override_applied=override_applied,
                        base_allowed=base_allowed, outcome=outcome, reason=reason)
    return result
