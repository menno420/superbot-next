"""S10 scheduler-test fakes: an in-memory due-queue DB + idempotency +
transaction, monkeypatched into sb.kernel.scheduler.due_queue's imported
symbols (the module imports names directly, so patch the MODULE attrs)."""

from __future__ import annotations

import contextlib
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from sb.kernel.db.scheduler import DueTimer
from sb.kernel.scheduler import due_queue as dq


class FakeSchedulerDb:
    """In-memory sb_due_queue honoring the primitive's contracts."""

    def __init__(self) -> None:
        self.timers: dict[str, DueTimer] = {}
        self.dead: list[str] = []
        self.cancelled: list[str] = []

    async def arm(self, timer: DueTimer, *, conn) -> None:
        if timer.recurring:
            slot = (timer.task_key, timer.guild_id or 0)
            for t in self.timers.values():
                if t.recurring and (t.task_key, t.guild_id or 0) == slot:
                    return   # ON CONFLICT DO NOTHING
        self.timers[timer.task_id] = timer

    async def claim_due(self, now, *, limit, lease_s, instance_id, conn):
        due = sorted((t for t in self.timers.values()
                      if t.status == "pending" and t.fire_at <= now),
                     key=lambda t: t.fire_at)[:limit]
        out = []
        for t in due:
            claimed = replace(t, status="claimed", claimed_by=instance_id,
                              attempts=t.attempts + 1)
            self.timers[t.task_id] = claimed
            out.append(claimed)
        return tuple(out)

    async def mark_fired(self, timer, next_fire_at, *, conn):
        if next_fire_at is None:
            self.timers.pop(timer.task_id, None)
        else:
            self.timers[timer.task_id] = replace(
                self.timers[timer.task_id], status="pending",
                fire_at=next_fire_at, attempts=0, claimed_by=None)

    async def mark_failed(self, task_id, error, *, retryable, conn):
        t = self.timers[task_id]
        if retryable:
            t = replace(t, status="pending", claimed_by=None)
        else:
            t = replace(t, consecutive_failures=t.consecutive_failures + 1)
        self.timers[task_id] = t
        return t

    async def mark_dead(self, task_id, finding, *, conn):
        self.timers[task_id] = replace(self.timers[task_id], status="dead")
        self.dead.append(task_id)

    async def reap_expired_leases(self, now, *, conn):
        n = 0
        for tid, t in list(self.timers.items()):
            if t.status == "claimed" and t.lease_expires_at and t.lease_expires_at < now:
                self.timers[tid] = replace(t, status="pending", claimed_by=None)
                n += 1
        return n

    async def cancel(self, task_id, *, conn):
        if task_id in self.timers:
            self.timers[task_id] = replace(self.timers[task_id], status="cancelled")
            self.cancelled.append(task_id)
            return 1
        return 0


class FakeIdempotency:
    def __init__(self) -> None:
        self.keys: dict[str, str | None] = {}

    async def once(self, key, *, conn) -> bool:
        k = key.render()
        if k in self.keys:
            return False
        self.keys[k] = None
        return True

    async def record_outcome(self, key, outcome, *, result_ref=None, conn) -> None:
        self.keys[key.render()] = outcome

    async def read_outcome(self, key, *, conn):
        return None


@pytest.fixture
def fake_env(monkeypatch):
    db = FakeSchedulerDb()
    idem = FakeIdempotency()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        # honor rollback semantics: an exception inside the txn restores
        # BOTH stores (the real once() guard row rolls back with the txn).
        timers_snapshot = dict(db.timers)
        keys_snapshot = dict(idem.keys)
        try:
            yield object()
        except BaseException:
            db.timers.clear(); db.timers.update(timers_snapshot)
            idem.keys.clear(); idem.keys.update(keys_snapshot)
            raise

    monkeypatch.setattr(dq, "scheduler_db", db)
    monkeypatch.setattr(dq, "transaction", fake_transaction)
    monkeypatch.setattr(dq, "once", idem.once)
    monkeypatch.setattr(dq, "record_outcome", idem.record_outcome)
    monkeypatch.setattr(dq, "read_outcome", idem.read_outcome)
    dq.clear_declared_tasks_for_tests()
    yield db, idem
    dq.clear_declared_tasks_for_tests()


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)
