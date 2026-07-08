"""Sequenced, per-op-atomic, idempotent apply over K7 (K9/S10 — frozen L0
spec 06 §3.5, PIN-2).

EVERY EFFECT-bearing draft op enters via ``run(spec, ctx)`` PER-OP — never
``run_ref``/``apply`` (their ``atomic_db_only`` fence excludes EFFECT legs;
the F-2 fork resolves by caller type). The draft is sequenced +
per-op-atomic + idempotent-resume, NOT one shared transaction: K7 owns the
per-op txn, the per-op ``once()`` (keyed on the ``_draft_dedup_token`` we
pass through ctx.params), and the ONE central audit row per op
(``correlation_id = draft_id`` groups them on the spine).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.authority.decision import AuthorityDecision
from sb.kernel.draft.preview import DraftPreview, verify_confirmation
from sb.kernel.draft.registry import OpKindRegistry
from sb.kernel.draft.store import DraftStore
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.kernel.workflow.result import WorkflowResult
from sb.spec.draft import (
    AcceptHook,
    ConfirmationResponse,
    Draft,
    DraftStatus,
)
from sb.spec.outcomes import BLOCKED, DECLINED, PARTIAL, SUCCESS

__all__ = ["DRAFT_APPLY_STUCK_TTL_S", "DraftApplyResult", "apply_draft"]

# comfortably above the worst-case honest apply (spec 06 §6) — the reaper's
# conditional CAS can only catch a genuine crash, never a live apply (the
# per-op heartbeat keeps a slow apply fresh).
DRAFT_APPLY_STUCK_TTL_S = 900


@dataclass(frozen=True)
class DraftApplyResult:
    draft_id: str
    outcome: str                             # §2.7 vocab ONLY
    op_results: tuple[WorkflowResult, ...]
    correlation_id: str
    applied: tuple[int, ...]                 # op_seqs that reached SUCCESS
    failed: tuple[int, ...]                  # the op_seq apply stopped at
    skipped: tuple[int, ...]                 # not attempted after the stop


async def apply_draft(draft: Draft, decision: AuthorityDecision,
                      preview: DraftPreview,
                      confirmation: ConfirmationResponse | None, *,
                      actor: object, store: DraftStore, registry: OpKindRegistry,
                      clock, hook: AcceptHook | None = None) -> DraftApplyResult:
    """The fixed §3.5 order — re-gate, APPLYING, per-op run(), rollup, CAS."""
    # 1. re-check accept + confirmation (fail-closed, NO writes on denial).
    if not decision.allowed:
        return DraftApplyResult(draft_id=draft.draft_id, outcome=DECLINED,
                                op_results=(), correlation_id=draft.correlation_id,
                                applied=(), failed=(), skipped=())
    if preview.requires_confirmation and not verify_confirmation(
            preview.confirmation, confirmation):
        return DraftApplyResult(draft_id=draft.draft_id, outcome=DECLINED,
                                op_results=(), correlation_id=draft.correlation_id,
                                applied=(), failed=(), skipped=())
    confirmed = True   # verified above (or trivially true for non-confirming)

    # 2. crash-visible APPLYING (the stuck-APPLYING sweep is the janitor's).
    await store.set_status(draft.draft_id, DraftStatus.APPLYING)

    op_results: list[WorkflowResult] = []
    applied: list[int] = []
    failed: list[int] = []
    skipped: list[int] = []
    stop = False
    test_mode = bool(draft.verification.test_mode) if draft.verification else False

    # 3. sequence in op_seq order — ONE K7 run() per op.
    for op in draft.operations:
        if stop:
            skipped.append(op.op_seq)
            continue
        # per-op heartbeat: bump updated_at so the stuck-TTL measures time
        # since the last op progressed (a slow apply is never reaped).
        await store.set_status(draft.draft_id, DraftStatus.APPLYING,
                               expect=DraftStatus.APPLYING)
        binding = registry.get(op.op_kind)
        if binding is None:
            failed.append(op.op_seq)
            stop = True
            continue
        dedup_token = op.dedup_token or f"{draft.draft_id}:{op.op_seq}"
        ctx = WorkflowContext(
            actor=actor,
            guild_id=draft.owner_scope.guild_id,
            request_id=f"{draft.draft_id}:{op.op_seq}", confirmed=confirmed,
            params={**dict(op.payload), "_draft_dedup_token": dedup_token},
            correlation_id=draft.draft_id, test_mode=test_mode, clock=clock)
        result = await workflow_engine.run(binding.workflow_ref, ctx)
        op_results.append(result)
        if result.outcome == SUCCESS:
            applied.append(op.op_seq)
        else:
            failed.append(op.op_seq)
            stop = True   # SF-f: stop on the first non-SUCCESS

    # 4. rollup.
    if failed:
        outcome = PARTIAL if applied else (
            op_results[-1].outcome if op_results else BLOCKED)
    else:
        outcome = SUCCESS

    # 5. terminal status — CONDITIONAL CAS on full success (the reaper race).
    if outcome == SUCCESS:
        flipped = await store.set_status(draft.draft_id, DraftStatus.APPLIED,
                                         expect=DraftStatus.APPLYING)
        if not flipped:
            # the reaper won — honor the PARTIAL (ops are durable; a re-run
            # once()-skips), never APPLIED-over-PARTIAL.
            current = await store.load(draft.draft_id)
            if current is not None and current.status is DraftStatus.PARTIAL:
                outcome = PARTIAL
    else:
        await store.set_status(draft.draft_id, DraftStatus.PARTIAL)

    result = DraftApplyResult(
        draft_id=draft.draft_id, outcome=outcome, op_results=tuple(op_results),
        correlation_id=draft.correlation_id, applied=tuple(applied),
        failed=tuple(failed), skipped=tuple(skipped))

    # 6. the AcceptHook (fail-open — a broken hook never blocks apply).
    if hook is not None:
        try:
            await hook.on_applied(draft, result)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("AcceptHook.on_applied failed",
                                                exc_info=True)
    return result
