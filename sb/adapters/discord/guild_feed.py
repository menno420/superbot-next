"""The live GUILD-JOIN FEED adapter — the gateway ``on_guild_join``
event → the kernel guild-events seam
(sb/kernel/interaction/guild_events.py).

Mirrors reaction_feed.py's shape: duck-typed against discord.py (no
discord import — the guild object arrives from the gateway at runtime),
additive listener registration (``bot.add_listener``), and the
never-raise posture (a dispatch fault is logged; the gateway task
survives).

The guilds gateway intent is NON-privileged (``Intents.default()``
carries ``guilds`` — sb/adapters/discord/gateway.build_intents), so this
feed arms unconditionally; a misconfiguration degrades to "no events",
which the consumers already treat as silence.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.guild_events import (
    GuildJoinEvent,
    dispatch_guild_join,
)

logger = logging.getLogger("sb.adapters.discord.guild_feed")

__all__ = ["arm_guild_join_feed", "handle_gateway_guild_join"]


def _event_from_guild(guild: object) -> GuildJoinEvent:
    system = getattr(guild, "system_channel", None)
    system_id = getattr(system, "id", None)
    return GuildJoinEvent(
        guild_id=int(getattr(guild, "id", 0) or 0),
        guild_name=str(getattr(guild, "name", "") or ""),
        owner_id=int(getattr(guild, "owner_id", 0) or 0),
        system_channel_id=int(system_id) if system_id is not None else None,
    )


async def handle_gateway_guild_join(guild: object) -> int | None:
    """One gateway join through the kernel seam. Returns the consumer
    count, or None when the event could not be dispatched."""
    try:
        return await dispatch_guild_join(_event_from_guild(guild))
    except Exception:  # noqa: BLE001 — the feed never breaks the event loop
        logger.warning("guild-join dispatch fault", exc_info=True)
        return None


def arm_guild_join_feed(bot: object) -> None:
    """Register the guild-join listener (additive — never replaces the
    Bot's own events)."""

    async def on_guild_join(guild: object) -> None:
        await handle_gateway_guild_join(guild)

    bot.add_listener(on_guild_join, "on_guild_join")
