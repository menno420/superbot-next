"""The LIVE channel adapters (SLICE 3 of the live-guild-effects lane; the
channel/proof twin of ``DiscordModerationActions`` (SLICE 1, D-0049) and the
role adapters (SLICE 2)). Concrete implementations of TWO SEPARATE ports the
composition root installs behind the channel EFFECT legs — the domains never
touch ``discord``, and the not-installed defaults keep raising LOUDLY (an
EFFECT-leg failure classifies as PARTIAL + operator finding, never a silent
success):

- ``DiscordChannelStateActions`` (``ChannelStateActions``,
  sb/domain/channel/service.py) — the shipped ``ChannelLifecycleService``
  Discord edits + the ``!invite`` re-home:
  - ``set_slowmode`` → ``channel.edit(slowmode_delay=…)`` (wire ``edit_channel``
    with ``rate_limit_per_user``).
  - ``set_overwrite`` → ``channel.set_permissions(target, overwrite=…)`` (wire
    ``edit_channel_permissions`` — the target is resolved role/member; the int
    convention is ``target_type`` 0 = role, 1 = member, per the
    ``ChannelOverwrite`` docstring).
  - ``create_text_channel`` → ``guild.create_text_channel(…)`` (wire
    ``create_channel`` — overwrites ride AT creation; returns the new id).
    ALWAYS creates: get-before-create is DOMAIN logic (D-0077).
  - ``delete_channel`` → ``channel.delete(…)`` (wire ``delete_channel``); a
    live delete treats ``discord.NotFound`` as SUCCESS (already-gone is the
    goal state — the oracle's ``delete_setup_channel``, D-0077).
  - ``create_invite`` → ``channel.create_invite(…)`` (wire ``create_invite``);
    returns the minted invite URL. (The parity twin RAISES
    ``CaptureInviteParseError`` — a CAPTURE-WORLD artifact only; a live invite
    adapter simply does not raise.)

- ``DiscordProofChannelActions`` (``ChannelPermActions``,
  sb/domain/proof_channel/service.py — a SEPARATE port from the channel
  domain, NOT to be conflated) — the shipped ``proof_channel_cog`` prize-access
  lock/unlock, each a bulk ``channel.edit(overwrites=…)`` (wire
  ``edit_channel``): ``lock_channel_for_winner`` grants the winner
  view+send while hiding the channel from ``@everyone`` (keeping the bot
  visible); ``unlock_channel`` restores read-only-for-everyone.

- ``DiscordChannelLookup`` — the live channel NAME lookup (the shipped
  ``TextChannelConverter`` gateway-cache name leg) behind
  ``install_channel_lookup``; test-guild-scoped (any other guild resolves to
  ``None``, a read never mutates).

Import-guarded (discord absent in CI containers by design — the layer fence
keeps ``import discord`` inside sb/adapters/discord/ only). The hard test-guild
allow-list (``GuildNotAllowedError`` + ``_GuildAllowList`` reused from
moderation_actions / role_actions) is raised BEFORE any Discord call: the bot
still holds the PRODUCTION gateway token, so ``SB_DATA_PLANE=test`` alone (DB
protection) could otherwise mutate a real guild's channels. For the
channel-scoped methods (only ``channel_id``, no ``guild_id``) the guild is
resolved from the channel's CACHE entry (``bot.get_channel``, never a REST
fetch) and an unresolvable-guild channel — a DM, an uncached prod channel — is
REFUSED, EXACTLY the cache-only fence SLICE 2's MessageOps used (keeps the
"before any Discord call" fence honest). For the guild_id-carrying methods
(``create_text_channel``, the two proof_channel methods) the allow-list is
checked directly.
"""

from __future__ import annotations

import logging

from sb.adapters.discord.moderation_actions import GuildNotAllowedError
from sb.adapters.discord.role_actions import _GuildAllowList

logger = logging.getLogger("sb.adapters.discord.channel_actions")

try:  # pragma: no cover — discord is absent in CI containers by design
    import discord
except ImportError:
    discord = None  # type: ignore[assignment]

__all__ = [
    "DiscordChannelLookup",
    "DiscordChannelStateActions",
    "DiscordProofChannelActions",
    "GuildNotAllowedError",
]


class _ChannelGuildAllowList(_GuildAllowList):
    """Reuses the shared ``_GuildAllowList`` base (constructor) but overrides
    ``_require_discord`` to guard THIS module's ``discord`` symbol (the base's
    guards role_actions' — each adapter module carries its own import-guarded
    reference) and ``_guild`` to raise with THIS lane's ``effect`` word (the
    base hardcodes ``effect="role"``; ``_effect`` names the effect domain so a
    refusal echoes "channel effect REFUSED" / "proof_channel effect REFUSED",
    surfaced verbatim at the channel handlers, not the role/moderation copy)."""

    #: the effect-domain word this adapter's refusals carry (overridden per
    #: port — proof_channel below).
    _effect = "channel"

    def _require_discord(self):
        if discord is None:
            raise RuntimeError("discord is not installed")
        return discord

    def _guild(self, guild_id: int):
        # HARD test-guild allow-list — refuse ANY non-allowed guild before a
        # single Discord call. effect=self._effect so the refusal copy reads
        # this lane's domain word (not the base's role default).
        if int(guild_id) != self._allowed_guild_id:
            raise GuildNotAllowedError(guild_id, self._allowed_guild_id,
                                       effect=self._effect)
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            raise RuntimeError(f"guild {guild_id} is not available")
        return guild


