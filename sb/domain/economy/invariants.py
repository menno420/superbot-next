"""INV-F's data-content half (band 3, S12 grammar): the aggregate⊄ledger
reconciliation — `economy_balances.coins == baseline + Σ economy_audit_log.
delta` per (user, guild), within tolerance 0.

Severity QUARANTINE_ONLY: the repair DIRECTION for money is an OWNER call
(Q3/Q-D13 — never guessed); drift isolates + files a finding, never
auto-mutates. `baseline_ref` returns the per-key genesis offset — zeros
until the CUT-2 import re-baselines (spec 11 §2.1: the baseline is drawn at
the reconciliation epoch).
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

__all__ = ["economy_reconciliation_spec", "ensure_invariant_refs"]

_CHECK = "economy.check_balance_ledger"
_BASELINE = "economy.baseline_balance_ledger"


def _fingerprint(invariant_id: str, store: str, row_id: str,
                 value: object) -> str:
    raw = f"{invariant_id}|{store}|{row_id}|{value}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _ensure_providers() -> None:
    if is_registered(ProviderRef(_CHECK)):
        return

    @provider(_CHECK)
    async def check_balance_ledger(spec, *, guild_id: int, conn=None):
        from sb.kernel.db.pool import fetchall

        baseline = await _baseline(spec, guild_id=guild_id, conn=conn)
        rows = await fetchall(
            "SELECT b.user_id, b.coins, "
            "COALESCE(SUM(a.delta), 0)::bigint AS ledger_sum "
            "FROM economy_balances b "
            "LEFT JOIN economy_audit_log a "
            "ON a.user_id = b.user_id AND a.guild_id = b.guild_id "
            "WHERE b.guild_id = $1 "
            "GROUP BY b.user_id, b.coins", (guild_id,), conn=conn)
        violations = []
        for row in rows:
            row_id = f"{row['user_id']}:{guild_id}"
            expected = int(baseline.get(row_id, 0)) + int(row["ledger_sum"])
            drift = int(row["coins"]) - expected
            if abs(drift) > spec.tolerance:
                violations.append(Violation(
                    stores=("economy_balances", "economy_audit_log"),
                    primary_store="economy_balances",
                    row_id=row_id, guild_id=guild_id,
                    fingerprint=_fingerprint(spec.invariant_id,
                                             "economy_balances", row_id,
                                             row["coins"]),
                    detail=(f"aggregate {row['coins']} != baseline+ledger "
                            f"{expected} (drift {drift:+d})")))
        return tuple(violations)

    @provider(_BASELINE)
    async def baseline_balance_ledger(spec, *, guild_id: int, conn=None):
        """Zeros until the CUT-2 import draws real genesis offsets — every
        pre-rebuild balance arrives WITH its imported ledger, so the fresh
        epoch starts consistent."""
        return {}

    _baseline_holder["fn"] = baseline_balance_ledger


_baseline_holder: dict = {}


async def _baseline(spec, *, guild_id: int, conn=None) -> dict:
    fn = _baseline_holder.get("fn")
    return await fn(spec, guild_id=guild_id, conn=conn) if fn else {}


def economy_reconciliation_spec() -> InvariantSpec:
    _ensure_providers()
    return InvariantSpec(
        invariant_id="economy.balance_ledger_reconciliation",
        kind=InvariantKind.RECONCILIATION,
        owner_subsystem="economy",
        stores=("economy_balances", "economy_audit_log"),
        check_ref=ProviderRef(_CHECK),
        severity=Severity.QUARANTINE_ONLY,
        bears_value=True,
        baseline_ref=ProviderRef(_BASELINE),
        tolerance=0,
        cadence=SweepCadence.DAILY,
    )


_DECLARED: dict = {}


def declare_economy_invariants() -> InvariantSpec:
    spec = economy_reconciliation_spec()
    try:
        declare_invariant(spec)
    except ValueError as exc:
        if "declared twice" not in str(exc):
            raise
    _DECLARED["economy"] = spec
    return spec


def ensure_invariant_refs() -> None:
    _ensure_providers()
    declare_economy_invariants()
