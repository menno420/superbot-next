"""Contract test for the LIVE proof_channel adapter
(``DiscordProofChannelActions`` in sb/adapters/discord/channel_actions.py,
SLICE 3 of the live-guild-effects lane). This is the proof_channel domain's
OWN ``ChannelPermActions`` port (sb/domain/proof_channel/service.py) — a
SEPARATE seam from the channel domain's ChannelStateActions. Drives lock/unlock
against a duck-typed ``bot``/``guild``/``channel`` and asserts the EXACT
discord.py call: a bulk ``channel.edit(overwrites=…)`` whose overwrite set
mirrors the shipped ``proof_channel_cog`` (`_lock_for_winner` hides the channel
from @everyone, grants the winner view+send, keeps the bot visible; `_unlock`
restores read-only-for-everyone). And the SAFETY contract: both methods
(guild-scoped) REFUSE a non-allowed guild BEFORE any Discord call.
"""

from __future__ import annotations

import asyncio

import pytest

from sb.adapters.discord import channel_actions as chan_mod
from sb.adapters.discord.channel_actions import (
    DiscordProofChannelActions,
    GuildNotAllowedError,
)

run = asyncio.run

_GUILD = 1
_OTHER_GUILD = 999


class _FakePermissionOverwrite:
    def __init__(self, *, view_channel=None, send_messages=None) -> None:
        self.view_channel = view_channel
        self.send_messages = send_messages

    def __eq__(self, other):
        return (isinstance(other, _FakePermissionOverwrite)
                and self.view_channel == other.view_channel
                and self.send_messages == other.send_messages)


class _FakeDiscord:
    PermissionOverwrite = _FakePermissionOverwrite


class _FakeMember:
    def __init__(self, member_id: int) -> None:
        self.id = int(member_id)


class _FakeChannel:
    def __init__(self, channel_id: int = 50) -> None:
        self.id = int(channel_id)
        self.calls: list[dict] = []

    async def edit(self, *, overwrites):
        self.calls.append(overwrites)


class _FakeGuild:
    def __init__(self, guild_id: int = _GUILD, *,
                 channel: _FakeChannel | None = None,
                 member: _FakeMember | None = None) -> None:
        self.id = int(guild_id)
        self.default_role = object()
        self.me = object()
        self._channel = channel
        self._member = member

    def get_channel(self, channel_id):
        return self._channel

    def get_member(self, member_id):
        return self._member


class _FakeBot:
    def __init__(self, guild: _FakeGuild | None = None) -> None:
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild

    def get_channel(self, channel_id):
        return None


@pytest.fixture(autouse=True)
def _fake_discord(monkeypatch):
    monkeypatch.setattr(chan_mod, "discord", _FakeDiscord)


def test_lock_for_winner_hides_everyone_grants_winner_keeps_bot():
    channel = _FakeChannel()
    member = _FakeMember(103)
    guild = _FakeGuild(channel=channel, member=member)
    actions = DiscordProofChannelActions(_FakeBot(guild),
                                         allowed_guild_id=_GUILD)
    run(actions.lock_channel_for_winner(_GUILD, 50, 103))
    (overwrites,) = channel.calls
    # @everyone hidden, winner view+send, bot visible — the oracle's set
    assert overwrites[guild.default_role] == _FakePermissionOverwrite(
        view_channel=False)
    assert overwrites[member] == _FakePermissionOverwrite(
        view_channel=True, send_messages=True)
    assert overwrites[guild.me] == _FakePermissionOverwrite(view_channel=True)


def test_unlock_restores_read_only_for_everyone():
    channel = _FakeChannel()
    guild = _FakeGuild(channel=channel)
    actions = DiscordProofChannelActions(_FakeBot(guild),
                                         allowed_guild_id=_GUILD)
    run(actions.unlock_channel(_GUILD, 50))
    (overwrites,) = channel.calls
    # everyone: view yes, send no; bot visible; winner entry gone
    assert overwrites[guild.default_role] == _FakePermissionOverwrite(
        view_channel=True, send_messages=False)
    assert overwrites[guild.me] == _FakePermissionOverwrite(view_channel=True)
    assert len(overwrites) == 2


def test_lock_and_unlock_refuse_a_non_allowed_guild():
    channel = _FakeChannel()
    member = _FakeMember(103)
    guild = _FakeGuild(channel=channel, member=member)
    actions = DiscordProofChannelActions(_FakeBot(guild),
                                         allowed_guild_id=_GUILD)
    with pytest.raises(GuildNotAllowedError):
        run(actions.lock_channel_for_winner(_OTHER_GUILD, 50, 103))
    with pytest.raises(GuildNotAllowedError):
        run(actions.unlock_channel(_OTHER_GUILD, 50))
    assert channel.calls == []  # refused BEFORE any Discord call