class _ChannelAllowList(_ChannelGuildAllowList):
    """Adds the CHANNEL-scoped cache-only fence to the shared
    ``_GuildAllowList`` base (SLICE 2's MessageOps posture): a channel is
    resolved from the gateway CACHE (never a REST fetch — resolving via REST
    would touch a possibly-prod channel before the allow-list runs), and a
    channel whose guild is not the allowed test guild — or is not resolvable
    from cache at all (a DM channel, an uncached channel) — is REFUSED here,
    BEFORE any Discord call."""

    def _channel(self, channel_id: int):
        # cache-only resolve — no Discord call before the allow-list runs.
        channel = self._bot.get_channel(int(channel_id))
        # a resolvable guild is checked against the allow-list; an
        # unresolvable one (guild is None → id 0) can never equal the allowed
        # test guild, so it is REFUSED here, BEFORE any Discord call.
        guild = getattr(channel, "guild", None)
        guild_id = int(getattr(guild, "id", 0) or 0)
        if guild_id != self._allowed_guild_id:
            raise GuildNotAllowedError(guild_id, self._allowed_guild_id,
                                       effect=self._effect)
        if channel is None:  # pragma: no cover — guild check already refused
            raise RuntimeError(f"channel {channel_id} is not available")
        return channel

    async def _overwrite_target(self, guild, target_id: int,
                                target_type: int):
        # int convention (ChannelOverwrite docstring): 0 = role, 1 = member.
        # set_permissions / create_text_channel need a real Role/Member object
        # (a bare snowflake carries no role-vs-member type).
        if int(target_type) == 0:
            target = guild.get_role(int(target_id))
        else:
            # member overwrites: cache first, then a REST fetch_member fallback
            # (the proof adapter's _member posture, safely post-fence). setup
            # builds member-typed entries for the bot/invoker/delegated members
            # (sb/domain/setup/service.py) — a delegated/uncached member must
            # not break the create the oracle (Member in hand) succeeded at.
            target = guild.get_member(int(target_id))
            if target is None:
                target = await guild.fetch_member(int(target_id))
        if target is None:
            raise RuntimeError(
                f"overwrite target {target_id} (type {target_type}) is not "
                f"available in guild {getattr(guild, 'id', '?')}")
        return target

    def _pair_overwrite(self, allow: int, deny: int):
        return discord.PermissionOverwrite.from_pair(
            discord.Permissions(int(allow)), discord.Permissions(int(deny)))

    @staticmethod
    def _as_runtime(exc: Exception) -> RuntimeError:
        # translate a live Discord HTTP failure (Forbidden/NotFound/rate-limit/
        # …) to RuntimeError so the shipped `❌ Could not …: {exc}` branch
        # renders — the channel handlers catch RuntimeError, not the
        # discord.HTTPException family (the role slice's translate-in-adapter
        # posture, role_actions fetch_message → LookupError).
        return RuntimeError(str(exc))


