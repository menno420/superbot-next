"""WorkflowRegistry (frozen L0 spec 07 §2) — THE single place a
`WorkflowRef` / draft `op_kind` resolves to its `CompoundOpSpec`.

Registration runs the K7 declaration fences (spec 07 §3.6 — structural,
always-on: a mis-declared spec never enters the registry; the same fence
functions are exported for the CI pass over a fully-populated registry).
"""

from __future__ import annotations

from sb.kernel.workflow.compile import check_spec
from sb.kernel.workflow.spec import CompoundOpSpec

__all__ = ["WorkflowRegistry", "REGISTRY"]


class WorkflowRegistry:
    def __init__(self) -> None:
        self._by_op_key: dict[str, CompoundOpSpec] = {}

    def register(self, spec: CompoundOpSpec) -> CompoundOpSpec:
        """Register (fence-checked). Returns the FROZEN spec — with the
        derived `reversibility` rollup stamped (author never sets it)."""
        problems = check_spec(spec)
        if problems:
            raise ValueError(
                f"CompoundOpSpec {spec.op_key!r} fence violations: " + "; ".join(problems)
            )
        if spec.op_key in self._by_op_key:
            raise ValueError(f"duplicate CompoundOpSpec op_key {spec.op_key!r}")
        from sb.kernel.workflow.compile import derive_reversibility
        frozen = derive_reversibility(spec)
        self._by_op_key[spec.op_key] = frozen
        return frozen

    def resolve(self, ref: object) -> CompoundOpSpec:
        """WorkflowRef -> CompoundOpSpec (the resolver INVOKE_WORKFLOW +
        scheduler/invariant/version `run_ref` resolution)."""
        name = getattr(ref, "name", ref)
        try:
            return self._by_op_key[str(name)]
        except KeyError:
            raise LookupError(f"no CompoundOpSpec registered for {name!r}") from None

    def resolve_op_kind(self, op_kind: str) -> CompoundOpSpec:
        """Draft `DraftOperation.op_kind` -> spec (op_kind IS the op_key)."""
        return self.resolve(op_kind)

    def all_specs(self) -> tuple[CompoundOpSpec, ...]:
        return tuple(self._by_op_key.values())

    def clear_for_tests(self) -> None:
        self._by_op_key.clear()


# The module-level default registry the engine and composition root share.
REGISTRY = WorkflowRegistry()
