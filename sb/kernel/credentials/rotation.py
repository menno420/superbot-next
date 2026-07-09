"""The rotation EXECUTOR — a distinguished externally-effecting durable
one-shot (S13, frozen L0 spec 12 §2.B(1a-1c)).

NOT a vanilla pure-DB `_fire_one` fire: the effect is EXTERNAL (a provider
re-issue + a store-var swap that may restart the very worker performing it),
so this fire is exempt from the pure-DB scheduler-fire fence and rides only
the due-queue's durable timer + `reconcile_on_boot` + a deterministic
HORIZON-STABLE once() key — `credential.rotation : 0 : {name}:{horizon}` —
running its OWN resumable multi-txn protocol over the phase ledger:

    txn-1  once(key) guard + RESERVED ledger row (before any external call)
    txn-2  ISSUED_PENDING_VERIFY (+ non-secret fingerprint) after issue+swap
    txn-3  VERIFIED + record_outcome("success") after post-boot read-back

Re-run rule (boot-reconcile re-fire after the swap-triggered redeploy):
once() -> False, read_outcome -> pending  =>  load the ledger `phase` and
RESUME — ISSUED_PENDING_VERIFY runs only the verify; RESERVED adopts an
orphaned issuance (or issues); VERIFIED no-ops. A duplicate arm and a
crash-retry both resolve to the same guard row: never a second credential.

The concrete provider/Railway/Discord API bindings are CUT-1 ops wiring
behind the installable `RotationProvider` port; the un-installed default
FAILs the rotation loudly (operator finding), never silently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from sb.kernel.db import credentials as ledger_db
from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.db.pool import transaction
from sb.kernel.observability.findings import record_operator_finding
from sb.spec.credentials import CredentialSpec, credential_for
from sb.spec.refs import HandlerRef, handler
from sb.spec.scheduler import ErrorPolicy, ManagedTaskSpec, OneShot, TaskDurability

__all__ = [
    "ROTATION_TASK",
    "RotationProvider",
    "RotationUnavailable",
    "install_rotation_provider",
    "reset_rotation_ports_for_tests",
    "rotation_key",
    "run_rotation",
]

ROTATION_NAMESPACE = "credential.rotation"


class RotationUnavailable(ConnectionError):
    """Raised when the rotation cannot proceed THIS fire (provider port not
    installed / read-back not yet serving). Subclasses ConnectionError so the
    scheduler's failure routing classifies it TRANSIENT and retries — the
    phase ledger makes the retry a resume, never a re-issue."""


class RotationProvider(Protocol):
    """The CUT-1 ops port. The SECRET VALUE never crosses this boundary back
    to the caller — `issue` performs the re-issue AND the store-var swap and
    returns only the new credential's NON-SECRET fingerprint.

    CL-2 RULING (PR #30, 2026-07-08; D-0033): when CUT-1 installs a real
    provider, credential REVOCATION over the closed `RevocationRef` set is
    agent-runnable during a compromise response (the narrowed Q-0213
    brake). The carve-out is scoped STRICTLY to `RevocationRef` kinds —
    never store/resource deletion, which stays ask-first. Encode the
    exception at the dispatch site that fires revocation, not here in the
    Protocol (nothing executes today; un-installed = loud FAILED+finding).
    """

    async def issue(self, cred: CredentialSpec) -> str:
        """Re-issue + swap the store var; return the non-secret fingerprint."""
        ...

    async def adopt_orphan(self, cred: CredentialSpec, horizon_epoch: int) -> str | None:
        """RESERVED-crash resume: an issuance already tagged with this
        horizon, or None (spec 12 §2.B(1c) re-run rule)."""
        ...

    async def verify(self, cred: CredentialSpec, fingerprint: str) -> bool:
        """Read-back: the credential identified by `fingerprint` serves."""
        ...


_PROVIDER: RotationProvider | None = None


def install_rotation_provider(provider: RotationProvider) -> None:
    global _PROVIDER
    _PROVIDER = provider


def reset_rotation_ports_for_tests() -> None:
    global _PROVIDER
    _PROVIDER = None


def rotation_key(name: str, horizon_epoch: int) -> IdempotencyKey:
    """HORIZON-stable, not timer-instance-stable (spec 12 §2.B(1b)) — a
    duplicate arm and a boot-reconcile re-fire resolve to the SAME guard."""
    return IdempotencyKey(namespace=ROTATION_NAMESPACE, guild_id=0,
                          dedup_token=f"{name}:{horizon_epoch}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_rotation(name: str, horizon_epoch: int, *, clock=_now) -> str:
    """Drive the phase machine to its next stable state. Returns the phase
    reached ('verified' | 'issued_pending_verify' | 'failed' | 'noop')."""
    cred = credential_for(name)
    key = rotation_key(name, horizon_epoch)

    # txn-1: the guard + RESERVED row, BEFORE any external call.
    async with transaction() as conn:
        fresh = await once(key, conn=conn)
        if not fresh:
            prior = await read_outcome(key, conn=conn)
            if prior is not None and prior.outcome is not None:
                return "noop"  # terminal outcome recorded — reproduce/no-op
        await ledger_db.reserve_rotation(name, horizon_epoch, now=clock(), conn=conn)

    async with transaction() as conn:
        row = await ledger_db.read_rotation(name, horizon_epoch, conn=conn)
    phase = row.phase if row else "reserved"

    if phase == "verified":
        return await _finish(key, "noop")
    if phase == "failed":
        return "failed"

    if _PROVIDER is None:
        # Loud, terminal-for-this-arm: the recovery arm exists, its ops
        # wiring does not (CUT-1). Never a silent pass.
        async with transaction() as conn:
            await ledger_db.set_phase(name, horizon_epoch, "failed", now=clock(),
                                      detail="rotation provider not installed "
                                             "(CUT-1 ops wiring)", conn=conn)
            await record_outcome(key, "blocked", conn=conn)
        record_operator_finding(
            source="credentials", severity="error",
            summary=f"rotation blocked: {name}",
            detail="RotationProvider port not installed (spec 12 CUT-1 wiring); "
                   f"horizon={horizon_epoch}")
        return "failed"

    fingerprint = row.fingerprint if row else None
    if phase == "reserved":
        # No confirmed issuance: adopt an orphan tagged with this horizon,
        # else issue now. issue() swaps the store var (may restart us).
        fingerprint = await _PROVIDER.adopt_orphan(cred, horizon_epoch)
        if fingerprint is None:
            fingerprint = await _PROVIDER.issue(cred)
        async with transaction() as conn:  # txn-2
            await ledger_db.set_phase(name, horizon_epoch, "issued_pending_verify",
                                      now=clock(), fingerprint=fingerprint, conn=conn)

    # ISSUED_PENDING_VERIFY (the expected restart landing): verify only.
    assert fingerprint is not None
    ok = await _PROVIDER.verify(cred, fingerprint)
    if not ok:
        # Not serving yet — transient; the durable timer retries and the
        # ledger resumes at the verify, never re-issuing.
        raise RotationUnavailable(f"read-back verify pending for {name}")
    async with transaction() as conn:  # txn-3
        await ledger_db.set_phase(name, horizon_epoch, "verified", now=clock(),
                                  conn=conn)
        await record_outcome(key, "success", result_ref=fingerprint, conn=conn)
    return "verified"


async def _finish(key: IdempotencyKey, result: str) -> str:
    async with transaction() as conn:
        prior = await read_outcome(key, conn=conn)
        if prior is None or prior.outcome is None:
            await record_outcome(key, "success", conn=conn)
    return result


@handler("kernel.credentials.rotation_fire")
async def rotation_fire(ctx) -> str:
    """The due-queue handler. Registered as a HandlerRef DELIBERATELY: this
    is the sanctioned externally-effecting fire (spec 12 §2.B(1b)) — its
    mutations are guarded by the horizon-stable once() + the phase ledger,
    NOT by the K7 seam (provider consoles are not workflows). It must never
    be given a pure-DB effect."""
    name = str(ctx.params["name"])
    horizon_epoch = int(ctx.params["horizon_epoch"])
    return await run_rotation(name, horizon_epoch)


ROTATION_TASK = ManagedTaskSpec(
    name="credentials:rotate",
    trigger=OneShot(),
    handler=HandlerRef("kernel.credentials.rotation_fire"),
    error_policy=ErrorPolicy.ESCALATE_FINDING,
    durability=TaskDurability.DURABLE,
)
