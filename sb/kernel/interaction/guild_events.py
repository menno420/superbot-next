"""The GUILD-JOIN ingress seam — the kernel half of the on-guild-join
feed (the night-tail-2 launcher port): the gateway ``GUILD_CREATE`` join
event → a registry of named domain consumers.

Mirrors the reaction seam's layering (sb/kernel/interaction/reactions.py):
the live adapter (sb/adapters/discord/guild_feed.py) listens on the
gateway and calls :func:`dispatch_guild_join`; domains register consumers
at MODULE IMPORT (declaring IS reserving — the same composition-parity
rule the handler tables follow) so the live root and any replay root see
one roster.

The kernel owns the registry, not the consumers: the shipped oracle's
join surfaces (the setup launcher post — disbot/cogs/setup_cog.py
``on_guild_join``; the economy log-channel ensure —
disbot/cogs/economy_cog.py ``on_guild_join``) are independent domains;
this seam is the shared substrate they bind to, so each consumer PR
stays pure-domain.

Dispatch NEVER raises — a consumer fault is logged and the loop continues
(the feed must never break the gateway task), exactly the reaction feed's
posture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger("sb.kernel.interaction.guild_events")

__all__ = [
    "GuildJoinEvent",
    "dispatch_guild_join",
    "register_guild_join_consumer",
    "registered_guild_join_consumers",
    "reset_guild_join_consumers_for_tests",
]


@dataclass(frozen=True)
class GuildJoinEvent:
    """One guild join, duck-shaped off the gateway guild object (no
    discord import — the adapter builds it from ``discord.Guild``)."""

    guild_id: int
    guild_name: str = ""
    #: ``guild.owner_id`` — 0 when the gateway did not carry it.
    owner_id: int = 0
    #: ``guild.system_channel.id`` — the fallback ladder's first rung
    #: (None when the guild has none / the cache lacks it).
    system_channel_id: int | None = None


GuildJoinConsumer = Callable[[GuildJoinEvent], Awaitable[None]]

_consumers: dict[str, GuildJoinConsumer] = {}


def register_guild_join_consumer(name: str,
                                 consumer: GuildJoinConsumer) -> None:
    """Claim *name* with a consumer. Idempotent re-registration (the
    ENSURE_REFS re-arm) is a no-op for the same name; a DIFFERING second
    claim overwrites deliberately — module reload semantics, the consumer
    is looked up by name at dispatch time (the reaction-registry
    contract, verbatim)."""
    _consumers[name] = consumer


def registered_guild_join_consumers() -> tuple[str, ...]:
    return tuple(sorted(_consumers))


def reset_guild_join_consumers_for_tests() -> None:
    _consumers.clear()


async def dispatch_guild_join(event: GuildJoinEvent) -> int:
    """Fan one join event out to every registered consumer. Returns the
    count of consumers that ran clean; faults are logged, never raised."""
    ran = 0
    for name, consumer in list(_consumers.items()):
        try:
            await consumer(event)
            ran += 1
        except Exception:  # noqa: BLE001 — the feed never breaks the loop
            logger.warning("guild-join consumer %r faulted", name,
                           exc_info=True)
    return ran
