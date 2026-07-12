"""The LIVE role adapters (SLICE 2 of the live-guild-effects lane; the role
twin of ``DiscordModerationActions``, D-0049). Three concrete ports the
composition root installs behind the role EFFECT legs
(sb/domain/role/service.py) — the domain never touches ``discord``, and the
not-installed defaults keep raising LOUDLY (an EFFECT-leg failure classifies
as PARTIAL + operator finding, never a silent success):

- ``DiscordGuildRoleActions`` (``GuildRoleActions``) — add/remove a role on a
  member (``member.add_roles`` / ``member.remove_roles`` with a bare
  ``discord.Object`` snowflake; the shipped reaction-role + temp-grant +
  level-role lanes).
- ``DiscordRoleProvisioning`` (``RoleProvisioning``) — create/delete a guild
  role (``guild.create_role`` → ``role.delete``; the !createrole/!deleterole
  lanes). The port method is ``create_guild_role``; the captured wire verb is
  ``create_role`` (goldens/role/sweep_createrole) — the A-5 fence, method name
  and wire verb differ ON PURPOSE, do not reconcile.
- ``DiscordRoleMessageOps`` (``MessageOps``) — fetch a message + add a
  reaction for the reaction-role bind flow (``channel.fetch_message`` →
  ``message.add_reaction``; goldens/role/sweep_reactroles).

The wire verbs mirror the parity capture twins (sb/adapters/parity/transport.py
``ParityRoleProvisioning`` / ``ParityRoleMessageOps``). Import-guarded (discord
absent in CI containers by design — the layer fence keeps ``import discord``
inside sb/adapters/discord/ only). The hard test-guild allow-list
(``GuildNotAllowedError`` reused from moderation_actions) is raised BEFORE any
Discord call when a resolvable guild is not the single allowed test guild — the
bot still holds the PRODUCTION gateway token, so ``SB_DATA_PLANE=test`` alone
(DB protection) could otherwise mutate a real guild's roles/members. For the
channel-scoped MessageOps the guild is resolved from the channel's cache entry;
a channel whose guild is NOT the allowed test guild (or is not resolvable from
cache at all — a DM channel, or an uncached prod channel) is REFUSED, so a
reaction-role bind can never touch a production message.
"""

from __future__ import annotations

import logging

from sb.adapters.discord.moderation_actions import GuildNotAllowedError

logger = logging.getLogger("sb.adapters.discord.role_actions")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
except ImportError:
    discord = None  # type: ignore[assignment]

__all__ = [
    "DiscordGuildRoleActions",
    "DiscordRoleMessageOps",
    "DiscordRoleProvisioning",
    "GuildNotAllowedError",
]


class _GuildAllowList:
    """Shared base: ``bot`` duck-types ``get_guild`` (discord.py
    ``commands.Bot``); ``allowed_guild_id`` is the SINGLE test guild every
    guild-scoped effect may mutate — a hard per-call allow-list refusing any
    other guild BEFORE a single Discord call (the moderation-actions posture)."""

    def __init__(self, bot: object, *, allowed_guild_id: int) -> None:
        self._bot = bot
        self._allowed_guild_id = int(allowed_guild_id)

    def _require_discord(self):
        if discord is None:
            raise RuntimeError("discord is not installed")
        return discord

    def _guild(self, guild_id: int):
        # HARD test-guild allow-list — refuse ANY non-allowed guild before a
        # single Discord call touches a role or member.
        if int(guild_id) != self._allowed_guild_id:
            raise GuildNotAllowedError(guild_id, self._allowed_guild_id)
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            raise RuntimeError(f"guild {guild_id} is not available")
        return guild


