"""Composition-root wiring for the ONE PollSupervisor (K5, spec 09 §3.6).

The composition root (the eventual `sb/app` main, K8/CUT-1) calls
`build_poll_supervisor(...)` after `db.init(cfg)` and hands
`supervisor.run_forever(poll_interval_s=5)` to the K5 task supervisor as ONE
supervised task. Registration here is the "REGISTERED at K5" half of the
outbox lanes' authored/registered split (F-1/RC-20).

Lane roster (non-exhaustive — spec 09 §3.6): the outbox relay + reaper today;
S10 registers DueQueueLane + ExpiryJanitorLane; S12 adds InvariantSweepLane;
a credential-rotation lane rides later (spec 12).
"""

from __future__ import annotations

from typing import Callable

from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.outbox.relay import OutboxReaperLane, OutboxRelayLane
from sb.kernel.outbox.store import STORE, OutboxStore
from sb.kernel.scheduler.poll import SYSTEM_CLOCK, PollSupervisor

__all__ = ["build_poll_supervisor"]


def build_poll_supervisor(
    *,
    bus,
    lifecycle=None,
    store: OutboxStore = STORE,
    findings: Callable = record_operator_finding,
    clock=SYSTEM_CLOCK,
) -> PollSupervisor:
    """Build the ONE supervisor with the K4 outbox lanes registered.

    `bus` is the event bus port (`async emit(name, **payload)`) — the K8
    band lands the rebuilt EventBus; until then a test double serves.
    `lifecycle` defaults to the sb.kernel.lifecycle module.
    """
    if lifecycle is None:
        from sb.kernel import lifecycle as lifecycle_module

        lifecycle = lifecycle_module
    supervisor = PollSupervisor(lifecycle=lifecycle, clock=clock)
    supervisor.register_lane(OutboxRelayLane(bus=bus, store=store, findings=findings))
    supervisor.register_lane(OutboxReaperLane(store=store))
    return supervisor
