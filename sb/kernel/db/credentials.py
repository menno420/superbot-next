"""sb_credential_rotation CRUD — the rotation phase ledger (S13, frozen L0
spec 12 §2.B(1c)). asyncpg SQL only, behind the K3 seam. The secret value
NEVER enters this table (fingerprint = non-secret identity only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef
from sb.spec.versioning import CheckpointClass, StoreSpec, register_store

__all__ = [
    "CREDENTIAL_ROTATION_STORE",
    "RotationRow",
    "last_verified_at",
    "read_rotation",
    "reserve_rotation",
    "set_phase",
]

# No member data: credential names + non-secret fingerprints only.
CREDENTIAL_ROTATION_STORE = register_store(StoreSpec(
    table="sb_credential_rotation",
    sole_writer=EngineRef("sb.kernel.credentials"),
    retention="permanent",           # the credential-incident audit trail
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="credential_rotation",
    reader_domains=("operator_dashboard",),
))


@dataclass(frozen=True)
class RotationRow:
    name: str
    horizon_epoch: int
    phase: str                       # reserved | issued_pending_verify | verified | failed
    fingerprint: str | None
    issued_at: datetime | None
    verified_at: datetime | None
    detail: str | None


def _row(r) -> RotationRow:
    return RotationRow(
        name=r["name"], horizon_epoch=r["horizon_epoch"], phase=r["phase"],
        fingerprint=r["fingerprint"], issued_at=r["issued_at"],
        verified_at=r["verified_at"], detail=r["detail"])


async def reserve_rotation(name: str, horizon_epoch: int, *, now: datetime,
                           conn) -> None:
    """txn-1 companion of the horizon-stable once() guard: the RESERVED
    ledger row (idempotent — a duplicate arm resolves to the same row)."""
    await execute(
        """
        INSERT INTO sb_credential_rotation (name, horizon_epoch, phase,
                                            created_at, updated_at)
        VALUES ($1, $2, 'reserved', $3, $3)
        ON CONFLICT (name, horizon_epoch) DO NOTHING
        """,
        (name, horizon_epoch, now), conn=conn)


async def read_rotation(name: str, horizon_epoch: int, *, conn) -> RotationRow | None:
    r = await fetchone(
        """
        SELECT name, horizon_epoch, phase, fingerprint, issued_at,
               verified_at, detail
        FROM sb_credential_rotation WHERE name = $1 AND horizon_epoch = $2
        """,
        (name, horizon_epoch), conn=conn)
    return _row(r) if r else None


async def set_phase(name: str, horizon_epoch: int, phase: str, *,
                    now: datetime, fingerprint: str | None = None,
                    detail: str | None = None, conn) -> None:
    """Advance the phase machine (each advance is its own committed txn —
    the executor's multi-txn protocol, spec 12 §2.B(1c))."""
    await execute(
        """
        UPDATE sb_credential_rotation
        SET phase = $3,
            fingerprint = COALESCE($4, fingerprint),
            issued_at = CASE WHEN $3 = 'issued_pending_verify' THEN $5
                             ELSE issued_at END,
            verified_at = CASE WHEN $3 = 'verified' THEN $5 ELSE verified_at END,
            detail = COALESCE($6, detail),
            updated_at = $5
        WHERE name = $1 AND horizon_epoch = $2
        """,
        (name, horizon_epoch, phase, fingerprint, now, detail), conn=conn)


async def last_verified_at(*, conn) -> dict[str, datetime]:
    """`last_rotated_at` per credential name — the cadence detector's join
    input (MAX(verified_at) over terminal-success rotations)."""
    rows = await fetchall(
        """
        SELECT name, MAX(verified_at) AS last_verified
        FROM sb_credential_rotation WHERE phase = 'verified' GROUP BY name
        """,
        (), conn=conn)
    return {r["name"]: r["last_verified"] for r in rows}
