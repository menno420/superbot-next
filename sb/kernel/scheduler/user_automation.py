"""A-13 — the user-self-service automation PRODUCER + guardrails (K9/S10).

A user-scoped task source on the K9 due-queue: reserved K1 namespace
``user_automation:*`` + a per-user domain store (the participation side,
``data_class=MEMBER_ID`` — ports at the consumer bands) whose producer arms
DURABLE timers. NO ``TaskScope.USER``, NO ``sb_due_queue`` schema change,
NO Producer-enum change — the spec-09 §5 ``automation_rules`` pattern.

Kernel guardrails at the producer/arm seam (all structural):
- interval-floor fence (``min_interval_s``);
- per-user active-automation cap (the spec-10 PER_ACTOR_QUOTA socket —
  an installable counter port until the quota engine lands at S11);
- quiet-hours/delivery-window ride ``ManagedTaskSpec.quiet_hours``;
- delivery exclusively via the frozen AT_LEAST_ONCE outbox path (the fired
  workflow is ``atomic_db_only``-fenced like every scheduler fire — category
  A needs zero new machinery);
- **category B (auto-acting) is structurally reserved but OFF**: arming an
  ``AutomationEligibility.ACTION`` automation is a SEMANTIC_VIOLATION until
  the dedicated pricing session mints its ruling (Q-0243 — the price is a
  dedicated simulation's output, never a guessed number);
- the authority rider: user-scoped fires carry the CREATOR's ActorRef and
  re-resolve K6 at fire time (the due-queue's ``_creator_actor`` payload
  channel) — never the SYSTEM_ACTOR scripted bypass.
"""

from __future__ import annotations

from datetime import datetime
from typing import Awaitable, Callable, Mapping

from sb.kernel.interaction.request import ActorRef
from sb.kernel.scheduler.due_queue import DueQueueLane, SchedulerFenceError
from sb.spec.scheduler import (
    AutomationEligibility,
    Interval,
    ManagedTaskSpec,
    TaskDurability,
)

__all__ = [
    "MIN_AUTOMATION_INTERVAL_S",
    "MAX_ACTIVE_PER_USER",
    "USER_AUTOMATION_PREFIX",
    "arm_user_automation",
    "check_user_automation",
    "install_active_count_reader",
    "reset_user_automation_ports_for_tests",
]

USER_AUTOMATION_PREFIX = "user_automation:"
MIN_AUTOMATION_INTERVAL_S = 3600      # the interval floor (hourly)
MAX_ACTIVE_PER_USER = 5               # per-user active-automation cap (PER_ACTOR_QUOTA socket)

# active-count port: (guild_id, user_id) -> live automation count. The real
# reader rides the per-user domain store at its port band; default = 0.
ActiveCountReader = Callable[[int, int], Awaitable[int]]


async def _zero_active(guild_id: int, user_id: int) -> int:
    return 0


_active_count: ActiveCountReader = _zero_active


def install_active_count_reader(reader: ActiveCountReader) -> None:
    global _active_count
    _active_count = reader


def reset_user_automation_ports_for_tests() -> None:
    global _active_count
    _active_count = _zero_active


def check_user_automation(spec: ManagedTaskSpec, *,
                          eligibility: AutomationEligibility) -> None:
    """The arm-seam fences (SEMANTIC_VIOLATION class, fail-closed)."""
    if not spec.name.startswith(USER_AUTOMATION_PREFIX):
        raise SchedulerFenceError(
            f"{spec.name}: user automations live under the reserved "
            f"{USER_AUTOMATION_PREFIX}* namespace")
    if eligibility is AutomationEligibility.ACTION:
        # category B fenced OFF pending the pricing session (Q-0243).
        raise SchedulerFenceError(
            f"{spec.name}: automation_eligibility=action (category B) is "
            f"structurally reserved but OFF until the pricing session rules")
    if eligibility is AutomationEligibility.NONE:
        raise SchedulerFenceError(
            f"{spec.name}: the target declares automation_eligibility=none")
    if spec.durability is not TaskDurability.DURABLE:
        raise SchedulerFenceError(
            f"{spec.name}: user automations must be DURABLE (merge=deploy survival)")
    trigger = spec.trigger
    if isinstance(trigger, Interval) and trigger.seconds < MIN_AUTOMATION_INTERVAL_S:
        raise SchedulerFenceError(
            f"{spec.name}: interval {trigger.seconds}s under the "
            f"{MIN_AUTOMATION_INTERVAL_S}s floor")
    poll = getattr(trigger, "poll_interval_s", None)
    if poll is not None and poll < MIN_AUTOMATION_INTERVAL_S:
        raise SchedulerFenceError(
            f"{spec.name}: condition poll {poll}s under the "
            f"{MIN_AUTOMATION_INTERVAL_S}s floor")


async def arm_user_automation(lane: DueQueueLane, spec: ManagedTaskSpec, *,
                              creator: ActorRef, guild_id: int,
                              eligibility: AutomationEligibility,
                              payload: Mapping[str, object] | None = None,
                              now: datetime | None = None) -> str:
    """The producer arm: fences → per-user cap → arm with the creator's
    actor snapshot (the fire re-resolves K6 with THIS actor, never SYSTEM)."""
    check_user_automation(spec, eligibility=eligibility)
    if creator.user_id is None:
        raise SchedulerFenceError(f"{spec.name}: a user automation needs a creator")
    active = await _active_count(guild_id, creator.user_id)
    if active >= MAX_ACTIVE_PER_USER:
        raise SchedulerFenceError(
            f"{spec.name}: per-user active-automation cap "
            f"({MAX_ACTIVE_PER_USER}) reached")
    enriched = dict(payload or {})
    enriched["_creator_actor"] = {
        "user_id": creator.user_id,
        "is_guild_operator": creator.is_guild_operator,
        "member_tier": creator.member_tier,
        "role_ids": sorted(creator.role_ids),
    }
    return await lane.arm_task(spec, guild_id=guild_id, payload=enriched, now=now)
