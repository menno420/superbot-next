"""The ``version_policy_declared`` fence (K9/S10 — frozen L0 spec 09 §3.4).

Run at StoreSpec declaration / manifest compile. Returns a list of
violations (empty = clean) — same posture as the K7 fences.
"""

from __future__ import annotations

from sb.spec.versioning import CheckpointClass, StoreSpec, VersionPolicy

__all__ = ["check_version_policy"]

VALUE_CANNOT_DROP = "value_bearing_store_cannot_drop"
UPCAST_NEEDS_REF = "upcast_needs_upcast_ref"
VALUE_REJECT_NEEDS_COMPENSATION = "value_reject_needs_compensation"
RETIRE_NEEDS_RETIRE_REF = "retire_path_needs_retire_ref"
RECOVERY_NEEDS_READER = "recovery_needs_reader"


def check_version_policy(spec: StoreSpec) -> list[str]:
    problems: list[str] = []
    if spec.bears_value and spec.version_policy is VersionPolicy.DROP:
        problems.append(
            f"{VALUE_CANNOT_DROP}: {spec.table} bears value and declares DROP "
            f"(the RPS-forfeit shape — unbuildable)")
    if spec.version_policy is VersionPolicy.UPCAST and spec.upcast_ref is None:
        problems.append(f"{UPCAST_NEEDS_REF}: {spec.table}")
    if (spec.version_policy is VersionPolicy.REJECT_AND_PRESERVE
            and spec.bears_value and spec.compensation_ref is None):
        problems.append(f"{VALUE_REJECT_NEEDS_COMPENSATION}: {spec.table}")
    needs_retire = (
        spec.version_policy is VersionPolicy.DROP
        or (spec.version_policy is VersionPolicy.REJECT_AND_PRESERVE
            and not spec.bears_value))
    if needs_retire and spec.retire_ref is None:
        problems.append(f"{RETIRE_NEEDS_RETIRE_REF}: {spec.table}")
    swept = spec.bears_value or spec.checkpoint_class is CheckpointClass.SESSION
    if swept and spec.active_rows_ref is None:
        problems.append(f"{RECOVERY_NEEDS_READER}: {spec.table}")
    return problems
