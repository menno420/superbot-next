"""The shared poll infrastructure (frozen L0 spec 09 §3.6).

S5 landed the PORT half: `LaneTickResult` + the `PollLane` protocol — the
shape the K4 outbox relay/reaper lanes implement (spec 08 §3.4; lanes are
AUTHORED at K4, REGISTERED at K5 — F-1/RC-20). S6 (K5) adds `PollSupervisor`:
the ONE supervised loop the composition root spawns.

There is exactly ONE supervisor; lanes never ship their own loop (09 §8
"Poll topology": one PollSupervisor, registered lanes — over "3 loops").
ALWAYS-ON: no enablement flag (retires the shipped OFF-by-default spawn).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol, runtime_checkable

logger = logging.getLogger("sb.scheduler.poll")

__all__ = ["LaneTickResult", "PollLane", "PollSupervisor", "SYSTEM_CLOCK"]


def SYSTEM_CLOCK() -> datetime:
    """The default clock: timezone-aware UTC now."""
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True)
class LaneTickResult:
    """What one lane cycle did (spec 09 §3.6)."""

    lane: str
    claimed: int
    fired: int
    failed: int
    skipped: int


@runtime_checkable
class PollLane(Protocol):
    """The lane port. The supervisor owns the loop/cadence/readiness gate
    and per-lane exception isolation; the lane owns what one cycle does."""

    name: str

    async def tick(self, now: datetime) -> LaneTickResult:
        """Claim + process one cycle's due work."""
        ...

    async def reconcile_on_boot(self, now: datetime) -> None:
        """One-time overdue catch-up after RUNNING (default no-op)."""
        ...


class PollSupervisor:
    """The ONE supervised poll loop (spec 09 §3.6).

    - waits for lifecycle RUNNING before the FIRST reconcile_on_boot
      (vocab §⑤.5 ready-gate: never poll a DB the /ready gate would 503);
    - each tick: if NOT lifecycle.can_accept_commands() (DRAINING) the
      cycle skips claiming entirely (drain gate, vocab §⑤.2);
    - per-lane exception isolation: a lane raising is caught + logged and
      the loop continues (the shipped supervised pattern).

    `lifecycle` is the K5 lifecycle port — any object/module exposing
    `get_phase()` and `can_accept_commands()` (sb.kernel.lifecycle fits).
    """

    def __init__(self, *, lifecycle, clock: Callable[[], datetime] = SYSTEM_CLOCK) -> None:
        self._lifecycle = lifecycle
        self._clock = clock
        self._lanes: list[PollLane] = []

    def register_lane(self, lane: PollLane) -> None:
        """Composition root registers DueQueueLane + ExpiryJanitorLane +
        OutboxRelayLane + OutboxReaperLane (roster non-exhaustive)."""
        if any(existing.name == lane.name for existing in self._lanes):
            raise ValueError(f"lane {lane.name!r} already registered")
        self._lanes.append(lane)

    @property
    def lane_names(self) -> tuple[str, ...]:
        return tuple(lane.name for lane in self._lanes)

    async def run_forever(self, *, poll_interval_s: float = 5) -> None:
        """Spawned by the K5 task supervisor as ONE supervised task."""
        from sb.kernel.lifecycle import Phase  # the frozen phase vocabulary

        # Ready-gate: NO lane work — neither reconcile_on_boot nor tick —
        # until lifecycle RUNNING (spec 08 §3.4 step 0 relies on this).
        while self._lifecycle.get_phase() is not Phase.RUNNING:
            if self._lifecycle.get_phase() in (
                Phase.STOPPED, Phase.FAILED_STARTUP,
            ):
                return  # terminal before RUNNING: nothing to poll, ever
            await asyncio.sleep(min(0.2, poll_interval_s))

        now = self._clock()
        for lane in self._lanes:
            try:
                await lane.reconcile_on_boot(now)
            except Exception:  # noqa: BLE001 — per-lane isolation
                logger.exception("lane %s reconcile_on_boot raised", lane.name)

        while True:
            if self._lifecycle.can_accept_commands():
                await self.tick_once()
            await asyncio.sleep(poll_interval_s)

    async def tick_once(self) -> list[LaneTickResult]:
        """One supervised cycle over every lane (isolated); test seam."""
        results: list[LaneTickResult] = []
        now = self._clock()
        for lane in self._lanes:
            try:
                results.append(await lane.tick(now))
            except Exception:  # noqa: BLE001 — per-lane isolation
                logger.exception("lane %s tick raised; loop continues", lane.name)
        return results
