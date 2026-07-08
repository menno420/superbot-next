"""The treasury pool reconciliation (band 3, S12 grammar): every pool
movement leaves a `treasury:*` row on the economy ledger (contribute debits
the donor, disburse credits the grantee), so the pool balance MUST equal
`baseline + Σ(-delta over treasury:* ledger rows)` per guild. QUARANTINE_ONLY
(Q-D13 — the money direction is an owner call); baseline zeros until the
CUT-2 import re-baselines."""

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

__all__ = ["declare_treasury_invariants", "ensure_invariant_refs"]

_CHECK = "treasury.check_pool_ledger"
_BASELINE = "treasury.baseline_pool_ledger"

_baseline_holder: dict = {}


def _fingerprint(invariant_id: str, store: str, row_id: str,
                 value: object) -> str:
    raw = f"{invariant_id}|{store}|{row_id}|{value}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _ensure_providers() -> None:
    if is_registered(ProviderRef(_CHECK)):
        return

    @provider(_CHECK)
    async def check_pool_ledger(spec, *, guild_id: int, conn=None):
        from sb.kernel.db.pool import fetchone

        baseline_fn = _baseline_holder.get("fn")
        baseline = (await baseline_fn(spec, guild_id=guild_id, conn=conn)
                    if baseline_fn else {})
        row = await fetchone(
            "SELECT COALESCE((SELECT balance FROM guild_treasury "
            "WHERE guild_id=$1), 0) AS balance, "
            "COALESCE((SELECT SUM(-delta) FROM economy_audit_log "
            "WHERE guild_id=$1 AND reason LIKE 'treasury:%'), 0)::bigint "
            "AS ledger_sum", (guild_id,), conn=conn)
        if row is None:
            return ()
        row_id = str(guild_id)
        expected = int(baseline.get(row_id, 0)) + int(row["ledger_sum"])
        drift = int(row["balance"]) - expected
        if abs(drift) > spec.tolerance:
            return (Violation(
                stores=("guild_treasury", "economy_audit_log"),
                primary_store="guild_treasury",
                row_id=row_id, guild_id=guild_id,
                fingerprint=_fingerprint(spec.invariant_id, "guild_treasury",
                                         row_id, row["balance"]),
                detail=(f"pool {row['balance']} != baseline+ledger "
                        f"{expected} (drift {drift:+d})")),)
        return ()

    @provider(_BASELINE)
    async def baseline_pool_ledger(spec, *, guild_id: int, conn=None):
        return {}

    _baseline_holder["fn"] = baseline_pool_ledger


def treasury_reconciliation_spec() -> InvariantSpec:
    _ensure_providers()
    return InvariantSpec(
        invariant_id="treasury.pool_ledger_reconciliation",
        kind=InvariantKind.RECONCILIATION,
        owner_subsystem="treasury",
        stores=("guild_treasury", "economy_audit_log"),
        check_ref=ProviderRef(_CHECK),
        severity=Severity.QUARANTINE_ONLY,
        bears_value=True,
        baseline_ref=ProviderRef(_BASELINE),
        tolerance=0,
        cadence=SweepCadence.DAILY,
    )


def declare_treasury_invariants() -> InvariantSpec:
    spec = treasury_reconciliation_spec()
    try:
        declare_invariant(spec)
    except ValueError as exc:
        if "declared twice" not in str(exc):
            raise
    return spec


def ensure_invariant_refs() -> None:
    _ensure_providers()
    declare_treasury_invariants()
