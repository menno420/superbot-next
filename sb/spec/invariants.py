"""The declared-invariant grammar (S12 — frozen L0 spec 11 §2.1): the
load-time-blind, CONTENT-level complement to spec 09's version-drift policy.

A manifest-level facet (``SubsystemManifest.data_invariants``, sibling to
``stores``) — NOT a StoreSpec field, because a reconciliation invariant
spans TWO stores. No logic in the manifest: the check is a REGISTERED
``ProviderRef`` (pure read), the repair a REGISTERED ``WorkflowRef``
(audited K7, ``atomic_db_only``-fenced).

``invariant_id`` is namespace kind ``data_invariant`` — a DISTINCT axis from
``StoreSpec.invariant_tag`` (the INV-F/G/K sole-writer AST fence): that is a
code fence; this is a data-content rule.

RECONCILIATION is ``aggregate == baseline + Σ ledger.delta_since_epoch``
(within tolerance) — NEVER bare equality (the pre-ledger history would flood
quarantine on the first run); ``baseline_ref`` returns the per-key genesis
offset drawn at the reconciliation epoch (CUT-2 import, or the first
enforce=True flip).

Leaf imports: sb.spec.refs + sb.spec.scheduler (TaskScope) + sb.spec.roles.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sb.spec.refs import ProviderRef, WorkflowRef
from sb.spec.roles import register_field_roles
from sb.spec.scheduler import TaskScope

__all__ = [
    "CADENCE_SECONDS",
    "InvariantKind",
    "InvariantSpec",
    "Severity",
    "SweepCadence",
    "Violation",
    "clear_invariants_for_tests",
    "declare_invariant",
    "declared_invariants",
]


class InvariantKind(str, enum.Enum):
    ROW_PREDICATE = "row_predicate"    # each row must satisfy P(row)
    RECONCILIATION = "reconciliation"  # aggregate == baseline + Σ ledger.delta
    UNIQUENESS = "uniqueness"          # ≤1 row per natural key
    REFERENTIAL = "referential"        # every row in A has a live referent in B
    TERMINAL_ONCE = "terminal_once"    # ≤1 terminal/settle row per session


class Severity(str, enum.Enum):
    REPAIRABLE = "repairable"            # a safe audited repair exists (repair_ref REQUIRED)
    QUARANTINE_ONLY = "quarantine_only"  # isolate + finding; never auto-mutate
    ALERT_ONLY = "alert_only"            # metric + finding; no state change


class SweepCadence(str, enum.Enum):
    ON_BOOT = "on_boot"        # reconcile_on_boot only; no steady-state tick
    HOURLY = "hourly"
    SIX_HOURLY = "six_hourly"
    DAILY = "daily"            # default
    WEEKLY = "weekly"


CADENCE_SECONDS: dict[SweepCadence, int | None] = {
    SweepCadence.ON_BOOT: None,
    SweepCadence.HOURLY: 3600,
    SweepCadence.SIX_HOURLY: 21600,
    SweepCadence.DAILY: 86400,
    SweepCadence.WEEKLY: 604800,
}


@dataclass(frozen=True)
class InvariantSpec:
    invariant_id: str                  # [S] namespace kind `data_invariant`
    kind: InvariantKind                # [S]
    owner_subsystem: str               # [S] the subsystem that owns the fix
    stores: tuple[str, ...]            # [S] table(s) the check reads (declared StoreSpec.table)
    check_ref: ProviderRef             # [S] REGISTERED pure-read: (spec, *, guild_id, conn) -> tuple[Violation,...]
    severity: Severity                 # [S]
    repair_ref: WorkflowRef | None = None       # [S] REQUIRED iff REPAIRABLE; audited K7, atomic_db_only
    bears_value: bool = False          # [S] mirrors StoreSpec.bears_value
    # ---- RECONCILIATION grammar (satisfiable against real data, T-2) ----
    baseline_ref: ProviderRef | None = None     # [S] REQUIRED iff RECONCILIATION; (spec,*,guild_id,conn)->{row_id:offset}
    tolerance: int = 0                 # [S] allowed |drift| band; 0 = exact after baseline
    # ---- repair DIRECTION (the owner money call — Q3/Q-D13) ----
    ground_truth_store: str | None = None       # [S] REQUIRED iff REPAIRABLE ∧ bears_value ∧ kind ∈
                                       #     {RECONCILIATION, TERMINAL_ONCE}; never guessed
    # ---- posture (the LIVE enforce state is a runtime setting — §2.4) ----
    default_enforce: bool = False      # [S] the manifest DEFAULT (report-only)
    # ---- sweep bounds (T-6 circuit breaker) ----
    cadence: SweepCadence = SweepCadence.DAILY  # [S]
    max_actions_per_run: int = 100     # [S] actions-OR-findings cap; overflow ⇒ STOP + mass_corruption
    read_batch_size: int = 500         # [S] max rows per guild per tick
    scope: TaskScope = TaskScope.GUILD # [S] per-guild batched (GLOBAL scan = later band)


@dataclass(frozen=True)
class Violation:
    """What a check_ref returns per bad row."""

    stores: tuple[str, ...]            # the span this violation covers
    primary_store: str                 # the store whose row_id NAMES the violation
    row_id: str                        # canonical PK; composite keys ":"-joined in declared order
    guild_id: int | None
    fingerprint: str                   # stable hash of (invariant_id, store, row_id, value) — the dedup token
    detail: str                        # human reason


register_field_roles(
    "InvariantSpec",
    invariant_id="S", kind="S", owner_subsystem="S", stores="S", check_ref="S",
    severity="S", repair_ref="S", bears_value="S", baseline_ref="S",
    tolerance="S", ground_truth_store="S", default_enforce="S", cadence="S",
    max_actions_per_run="S", read_batch_size="S", scope="S",
)


# --- the declared-invariant registry (kernel + manifest facets register here) ---

_INVARIANTS: dict[str, InvariantSpec] = {}


def declare_invariant(spec: InvariantSpec) -> InvariantSpec:
    """Registration runs the S12 fence (sb.kernel.invariants.compile) —
    imported lazily so this leaf stays kernel-free."""
    from sb.kernel.invariants.compile import check_invariant

    problems = check_invariant(spec)
    if problems:
        raise ValueError(f"invariant {spec.invariant_id!r} fails the fence: {problems}")
    prior = _INVARIANTS.get(spec.invariant_id)
    if prior is not None and prior != spec:
        raise ValueError(f"invariant {spec.invariant_id!r} declared twice with differing specs")
    _INVARIANTS[spec.invariant_id] = spec
    return spec


def declared_invariants() -> tuple[InvariantSpec, ...]:
    return tuple(_INVARIANTS[k] for k in sorted(_INVARIANTS))


def clear_invariants_for_tests() -> None:
    _INVARIANTS.clear()
