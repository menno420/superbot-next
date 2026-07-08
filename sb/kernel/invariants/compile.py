"""The ``invariant_coverage`` fence (S12 — frozen L0 spec 11 §2.3; the
honesty mechanism, mirroring ``leaderboard-has-writer``).

Two entry points:
  - ``check_invariant(spec)`` — per-spec rules, run at declaration;
  - ``check_invariant_coverage(stores, invariants)`` — the value-bearing
    coverage rule over the whole registry ("a money store you can't
    reconcile-or-refer is a store you can't trust"), keyed on
    checkpoint_class (SESSION escrow ⇒ REFERENTIAL|TERMINAL_ONCE).
"""

from __future__ import annotations

from sb.kernel.workflow.compile import check_atomic_db_only
from sb.kernel.workflow.registry import REGISTRY as WORKFLOW_REGISTRY
from sb.spec.invariants import InvariantKind, InvariantSpec, Severity
from sb.spec.refs import ProviderRef, WorkflowRef
from sb.spec.versioning import CheckpointClass, StoreSpec

__all__ = ["check_invariant", "check_invariant_coverage"]

VALUE_UNCOVERED = "value_bearing_store_uncovered"
REPAIR_NEEDS_REF = "repairable_needs_repair_ref"
REPAIR_NOT_WORKFLOW = "repair_must_be_workflow_ref"
REPAIR_NOT_ATOMIC = "repair_not_atomic_db_only"
RECONCILIATION_NEEDS_BASELINE = "reconciliation_needs_baseline"
VALUE_REPAIR_NEEDS_DIRECTION = "value_repair_needs_direction"
CHECK_NOT_PROVIDER = "check_must_be_pure_read_provider"

_AGG_LEDGER_KINDS = {InvariantKind.RECONCILIATION, InvariantKind.TERMINAL_ONCE}
_SESSION_KINDS = {InvariantKind.REFERENTIAL, InvariantKind.TERMINAL_ONCE}


def check_invariant(spec: InvariantSpec) -> list[str]:
    problems: list[str] = []
    iid = spec.invariant_id
    if not isinstance(spec.check_ref, ProviderRef):
        problems.append(f"{CHECK_NOT_PROVIDER}: {iid} (a check that can write is rejected)")
    if spec.severity is Severity.REPAIRABLE:
        if spec.repair_ref is None:
            problems.append(f"{REPAIR_NEEDS_REF}: {iid}")
        elif not isinstance(spec.repair_ref, WorkflowRef):
            problems.append(f"{REPAIR_NOT_WORKFLOW}: {iid} (a bare HandlerRef bypasses the audited seam)")
        else:
            # atomic_db_only when the workflow is already registered (an
            # unresolved ref is boot's failure surface, not this fence's).
            try:
                op = WORKFLOW_REGISTRY.resolve(spec.repair_ref)
            except LookupError:
                op = None
            if op is not None:
                atomic = check_atomic_db_only(op)
                if atomic:
                    problems.append(f"{REPAIR_NOT_ATOMIC}: {iid}: {atomic}")
    if spec.kind is InvariantKind.RECONCILIATION and spec.baseline_ref is None:
        problems.append(f"{RECONCILIATION_NEEDS_BASELINE}: {iid} "
                        f"(an un-baselined reconciliation floods quarantine)")
    # Q3/Q-D13: the money direction is NEVER guessed — absent a declared
    # ground_truth_store such an invariant may only be QUARANTINE_ONLY.
    if (spec.severity is Severity.REPAIRABLE and spec.bears_value
            and spec.kind in _AGG_LEDGER_KINDS and spec.ground_truth_store is None):
        problems.append(f"{VALUE_REPAIR_NEEDS_DIRECTION}: {iid} (declare "
                        f"ground_truth_store or ship QUARANTINE_ONLY)")
    if spec.ground_truth_store is not None and spec.ground_truth_store not in spec.stores:
        problems.append(f"{iid}: ground_truth_store {spec.ground_truth_store!r} "
                        f"is not one of the invariant's stores")
    return problems


def check_invariant_coverage(stores: tuple[StoreSpec, ...],
                             invariants: tuple[InvariantSpec, ...]) -> list[str]:
    """Every bears_value store MUST be covered by ≥1 invariant of a kind
    legal for its checkpoint_class."""
    problems: list[str] = []
    by_store: dict[str, set[InvariantKind]] = {}
    for inv in invariants:
        for table in inv.stores:
            by_store.setdefault(table, set()).add(inv.kind)
    for store in stores:
        if not store.bears_value:
            continue
        allowed = (_SESSION_KINDS if store.checkpoint_class is CheckpointClass.SESSION
                   else _AGG_LEDGER_KINDS)
        covering = by_store.get(store.table, set())
        if not covering & allowed:
            problems.append(
                f"{VALUE_UNCOVERED}: {store.table} (bears_value, "
                f"{store.checkpoint_class.value}) needs "
                f"{sorted(k.value for k in allowed)} coverage")
    return problems
