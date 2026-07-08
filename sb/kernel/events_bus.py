"""The in-process EventBus (K8-adjacent composition primitive).

The minimal named-event bus the outbox relay (`OutboxRelayLane`), the
workflow engine's `BestEffortBatch`, and the dispatch trace emit over —
rebuilt from the shipped bus semantics: `on(name, handler)` subscription,
`emit(name, **payload)` with PER-HANDLER error isolation (one failing
subscriber never blocks the others or the emitter). `event_emitted=True`
means publish-accepted, not delivered (§2.8 honesty).

The composition root constructs ONE bus and threads it into
`build_poll_supervisor(bus=…)`, `workflow.engine.install_bus(bus)`, and
`interaction.trace.install_trace_bus(bus)`.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Awaitable, Callable

logger = logging.getLogger("sb.kernel.events_bus")

__all__ = ["EventBus"]

Handler = Callable[..., Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    def subscribers(self, event_name: str) -> tuple[Handler, ...]:
        return tuple(self._handlers.get(event_name, ()))

    async def emit(self, event_name: str, **payload: object) -> int:
        """Deliver to every subscriber; per-handler isolation. Returns the
        count of handlers that completed without raising."""
        delivered = 0
        for handler in self._handlers.get(event_name, ()):
            try:
                out = handler(**payload)
                if hasattr(out, "__await__"):
                    await out
                delivered += 1
            except Exception:  # noqa: BLE001 — isolation is the contract
                logger.exception("bus handler for %r failed", event_name)
        return delivered
