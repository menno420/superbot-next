"""K7 — the workflow / compound-op engine (frozen L0 spec 07).

The single audited seam every multi-write mutation runs through: declared
`CompoundOpSpec`s (ordered `LegSpec`s + ONE authority_ref + a mandated
`IdempotencyPosture` + one central audit verb), executed by three co-designed
entries over one `_execute` core (`run` self-txn / `run_ref(conn=)` +
`apply(op, conn)` external-conn / `preview` dry-run oracle). Settings
RESOLUTION (read side, design-spec §4.1-4.3) also homes in this band
(`sb.kernel.settings`) per F-3.4.
"""

from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.engine import ConfirmRequired, apply, preview, run, run_ref
from sb.kernel.workflow.registry import REGISTRY, WorkflowRegistry
from sb.kernel.workflow.result import (
    ConfirmationSpec,
    MutationPreview,
    StepResult,
    WorkflowResult,
    classify_outcome,
)
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    DedupKeySpec,
    EmptyResultSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegAuditSpec,
    LegKind,
    LegSpec,
    WorkflowLane,
)

__all__ = [
    "REGISTRY",
    "CompoundOpSpec",
    "ConfirmRequired",
    "ConfirmationSpec",
    "DedupKeySpec",
    "EmptyResultSpec",
    "EventEmitSpec",
    "IdempotencyPosture",
    "LegAuditSpec",
    "LegKind",
    "LegOutcome",
    "LegSpec",
    "MutationPreview",
    "StepResult",
    "WorkflowContext",
    "WorkflowLane",
    "WorkflowRegistry",
    "WorkflowResult",
    "apply",
    "classify_outcome",
    "preview",
    "run",
    "run_ref",
]
