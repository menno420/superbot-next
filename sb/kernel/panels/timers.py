"""One-shot in-process timers (the K8 panels band's real-time sidecar —
docs/decisions.md D-0090).

The sanctioned lane for SUB-SECOND real-time work that must land on a live
Discord surface — the fishing minigame's unprompted bite/fake-out/got-away
panel edits (``push_session_refresh``), the oracle's ``asyncio.sleep`` +
``message.edit`` background tasks made a supervised utility. Deliberately
NOT the S10 scheduler due-queue: that lane polls at 5 s granularity behind
the pure-DB fence (scheduler fires may not produce Discord output), both
of which structurally rule out a 4-second bite cue.

Posture (mirrors the shipped ``core.runtime.tasks.spawn`` supervision):

* **process-local** — a restart loses every armed timer, exactly the
  shipped game views' in-memory state (ADR-002, accepted for game views);
* **exception-contained** — a callback that raises is logged and never
  takes the loop down (the PollSupervisor's per-lane isolation posture);
* **cancel-safe** — ``cancel()`` is idempotent; a timer cancelled while
  sleeping (or at loop shutdown — ``asyncio.run`` cancels pending tasks)
  simply never fires.

Headless/parity: callers may arm timers freely — the parity harness runs
on the LOGICAL clock, so wall-clock timers never fire inside a driven
case, and their panel edits would no-op via ``EDIT_UNAVAILABLE`` anyway
(the uninstalled-editor degradation); the domain cancels armed timers in
its per-case state reset.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger("sb.kernel.panels.timers")

__all__ = ["OneShotTimer", "schedule"]


class OneShotTimer:
    """A handle on one scheduled callback."""

    __slots__ = ("_task",)

    def __init__(self, task: asyncio.Task) -> None:
        self._task = task

    def cancel(self) -> None:
        """Stop the timer if it has not fired yet (idempotent)."""
        self._task.cancel()

    @property
    def done(self) -> bool:
        """True once the callback finished, failed, or was cancelled."""
        return self._task.done()


def schedule(delay_s: float, callback: Callable[[], Awaitable[object]], *,
             name: str = "") -> OneShotTimer:
    """Run async *callback* once, *delay_s* seconds from now, on the
    RUNNING event loop (callers are async — there always is one). The
    returned handle's ``cancel()`` disarms it. A callback exception is
    logged via the observability logger and contained; cancellation
    (explicit or loop-shutdown) is silent."""

    async def _fire() -> None:
        try:
            await asyncio.sleep(max(0.0, float(delay_s)))
            await callback()
        except asyncio.CancelledError:
            raise                       # a cancelled timer just never fires
        except Exception:  # noqa: BLE001 — containment IS the contract
            logger.exception(
                "one-shot timer %r callback failed",
                name or getattr(callback, "__qualname__", "?"))

    task = asyncio.get_running_loop().create_task(
        _fire(), name=name or "sb-oneshot-timer")
    return OneShotTimer(task)
