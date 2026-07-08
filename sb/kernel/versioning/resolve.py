"""``resolve_versioned_load`` — the load-time upcast/compensate/drop/
quarantine primitive (K9/S10 — frozen L0 spec 09 §3.3), plus
``run_recovery``, the GENERATED sweep replacing every hand-written
``recover_*`` drop-vs-refund branch.

The refund-before-delete class fix: for a value-bearing
``REJECT_AND_PRESERVE`` store, the compensation is a K7 ``CompoundOpSpec``
whose ORDERED DB legs refund THEN retire — leg order inside ONE txn on OUR
conn (``run_ref(conn=…)``, ``atomic_db_only``-fenced), guarded by ``once()``
so a crash between refund and retire never double-refunds. If the
compensation FAILS the row is NOT retired (the txn rolls back — the
deliberate improvement over the #1693 stopgap). A broken UPCAST rung
QUARANTINES (row left in place, operator finding) — never falls through
into REJECT.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.db.pool import transaction
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.versioning.compile import check_version_policy
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.spec.refs import resolve as resolve_ref
from sb.spec.versioning import StoreSpec, VersionPolicy, VersionedRow

logger = logging.getLogger("sb.kernel.versioning.resolve")

__all__ = ["LoadDisposition", "resolve_versioned_load", "run_recovery"]


@dataclass(frozen=True)
class LoadDisposition:
    action: str   # resume | compensated_and_retired | rejected_and_retired | dropped | quarantined
    payload: Mapping[str, Any] | None = None
    compensation_result: object | None = None    # the refund's audited WorkflowResult
    finding: str | None = None                    # set on quarantined


def _reject_key(spec: StoreSpec, row: VersionedRow) -> IdempotencyKey:
    return IdempotencyKey(namespace=f"{spec.table}.version_reject",
                          guild_id=row.guild_id or 0,
                          dedup_token=f"{row.row_id}:{row.version}")


async def _run_retire(spec: StoreSpec, row: VersionedRow, ctx: WorkflowContext,
                      action: str) -> LoadDisposition:
    key = _reject_key(spec, row)
    async with transaction() as conn:
        if await once(key, conn=conn):
            result = await workflow_engine.run_ref(spec.retire_ref, ctx, conn=conn)
            await record_outcome(key, result.outcome,
                                 result_ref=result.mutation_id, conn=conn)
        else:
            await read_outcome(key, conn=conn)
    return LoadDisposition(action=action)


async def resolve_versioned_load(spec: StoreSpec, row: VersionedRow, *,
                                 ctx: WorkflowContext) -> LoadDisposition:
    """The fixed §3.3 algorithm (rows 0-4)."""
    # 0. current version — the common path.
    if row.version == spec.payload_version:
        return LoadDisposition(action="resume", payload=row.payload)

    # 1. UPCAST: run the rung chain from row.version → payload_version.
    if spec.version_policy is VersionPolicy.UPCAST:
        upcaster: Callable = resolve_ref(spec.upcast_ref)
        payload: Mapping[str, Any] | None = row.payload
        v = row.version
        while v < spec.payload_version and payload is not None:
            payload = upcaster(v, payload)    # a missing rung returns None
            v += 1
        if payload is None:
            finding = (f"upcast_chain_broken:{spec.table}:"
                       f"{row.version}->{spec.payload_version}")
            record_operator_finding(source="versioning", severity="error",
                                    summary=f"quarantined row in {spec.table}",
                                    detail=finding)
            return LoadDisposition(action="quarantined", finding=finding)
        return LoadDisposition(action="resume", payload=payload)

    # 2. DROP (fence-legal only when not bears_value): audited retire.
    if spec.version_policy is VersionPolicy.DROP:
        return await _run_retire(spec, row, ctx, "dropped")

    # 3/4. REJECT_AND_PRESERVE.
    if spec.bears_value:
        # the refund-before-delete class fix: refund THEN retire are ORDERED
        # legs of ONE compensation CompoundOpSpec, inside ONE txn, once()-guarded.
        key = _reject_key(spec, row)
        compensation_result = None
        async with transaction() as conn:
            if await once(key, conn=conn):
                compensation_result = await workflow_engine.run_ref(
                    spec.compensation_ref, ctx, conn=conn)
                await record_outcome(key, compensation_result.outcome,
                                     result_ref=compensation_result.mutation_id,
                                     conn=conn)
            else:
                await read_outcome(key, conn=conn)   # replay — no double refund
        return LoadDisposition(action="compensated_and_retired",
                               compensation_result=compensation_result)
    # non-value REJECT: nothing to compensate — audited retire only.
    return await _run_retire(spec, row, ctx, "rejected_and_retired")


async def run_recovery(spec: StoreSpec, *, ctx_factory: Callable[[VersionedRow], WorkflowContext],
                       ) -> tuple[LoadDisposition, ...]:
    """The GENERATED boot/cog-load sweep — the domain declares a StoreSpec
    (reader + refs) and calls this; it writes no drop-vs-refund branch."""
    problems = check_version_policy(spec)
    if problems:
        raise ValueError(f"StoreSpec {spec.table} fails version_policy_declared: {problems}")
    reader = resolve_ref(spec.active_rows_ref)
    async with transaction() as conn:
        rows = await reader(spec, conn=conn)
    dispositions = []
    for row in rows:
        disp = await resolve_versioned_load(spec, row, ctx=ctx_factory(row))
        dispositions.append(disp)
    return tuple(dispositions)
