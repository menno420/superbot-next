"""The Result grammar — WorkflowResult / MutationPreview (design-spec §2.7,
ADOPTED — spec 07 lands them, authors nothing new about their shape).

`StepResult` + `classify_outcome` port the shipped
`services/lifecycle/contracts.py:56/:108` verbatim; the outcome/reversibility
constants come from `sb.spec.outcomes` (the frozen five, shipped lowercase
values) and the three reversibility constants live here (shipped :40-42).
`WorkflowResult` is the strict superset of the shipped `LifecycleResult:77`
— every shipped field name/type/default unchanged, plus `lane`, `before`,
`after`, `cache_invalidated`, `warnings`, `user_message`, and the typed
`source` tag.

Outbox-seam carriers (spec 08 §3.5 duck-typed protocol, finalized here):
`op_key` (property = `operation`) and `dedup_key` (engine-populated runtime
field, a DURABLE_ONCE op's `once()` IdempotencyKey — NOT [S], never authored)
are what `outbox.enqueue_all` reads to derive AT_LEAST_ONCE dedup tokens.

`ConfirmationSpec` is re-exported from its `sb.spec.confirmation` leaf.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import TYPE_CHECKING

from sb.spec.confirmation import Challenge, ConfirmationSpec  # noqa: F401 — re-export (spec 07 §2)
from sb.spec.outcomes import DISCORD_FAILED, PARTIAL, SUCCESS

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.db.idempotency import IdempotencyKey
    from sb.kernel.workflow.spec import WorkflowLane

__all__ = [
    "COMPENSATABLE",
    "IRREVERSIBLE",
    "REVERSIBLE",
    "REVERSIBILITY_ORDER",
    "Challenge",
    "ConfirmationSpec",
    "FieldChange",
    "MutationPreview",
    "PlannedStep",
    "StepResult",
    "WorkflowResult",
    "classify_outcome",
]

# Reversibility — shipped constants verbatim (contracts.py:40-42) + the total
# order the derived op rollup uses (spec 07 §3.1).
REVERSIBLE = "reversible"
COMPENSATABLE = "compensatable"
IRREVERSIBLE = "irreversible"
REVERSIBILITY_ORDER: tuple[str, ...] = (REVERSIBLE, COMPENSATABLE, IRREVERSIBLE)


@dataclass(frozen=True)
class StepResult:
    """Outcome of one target within a (possibly batched) operation —
    shipped contracts.py:56, verbatim."""

    target_id: int
    target_name: str
    ok: bool
    error: str | None = None


def classify_outcome(steps: tuple[StepResult, ...]) -> str:
    """Shipped contracts.py:108 verbatim: SUCCESS / PARTIAL / DISCORD_FAILED
    over per-step results."""
    if not steps:
        return DISCORD_FAILED
    ok = sum(1 for s in steps if s.ok)
    if ok == len(steps):
        return SUCCESS
    if ok == 0:
        return DISCORD_FAILED
    return PARTIAL


@dataclass(frozen=True)
class WorkflowResult:
    """Design-spec §2.7's kernel type. The ten shipped `LifecycleResult`
    fields keep name/type/default; the golden harness reads new-as-old."""

    # --- the shipped LifecycleResult ten (contracts.py:77-90, verbatim) ---
    mutation_id: str
    guild_id: int
    domain: str
    operation: str                    # = op_key (spec 07 §3.3 step 7)
    outcome: str                      # the frozen §2.7 five ONLY
    reversibility: str
    steps: tuple[StepResult, ...] = field(default_factory=tuple)
    committed_at: datetime | None = None
    audit_emitted: bool = False       # publish-accepted-only honesty
    event_emitted: bool = False
    # --- the §2.7 additions ---
    lane: "WorkflowLane | None" = None
    before: object | None = None
    after: object | None = None
    cache_invalidated: bool = False
    warnings: tuple[str, ...] = ()
    user_message: str | None = None   # [S] copy
    source: object | None = None      # the ORIGINAL legacy object (adapters) — typed, never a stringly dict
    # --- outbox-seam runtime carrier (spec 08 §3.5; engine-populated) ---
    dedup_key: "IdempotencyKey | None" = None

    @property
    def op_key(self) -> str:
        """The outbox namespace carrier (spec 08 §3.5 reads result.op_key)."""
        return self.operation

    @property
    def applied(self) -> tuple[StepResult, ...]:
        return tuple(s for s in self.steps if s.ok)

    @property
    def failed(self) -> tuple[StepResult, ...]:
        return tuple(s for s in self.steps if not s.ok)

    @property
    def first_error(self) -> str:
        """First human-readable failure reason (shipped helper, verbatim)."""
        for step in self.failed:
            if step.error:
                return step.error
        return "operation could not be completed"


@dataclass(frozen=True)
class PlannedStep:
    """One step a preview would run (MutationPreview.planned_steps)."""

    target_id: int
    target_name: str
    summary: str = ""


@dataclass(frozen=True)
class FieldChange:
    """One structured before -> after entry (MutationPreview.diff)."""

    field_name: str
    before: object
    after: object


@dataclass(frozen=True)
class MutationPreview:
    """Design-spec §2.7 — the shipped LifecyclePreview/ProvisioningPreview
    generalized."""

    allowed: bool
    operation: str
    summary: str
    reversibility: str
    planned_steps: tuple[PlannedStep, ...] = ()
    diff: tuple[FieldChange, ...] = ()
    warnings: tuple[str, ...] = ()
    requires_confirmation: bool = False


# ---------------------------------------------------------------------------
# The from_* adapters (design-spec §2.7): duck-typed, name-for-name — every
# field the shipped shape shares with WorkflowResult maps unchanged; `lane`
# is set by the adapter; the ORIGINAL object rides `source`. Test-pinned;
# the port bands feed them the real legacy shapes (which do not exist in
# this repo — superbot stays the read-only oracle until then).
# ---------------------------------------------------------------------------

def _from_legacy(obj: object, *, lane: "WorkflowLane") -> WorkflowResult:
    def g(name: str, default: object = None) -> object:
        return getattr(obj, name, default)

    return WorkflowResult(
        mutation_id=str(g("mutation_id", "")),
        guild_id=int(g("guild_id", 0) or 0),
        domain=str(g("domain", "")),
        operation=str(g("operation", "")),
        outcome=str(g("outcome", "")),
        reversibility=str(g("reversibility", "")),
        steps=tuple(g("steps", ()) or ()),
        committed_at=g("committed_at"),
        audit_emitted=bool(g("audit_emitted", False)),
        event_emitted=bool(g("event_emitted", False)),
        lane=lane,
        before=g("before"),
        after=g("after"),
        warnings=tuple(g("warnings", ()) or ()),
        user_message=g("user_message"),
        source=obj,
    )


def _adapter(lane_token: str):
    def build(cls, obj: object) -> WorkflowResult:
        from sb.kernel.workflow.spec import WorkflowLane
        return _from_legacy(obj, lane=WorkflowLane(lane_token))
    return classmethod(build)


WorkflowResult.from_settings = _adapter("scalar")          # type: ignore[attr-defined]
WorkflowResult.from_lifecycle = _adapter("lifecycle")      # type: ignore[attr-defined]
WorkflowResult.from_provisioning = _adapter("resource")    # type: ignore[attr-defined]
WorkflowResult.from_governance = _adapter("governance")    # type: ignore[attr-defined]
WorkflowResult.from_treasury = _adapter("domain")          # type: ignore[attr-defined]


def finalize(result: WorkflowResult, **changes: object) -> WorkflowResult:
    """dataclasses.replace re-export (step-7 finalization helper)."""
    return replace(result, **changes)
