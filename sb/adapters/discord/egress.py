"""``DiscordChannelEmitter`` (S11 — spec 10 §2.A/§8.1): the ONLY module that
constructs ``discord.AllowedMentions``, computed from ``(trust,
allow_mentions)`` — UNTRUSTED ⇒ ``AllowedMentions.none()`` + kernel-side
markdown/mention neutralization; TRUSTED/SYSTEM ⇒ the explicit allowlist
ONLY. Import-guarded (discord absent in CI containers by design).
"""

from __future__ import annotations

import logging

from sb.kernel.interaction.egress import (
    EmitResult,
    OutboundContent,
    TrustLevel,
    neutralize_untrusted,
)

logger = logging.getLogger("sb.adapters.discord.egress")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
except ImportError:
    discord = None   # type: ignore[assignment]

__all__ = ["DiscordChannelEmitter", "allowed_mentions_for"]


def allowed_mentions_for(content: OutboundContent):
    """(trust, allow_mentions) → discord.AllowedMentions. The default-deny
    policy: UNTRUSTED always AllowedMentions.none(); TRUSTED/SYSTEM honor
    ONLY the explicit allowlist."""
    if discord is None:
        raise RuntimeError("discord is not installed")
    if content.trust is TrustLevel.UNTRUSTED or not content.allow_mentions:
        return discord.AllowedMentions.none()
    everyone = "everyone" in content.allow_mentions or "here" in content.allow_mentions
    roles = [discord.Object(id=int(t.split(":", 1)[1]))
             for t in content.allow_mentions if t.startswith("role:")]
    users = [discord.Object(id=int(t.split(":", 1)[1]))
             for t in content.allow_mentions if t.startswith("user:")]
    return discord.AllowedMentions(everyone=everyone, roles=roles or False,
                                   users=users or False, replied_user=False)


class DiscordChannelEmitter:
    """The concrete send-egress adapter. ``bot`` duck-types
    ``get_channel``/``fetch_channel``."""

    def __init__(self, bot: object) -> None:
        self._bot = bot

    async def send(self, channel_id: int, content: OutboundContent, *,
                   guild_id: int) -> EmitResult:
        if discord is None:
            return EmitResult(sent=False, error="discord not installed")
        channel = self._bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(channel_id)
            except Exception as exc:  # noqa: BLE001
                return EmitResult(sent=False, error=f"channel unavailable: {exc}")
        body = content.body
        if content.trust is TrustLevel.UNTRUSTED:
            body = neutralize_untrusted(body)
        try:
            message = await channel.send(
                body, allowed_mentions=allowed_mentions_for(content))
        except Exception as exc:  # noqa: BLE001 — the emitter never raises out
            logger.warning("channel send failed (%s)", channel_id, exc_info=True)
            return EmitResult(sent=False, error=str(exc))
        return EmitResult(sent=True, message_id=getattr(message, "id", None))
