"""The fail-closed op-kind registry (K9/S10 — frozen L0 spec 06 §3.3).

The ONE key: ``op_kind → (WorkflowRef, payload_schema, is_resource_create)``.
A kind with no binding is UN-DRAFTABLE (an un-previewable draft is an
un-confirmable draft — structural, not operator vigilance). The binding's
``workflow_ref`` is typed ``WorkflowRef`` — the ③.4 audit fence by
construction (a draftable mutating op cannot map to a bare HandlerRef).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.events import FieldSpec
from sb.spec.refs import WorkflowRef

__all__ = ["OpKindBinding", "OpKindRegistry", "OP_KINDS"]


@dataclass(frozen=True)
class OpKindBinding:
    op_kind: str
    workflow_ref: WorkflowRef             # [S] → the STATIC CompoundOpSpec K7 runs/previews
    payload_schema: tuple[FieldSpec, ...] # [S] fields DraftOperation.payload MUST carry
    is_resource_create: bool = False      # [S] DECLARED — preview warning + T2-1 note ONLY


class OpKindRegistry:
    def __init__(self) -> None:
        self._bindings: dict[str, OpKindBinding] = {}

    def register(self, binding: OpKindBinding) -> OpKindBinding:
        prior = self._bindings.get(binding.op_kind)
        if prior is not None and prior != binding:
            raise ValueError(f"op_kind {binding.op_kind!r} bound twice with differing bindings")
        self._bindings[binding.op_kind] = binding
        return binding

    def get(self, op_kind: str) -> OpKindBinding | None:
        """None ⇒ FAIL-CLOSED (un-draftable)."""
        return self._bindings.get(op_kind)

    def is_draftable(self, op_kind: str) -> bool:
        return op_kind in self._bindings

    def clear_for_tests(self) -> None:
        self._bindings.clear()


# the module-level default registry the pipeline and composition root share.
OP_KINDS = OpKindRegistry()
