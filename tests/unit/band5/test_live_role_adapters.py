"""Contract test for the LIVE role adapters (sb/adapters/discord/role_actions.py,
SLICE 2 of the live-guild-effects lane — the role twin of
tests/unit/band2/test_live_moderation_adapter.py). Drives each port method
against a duck-typed ``bot``/``guild``/``member``/``role``/``channel``/``message``
and asserts the EXACT discord.py call + kwargs.

``discord`` is absent in CI containers by design, so the module-level guarded
``discord`` is monkeypatched with a minimal fake supplying the two symbols the
adapters construct off it — ``discord.Object`` (the bare snowflake for
add_roles/remove_roles) and ``discord.Colour`` (the create_role colour). The
behavioral contract this pins: add/remove role pass a bare snowflake + reason;
create_guild_role wraps the int colour in ``discord.Colour`` and returns the new
role's id; delete_role resolves the cached role then deletes with the reason;
the MessageOps pair fetches the message then reacts. And the SAFETY contract:
every guild-scoped method REFUSES a non-allowed guild BEFORE any Discord call,
and the channel-scoped MessageOps refuses a channel whose guild is not the
allowed test guild (or is not resolvable at all).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.adapters.discord import role_actions as role_mod
from sb.adapters.discord.role_actions import (
    DiscordGuildRoleActions,
    DiscordRoleMessageOps,
    DiscordRoleProvisioning,
    GuildNotAllowedError,
)

run = asyncio.run

_GUILD = 1
_OTHER_GUILD = 999
_NEW_ROLE_ID = 5555


class _FakeObject:
    """Stand-in for ``discord.Object(id)`` — the bare snowflake."""

    def __init__(self, id: int) -> None:  # noqa: A002 — mirrors discord.Object
        self.id = int(id)


class _FakeColour:
    """Stand-in for ``discord.Colour(value)``."""

    def __init__(self, value: int) -> None:
        self.value = int(value)


class _FakeDiscord:
    """Minimal fake of the ``discord`` module the adapters read off."""

    Object = _FakeObject
    Colour = _FakeColour


class _FakeMember:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def add_roles(self, role, *, reason):
        self.calls.append(("add_roles", role, reason))

    async def remove_roles(self, role, *, reason):
        self.calls.append(("remove_roles", role, reason))


class _FakeRole:
    def __init__(self, role_id: int) -> None:
        self.id = int(role_id)
        self.calls: list[tuple] = []

    async def delete(self, *, reason):
        self.calls.append(("delete", reason))


class _FakeMessage:
    def __init__(self) -> None:
        self.reactions: list[str] = []

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)


class _FakeGuild:
    def __init__(self, member: _FakeMember | None = None,
                 role: _FakeRole | None = None) -> None:
        self._member = member
        self._role = role
        self.calls: list[tuple] = []

    def get_member(self, member_id):
        return self._member

    def get_role(self, role_id):
        return self._role

    async def create_role(self, *, name, colour, reason):
        self.calls.append(("create_role", name, colour, reason))
        return _FakeRole(_NEW_ROLE_ID)


class _FakeChannel:
    def __init__(self, guild, message: _FakeMessage | None = None) -> None:
        self.guild = guild
        self._message = message
        self.fetched: list[int] = []

    async def fetch_message(self, message_id):
        self.fetched.append(int(message_id))
        return self._message


class _FakeBot:
    def __init__(self, guild: _FakeGuild | None = None,
                 channel: _FakeChannel | None = None) -> None:
        self._guild = guild
        self._channel = channel

    def get_guild(self, guild_id):
        return self._guild

    def get_channel(self, channel_id):
        return self._channel


@pytest.fixture(autouse=True)
def _fake_discord(monkeypatch):
    monkeypatch.setattr(role_mod, "discord", _FakeDiscord)


# --- GuildRoleActions ------------------------------------------------------

def test_add_role_passes_bare_snowflake_and_reason():
    member = _FakeMember()
    guild = _FakeGuild(member)
    actions = DiscordGuildRoleActions(_FakeBot(guild), allowed_guild_id=_GUILD)
    run(actions.add_role(_GUILD, 103, 777, reason="Reaction role"))
    (call,) = member.calls
    verb, role, reason = call
    assert verb == "add_roles"
    assert isinstance(role, _FakeObject) and role.id == 777
    assert reason == "Reaction role"


def test_remove_role_passes_bare_snowflake_and_reason():
    member = _FakeMember()
    guild = _FakeGuild(member)
    actions = DiscordGuildRoleActions(_FakeBot(guild), allowed_guild_id=_GUILD)
    run(actions.remove_role(_GUILD, 103, 777, reason="Temporary role expired"))
    (call,) = member.calls
    verb, role, reason = call
    assert verb == "remove_roles"
    assert isinstance(role, _FakeObject) and role.id == 777
    assert reason == "Temporary role expired"


# --- RoleProvisioning ------------------------------------------------------

def test_create_guild_role_wraps_colour_and_returns_new_id():
    guild = _FakeGuild()
    prov = DiscordRoleProvisioning(_FakeBot(guild), allowed_guild_id=_GUILD)
    new_id = run(prov.create_guild_role(_GUILD, name="VIP", color=0xFF00FF,
                                        reason="!createrole"))
    # the created role's id flows back through the port
    assert new_id == _NEW_ROLE_ID
    (call,) = guild.calls
    verb, name, colour, reason = call
    assert verb == "create_role"
    assert name == "VIP"
    # the int colour is wrapped in discord.Colour, value preserved
    assert isinstance(colour, _FakeColour) and colour.value == 0xFF00FF
    assert reason == "!createrole"


def test_delete_role_resolves_cached_role_then_deletes():
    role = _FakeRole(777)
    guild = _FakeGuild(role=role)
    prov = DiscordRoleProvisioning(_FakeBot(guild), allowed_guild_id=_GUILD)
    run(prov.delete_role(_GUILD, 777, reason="!deleterole"))
    (call,) = role.calls
    verb, reason = call
    assert verb == "delete"
    assert reason == "!deleterole"


def test_delete_role_raises_loudly_on_a_vanished_role():
    guild = _FakeGuild(role=None)  # get_role → None
    prov = DiscordRoleProvisioning(_FakeBot(guild), allowed_guild_id=_GUILD)
    with pytest.raises(RuntimeError):
        run(prov.delete_role(_GUILD, 777, reason="x"))


# --- MessageOps ------------------------------------------------------------

def test_fetch_message_reads_the_message_in_the_allowed_guild():
    message = _FakeMessage()
    channel = _FakeChannel(SimpleNamespace(id=_GUILD), message)
    ops = DiscordRoleMessageOps(_FakeBot(channel=channel),
                                allowed_guild_id=_GUILD)
    run(ops.fetch_message(50, 60))
    assert channel.fetched == [60]


def test_add_reaction_fetches_then_reacts():
    message = _FakeMessage()
    channel = _FakeChannel(SimpleNamespace(id=_GUILD), message)
    ops = DiscordRoleMessageOps(_FakeBot(channel=channel),
                                allowed_guild_id=_GUILD)
    run(ops.add_reaction(50, 60, "✅"))
    assert channel.fetched == [60]
    assert message.reactions == ["✅"]


# --- the test-guild allow-list (SAFETY) ------------------------------------

def test_guild_scoped_methods_refuse_a_non_allowed_guild():
    member = _FakeMember()
    role = _FakeRole(777)
    guild = _FakeGuild(member, role)
    bot = _FakeBot(guild)
    actions = DiscordGuildRoleActions(bot, allowed_guild_id=_GUILD)
    prov = DiscordRoleProvisioning(bot, allowed_guild_id=_GUILD)
    with pytest.raises(GuildNotAllowedError):
        run(actions.add_role(_OTHER_GUILD, 103, 777, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(actions.remove_role(_OTHER_GUILD, 103, 777, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(prov.create_guild_role(_OTHER_GUILD, name="x", color=0,
                                   reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(prov.delete_role(_OTHER_GUILD, 777, reason="x"))
    # the refusal is BEFORE any Discord call — nothing was mutated
    assert member.calls == []
    assert guild.calls == []
    assert role.calls == []


def test_message_ops_refuse_a_channel_in_a_non_allowed_guild():
    message = _FakeMessage()
    # channel resolvable but its guild is NOT the allowed test guild
    channel = _FakeChannel(SimpleNamespace(id=_OTHER_GUILD), message)
    ops = DiscordRoleMessageOps(_FakeBot(channel=channel),
                                allowed_guild_id=_GUILD)
    with pytest.raises(GuildNotAllowedError):
        run(ops.fetch_message(50, 60))
    with pytest.raises(GuildNotAllowedError):
        run(ops.add_reaction(50, 60, "✅"))
    assert channel.fetched == []
    assert message.reactions == []


def test_message_ops_refuse_a_channel_with_no_resolvable_guild():
    # no channel in cache (get_channel → None): a DM/uncached channel can
    # never be proven to be the test guild, so the bind is REFUSED.
    ops = DiscordRoleMessageOps(_FakeBot(channel=None), allowed_guild_id=_GUILD)
    with pytest.raises(GuildNotAllowedError):
        run(ops.fetch_message(50, 60))
    with pytest.raises(GuildNotAllowedError):
        run(ops.add_reaction(50, 60, "✅"))
