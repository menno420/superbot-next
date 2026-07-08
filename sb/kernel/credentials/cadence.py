"""The cadence DETECTOR (S13, frozen L0 spec 12 §2.B(1)/(1a)).

The routine only DETECTS due and ARMS — it never swaps inline (the earlier
inline-routine design had no boot-reconcile; a DURABLE `sb_due_queue` row is
what makes 09's `reconcile_on_boot` literally apply).

- leaf due (AUTONOMOUS)     -> arm a DURABLE OneShot on 09's due-queue
- root due (OWNER_PROMPT)   -> ONE scheduled operator prompt (irreducible)
- MANAGED / ON_COMPROMISE   -> skipped (no our-side horizon)

`horizon_epoch` is the cadence period index (days-since-epoch //
cadence_days) so every detector instance computes the SAME horizon during a
deploy overlap — the executor's horizon-stable once() then folds duplicate
arms into one rotation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from sb.kernel.observability.findings import record_operator_finding
from sb.spec.credentials import (
    CREDENTIAL_REGISTRY,
    CredentialSpec,
    RotationPosture,
)

__all__ = ["DueRotation", "arm_due_rotations", "horizon_epoch", "rotation_due"]

_DAY_S = 86_400


@dataclass(frozen=True)
class DueRotation:
    cred: CredentialSpec
    horizon_epoch: int
    is_root: bool          # OWNER_PROMPT => prompt; AUTONOMOUS => arm


def horizon_epoch(cred: CredentialSpec, now: datetime) -> int:
    """The cadence period this instant falls in — deterministic across
    instances (the once()-key stability input, spec 12 §2.B(1b))."""
    if cred.cadence_days is None:
        raise ValueError(f"{cred.name}: no cadence horizon")
    return int(now.timestamp()) // (_DAY_S * cred.cadence_days)


def rotation_due(last_rotated: Mapping[str, datetime], now: datetime,
                 registry: tuple[CredentialSpec, ...] = CREDENTIAL_REGISTRY,
                 ) -> tuple[DueRotation, ...]:
    """Join the registry's static `cadence_days` against the rotation
    ledger's `last_rotated_at` (sb.kernel.db.credentials.last_verified_at).
    A never-rotated cadence row is DUE (conservative: the horizon starts at
    the registry's birth, not an unknowable first-seen)."""
    due: list[DueRotation] = []
    for cred in registry:
        if cred.rotation not in (RotationPosture.AUTONOMOUS,
                                 RotationPosture.OWNER_PROMPT):
            continue  # MANAGED / ON_COMPROMISE: no our-side horizon
        assert cred.cadence_days is not None  # checker-enforced (rule 2)
        last = last_rotated.get(cred.name)
        overdue = (last is None
                   or (now - last).total_seconds() > cred.cadence_days * _DAY_S)
        if overdue:
            due.append(DueRotation(
                cred=cred, horizon_epoch=horizon_epoch(cred, now),
                is_root=cred.rotation is RotationPosture.OWNER_PROMPT))
    return tuple(due)


async def arm_due_rotations(lane, now: datetime | None = None, *,
                            last_rotated: Mapping[str, datetime] | None = None,
                            ) -> tuple[int, int]:
    """Detect + dispatch: arm a DURABLE one-shot per due LEAF on `lane`
    (a DueQueueLane), emit ONE operator prompt per due ROOT.
    Returns (leaves_armed, roots_prompted)."""
    from sb.kernel.credentials.rotation import ROTATION_TASK
    from sb.kernel.db import credentials as ledger_db
    from sb.kernel.db.pool import transaction

    now = now or datetime.now(timezone.utc)
    if last_rotated is None:
        async with transaction() as conn:
            last_rotated = await ledger_db.last_verified_at(conn=conn)
    armed = prompted = 0
    for item in rotation_due(last_rotated, now):
        if item.is_root:
            record_operator_finding(
                source="credentials", severity="warning",
                summary=f"root credential rotation due: {item.cred.name}",
                detail=f"cadence {item.cred.cadence_days}d elapsed — one owner "
                       f"platform step required (spec 12 §2.B root tier); "
                       f"revocation_ref={item.cred.revocation_ref.value}")
            prompted += 1
            continue
        await lane.arm_one_shot(
            ROTATION_TASK, fire_at=now,
            payload={"name": item.cred.name,
                     "horizon_epoch": item.horizon_epoch})
        armed += 1
    return armed, prompted
