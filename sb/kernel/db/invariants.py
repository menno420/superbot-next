"""sb_quarantine + sb_invariant_sweep_log CRUD (S12 — frozen L0 spec 11 §3).
asyncpg SQL only, behind the K3 seam.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from sb.kernel.db.pool import execute, fetchall
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    StoreSpec,
    register_store,
)

__all__ = [
    "QUARANTINE_STORE",
    "SWEEP_LOG_STORE",
    "SweepRun",
    "list_quarantined",
    "quarantine_row",
    "write_sweep_log",
]

# The quarantine snapshot preserves FULL row payloads — potentially direct
# PII. Erasure = scrub snapshot_json for the subject (evidence skeleton
# kept); body lands with the operator band, ref DECLARED now.
QUARANTINE_STORE = register_store(StoreSpec(
    table="sb_quarantine",
    sole_writer=EngineRef("sb.kernel.invariants"),
    retention="until_disposition",   # owner-signed disposition closes a row
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="quarantine_evidence",
    reader_domains=("operator_dashboard",),
    data_class=DataClass.MEMBER_PII,
    erasure_ref=WorkflowRef("kernel.invariants.scrub_quarantine_subject"),
))

SWEEP_LOG_STORE = register_store(StoreSpec(
    table="sb_invariant_sweep_log",
    sole_writer=EngineRef("sb.kernel.invariants"),
    retention="180d",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="sweep_bookkeeping",
    reader_domains=("operator_dashboard",),
))


async def quarantine_row(*, invariant_id: str, primary_store: str,
                         stores: tuple[str, ...], row_id: str,
                         guild_id: int | None, snapshot: Mapping[str, Any],
                         now: datetime, conn) -> str:
    quarantine_id = str(uuid.uuid4())
    await execute(
        "INSERT INTO sb_quarantine (quarantine_id, invariant_id, primary_store,"
        " stores, row_id, guild_id, snapshot_json, quarantined_at)"
        " VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
        (quarantine_id, invariant_id, primary_store, list(stores), row_id,
         guild_id, json.dumps(dict(snapshot)), now), conn=conn)
    return quarantine_id


async def list_quarantined(invariant_id: str | None = None, *,
                           conn=None) -> list[dict]:
    if invariant_id is None:
        return await fetchall(
            "SELECT * FROM sb_quarantine WHERE disposition IS NULL"
            " ORDER BY quarantined_at DESC", (), conn=conn)
    return await fetchall(
        "SELECT * FROM sb_quarantine WHERE invariant_id=$1 AND disposition IS NULL"
        " ORDER BY quarantined_at DESC", (invariant_id,), conn=conn)


@dataclass
class SweepRun:
    invariant_id: str
    cadence_epoch: int
    started_at: datetime
    enforce_effective: bool
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    finished_at: datetime | None = None
    guilds_scanned: int = 0
    rows_read: int = 0
    violations_found: int = 0
    repairs_applied: int = 0
    quarantined: int = 0
    alerts: int = 0
    breaker_tripped: bool = False
    outcome: str = "success"


async def write_sweep_log(run: SweepRun, *, conn) -> None:
    await execute(
        "INSERT INTO sb_invariant_sweep_log (run_id, invariant_id, cadence_epoch,"
        " started_at, finished_at, enforce_effective, guilds_scanned, rows_read,"
        " violations_found, repairs_applied, quarantined, alerts, breaker_tripped)"
        " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",
        (run.run_id, run.invariant_id, run.cadence_epoch, run.started_at,
         run.finished_at, run.enforce_effective, run.guilds_scanned,
         run.rows_read, run.violations_found, run.repairs_applied,
         run.quarantined, run.alerts, run.breaker_tripped), conn=conn)
