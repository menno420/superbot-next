"""The K7 engine (frozen L0 spec 07 §3.2/§3.3/§3.5/§3.7) — THREE co-designed
entries over ONE internal core:

- ``run(target, ctx, *, dry_run=False)`` — self-owned txn + self-owned
  ``once()`` (namespace = op_key). The resolver ``INVOKE_WORKFLOW`` target
  AND the draft pipeline's per-op entry (PIN-2/F-2: EFFECT-bearing draft ops
  come through HERE, per-op-atomic + idempotent-resume — never one shared
  txn).
- ``run_ref(ref, ctx, *, conn=None)`` — conn=None delegates to ``run``;
  conn provided = EXTERNAL-CONN mode: DB legs + central audit + AT_LEAST_ONCE
  emits on the CALLER's conn; no txn, no once()/record_outcome (caller owns
  dedup), no EFFECT legs, no BEST_EFFORT emit (caller owns commit). The
  scheduler ``_fire`` / invariant ``repair_refs`` / version
  ``compensation_refs`` seam (spec 09).
- ``apply(op, *, conn)`` — the op_kind → spec external-conn SIBLING of
  ``run_ref`` (draft op-kind dispatch shape; NOT the draft's live entry).
- ``preview(target, ctx)`` — ``run(dry_run=True)`` projected to
  ``MutationPreview``: txn-rollback + skip-EFFECT is the STRUCTURAL dry-run
  oracle (after preview, DB state is byte-identical and zero effect calls
  fired).

Error-return contract (spec 07 §3.3-note / §8 fork G): every CLASSIFIED leg
failure is caught, the txn rolled back, and a ``WorkflowResult`` on the
frozen five RETURNED — never raised. Classification goes through spec 02's
``from_exception(exc, surface=MAINTENANCE, target=None)`` once S9 lands it;
until then the K7-local ``_classify_exception`` mirrors the frozen table's
rows for the exception types reachable pre-K8 (ConnectionError/TimeoutError
⇒ transient/DISCORD_FAILED; everything else ⇒ bug/BLOCKED) — S9 MUST re-point
``_classify_exception`` to the real ``from_exception`` (recorded D-0010).

``ConfirmRequired`` is a typed CONTROL SIGNAL, never a ``from_exception``
input: the headless backstop maps it to BLOCKED/CONFIRM_DECLINED.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import replace
from typing import TYPE_CHECKING

from sb.kernel.authority.decision import AuthorityRequest
from sb.kernel.authority.resolve import resolve_authority
from sb.kernel.db import pool as db
from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.outbox.enqueue import enqueue_all
from sb.kernel.workflow.audit import emit_central_audit
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY, WorkflowRegistry
from sb.kernel.workflow.result import (
    FieldChange,
    MutationPreview,
    PlannedStep,
    StepResult,
    WorkflowResult,
    classify_outcome,
)
from sb.kernel.workflow.spec import CompoundOpSpec, IdempotencyPosture, LegKind
from sb.spec.outcomes import BLOCKED, DISCORD_FAILED, PARTIAL, SUCCESS, DenialReason
from sb.spec.refs import WorkflowRef, resolve

if TYPE_CHECKING:  # pragma: no cover - typing only
    import asyncpg

__all__ = ["ConfirmRequired", "apply", "preview", "run", "run_ref"]


class ConfirmRequired(Exception):
    """The typed control signal (spec 07 §3.3 step 2) — NOT an error."""


class _AbortTxn(Exception):
    """Internal sentinel: a required DB leg failed; carries the classified
    result fields so the outer wrapper RETURNS them after rollback."""

    def __init__(self, outcome: str, reason: DenialReason, user_message: str | None):
        self.outcome = outcome
        self.reason = reason
        self.user_message = user_message


class _DryRunRollback(Exception):
    """Raised at step 4g so the txn context manager rolls everything back."""

    def __init__(self, result: WorkflowResult):
        self.result = result


# In-process SINGLE_FLIGHT locks (ADR-001 single-process posture).
_single_flight_locks: dict[str, asyncio.Lock] = {}

# The event bus wired at the composition root (K8) for BEST_EFFORT emits.
_bus: object | None = None


def install_bus(bus: object) -> None:
    global _bus
    _bus = bus


def _classify_exception(exc: BaseException) -> tuple[str, DenialReason, str]:
    """The K7 leg-exception path (spec 07 §3.3 step 4b, RC-19): classify
    through spec 02's `from_exception(exc, surface=Surface.MAINTENANCE,
    target=None)` — K7 is the surface-agnostic composition layer, so it
    classifies under the ONE background surface with no target (PIN-4).
    Function-level import: kernel/interaction imports kernel/workflow at
    module level (the resolver dispatches run()), so this edge stays lazy."""
    from sb.kernel.interaction.errors import from_exception
    from sb.kernel.interaction.request import Surface

    envelope = from_exception(exc, surface=Surface.MAINTENANCE, target=None)
    return envelope.outcome, envelope.reason, envelope.user_message


def _blocked(spec: CompoundOpSpec, ctx: WorkflowContext, *, outcome: str,
             user_message: str | None, mutation_id: str = "") -> WorkflowResult:
    return WorkflowResult(
        mutation_id=mutation_id, guild_id=ctx.guild_id, domain=spec.domain,
        operation=spec.op_key, outcome=outcome, reversibility=spec.reversibility,
        lane=spec.lane, user_message=user_message,
    )


async def _resolve_leg0(spec: CompoundOpSpec, ctx: WorkflowContext):
    """Leg-0: authority (K6). K7 maps ctx.actor.* → AuthorityRequest
    (RC-12/RC-18); cross-guild membership is asserted by the caller."""
    actor = ctx.actor
    return await resolve_authority(AuthorityRequest(
        authority_ref=spec.authority_ref,
        actor_type=getattr(actor, "actor_type", "user") or "user",
        user_id=getattr(actor, "user_id", None),
        guild_id=ctx.guild_id or None,
        is_member=bool(ctx.guild_id) and not getattr(actor, "is_dm", False),
        member_tier=getattr(actor, "member_tier", None),
        role_ids=getattr(actor, "role_ids", frozenset()) or frozenset(),
    ))


async def _run_db_legs(spec, ctx, conn) -> tuple[list[LegOutcome], list[StepResult]]:
    """Step 4b — DB legs in order; a required leg failure aborts the txn via
    _AbortTxn; a failed optional leg degrades to PARTIAL."""
    outcomes: list[LegOutcome] = []
    steps: list[StepResult] = []
    for leg in spec.legs:
        if leg.kind is not LegKind.DB:
            continue
        handler = resolve(leg.handler)
        try:
            out = await handler(conn, ctx)
        except Exception as exc:  # noqa: BLE001 — classified, returned (fork G)
            if not leg.optional:
                outcome, reason, message = _classify_exception(exc)
                raise _AbortTxn(outcome, reason, message) from exc
            steps.append(StepResult(0, leg.leg_id, False, str(exc)))
            continue
        outcomes.append(out)
        steps.append(out.step)
    return outcomes, steps


def _join_leg_copy(outcomes: list[LegOutcome]) -> str | None:
    """Success copy supplied by legs (LegOutcome.user_message), leg order,
    newline-joined — the surface renders WorkflowResult.user_message as-is."""
    lines = [str(o.user_message) for o in outcomes
             if getattr(o, "user_message", None)]
    return "\n".join(lines) if lines else None


def _rollup(outcomes: list[LegOutcome]) -> tuple[object, object]:
    befores = {getattr(o.step, "target_name", str(i)): o.before
               for i, o in enumerate(outcomes) if o.before is not None}
    afters = {getattr(o.step, "target_name", str(i)): o.after
              for i, o in enumerate(outcomes) if o.after is not None}
    return (befores or None, afters or None)


async def _reproduce(spec: CompoundOpSpec, ctx: WorkflowContext, prior,
                     conn) -> WorkflowResult:
    """Spec 07 §3.7 — the deduped-replay result: re-read the audit_log row by
    mutation_id, reproduce the first result, run NO effects and NO emits."""
    row = None
    if prior is not None and prior.result_ref:
        row = await db.fetchone(
            "SELECT prev_value, new_value, detail, occurred_at FROM audit_log "
            "WHERE mutation_id = $1", (prior.result_ref,), conn=conn)
    return WorkflowResult(
        mutation_id=(prior.result_ref if prior else "") or "",
        guild_id=ctx.guild_id, domain=spec.domain, operation=spec.op_key,
        outcome=prior.outcome if prior else SUCCESS,
        reversibility=spec.reversibility, lane=spec.lane,
        before=row["prev_value"] if row else None,
        after=row["new_value"] if row else None,
        committed_at=row["occurred_at"] if row else None,
        audit_emitted=row is not None, event_emitted=False,
        user_message="This action was already completed.",
    )


async def _execute(spec: CompoundOpSpec, ctx: WorkflowContext, *,
                   external_conn: "asyncpg.Connection | None") -> WorkflowResult:
    """The ONE core (spec 07 §3.3). external_conn=None => the self-owned-txn
    run() path; else the external-conn variant (steps 0-4e on the caller's
    conn; 4a/4f/5/6 skipped)."""
    # 0. empty-state — no txn, no audit, no dedup.
    if spec.empty_result is not None and resolve(spec.empty_result.predicate)(ctx):
        return WorkflowResult(
            mutation_id="", guild_id=ctx.guild_id, domain=spec.domain,
            operation=spec.op_key, outcome=SUCCESS,
            reversibility=spec.reversibility, lane=spec.lane,
            user_message=spec.empty_result.user_message,
        )

    # 1. authority (leg-0, K6).
    decision = await _resolve_leg0(spec, ctx)
    if not decision.allowed:
        return _blocked(spec, ctx, outcome=BLOCKED,
                        user_message=decision.denial_message)

    # 2. confirm backstop — presence-keyed (fork H); headless mapping below.
    if spec.confirmation is not None and not ctx.confirmed:
        raise ConfirmRequired(spec.op_key)

    # 3. mint + key (+ SINGLE_FLIGHT lock). The key is minted on the
    # self-owned lane only — external-conn callers own dedup (steps 4a/4f
    # skipped there, spec 07 §3.3 external-conn variant).
    mutation_id = str(uuid.uuid4())
    key: IdempotencyKey | None = None
    if external_conn is None and spec.idempotency is IdempotencyPosture.DURABLE_ONCE:
        key = IdempotencyKey(
            namespace=spec.op_key, guild_id=ctx.guild_id,
            dedup_token=spec.dedup_key.render(ctx),
        )
    lock: asyncio.Lock | None = None
    if spec.idempotency is IdempotencyPosture.SINGLE_FLIGHT:
        scope = spec.single_flight_scope or spec.op_key
        lock = _single_flight_locks.setdefault(scope, asyncio.Lock())
        await lock.acquire()

    batch = None
    committed_stamp = None
    try:
        async def _in_txn(conn) -> WorkflowResult:
            nonlocal batch, committed_stamp
            # 4a. guard (self-owned lane only).
            if external_conn is None and key is not None:
                if not await once(key, conn=conn):
                    return await _reproduce(spec, ctx, await read_outcome(key, conn=conn), conn)
            # 4b. DB legs.
            outcomes, steps = await _run_db_legs(spec, ctx, conn)
            before, after = _rollup(outcomes)
            outcome_so_far = SUCCESS if all(s.ok for s in steps) else PARTIAL
            # 4c. pending result (payload_builder may read every field here).
            # Legs may supply success copy (LegOutcome.user_message) — joined
            # in leg order; EFFECT legs append theirs post-commit (step 5).
            db_copy = _join_leg_copy(outcomes)
            pending = WorkflowResult(
                mutation_id=mutation_id, guild_id=ctx.guild_id,
                domain=spec.domain, operation=spec.op_key,
                outcome=outcome_so_far, reversibility=spec.reversibility,
                steps=tuple(steps), lane=spec.lane, before=before, after=after,
                committed_at=None, dedup_key=key, user_message=db_copy,
            )
            # 4d. central audit (row + durable bus twin), in-txn.
            occurred_at = ctx.clock() if callable(ctx.clock) else ctx.clock
            detail = {
                "legs": [
                    {"leg_id": getattr(s, "target_name", ""), "ok": s.ok, "error": s.error}
                    for s in steps
                ],
                "changes": [],
            }
            audit_emitted, event_emitted = await emit_central_audit(
                conn, spec=spec, ctx=ctx, mutation_id=mutation_id,
                prev_value=before, new_value=after, detail=detail,
                occurred_at=occurred_at,
            )
            committed_stamp = occurred_at
            # pending keeps committed_at=None (spec 07 §3.3 step 4c — the
            # final result at step 7 only ADDS committed_at + effect legs).
            pending = replace(pending, audit_emitted=audit_emitted,
                              event_emitted=event_emitted)
            # 4e. emits: AT_LEAST_ONCE in-txn now; BEST_EFFORT into the batch.
            resolved_emits = tuple(
                _ResolvedEmit(e.event, resolve(e.payload_builder), e.delivery)
                for e in spec.emits
            )
            batch = await enqueue_all(resolved_emits, ctx, pending, conn=conn, bus=_bus)
            # 4f. record (self-owned lane only).
            if external_conn is None and key is not None:
                await record_outcome(key, pending.outcome,
                                     result_ref=mutation_id, conn=conn)
            # 4g. dry-run rollback — nothing persists.
            if ctx.dry_run:
                raise _DryRunRollback(pending)
            return pending

        if external_conn is not None:
            result = await _in_txn(external_conn)
            # caller owns commit: committed_at=None stamps that honesty.
            return replace(result, committed_at=None)

        try:
            async with db.transaction() as conn:
                result = await _in_txn(conn)
        except _DryRunRollback as rollback:
            return rollback.result

        # 7-part-1. the commit fact stamps durability (step 4d's clock read).
        if committed_stamp is not None and result.committed_at is None:
            result = replace(result, committed_at=committed_stamp)
        # 5. EFFECT legs (post-commit; skipped under dry_run — unreachable here).
        result = await _run_effect_legs(spec, ctx, result)
        # 6. best-effort emit (post-commit).
        if batch is not None:
            await batch.emit_after_commit()
        return result

    except _AbortTxn as abort:
        return _blocked(spec, ctx, outcome=abort.outcome,
                        user_message=abort.user_message, mutation_id=mutation_id)
    finally:
        if lock is not None and lock.locked():
            lock.release()


async def _run_effect_legs(spec: CompoundOpSpec, ctx: WorkflowContext,
                           result: WorkflowResult) -> WorkflowResult:
    """Step 5 — EFFECT legs (conn=None). Fail + COMPENSATABLE => run the
    compensator, PARTIAL; fail + IRREVERSIBLE/other => operator finding,
    PARTIAL (fork E — no saga engine in v1)."""
    steps = list(result.steps)
    degraded = False
    copy_lines: list[str] = []
    for leg in spec.legs:
        if leg.kind is not LegKind.EFFECT:
            continue
        handler = resolve(leg.handler)
        try:
            out = await handler(None, ctx)
            steps.append(out.step)
            if getattr(out, "user_message", None):
                copy_lines.append(str(out.user_message))
        except Exception as exc:  # noqa: BLE001 — compensate-or-record (fork E)
            degraded = True
            steps.append(StepResult(0, leg.leg_id, False, str(exc)))
            if leg.compensator is not None:
                try:
                    await resolve(leg.compensator)(None, ctx)
                except Exception as comp_exc:  # noqa: BLE001
                    _record_finding(spec, leg.leg_id, f"compensator failed: {comp_exc}")
            else:
                _record_finding(spec, leg.leg_id, f"effect leg failed: {exc}")
    outcome = classify_outcome(tuple(steps)) if steps else result.outcome
    if degraded and outcome == SUCCESS:
        outcome = PARTIAL
    user_message = result.user_message
    if copy_lines:
        user_message = "\n".join(filter(None, [user_message, *copy_lines]))
    return replace(result, steps=tuple(steps), outcome=outcome,
                   user_message=user_message)


def _record_finding(spec: CompoundOpSpec, leg_id: str, summary: str) -> None:
    try:
        from sb.kernel.observability.findings import record_operator_finding
        record_operator_finding(
            source=f"workflow:{spec.op_key}", severity="warning",
            summary=f"EFFECT leg {leg_id!r}: {summary}", detail="",
            correlation_id=None,
        )
    except Exception:  # noqa: BLE001 — findings are observability only
        pass


class _ResolvedEmit:
    """EventEmitSpec with the payload_builder WorkflowRef pre-resolved to a
    callable — the shape `outbox.enqueue_all` duck-reads."""

    __slots__ = ("delivery", "event", "payload_builder")

    def __init__(self, event: str, payload_builder, delivery) -> None:
        self.event = event
        self.payload_builder = payload_builder
        self.delivery = delivery


def _headless_confirm_result(spec: CompoundOpSpec, ctx: WorkflowContext) -> WorkflowResult:
    return WorkflowResult(
        mutation_id="", guild_id=ctx.guild_id, domain=spec.domain,
        operation=spec.op_key, outcome=BLOCKED, reversibility=spec.reversibility,
        lane=spec.lane,
        user_message="This action needs interactive confirmation and can't run unattended.",
    )


def _resolve_target(target: "WorkflowRef | CompoundOpSpec",
                    registry: WorkflowRegistry) -> CompoundOpSpec:
    if isinstance(target, CompoundOpSpec):
        return target
    return registry.resolve(target)


async def run(target: "WorkflowRef | CompoundOpSpec", ctx: WorkflowContext, *,
              dry_run: bool = False,
              registry: WorkflowRegistry = REGISTRY) -> WorkflowResult:
    """The self-owned-txn entry (resolver INVOKE_WORKFLOW + draft per-op)."""
    spec = _resolve_target(target, registry)
    if dry_run and not ctx.dry_run:
        ctx = replace(ctx, dry_run=True)
    try:
        return await _execute(spec, ctx, external_conn=None)
    except ConfirmRequired:
        if getattr(ctx.actor, "actor_type", "user") in ("system", "backfill"):
            return _headless_confirm_result(spec, ctx)
        # interactive callers (the resolver) gate confirms at THEIR step 5;
        # reaching here headless without a scripted actor is still headless.
        return _headless_confirm_result(spec, ctx)


async def run_ref(ref: "WorkflowRef", ctx: WorkflowContext, *,
                  conn: "asyncpg.Connection | None" = None,
                  registry: WorkflowRegistry = REGISTRY) -> WorkflowResult:
    """conn=None => run(); conn => EXTERNAL-CONN mode (scheduler/invariant/
    version callers own txn + dedup; atomic_db_only-fenced specs only)."""
    spec = registry.resolve(ref)
    if conn is None:
        return await run(spec, ctx, registry=registry)
    try:
        return await _execute(spec, ctx, external_conn=conn)
    except ConfirmRequired:
        return _headless_confirm_result(spec, ctx)


async def apply(op: object, *, conn: "asyncpg.Connection",
                registry: WorkflowRegistry = REGISTRY) -> WorkflowResult:
    """The op_kind → spec external-conn sibling of run_ref (NOT the draft's
    live entry — the draft calls run() per-op, PIN-2)."""
    spec = registry.resolve_op_kind(str(getattr(op, "op_kind")))
    ctx = getattr(op, "ctx", None)
    if ctx is None:
        raise ValueError("apply(op) requires op.ctx (a WorkflowContext)")
    try:
        return await _execute(spec, ctx, external_conn=conn)
    except ConfirmRequired:
        return _headless_confirm_result(spec, ctx)


async def preview(target: "WorkflowRef | CompoundOpSpec", ctx: WorkflowContext, *,
                  registry: WorkflowRegistry = REGISTRY) -> MutationPreview:
    """The dry-run oracle (spec 07 §3.5): txn-rollback + skip-EFFECT; after
    preview, DB state is byte-identical and zero effect calls fired."""
    spec = _resolve_target(target, registry)
    result = await run(spec, replace(ctx, dry_run=True), registry=registry)
    diff: list[FieldChange] = []
    if isinstance(result.before, dict) or isinstance(result.after, dict):
        keys = set((result.before or {}).keys()) | set((result.after or {}).keys())
        for k in sorted(keys):
            diff.append(FieldChange(k, (result.before or {}).get(k),
                                    (result.after or {}).get(k)))
    return MutationPreview(
        allowed=result.outcome != BLOCKED,
        operation=spec.op_key,
        summary=result.user_message or f"{spec.audit_verb} ({len(result.steps)} steps)",
        reversibility=spec.reversibility,
        planned_steps=tuple(
            PlannedStep(getattr(s, "target_id", 0), getattr(s, "target_name", ""), "")
            for s in result.steps
        ),
        diff=tuple(diff),
        warnings=result.warnings,
        requires_confirmation=spec.confirmation is not None,
    )
