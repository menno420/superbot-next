"""The due-queue DB primitive (K9/S10 — frozen L0 spec 09 §3.5). asyncpg
SQL only — no other kernel imports; every caller supplies a txn-bound conn
from ``db.transaction()`` (the fire txn) or runs a standalone statement.

`claim_due` is the dual-instance-safe claim (FOR UPDATE SKIP LOCKED — the
fix for the shipped uuid4-defeated `claim_run`), and the BOUNDED
boot-reconcile primitive: boot uses the same path as steady-state, so a
large overdue backlog drains in batches and two booting instances cannot
double-claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Mapping

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import CheckpointClass, DataClass, StoreSpec, register_store

__all__ = [
    "DUE_QUEUE_STORE",
    "DueTimer",
    "MAX_FIRE_ATTEMPTS",
    "arm",
    "cancel",
    "cancel_scope",
    "claim_due",
    "mark_dead",
    "mark_failed",
    "mark_fired",
    "reap_expired_leases",
    "select_overdue",
]

MAX_FIRE_ATTEMPTS = 12   # transient re-claim cap for one fire_epoch → DEAD (mirrors the outbox)

# S11 class 12: user-automation timers carry the creator's actor snapshot in
# payload_json (_creator_actor) — a MEMBER_ID store. Erasure = cancel + scrub
# the subject's timers; body lands with the automation band, ref DECLARED now.
DUE_QUEUE_STORE = register_store(StoreSpec(
    table="sb_due_queue",
    sole_writer=EngineRef("sb.kernel.db.scheduler"),
    retention="live",   # rows delete on one-shot success / cancel; no idle history
    # SELF-MANAGED like the outbox: boot-reconcile owns cross-deploy resume,
    # so this store does NOT route through run_recovery (AGGREGATE, no reader).
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="due_queue",
    reader_domains=("operator_dashboard",),
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("kernel.scheduler.erase_subject_timers"),
))


@dataclass(frozen=True)
class DueTimer:
    task_id: str
    task_key: str
    guild_id: int | None
    trigger_kind: str
    fire_at: datetime
    payload: Mapping[str, Any]
    payload_version: int
    recurring: bool
    misfire_policy: str
    catch_up: bool
    grace_s: int
    max_catchup: int
    interval_seconds: int | None
    cron_expr: str | None
    error_policy: str
    status: str = "pending"           # pending | claimed | dead | cancelled
    claimed_by: str | None = None
    lease_expires_at: datetime | None = None
    attempts: int = 0
    consecutive_failures: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _row_to_timer(row: Mapping[str, Any]) -> DueTimer:
    payload = row["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return DueTimer(
        task_id=str(row["task_id"]), task_key=row["task_key"],
        guild_id=row["guild_id"], trigger_kind=row["trigger_kind"],
        fire_at=row["fire_at"], payload=payload or {},
        payload_version=row["payload_version"], recurring=row["recurring"],
        misfire_policy=row["misfire_policy"], catch_up=row["catch_up"],
        grace_s=row["grace_s"], max_catchup=row["max_catchup"],
        interval_seconds=row["interval_seconds"], cron_expr=row["cron_expr"],
        error_policy=row["error_policy"], status=row["status"],
        claimed_by=row["claimed_by"], lease_expires_at=row["lease_expires_at"],
        attempts=row["attempts"], consecutive_failures=row["consecutive_failures"],
        created_at=row["created_at"], updated_at=row["updated_at"])


_ARM_RECURRING = """
INSERT INTO sb_due_queue (
    task_id, task_key, guild_id, trigger_kind, fire_at, payload_json,
    payload_version, recurring, misfire_policy, catch_up, grace_s,
    max_catchup, interval_seconds, cron_expr, error_policy,
    created_at, updated_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,TRUE,$8,$9,$10,$11,$12,$13,$14,$15,$15)
ON CONFLICT (task_key, COALESCE(guild_id, 0)) WHERE recurring DO NOTHING
"""

_ARM_ONE_SHOT = """
INSERT INTO sb_due_queue (
    task_id, task_key, guild_id, trigger_kind, fire_at, payload_json,
    payload_version, recurring, misfire_policy, catch_up, grace_s,
    max_catchup, interval_seconds, cron_expr, error_policy,
    created_at, updated_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,FALSE,$8,$9,$10,$11,$12,$13,$14,$15,$15)
