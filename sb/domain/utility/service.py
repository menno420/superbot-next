"""Utility read ports — the guild/member directory + the gateway probe.

The shipped utility_cog read live discord.py models (``ctx.guild``,
``member.display_avatar``, ``bot.latency``); sb/ is gateway-free, so the
same reads arrive through TWO installable ports:

* :class:`GuildDirectory` — view-only guild/member metadata (the
  ``!serverinfo`` / ``!avatar`` / user-info read surface). The parity
  harness installs a fake-world-backed implementation
  (sb/adapters/parity/boot.py); the live discord adapter's implementation
  arms with the live root (the moderation-actions port precedent — until
  then the entry points degrade to the honest not-armed refusal).
* ``gateway_latency_ms`` — the shipped ``bot.latency * 1000`` read for the
  ``!ping`` Gateway field. Uninstalled ⇒ ``nan`` (discord.py's own
  no-heartbeat-yet value — also what the capture world reports).

No stores, no events, no writes — the whole subsystem surface is reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

__all__ = [
    "GuildDirectory",
    "GuildDirectoryNotInstalled",
    "GuildInfo",
    "MemberInfo",
    "gateway_latency_ms",
    "guild_directory",
    "install_gateway_probe",
    "install_guild_directory",
    "reset_utility_ports_for_tests",
]


@dataclass(frozen=True)
class GuildInfo:
    """The ``!serverinfo`` read set (utility_cog's `!info server` embed).

    ``bots`` joined at the counters flip — the shipped
    ``counter_service.compute_counts`` read the SAME gateway guild cache
    (``guild.member_count`` + per-member bot flags), so the split rides
    this port rather than a new seam (humans = member_count - bots).
    Defaulted for directories that predate the field.

    ``online_members`` / ``roles`` joined at the admin serverstats
    re-home — the shipped ``!serverstats`` census (admin_cog.py
    ``server_stats``: ``sum(m.status != offline for m in guild.members)``
    and ``len(guild.roles)``) reads the same cache, so both ride this
    port too (goldens/admin/sweep_serverstats pins the values).
    Defaulted for directories that predate the fields.
    """

    name: str
    owner_id: int
    member_count: int
    premium_tier: int
    created_at: datetime
    text_channels: int
    voice_channels: int
    bots: int = 0
    online_members: int = 0
    roles: int = 0


@dataclass(frozen=True)
class MemberInfo:
    """The per-member read set (avatar / user-info cards)."""

    user_id: int
    tag: str                     # str(member) — "Name#0000"
    display_avatar_url: str      # member.display_avatar.url
    created_at: datetime         # user snowflake time ("Joined Discord")
    joined_at: datetime          # guild join time ("Joined Server")


class GuildDirectory(Protocol):
    async def guild_info(self, guild_id: int) -> GuildInfo: ...

    async def member_info(self, guild_id: int, user_id: int) -> MemberInfo: ...


class GuildDirectoryNotInstalled(RuntimeError):
    """No directory armed — surfaces refuse politely, never invent data."""


_directory: GuildDirectory | None = None
_latency_probe: Callable[[], float] | None = None


def install_guild_directory(directory: GuildDirectory) -> None:
    global _directory
    _directory = directory


def guild_directory() -> GuildDirectory:
    if _directory is None:
        raise GuildDirectoryNotInstalled(
            "guild directory port not installed "
            "(sb/domain/utility/service.install_guild_directory)")
    return _directory


def install_gateway_probe(probe: Callable[[], float]) -> None:
    """``probe() -> latency_ms`` (the shipped ``bot.latency * 1000``)."""
    global _latency_probe
    _latency_probe = probe


def gateway_latency_ms() -> float:
    if _latency_probe is None:
        return float("nan")      # discord.py's pre-heartbeat latency
    return float(_latency_probe())


def reset_utility_ports_for_tests() -> None:
    global _directory, _latency_probe
    _directory = None
    _latency_probe = None