class DiscordGuildRoleActions(_GuildAllowList):
    """The concrete ``GuildRoleActions`` adapter (add/remove a role on a
    member). Guild-scoped → the test-guild allow-list gates every call."""

    async def _member(self, guild, member_id: int):
        member = guild.get_member(int(member_id))
        if member is None:
            member = await guild.fetch_member(int(member_id))
        return member

    async def add_role(self, guild_id: int, member_id: int, role_id: int,
                       *, reason: str) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        member = await self._member(guild, member_id)
        # a bare snowflake (discord.Object) — no cached-Role round-trip needed.
        await member.add_roles(discord.Object(int(role_id)), reason=reason)

    async def remove_role(self, guild_id: int, member_id: int, role_id: int,
                          *, reason: str) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        member = await self._member(guild, member_id)
        await member.remove_roles(discord.Object(int(role_id)), reason=reason)


class DiscordRoleProvisioning(_GuildAllowList):
    """The concrete ``RoleProvisioning`` adapter (create/delete a guild role).
    Guild-scoped → the test-guild allow-list gates every call. NOTE the A-5
    fence: the port method is ``create_guild_role`` but the shipped/captured
    wire verb is discord.py's ``guild.create_role`` (goldens/role/
    sweep_createrole) — the name split is intentional, not a rename."""

    async def create_guild_role(self, guild_id: int, *, name: str, color: int,
                                reason: str | None) -> int:
        discord = self._require_discord()
        guild = self._guild(guild_id)
        # discord.py 2.x ``Guild.create_role`` — ``colour`` takes a
        # discord.Colour off the raw int (the capture twin recorded the same
        # value under the 2.x ``colors.primary_color`` body key). Returns the
        # created Role; the port hands back its snowflake id.
        role = await guild.create_role(
            name=name, colour=discord.Colour(int(color)), reason=reason)
        return int(role.id)

    async def delete_role(self, guild_id: int, role_id: int, *,
                          reason: str | None) -> None:
        self._require_discord()
        guild = self._guild(guild_id)
        # resolve the cached Role (the shipped !deleterole rode a RoleConverter
        # — a cache read, never a REST fetch); a vanished role is an honest
        # loud failure (the not-installed-port posture), never a silent no-op.
        role = guild.get_role(int(role_id))
        if role is None:
            raise RuntimeError(
                f"role {role_id} is not available in guild {guild_id}")
        await role.delete(reason=reason)


class DiscordRoleMessageOps(_GuildAllowList):
    """The concrete ``MessageOps`` adapter (fetch a message + add a reaction)
    for the reaction-role bind flow. CHANNEL-scoped: the guild is resolved
    from the channel's CACHE entry (never a REST fetch — resolving via REST
    would touch a possibly-prod channel before the allow-list runs), and the
    allow-list is applied where a guild is resolvable. A channel whose guild
    is not the allowed test guild — or is not resolvable from cache at all (a
    DM channel, an uncached channel) — is REFUSED, so a reaction-role bind
    stays test-guild-only and can never react to a production message."""

    def _channel(self, channel_id: int):
        # cache-only resolve — no Discord call before the allow-list runs.
        channel = self._bot.get_channel(int(channel_id))
        # a resolvable guild is checked against the allow-list; an
        # unresolvable one (guild is None → id 0) can never equal the allowed
        # test guild, so it is REFUSED here, BEFORE any Discord call.
        guild = getattr(channel, "guild", None)
        guild_id = int(getattr(guild, "id", 0) or 0)
        if guild_id != self._allowed_guild_id:
            raise GuildNotAllowedError(guild_id, self._allowed_guild_id)
        if channel is None:  # pragma: no cover — guild check already refused
            raise RuntimeError(f"channel {channel_id} is not available")
        return channel

    async def fetch_message(self, channel_id: int, message_id: int) -> None:
        self._require_discord()
        channel = self._channel(channel_id)
        # mirrors the oracle's ctx.fetch_message(message_id) existence read
        # (captured as get_message); the port returns None (the bind flow adds
        # the reaction through add_reaction below, a separate call).
        await channel.fetch_message(int(message_id))

    async def add_reaction(self, channel_id: int, message_id: int,
                           emoji: str) -> None:
        self._require_discord()
        channel = self._channel(channel_id)
        message = await channel.fetch_message(int(message_id))
        await message.add_reaction(emoji)
