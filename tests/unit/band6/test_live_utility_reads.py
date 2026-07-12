"""Contract test for the LIVE utility READ adapter
(sb/adapters/discord/utility_reads.py — the gateway-cache guild/member census
behind ``install_guild_directory``; the live twin of the parity harness's
``_WorldGuildDirectory``). Drives ``guild_info`` / ``member_info`` against a
duck-typed guild cache and pins: the census field mapping (bots / online /
roles / channel counts off the cached members), the member card mapping
(tag / avatar / status / activity, cache-first with ONE REST ``fetch_member``
fallback), and the READ fence — a non-allowed or uncached guild refuses as
``GuildDirectoryNotInstalled`` (the polite pre-arm refusal every consuming
surface already renders), never a mutation-style error, and never touches the
cache for a non-allowed id."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from sb.adapters.discord.utility_reads import DiscordGuildDirectory
from sb.domain.utility.service import GuildDirectoryNotInstalled

run = asyncio.run

_GUILD = 1
_OTHER_GUILD = 999
_CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)
_JOINED = datetime(2026, 2, 2, tzinfo=timezone.utc)


class _FakeMember:
    def __init__(self, uid, *, bot=False, status="offline", activity=None,
                 tag="User#0000", avatar="https://cdn/av.png") -> None:
        self.id = int(uid)
        self.bot = bot
        self.status = status
        self.activity = activity
        self.display_avatar = SimpleNamespace(url=avatar)
        self.created_at = _CREATED
        self.joined_at = _JOINED
        self._tag = tag

    def __str__(self) -> str:
        return self._tag


class _FakeGuild:
    def __init__(self, *, members=(), member=None, fetched=None) -> None:
        self.id = _GUILD
        self.name = "Superbot Admin"
        self.owner_id = 42
        self.member_count = len(members) or 4
        self.premium_tier = 1
        self.created_at = _CREATED
        self.members = list(members)
        self.text_channels = [1, 2, 3]
        self.voice_channels = [4]
        self.roles = [1, 2]
        self._member = member
        self._fetched = fetched
        self.fetched_ids: list[int] = []

    def get_member(self, uid):
        return self._member

    async def fetch_member(self, uid):
        self.fetched_ids.append(int(uid))
        return self._fetched


def _directory(guild):
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    return DiscordGuildDirectory(bot, allowed_guild_id=_GUILD)


def test_guild_info_maps_the_cache_census():
    members = [_FakeMember(1), _FakeMember(2, bot=True),
               _FakeMember(3, status="online")]
    guild = _FakeGuild(members=members)
    info = run(_directory(guild).guild_info(_GUILD))
    assert info.name == "Superbot Admin"
    assert info.owner_id == 42
    assert info.member_count == 3
    assert info.premium_tier == 1
    assert info.created_at == _CREATED
    assert info.text_channels == 3 and info.voice_channels == 1
    assert info.bots == 1                 # the per-member bot-flag census
    assert info.online_members == 1       # sum(status != offline), the shipped read
    assert info.roles == 2                # len(guild.roles)


def test_member_info_maps_the_cached_member():
    member = _FakeMember(7, status="online",
                         activity=SimpleNamespace(name="mining"),
                         tag="Menno#0001", avatar="https://cdn/menno.png")
    guild = _FakeGuild(member=member)
    card = run(_directory(guild).member_info(_GUILD, 7))
    assert card.user_id == 7
    assert card.tag == "Menno#0001"
    assert card.display_avatar_url == "https://cdn/menno.png"
    assert card.created_at == _CREATED and card.joined_at == _JOINED
    assert card.status == "online"
    assert card.activity_name == "mining"
    assert guild.fetched_ids == []        # cache hit → NO REST fetch


def test_member_info_falls_back_to_one_rest_fetch_for_uncached():
    fetched = _FakeMember(7)
    guild = _FakeGuild(member=None, fetched=fetched)
    card = run(_directory(guild).member_info(_GUILD, 7))
    assert card.user_id == 7
    assert card.status == "offline" and card.activity_name is None
    assert guild.fetched_ids == [7]       # exactly ONE fetch_member


class _RaisingBot:
    """get_guild MUST NOT be reached for a non-allowed guild id."""

    def get_guild(self, guild_id):
        raise AssertionError("get_guild reached past the guild fence")


def test_reads_refuse_a_non_allowed_guild_as_not_armed():
    directory = DiscordGuildDirectory(_RaisingBot(), allowed_guild_id=_GUILD)
    # the fence fires BEFORE the cache read (the _RaisingBot asserts it) and
    # refuses with the NOT-ARMED error the handlers already render politely.
    with pytest.raises(GuildDirectoryNotInstalled):
        run(directory.guild_info(_OTHER_GUILD))
    with pytest.raises(GuildDirectoryNotInstalled):
        run(directory.member_info(_OTHER_GUILD, 7))


def test_reads_refuse_an_uncached_allowed_guild_as_not_armed():
    bot = SimpleNamespace(get_guild=lambda gid: None)
    directory = DiscordGuildDirectory(bot, allowed_guild_id=_GUILD)
    with pytest.raises(GuildDirectoryNotInstalled):
        run(directory.guild_info(_GUILD))
