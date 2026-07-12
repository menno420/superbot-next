"""``DiscordModerationActions`` (D-0049 live successor): the LIVE guild-action
adapter behind the moderation EFFECT legs' ``GuildModerationActions`` port
(sb/domain/moderation/service.py). The moderation twin of RC-21's
``DiscordChannelEmitter`` — the domain never touches ``discord``; the
composition root installs this concrete implementation and the not-installed
default raises LOUDLY.

The wire verbs mirror the parity capture twin (sb/adapters/parity/transport.py
``ParityModerationActions``) and the shipped oracle
(disbot/services/moderation_service.py): kick/ban pass a bare snowflake
(``discord.Object``), ban passes ``delete_message_seconds`` ONLY when a purge
window is configured, unban fetches-then-unbans, timeout computes the until
instant off ``discord.utils.utcnow()``. Import-guarded (discord absent in CI
containers by design — the layer fence keeps ``import discord`` inside
sb/adapters/discord/ only).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sb.domain.moderation.service import ModerationReadiness

logger = logging.getLogger("sb.adapters.discord.moderation_actions")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
except ImportError:
    discord = None  # type: ignore[assignment]

__all__ = ["DiscordModerationActions", "DiscordModerationReadinessReader"]


class DiscordModerationActions:
    """The concrete guild-action adapter. ``bot`` duck-types
    ``get_guild``/``fetch_user`` (discord.py ``commands.Bot``)."""

    def __init__(self, bot: object) -> None:
        self._bot = bot

    def _require_discord(self):
        if discord is None:
            raise RuntimeError("discord is not installed")
        return discord

    def _guild(self, guild_id: int):
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            raise RuntimeError(f"guild {guild_id} is not available")
        return guild

    async def _member(self, guild, user_id: int):
        member = guild.get_member(int(user_id))
        if member is None:
            member = await guild.fetch_member(int(user_id))
        return member

    async def timeout_member(self, guild_id: int, user_id: int, *,
                             minutes: int, reason: str) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        member = await self._member(guild, user_id)
        # discord.utils.utcnow() — tz-aware "now" (never bare datetime.now()).
        until = discord.utils.utcnow() + timedelta(minutes=int(minutes))
        await member.timeout(until, reason=reason)

    async def kick_member(self, guild_id: int, user_id: int, *,
                          reason: str) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        await guild.kick(discord.Object(int(user_id)), reason=reason)

    async def ban_member(self, guild_id: int, user_id: int, *, reason: str,
                         delete_message_days: int) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        # Shipped rule (moderation_service.ban / ParityModerationActions):
        # discord.py takes SECONDS; the kwarg is passed ONLY when a purge
        # window is configured (oracle default 0 = no purge, kwarg omitted).
        if int(delete_message_days) > 0:
            await guild.ban(
                discord.Object(int(user_id)), reason=reason,
                delete_message_seconds=int(delete_message_days) * 86400)
        else:
            await guild.ban(discord.Object(int(user_id)), reason=reason)

    async def unban_member(self, guild_id: int, user_id: int, *,
                           reason: str) -> None:
        # Shipped unban: fetch the user THEN unban (a banned user is not in
        # the guild, so guild.unban needs a resolved snowflake — the oracle's
        # bot.fetch_user()→guild.unban() order; goldens/moderation/sweep_unban
        # pins get_user then unban).
        guild = self._guild(guild_id)
        user = await self._bot.fetch_user(int(user_id))
        await guild.unban(user, reason=reason)

    async def fetch_user(self, user_id: int):
        return await self._bot.fetch_user(int(user_id))

    async def dm_member(self, user_id: int, text: str) -> None:
        user = await self._bot.fetch_user(int(user_id))
        await user.send(text)


class DiscordModerationReadinessReader:
    """The LIVE 🤖 Bot-readiness read seam (installed via
    ``install_moderation_readiness``): reads the bot's own moderation
    capability from ``guild.me`` — the byte-for-byte oracle contract
    (disbot/utils/moderation_feasibility.evaluate_moderation_readiness):
    administrator implies every capability, top_role_is_lowest is
    ``top_role.position == 0``. Returns None when the guild (or its bot
    member) is not in cache — the shipped embed DROPS the field then, the
    documented degrade, never a fabricated readiness."""

    def __init__(self, bot: object) -> None:
        self._bot = bot

    async def __call__(self, guild_id: int) -> ModerationReadiness | None:
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            return None
        me = getattr(guild, "me", None)
        if me is None:
            return None
        perms = me.guild_permissions
        admin = bool(perms.administrator)
        top_role = me.top_role
        return ModerationReadiness(
            can_ban=admin or bool(perms.ban_members),
            can_kick=admin or bool(perms.kick_members),
            can_timeout=admin or bool(perms.moderate_members),
            top_role_name=top_role.name,
            top_role_is_lowest=top_role.position == 0,
        )
