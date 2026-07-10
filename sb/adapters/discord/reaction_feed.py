"""The live REACTION FEED adapter — gateway raw reaction events → the
kernel reaction seam (sb/kernel/interaction/reactions.py).

Mirrors message_feed.py's shape: duck-typed against discord.py (no discord
import — payloads arrive from the gateway at runtime), additive listener
registration (``bot.add_listener``), and the never-raise posture (a
dispatch fault is logged; the gateway task survives).

Shipped old-bot contract carried verbatim: bot-authored reactions are
ignored before anything else (the oracle's ``on_reaction_add`` guard
``if user.bot: return`` — the bot's own ✅ primer on a registration
message must never sign the bot up). RAW events are used (the oracle's
newer cogs' ``on_raw_reaction_add`` posture) so reactions on uncached
messages still dispatch after a restart.

The reactions gateway intent is NON-privileged (Intents.default() carries
it — sb/adapters/discord/gateway.build_intents), so this feed arms
unconditionally; a guild-level intent misconfiguration degrades to "no
events", which the consumers already treat as silence.
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.reactions import ReactionEvent, dispatch_reaction

logger = logging.getLogger("sb.adapters.discord.reaction_feed")

__all__ = ["arm_reaction_feed", "handle_raw_reaction"]


def _event_from_payload(payload: object, *, added: bool) -> ReactionEvent:
    emoji = getattr(payload, "emoji", None)
    return ReactionEvent(
        guild_id=int(getattr(payload, "guild_id", 0) or 0),
        channel_id=int(getattr(payload, "channel_id", 0) or 0),
        message_id=int(getattr(payload, "message_id", 0) or 0),
        user_id=int(getattr(payload, "user_id", 0) or 0),
        emoji=str(getattr(emoji, "name", "") or emoji or ""),
        added=added,
        member=getattr(payload, "member", None),
    )


async def handle_raw_reaction(payload: object, *, bot_user_id: int | None,
                              added: bool) -> int | None:
    """One raw reaction event through the kernel seam. Returns the consumer
    count, or None when the event is ignored (bot/self reactor)."""
    member = getattr(payload, "member", None)
    if member is not None and bool(getattr(member, "bot", False)):
        return None                       # shipped guard: bots never sign up
    user_id = int(getattr(payload, "user_id", 0) or 0)
    if bot_user_id is not None and user_id == int(bot_user_id):
        return None                       # the bot's own ✅ primer
    try:
        return await dispatch_reaction(_event_from_payload(payload,
                                                           added=added))
    except Exception:  # noqa: BLE001 — the feed never breaks the event loop
        logger.warning("reaction dispatch fault", exc_info=True)
        return None


def arm_reaction_feed(bot: object) -> None:
    """Register the raw reaction listeners (additive — never replaces the
    Bot's own events)."""

    def _bot_user_id() -> int | None:
        user = getattr(bot, "user", None)
        uid = getattr(user, "id", None)
        return int(uid) if uid is not None else None

    async def on_raw_reaction_add(payload: object) -> None:
        await handle_raw_reaction(payload, bot_user_id=_bot_user_id(),
                                  added=True)

    async def on_raw_reaction_remove(payload: object) -> None:
        await handle_raw_reaction(payload, bot_user_id=_bot_user_id(),
                                  added=False)

    bot.add_listener(on_raw_reaction_add, "on_raw_reaction_add")
    bot.add_listener(on_raw_reaction_remove, "on_raw_reaction_remove")