"""


async def arm(timer: DueTimer, *, conn) -> None:
    """Recurring: idempotent slot upsert (ON CONFLICT on the COALESCE
    partial index — a live/advanced slot is NOT reset; a GLOBAL NULL guild
    cannot re-arm a second row). One-shot: plain INSERT (free-multi)."""
    now = timer.created_at or timer.fire_at
    params = (
        timer.task_id, timer.task_key, timer.guild_id, timer.trigger_kind,
        timer.fire_at, json.dumps(dict(timer.payload)), timer.payload_version,
        timer.misfire_policy, timer.catch_up, timer.grace_s, timer.max_catchup,
        timer.interval_seconds, timer.cron_expr, timer.error_policy, now)
    await execute(_ARM_RECURRING if timer.recurring else _ARM_ONE_SHOT,
                  params, conn=conn)


_CLAIM_DUE = """
UPDATE sb_due_queue SET status='claimed', claimed_by=$4,
       lease_expires_at = $1 + make_interval(secs => $3),
       attempts = attempts + 1, updated_at = $1
 WHERE task_id IN (
     SELECT task_id FROM sb_due_queue
      WHERE status='pending' AND fire_at <= $1
      ORDER BY fire_at
      FOR UPDATE SKIP LOCKED
      LIMIT $2 )
RETURNING *
"""


async def claim_due(now: datetime, *, limit: int, lease_s: int,
                    instance_id: str, conn) -> tuple[DueTimer, ...]:
    rows = await fetchall(_CLAIM_DUE, (now, limit, float(lease_s), instance_id),
                          conn=conn)
    return tuple(_row_to_timer(r) for r in rows)


async def mark_fired(timer: DueTimer, next_fire_at: datetime | None, *,
                     conn) -> None:
    """One-shot success = DELETE; recurring success = ADVANCE back to
    pending (inside the fire txn — no crash-after-commit-before-rearm
    window)."""
    if next_fire_at is None:
        await execute("DELETE FROM sb_due_queue WHERE task_id = $1",
                      (timer.task_id,), conn=conn)
    else:
        await execute(
            "UPDATE sb_due_queue SET status='pending', fire_at=$2, attempts=0,"
            " claimed_by=NULL, lease_expires_at=NULL, consecutive_failures=$3,"
            " updated_at=now() WHERE task_id=$1",
            (timer.task_id, next_fire_at, 0), conn=conn)


async def mark_failed(task_id: str, error: str, *, retryable: bool,
                      conn) -> DueTimer | None:
    """Transient ⇒ back to pending (the lease will re-claim); non-retryable
    ⇒ consecutive_failures++ and stay claimed for the caller to route
    error_policy. Returns the updated row."""
    if retryable:
        row = await fetchone(
            "UPDATE sb_due_queue SET status='pending', claimed_by=NULL,"
            " lease_expires_at=NULL, updated_at=now()"
            " WHERE task_id=$1 RETURNING *", (task_id,), conn=conn)
    else:
        row = await fetchone(
            "UPDATE sb_due_queue SET consecutive_failures = consecutive_failures + 1,"
            " updated_at=now() WHERE task_id=$1 RETURNING *", (task_id,), conn=conn)
    return _row_to_timer(row) if row else None


async def mark_dead(task_id: str, finding: str, *, conn) -> None:
    """Terminal: the transient cap hit; the caller records the finding."""
    await execute(
        "UPDATE sb_due_queue SET status='dead', updated_at=now()"
        " WHERE task_id=$1", (task_id,), conn=conn)


async def reap_expired_leases(now: datetime, *, conn) -> int:
    tag = await execute(
        "UPDATE sb_due_queue SET status='pending', claimed_by=NULL,"
        " lease_expires_at=NULL, updated_at=$1"
        " WHERE status='claimed' AND lease_expires_at < $1", (now,), conn=conn)
    try:
        return int(str(tag).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def select_overdue(now: datetime, *, conn=None) -> tuple[DueTimer, ...]:
    """READ-ONLY diagnostic (dashboard) — boot uses claim_due, never this."""
    rows = await fetchall(
        "SELECT * FROM sb_due_queue WHERE status='pending' AND fire_at <= $1"
        " ORDER BY fire_at", (now,), conn=conn)
    return tuple(_row_to_timer(r) for r in rows)


async def cancel(task_id: str, *, conn) -> int:
    tag = await execute(
        "UPDATE sb_due_queue SET status='cancelled', updated_at=now()"
        " WHERE task_id=$1 AND status NOT IN ('dead','cancelled')",
        (task_id,), conn=conn)
    try:
        return int(str(tag).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def cancel_scope(guild_id: int, *, conn) -> tuple[DueTimer, ...]:
    """Guild-leave reclaim (C-8) — returns the cancelled timers so
    value-bearing ones can route compensation."""
    rows = await fetchall(
        "UPDATE sb_due_queue SET status='cancelled', updated_at=now()"
        " WHERE guild_id=$1 AND status NOT IN ('dead','cancelled')"
        " RETURNING *", (guild_id,), conn=conn)
    return tuple(_row_to_timer(r) for r in rows)
