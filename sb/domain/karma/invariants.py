"""INV-K's data-content half (band 4, S12 grammar): the aggregate⊄ledger
reconciliation — ``karma.karma_points == baseline + Σ karma_audit_log.
delta`` per recipient, and ``received_count`` == the row count, within
tolerance 0.

QUARANTINE_ONLY (the D-0031 economy posture): reputation is value-bearing
state whose repair DIRECTION is never guessed; drift isolates + files a
finding. ``baseline_ref`` returns zeros until the CUT-2 import
re-baselines (every pre-rebuild total arrives WITH its imported ledger).
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
from sb.spec.refs import ProviderRef, is_registered, provider

__all__ = ["declare_karma_invariants", "ensure_invariant_refs",
           "karma_reconciliation_spec"]

_CHECK = "karma.check_points_ledger"
_BASELINE = "karma.baseline_points_ledger"


def _fingerprint(invariant_id: str, store: str, row_id: str,
                 value: object) -> str:
    raw = f"{invariant_id}|{store}|{row_id}|{value}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _ensure_providers() -> None:
    if is_registered(ProviderRef(_CHECK)):
        return

    @provider(_CHECK)
    async def check_points_ledger(spec, *, guild_id: int, conn=None):
        from sb.kernel.db.pool import fetchall

        baseline = await _baseline(spec, guild_id=guild_id, conn=conn)
        rows = await fetchall(
            "SELECT k.user_id, k.karma_points, k.received_count, "
            "COALESCE(SUM(a.delta), 0)::bigint AS ledger_sum, "
            "COUNT(a.id)::bigint AS ledger_rows "
            "FROM karma k "
            "LEFT JOIN karma_audit_log a "
            "ON a.to_user = k.user_id AND a.guild_id = k.guild_id "
            "WHERE k.guild_id = $1 "
            "GROUP BY k.user_id, k.karma_points, k.received_count",
            (guild_id,), conn=conn)
        violations = []
        for row in rows:
            row_id = f"{row['user_id']}:{guild_id}"
            expected = int(baseline.get(row_id, 0)) + int(row["ledger_sum"])
            drift = int(row["karma_points"]) - expected
            if abs(drift) > spec.tolerance:
                violations.append(Violation(
                    stores=("karma", "karma_audit_log"),
                    primary_store="karma",
                    row_id=row_id, guild_id=guild_id,
                    fingerprint=_fingerprint(spec.invariant_id, "karma",
                                             row_id, row["karma_points"]),
                    detail=(f"aggregate {row['karma_points']} != "
                            f"baseline+ledger {expected} (drift {drift:+d})")))
        return tuple(violations)

    @provider(_BASELINE)
    async def baseline_points_ledger(spec, *, guild_id: int, conn=None):
        """Zeros until the CUT-2 import draws real genesis offsets."""
        return {}

    _baseline_holder["fn"] = baseline_points_ledger


_baseline_holder: dict = {}


async def _baseline(spec, *, guild_id: int, conn=None) -> dict:
    fn = _baseline_holder.get("fn")
    return await fn(spec, guild_id=guild_id, conn=conn) if fn else {}


def karma_reconciliation_spec() -> InvariantSpec:
    _ensure_providers()
    return InvariantSpec(
        invariant_id="karma.points_ledger_reconciliation",
        kind=InvariantKind.RECONCILIATION,
        owner_subsystem="karma",
        stores=("karma", "karma_audit_log"),
        check_ref=ProviderRef(_CHECK),
        severity=Severity.QUARANTINE_ONLY,
        bears_value=True,
        baseline_ref=ProviderRef(_BASELINE),
        tolerance=0,
        cadence=SweepCadence.DAILY,
    )


def declare_karma_invariants() -> InvariantSpec:
    spec = karma_reconciliation_spec()
    try:
        declare_invariant(spec)
    except ValueError as exc:
        if "declared twice" not in str(exc):
            raise
    return spec


def ensure_invariant_refs() -> None:
    _ensure_providers()
    declare_karma_invariants()