class DiscordChannelStateActions(_ChannelAllowList):
    """The concrete ``ChannelStateActions`` adapter. ``set_slowmode`` /
    ``set_overwrite`` / ``delete_channel`` / ``create_invite`` are
    CHANNEL-scoped (cache-only fence); ``create_text_channel`` is guild-scoped
    (the test-guild allow-list is checked directly)."""

    async def set_slowmode(self, channel_id: int, *, seconds: int,
                           reason: str | None) -> None:
        discord = self._require_discord()
        channel = self._channel(channel_id)
        # discord.py TextChannel.edit(slowmode_delay=…) → the HTTP layer's
        # edit_channel PATCH carrying rate_limit_per_user (the parity twin's
        # wire verb; goldens/channel/sweep_slowmode).
        try:
            await channel.edit(slowmode_delay=int(seconds), reason=reason)
        except discord.HTTPException as exc:
            raise self._as_runtime(exc) from exc

    async def set_overwrite(self, channel_id: int, *, target_id: int,
                            allow: int, deny: int, target_type: int,
                            reason: str | None) -> None:
        discord = self._require_discord()
        channel = self._channel(channel_id)
        # the guild is the SAME cache entry the fence resolved on — resolve the
        # overwrite target off it (role vs member per target_type), then
        # set_permissions → the edit_channel_permissions PUT (the parity twin's
        # wire verb; goldens/channel/sweep_lock + sweep_unlock).
        guild = channel.guild
        target = await self._overwrite_target(guild, target_id, target_type)
        try:
            await channel.set_permissions(
                target, overwrite=self._pair_overwrite(allow, deny),
                reason=reason)
        except discord.HTTPException as exc:
            raise self._as_runtime(exc) from exc

    async def create_text_channel(
            self, guild_id: int, *, name: str,
            overwrites: tuple, parent_id: int | None,
            reason: str | None) -> int:
        self._require_discord()
        guild = self._guild(guild_id)  # guild-scoped → allow-list direct
        # map the ChannelOverwrite tuple → discord's {target: PermissionOverwrite}
        # (the overwrites ride AT creation — the oracle's
        # guild_resources.ensure_channel create path; wire verb create_channel).
        overwrite_map = {}
        for ow in overwrites:
            target = await self._overwrite_target(
                guild, ow.target_id, ow.target_type)
            overwrite_map[target] = self._pair_overwrite(ow.allow, ow.deny)
        category = (guild.get_channel(int(parent_id))
                    if parent_id is not None else None)
        # ALWAYS creates — get-before-create/idempotent reuse is DOMAIN logic
        # (the oracle's ensure_setup_channel), never the port's (D-0077).
        channel = await guild.create_text_channel(
            name=name, overwrites=overwrite_map, category=category,
            reason=reason)
        return int(channel.id)

    async def delete_channel(self, channel_id: int, *,
                             reason: str | None) -> None:
        discord = self._require_discord()
        channel = self._channel(channel_id)
        try:
            await channel.delete(reason=reason)
        except discord.NotFound:
            # already-gone is the GOAL state — a live delete treats Discord
            # NotFound as SUCCESS (the oracle's delete_setup_channel
            # `except discord.NotFound: return True`; D-0077). The name/id
            # guards stay in the calling domain, not here.
            logger.info("channel %s already deleted — NotFound as success",
                        channel_id)

    async def create_invite(self, channel_id: int, *, max_age: int,
                            max_uses: int, temporary: bool, unique: bool,
                            reason: str | None) -> str:
        self._require_discord()
        channel = self._channel(channel_id)
        # the shipped `!invite` ctx.channel.create_invite(...); wire verb
        # create_invite. Unlike the parity twin (which reproduces the
        # capture-world unparseable-response artifact, CaptureInviteParseError),
        # a LIVE invite adapter simply returns the minted invite URL.
        invite = await channel.create_invite(
            max_age=int(max_age), max_uses=int(max_uses),
            temporary=bool(temporary), unique=bool(unique), reason=reason)
        return str(invite.url)


class DiscordProofChannelActions(_ChannelGuildAllowList):
    """The concrete proof_channel ``ChannelPermActions`` adapter — a SEPARATE
    port from the channel domain (do NOT conflate). Both methods carry
    ``guild_id`` → the test-guild allow-list is checked DIRECTLY. The prize
    lock/unlock is a bulk ``channel.edit(overwrites=…)`` (the shipped
    proof_channel_cog `_lock_for_winner` / `_unlock`, wire verb edit_channel),
    a distinct verb from ChannelStateActions.set_overwrite's per-target
    edit_channel_permissions PUT — hence the distinct adapter class."""

    #: refusals in THIS port read "proof_channel effect REFUSED" (the prize
    #: lock/unlock lane), not the channel-domain default.
    _effect = "proof_channel"

    def _proof_channel(self, guild, channel_id: int):
        channel = (guild.get_channel(int(channel_id))
                   or self._bot.get_channel(int(channel_id)))
        if channel is None:
            raise RuntimeError(
                f"channel {channel_id} is not available in guild "
                f"{getattr(guild, 'id', '?')}")
        return channel

    async def _member(self, guild, member_id: int):
        member = guild.get_member(int(member_id))
        if member is None:
            member = await guild.fetch_member(int(member_id))
        return member

    async def lock_channel_for_winner(self, guild_id: int, channel_id: int,
                                      winner_id: int) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)  # guild-scoped → allow-list direct
        channel = self._proof_channel(guild, channel_id)
        winner = await self._member(guild, winner_id)
        # the oracle's _lock_for_winner overwrite set verbatim: hide from
        # @everyone, grant the winner view+send, keep the bot visible.
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            winner: discord.PermissionOverwrite(view_channel=True,
                                                send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }
        await channel.edit(overwrites=overwrites)

    async def unlock_channel(self, guild_id: int, channel_id: int) -> None:
        discord = self._require_discord()
        guild = self._guild(guild_id)  # guild-scoped → allow-list direct
        channel = self._proof_channel(guild, channel_id)
        # the oracle's _unlock overwrite set verbatim: read-only for everyone
        # (view yes, send no), the bot visible.
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }
        await channel.edit(overwrites=overwrites)


class DiscordChannelLookup(_ChannelGuildAllowList):
    """The live channel NAME lookup behind ``install_channel_lookup`` — the
    shipped TextChannelConverter gateway-cache name leg. A READ (never a
    mutation): any guild other than the allowed test guild resolves to
    ``None`` (resolve_channel treats None as 'not found'), so the name leg
    stays test-guild-scoped too."""

    async def __call__(self, guild_id: int, name: str) -> int | None:
        if int(guild_id) != self._allowed_guild_id:
            return None
        guild = self._bot.get_guild(int(guild_id))
        if guild is None:
            return None
        for channel in getattr(guild, "text_channels", []) or []:
            if getattr(channel, "name", None) == name:
                return int(channel.id)
        return None
