"""The shared poll infrastructure (frozen L0 spec 09 §3.6).

S5 lands the PORT half: `LaneTickResult` + the `PollLane` protocol — the
shape the K4 outbox relay/reaper lanes implement (spec 08 §3.4; lanes are
AUTHORED at K4, REGISTERED at K5 — F-1/RC-20). S6 (K5) adds `PollSupervisor`
(the ONE supervised loop) to this module and the composition root spawns it.

There is exactly ONE supervisor; lanes never ship their own loop (09 §8
"Poll topology": one PollSupervisor, registered lanes — over "3 loops").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

__all__ = ["LaneTickResult", "PollLane"]


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
