"""The LIVE utility READ adapter — the gateway-cache guild/member census
behind ``sb.domain.utility.service.install_guild_directory`` (the live twin of
the parity harness's ``_WorldGuildDirectory``, sb/adapters/parity/boot.py).
Feeds the shipped read surfaces that walk ``ctx.guild`` / ``member``:
``!serverinfo`` / ``!serverstats`` (guild_info) and the avatar / user-info /
panel member cards (member_info) — READS ONLY, never a mutation.

Cache semantics, stated plainly: every value is the gateway cache's view.
``online_members`` counts ``member.status != offline`` exactly like the
shipped census — without the presence intent every cached member reads
offline (count 0), the same degraded-but-truthful read the capture world
pinned (goldens/admin/sweep_serverstats "Online Members: 0"). ``member_info``
resolves the cache first and falls back to ONE REST ``fetch_member`` for an
uncached member (a read, post-fence — the channel adapters' delegated-member
posture).

READ posture for the fence (the ``DiscordChannelDirectory`` precedent): a
guild other than the allowed test guild — or one not resolvable from cache —
raises ``GuildDirectoryNotInstalled``, EXACTLY the not-armed refusal the
handlers already render politely (``sb/domain/utility/handlers.py`` catches
it per surface), so a non-test guild keeps the pre-arm behavior verbatim.

Import-guarded like its siblings (discord absent in CI containers by design;
this module reads only duck attributes, so no ``discord`` symbol is
required — the guard is not even needed, and the module imports clean).
"""

from __future__ import annotations

import logging

from sb.domain.utility.service import (
    GuildDirectoryNotInstalled,
    GuildInfo,
    MemberInfo,
)

logger = logging.getLogger("sb.adapters.discord.utility_reads")

__all__ = ["DiscordGuildDirectory"]


class DiscordGuildDirectory:
    """The concrete ``GuildDirectory`` over the live gateway cache,
    test-guild-scoped (``allowed_guild_id`` — the same single test-guild
    identity every live effect adapter carries)."""

    def __init__(self, bot, *, allowed_guild_id: int) -> None:
        self._bot = bot
        self._allowed_guild_id = int(allowed_guild_id)

    def _guild(self, guild_id: int):
        # the READ fence: a non-allowed or uncached guild refuses as
        # NOT-ARMED (GuildDirectoryNotInstalled — the polite refusal branch
        # every consuming surface already renders), never a mutation-style
        # hard error.
        if int(guild_id) != self._allowed_guild_id:
            raise GuildDirectoryNotInstalled(
                f"guild directory not armed for guild {guild_id} "
                f"(test-guild fence)")
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            raise GuildDirectoryNotInstalled(
                f"guild {guild_id} is not available in the gateway cache")
        return guild

    async def guild_info(self, guild_id: int) -> GuildInfo:
        guild = self._guild(guild_id)
        members = list(getattr(guild, "members", []) or [])
        bots = sum(1 for m in members if bool(getattr(m, "bot", False)))
        # the shipped census: sum(m.status != offline) — presence-intent
        # dependent; without it every cached member reads offline (0).
        online = sum(1 for m in members
                     if str(getattr(m, "status", "offline")) != "offline")
        return GuildInfo(
            name=str(guild.name),
            owner_id=int(getattr(guild, "owner_id", 0) or 0),
            member_count=int(getattr(guild, "member_count", 0)
                             or len(members)),
            premium_tier=int(getattr(guild, "premium_tier", 0) or 0),
            created_at=guild.created_at,
            text_channels=len(getattr(guild, "text_channels", []) or []),
            voice_channels=len(getattr(guild, "voice_channels", []) or []),
            bots=bots,
            online_members=online,
            roles=len(getattr(guild, "roles", []) or []),
        )

    async def member_info(self, guild_id: int, user_id: int) -> MemberInfo:
        guild = self._guild(guild_id)
        member = guild.get_member(int(user_id))
        if member is None:
            # ONE REST fallback for an uncached member (a read, post-fence).
            member = await guild.fetch_member(int(user_id))
        activity = getattr(member, "activity", None)
        return MemberInfo(
            user_id=int(member.id),
            tag=str(member),
            display_avatar_url=str(
                getattr(member.display_avatar, "url", member.display_avatar)),
            created_at=member.created_at,
            joined_at=member.joined_at,
            status=str(getattr(member, "status", "offline")),
            activity_name=(str(activity.name)
                           if activity is not None
                           and getattr(activity, "name", None) else None),
            is_bot=bool(getattr(member, "bot", False)),
        )
