"""Composition-root wiring for the ONE PollSupervisor (K5, spec 09 §3.6).

The composition root (the eventual `sb/app` main, K8/CUT-1) calls
`build_poll_supervisor(...)` after `db.init(cfg)` and hands
`supervisor.run_forever(poll_interval_s=5)` to the K5 task supervisor as ONE
supervised task. Registration here is the "REGISTERED at K5" half of the
outbox lanes' authored/registered split (F-1/RC-20).

Lane roster (non-exhaustive — spec 09 §3.6): outbox relay + reaper (K4),
DueQueueLane + ExpiryJanitorLane (S10); S12 adds InvariantSweepLane; a
credential-rotation lane rides later (spec 12).
"""

from __future__ import annotations

from typing import Callable

from sb.kernel.draft.janitor import ExpiryJanitorLane
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.outbox.relay import OutboxReaperLane, OutboxRelayLane
from sb.kernel.outbox.store import STORE, OutboxStore
from sb.kernel.scheduler.due_queue import DueQueueLane
from sb.kernel.scheduler.poll import SYSTEM_CLOCK, PollSupervisor

__all__ = ["build_poll_supervisor"]


def build_poll_supervisor(
    *,
    bus,
    lifecycle=None,
    store: OutboxStore = STORE,
    findings: Callable = record_operator_finding,
    clock=SYSTEM_CLOCK,
    instance_id: str | None = None,
    with_durability_lanes: bool = True,
) -> PollSupervisor:
    """Build the ONE supervisor with the K4 outbox lanes + the K9
    durability lanes registered.

    `bus` is the event bus port (`async emit(name, **payload)`).
    `lifecycle` defaults to the sb.kernel.lifecycle module.
    `with_durability_lanes=False` keeps the pre-S10 roster (test hosts
    without a due-queue/drafts schema).
    """
    if lifecycle is None:
        from sb.kernel import lifecycle as lifecycle_module

        lifecycle = lifecycle_module
    supervisor = PollSupervisor(lifecycle=lifecycle, clock=clock)
    supervisor.register_lane(OutboxRelayLane(bus=bus, store=store, findings=findings))
    supervisor.register_lane(OutboxReaperLane(store=store))
    if with_durability_lanes:
        supervisor.register_lane(DueQueueLane(instance_id=instance_id, clock=clock))
        supervisor.register_lane(ExpiryJanitorLane())
    return supervisor
