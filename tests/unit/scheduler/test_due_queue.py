"""S10: the DueQueueLane — arm/claim/fire exactly-once, quiet hours,
condition polls, failure routing, boot reconcile (spec 09 §3.7/§3.8)."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from sb.kernel.scheduler import due_queue as dq
from sb.kernel.scheduler.due_queue import (
    DueQueueLane,
    SYSTEM_ACTOR,
    SchedulerFenceError,
    declare_task,
)
from sb.spec.refs import HandlerRef, WorkflowRef, clear_ref_table, handler
from sb.spec.scheduler import (
    ErrorPolicy,
    EventTrigger,
    Interval,
    ManagedTaskSpec,
    QuietHours,
    QuietHoursPolicy,
    TaskDurability,
)

from tests.unit.scheduler.conftest import utc

run = asyncio.run
T0 = utc(2026, 7, 8, 12, 0, 0)


@pytest.fixture(autouse=True)
def _refs():
    clear_ref_table()
    yield
    clear_ref_table()


def make_spec(name="gc:sweep", seconds=600, **kw) -> ManagedTaskSpec:
    kw.setdefault("trigger", Interval(seconds=seconds))
    kw.setdefault("handler", HandlerRef(f"{name}.fire"))
    kw.setdefault("durability", TaskDurability.DURABLE)
    return ManagedTaskSpec(name=name, **kw)


def test_system_actor_sentinel():
    assert SYSTEM_ACTOR.actor_type == "system"
    assert SYSTEM_ACTOR.user_id is None


def test_declare_fences():
    with pytest.raises(SchedulerFenceError, match="bus"):
        declare_task(make_spec(trigger=EventTrigger(event="xp.awarded")))
    with pytest.raises(SchedulerFenceError, match="0-23"):
        declare_task(make_spec(quiet_hours=QuietHours(start_hour=25, end_hour=8)))
    declare_task(make_spec())   # clean
    with pytest.raises(SchedulerFenceError, match="differing"):
        declare_task(make_spec(seconds=601))


def test_arm_declared_tasks_idempotent(fake_env):
    db, _ = fake_env
    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec())
    run(lane.arm_declared_tasks(T0))
    run(lane.arm_declared_tasks(T0))     # second boot: ON CONFLICT no-op
    assert len(db.timers) == 1
    t = next(iter(db.timers.values()))
    assert t.recurring and t.task_key == "gc:sweep"


def test_fire_happy_path_exactly_once(fake_env):
    db, idem = fake_env
    calls = []

    @handler("gc:sweep.fire")
    async def fire(ctx):
        calls.append(ctx.request_id)
        return "done"

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec())
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    now = T0 + timedelta(seconds=100)
    result = run(lane.tick(now))
    assert result.claimed == 1 and result.fired == 1
    assert len(calls) == 1
    # the recurring slot advanced (still one row, pending, future fire_at).
    t = next(iter(db.timers.values()))
    assert t.status == "pending" and t.fire_at > now
    # deterministic once() key: task_id:fire_epoch under the dot-folded namespace.
    key = next(iter(idem.keys))
    assert key.startswith("gc.sweep:")


def test_fire_replay_noop_via_once(fake_env):
    db, idem = fake_env
    calls = []

    @handler("gc:sweep.fire")
    async def fire(ctx):
        calls.append(1)

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec())
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    timer = next(iter(db.timers.values()))
    from sb.kernel.scheduler.misfire import apply_misfire
    decision = apply_misfire(timer, T0)
    # pre-seed the idempotency key (the "other instance already fired" case).
    from sb.kernel.db.idempotency import IdempotencyKey
    key = IdempotencyKey(namespace="gc.sweep", guild_id=0,
                         dedup_token=f"{timer.task_id}:{decision.fire_epochs[0]}")
    idem.keys[key.render()] = "success"
    fired, failed, skipped = run(lane._fire(timer, decision, T0))
    assert fired == 1 and calls == []        # replay no-op, slot still advanced


def test_transient_failure_requeues_then_dead_at_cap(fake_env):
    db, _ = fake_env

    @handler("gc:sweep.fire")
    async def fire(ctx):
        raise ConnectionError("db busy")     # DBUnavailable class → transient

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec())
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    result = run(lane.tick(T0)); assert result.failed == 1
    t = next(iter(db.timers.values()))
    assert t.status == "pending"             # requeued for the lease to re-claim
    # drive attempts past the cap:
    from dataclasses import replace
    tid = t.task_id
    db.timers[tid] = replace(t, attempts=dq.MAX_FIRE_ATTEMPTS)
    run(lane.tick(T0))
    assert db.timers[tid].status == "dead"


def test_nonretryable_log_advances_past_bad_slot(fake_env):
    db, _ = fake_env

    @handler("gc:sweep.fire")
    async def fire(ctx):
        raise ValueError("bad payload")      # bug → non-retryable

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec(error_policy=ErrorPolicy.LOG))
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    run(lane.tick(T0))
    t = next(iter(db.timers.values()))
    assert t.status == "pending" and t.fire_at > T0    # advanced, schedule survives


def test_disable_after_n_cancels(fake_env):
    db, _ = fake_env

    @handler("gc:sweep.fire")
    async def fire(ctx):
        raise ValueError("boom")

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec(error_policy=ErrorPolicy.DISABLE_AFTER_N))
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    tid = next(iter(db.timers))
    from dataclasses import replace
    db.timers[tid] = replace(db.timers[tid],
                             consecutive_failures=dq.DISABLE_AFTER_N - 1)
    run(lane.tick(T0))
    assert db.timers[tid].status == "cancelled"


def test_quiet_hours_defer_pushes_to_window_end(fake_env):
    db, _ = fake_env
    calls = []

    @handler("digest:daily.fire")
    async def fire(ctx):
        calls.append(1)

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec(
        name="digest:daily",
        quiet_hours=QuietHours(start_hour=10, end_hour=14,
                               policy=QuietHoursPolicy.DEFER)))
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    run(lane.tick(T0))                        # 12:00 UTC — inside the window
    assert calls == []
    t = next(iter(db.timers.values()))
    assert t.fire_at.hour == 14               # deferred to the window end


def test_quiet_hours_skip_drops_occurrence(fake_env):
    db, _ = fake_env
    calls = []

    @handler("digest:daily.fire")
    async def fire(ctx):
        calls.append(1)

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec(
        name="digest:daily", quiet_hours=QuietHours(
            start_hour=10, end_hour=14, policy=QuietHoursPolicy.SKIP)))
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=601)))
    run(lane.tick(T0))
    assert calls == []
    t = next(iter(db.timers.values()))
    assert t.status == "pending" and t.fire_at > T0    # re-armed forward


def test_one_shot_arm_and_fire_deletes_row(fake_env):
    db, _ = fake_env
    calls = []

    @handler("bj:window.fire")
    async def fire(ctx):
        calls.append(ctx.params.get("session"))

    lane = DueQueueLane(clock=lambda: T0)
    spec = make_spec(name="bj:window", trigger=dq.OneShot()
                     if hasattr(dq, "OneShot") else None)
    from sb.spec.scheduler import OneShot
    spec = ManagedTaskSpec(name="bj:window", trigger=OneShot(),
                           handler=HandlerRef("bj:window.fire"),
                           durability=TaskDurability.DURABLE)
    run(lane.arm_one_shot(spec, T0 + timedelta(seconds=60), guild_id=42,
                          payload={"session": "s1"}))
    assert len(db.timers) == 1
    run(lane.tick(T0 + timedelta(seconds=120)))
    assert calls == ["s1"]
    assert db.timers == {}                    # one-shot success = DELETE


def test_reconcile_on_boot_drains_backlog_bounded(fake_env):
    db, _ = fake_env
    calls = []

    @handler("gc:sweep.fire")
    async def fire(ctx):
        calls.append(1)

    lane = DueQueueLane(clock=lambda: T0)
    declare_task(make_spec())
    run(lane.arm_declared_tasks(T0 - timedelta(seconds=1201)))
    run(lane.reconcile_on_boot(T0))
    assert calls == [1]                       # coalesce: overdue fired ONCE
    t = next(iter(db.timers.values()))
    assert t.fire_at > T0
