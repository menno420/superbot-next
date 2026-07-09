"""INV-G's data-content half (band 4, S12 grammar): the level column is
DERIVED state — every row must satisfy ``level == level_progress(xp)[0]``.

ROW_PREDICATE + REPAIRABLE: the xp column is the in-row ground truth and
the re-derivation is deterministic (the one shipped drift source is the
monotonic-advance race window), so the audited K7 repair
(``xp.repair_level_consistency``) is safe. Report-only default like every
S12 lane; enforce = the ``invariants.enforce.<id>`` runtime toggle.
"""

from __future__ import annotations

import hashlib

from sb.spec.invariants import (
    InvariantKind,
    InvariantSpec,
    Severity,
    SweepCadence,
    Violation,
    declare_invariant,
)
from sb.spec.refs import ProviderRef, WorkflowRef, is_registered, provider

__all__ = ["declare_xp_invariants", "ensure_invariant_refs",
           "xp_level_consistency_spec"]

_CHECK = "xp.check_level_consistency"


def _fingerprint(invariant_id: str, store: str, row_id: str,
                 value: object) -> str:
    raw = f"{invariant_id}|{store}|{row_id}|{value}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _ensure_providers() -> None:
    if is_registered(ProviderRef(_CHECK)):
        return

    @provider(_CHECK)
    async def check_level_consistency(spec, *, guild_id: int, conn=None):
        from sb.domain.xp.levels import level_progress
        from sb.kernel.db.pool import fetchall

        rows = await fetchall(
            "SELECT user_id, xp, level FROM xp WHERE guild_id=$1",
            (guild_id,), conn=conn)
        violations = []
        for row in rows:
            derived, _, _ = level_progress(int(row["xp"]))
            if int(row["level"]) != derived:
                row_id = f"{row['user_id']}:{guild_id}"
                violations.append(Violation(
                    stores=("xp",),
                    primary_store="xp",
                    row_id=row_id, guild_id=guild_id,
                    fingerprint=_fingerprint(spec.invariant_id, "xp",
                                             row_id, row["level"]),
                    detail=(f"level {row['level']} != derived {derived} "
                            f"for xp={row['xp']}")))
        return tuple(violations)


def xp_level_consistency_spec() -> InvariantSpec:
    _ensure_providers()
    return InvariantSpec(
        invariant_id="xp.level_consistency",
        kind=InvariantKind.ROW_PREDICATE,
        owner_subsystem="xp",
        stores=("xp",),
        check_ref=ProviderRef(_CHECK),
        severity=Severity.REPAIRABLE,
        repair_ref=WorkflowRef("xp.repair_level_consistency"),
        bears_value=True,
        cadence=SweepCadence.DAILY,
    )


def declare_xp_invariants() -> InvariantSpec:
    spec = xp_level_consistency_spec()
    try:
        declare_invariant(spec)
    except ValueError as exc:
        if "declared twice" not in str(exc):
            raise
    return spec


def ensure_invariant_refs() -> None:
    _ensure_providers()
    declare_xp_invariants()
