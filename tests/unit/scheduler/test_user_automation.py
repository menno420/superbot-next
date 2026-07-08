"""S10: the A-13 user-automation producer guardrails."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.interaction.request import ActorRef
from sb.kernel.scheduler.due_queue import DueQueueLane, SchedulerFenceError
from sb.kernel.scheduler.user_automation import (
    MAX_ACTIVE_PER_USER,
    MIN_AUTOMATION_INTERVAL_S,
    arm_user_automation,
    check_user_automation,
    install_active_count_reader,
    reset_user_automation_ports_for_tests,
)
from sb.spec.refs import WorkflowRef
from sb.spec.scheduler import (
    AutomationEligibility,
    ConditionTrigger,
    Interval,
    ManagedTaskSpec,
    TaskDurability,
)

run = asyncio.run


@pytest.fixture(autouse=True)
def _ports():
    reset_user_automation_ports_for_tests()
    yield
    reset_user_automation_ports_for_tests()


def spec(name="user_automation:daily_collect", seconds=7200, **kw):
    kw.setdefault("trigger", Interval(seconds=seconds))
    kw.setdefault("handler", WorkflowRef("economy.idle_collect"))
    kw.setdefault("durability", TaskDurability.DURABLE)
    return ManagedTaskSpec(name=name, **kw)


def actor(uid=7):
    return ActorRef(user_id=uid, is_guild_operator=False, is_bot_owner=False,
                    is_dm=False, member_tier="member")


def test_fences():
    ok = spec()
    check_user_automation(ok, eligibility=AutomationEligibility.NOTIFY_ONLY)
    with pytest.raises(SchedulerFenceError, match="namespace"):
        check_user_automation(spec(name="economy:collect"),
                              eligibility=AutomationEligibility.NOTIFY_ONLY)
    # category B fenced OFF pending the pricing session (Q-0243).
    with pytest.raises(SchedulerFenceError, match="category B"):
        check_user_automation(ok, eligibility=AutomationEligibility.ACTION)
    with pytest.raises(SchedulerFenceError, match="none"):
        check_user_automation(ok, eligibility=AutomationEligibility.NONE)
    with pytest.raises(SchedulerFenceError, match="floor"):
        check_user_automation(spec(seconds=MIN_AUTOMATION_INTERVAL_S - 1),
                              eligibility=AutomationEligibility.NOTIFY_ONLY)
    with pytest.raises(SchedulerFenceError, match="floor"):
        check_user_automation(
            spec(trigger=ConditionTrigger(condition="setting:farm.ready",
                                          poll_interval_s=60)),
            eligibility=AutomationEligibility.NOTIFY_ONLY)
    with pytest.raises(SchedulerFenceError, match="DURABLE"):
        check_user_automation(spec(durability=TaskDurability.IN_MEMORY),
                              eligibility=AutomationEligibility.NOTIFY_ONLY)


class FakeLane(DueQueueLane):
    def __init__(self):
        super().__init__(instance_id="test")
        self.armed = []

    async def arm_task(self, s, *, guild_id=None, payload=None, now=None):
        self.armed.append((s, guild_id, payload))
        return "task-1"


def test_arm_embeds_creator_actor_never_system():
    lane = FakeLane()
    task_id = run(arm_user_automation(
        lane, spec(), creator=actor(7), guild_id=42,
        eligibility=AutomationEligibility.NOTIFY_ONLY))
    assert task_id == "task-1"
    _, guild_id, payload = lane.armed[0]
    assert guild_id == 42
    creator = payload["_creator_actor"]
    assert creator["user_id"] == 7 and creator["member_tier"] == "member"


def test_per_user_cap_blocks():
    async def full(guild_id, user_id):
        return MAX_ACTIVE_PER_USER
    install_active_count_reader(full)
    lane = FakeLane()
    with pytest.raises(SchedulerFenceError, match="cap"):
        run(arm_user_automation(lane, spec(), creator=actor(), guild_id=42,
                                eligibility=AutomationEligibility.NOTIFY_ONLY))


def test_creator_actor_rides_the_fire_context(fake_env):
    """The due-queue fire builds the CREATOR's ActorRef (K6 re-resolves at
    fire time inside K7) — never SYSTEM_ACTOR — when _creator_actor rides."""
    from sb.kernel.db.scheduler import DueTimer
    from sb.kernel.scheduler.due_queue import _actor_for
    from tests.unit.scheduler.conftest import utc
    t = DueTimer(task_id="t", task_key="user_automation:x", guild_id=42,
                 trigger_kind="interval", fire_at=utc(2026, 7, 8),
                 payload={"_creator_actor": {"user_id": 7, "member_tier": "member",
                                             "role_ids": [1, 2]}},
                 payload_version=1, recurring=True, misfire_policy="coalesce",
                 catch_up=True, grace_s=0, max_catchup=1, interval_seconds=3600,
                 cron_expr=None, error_policy="log")
    a = _actor_for(t)
    assert a.actor_type == "user" and a.user_id == 7
    assert a.role_ids == frozenset({1, 2})
