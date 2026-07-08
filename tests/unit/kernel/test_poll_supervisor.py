"""K5 PollSupervisor tests (frozen L0 spec 09 §3.6)."""

from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from sb.kernel.lifecycle import Phase
from sb.kernel.scheduler.poll import LaneTickResult, PollSupervisor

NOW = dt.datetime(2026, 7, 8, 12, 0, tzinfo=dt.timezone.utc)


class _FakeLifecycle:
    def __init__(self, phase: Phase = Phase.STARTING) -> None:
        self.phase = phase

    def get_phase(self) -> Phase:
        return self.phase

    def can_accept_commands(self) -> bool:
        return self.phase in (Phase.STARTING, Phase.RUNNING)


class _Lane:
    def __init__(self, name: str, raise_on_tick: bool = False) -> None:
        self.name = name
        self.raise_on_tick = raise_on_tick
        self.ticks = 0
        self.reconciles = 0

    async def tick(self, now):
        self.ticks += 1
        if self.raise_on_tick:
            raise RuntimeError("lane exploded")
        return LaneTickResult(lane=self.name, claimed=0, fired=0, failed=0, skipped=0)

    async def reconcile_on_boot(self, now):
        self.reconciles += 1


def test_duplicate_lane_name_rejected() -> None:
    sup = PollSupervisor(lifecycle=_FakeLifecycle())
    sup.register_lane(_Lane("outbox:relay"))
    with pytest.raises(ValueError):
        sup.register_lane(_Lane("outbox:relay"))
    assert sup.lane_names == ("outbox:relay",)


def test_no_lane_work_before_running_then_reconcile_then_tick() -> None:
    # Ready-gate (vocab §⑤.5): neither reconcile nor tick until RUNNING.
    lifecycle = _FakeLifecycle(Phase.STARTING)
    lane = _Lane("outbox:relay")
    sup = PollSupervisor(lifecycle=lifecycle, clock=lambda: NOW)
    sup.register_lane(lane)

    async def scenario() -> None:
        task = asyncio.create_task(sup.run_forever(poll_interval_s=0.01))
        await asyncio.sleep(0.05)
        assert lane.reconciles == 0 and lane.ticks == 0   # still STARTING
        lifecycle.phase = Phase.RUNNING
        await asyncio.sleep(0.08)
        assert lane.reconciles == 1                        # exactly one reconcile
        assert lane.ticks >= 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_draining_skips_claiming() -> None:
    lifecycle = _FakeLifecycle(Phase.RUNNING)
    lane = _Lane("outbox:relay")
    sup = PollSupervisor(lifecycle=lifecycle, clock=lambda: NOW)
    sup.register_lane(lane)

    async def scenario() -> None:
        task = asyncio.create_task(sup.run_forever(poll_interval_s=0.01))
        await asyncio.sleep(0.05)
        assert lane.ticks >= 1
        lifecycle.phase = Phase.DRAINING          # drain gate (vocab §⑤.2)
        await asyncio.sleep(0.03)
        ticks_at_drain = lane.ticks
        await asyncio.sleep(0.05)
        assert lane.ticks == ticks_at_drain       # no claims while draining
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_terminal_before_running_exits() -> None:
    lifecycle = _FakeLifecycle(Phase.FAILED_STARTUP)
    sup = PollSupervisor(lifecycle=lifecycle)
    sup.register_lane(_Lane("outbox:relay"))
    asyncio.run(asyncio.wait_for(sup.run_forever(poll_interval_s=0.01), timeout=1))


def test_per_lane_exception_isolation() -> None:
    lifecycle = _FakeLifecycle(Phase.RUNNING)
    bad = _Lane("outbox:relay", raise_on_tick=True)
    good = _Lane("outbox:reaper")
    sup = PollSupervisor(lifecycle=lifecycle, clock=lambda: NOW)
    sup.register_lane(bad)
    sup.register_lane(good)

    results = asyncio.run(sup.tick_once())
    # The raising lane is caught+logged; the loop continues to the next lane.
    assert [r.lane for r in results] == ["outbox:reaper"]
    assert bad.ticks == 1 and good.ticks == 1


def test_build_poll_supervisor_registers_outbox_lanes() -> None:
    from sb.app.poll_host import build_poll_supervisor

    class _Bus:
        async def emit(self, name, **payload):
            pass

    sup = build_poll_supervisor(bus=_Bus(), lifecycle=_FakeLifecycle())
    assert sup.lane_names == ("outbox:relay", "outbox:reaper",
                              "due_queue", "draft_janitor")
    bare = build_poll_supervisor(bus=_Bus(), lifecycle=_FakeLifecycle(),
                                 with_durability_lanes=False)
    assert bare.lane_names == ("outbox:relay", "outbox:reaper")
