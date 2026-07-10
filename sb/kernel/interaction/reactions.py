"""The REACTION ingress seam (band 6) — the kernel half of the
reaction-adapter gap named by every tournament ledger
(docs/ideas/reaction-adapter-seam-2026-07-10.md): raw reaction add/remove
events → a registry of named domain consumers.

Mirrors the message feed's layering: the live adapter
(sb/adapters/discord/reaction_feed.py) listens on the gateway and calls
:func:`dispatch_reaction`; domains register consumers at MODULE IMPORT
(declaring IS reserving — the same composition-parity rule the handler
tables follow) so the live root and the replay root see one roster.

The kernel owns the registry, not the consumers: the shipped oracle's
reaction surfaces (RPS/blackjack tournament sign-up, starboard,
reaction-roles, the AI-review 👎 listeners) are independent domains; this
seam is the shared substrate they bind to, so each consumer PR stays
pure-domain.

Dispatch NEVER raises — a consumer fault is logged and the loop continues
(the feed must never break the gateway task), exactly the message feed's
posture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger("sb.kernel.interaction.reactions")

__all__ = [
    "ReactionEvent",
    "dispatch_reaction",
    "register_reaction_consumer",
    "registered_reaction_consumers",
    "reset_reaction_consumers_for_tests",
]


@dataclass(frozen=True)
class ReactionEvent:
    """One raw reaction add/remove, duck-shaped off the gateway payload
    (no discord import — the adapter builds it from RawReactionActionEvent)."""

    guild_id: int
    channel_id: int
    message_id: int
    user_id: int
    emoji: str
    added: bool = True
    #: the raw member object when the gateway provides one (add events in
    #: guilds); consumers must treat it as optional.
    member: object | None = None


ReactionConsumer = Callable[[ReactionEvent], Awaitable[None]]

_consumers: dict[str, ReactionConsumer] = {}


def register_reaction_consumer(name: str, consumer: ReactionConsumer) -> None:
    """Claim *name* with a consumer. Idempotent re-registration (the
    ENSURE_REFS re-arm) is a no-op for the same name; a DIFFERING second
    claim overwrites deliberately — module reload semantics, the consumer
    is looked up by name at dispatch time."""
    _consumers[name] = consumer


def registered_reaction_consumers() -> tuple[str, ...]:
    return tuple(sorted(_consumers))


def reset_reaction_consumers_for_tests() -> None:
    _consumers.clear()


async def dispatch_reaction(event: ReactionEvent) -> int:
    """Fan one reaction event out to every registered consumer. Returns the
    count of consumers that ran clean; faults are logged, never raised."""
    ran = 0
    for name, consumer in list(_consumers.items()):
        try:
            await consumer(event)
            ran += 1
        except Exception:  # noqa: BLE001 — the feed never breaks the loop
            logger.warning("reaction consumer %r faulted", name,
                           exc_info=True)
    return ran
