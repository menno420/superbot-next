"""Contract test for the LIVE channel adapters
(sb/adapters/discord/channel_actions.py, SLICE 3 of the live-guild-effects
lane — the channel twin of tests/unit/band5/test_live_role_adapters.py).
Drives each ``ChannelStateActions`` port method against a duck-typed
``bot``/``guild``/``channel`` and asserts the EXACT discord.py call + kwargs.

``discord`` is absent in CI containers by design, so the module-level guarded
``discord`` is monkeypatched with a minimal fake supplying the symbols the
adapter constructs off it — ``discord.Permissions`` /
``discord.PermissionOverwrite`` (the overwrite pair) and ``discord.NotFound``
(the delete swallow). The behavioral contract this pins: set_slowmode edits
``slowmode_delay`` + reason; set_overwrite resolves the role/member target and
set_permissions with the from_pair overwrite; create_text_channel maps the
overwrite tuple, resolves the category, ALWAYS creates, and returns the new
channel id; delete_channel deletes with the reason AND swallows
``discord.NotFound`` as SUCCESS; create_invite returns the minted url. And the
SAFETY contract: create_text_channel (guild-scoped) REFUSES a non-allowed
guild, and the channel-scoped methods REFUSE a channel whose guild is not the
allowed test guild (or is not resolvable from cache at all) — all BEFORE any
Discord call.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.adapters.discord import channel_actions as chan_mod
from sb.adapters.discord.channel_actions import (
    DiscordChannelLookup,
    DiscordChannelStateActions,
    GuildNotAllowedError,
)
from sb.domain.channel.service import ChannelOverwrite

run = asyncio.run

_GUILD = 1
_OTHER_GUILD = 999
_NEW_CHANNEL_ID = 8888


# --- the minimal fake `discord` module -------------------------------------

class _FakeHTTPException(Exception):
    """Stand-in for ``discord.HTTPException`` (the base of the Discord HTTP
    error family: Forbidden / NotFound / rate-limit / ...)."""


class _FakeNotFound(_FakeHTTPException):
    """Stand-in for ``discord.NotFound`` (an HTTPException subclass)."""


class _FakeForbidden(_FakeHTTPException):
    """Stand-in for ``discord.Forbidden`` (an HTTPException subclass)."""


class _FakePermissions:
    def __init__(self, value: int) -> None:
        self.value = int(value)


class _FakePermissionOverwrite:
    def __init__(self, allow: int, deny: int) -> None:
        self.allow = int(allow)
        self.deny = int(deny)

    @classmethod
    def from_pair(cls, allow: _FakePermissions, deny: _FakePermissions):
        return cls(allow.value, deny.value)


class _FakeDiscord:
    Permissions = _FakePermissions
    PermissionOverwrite = _FakePermissionOverwrite
    HTTPException = _FakeHTTPException
    NotFound = _FakeNotFound
    Forbidden = _FakeForbidden


# --- the fake discord graph ------------------------------------------------

class _FakeRole:
    def __init__(self, role_id: int) -> None:
        self.id = int(role_id)


class _FakeMember:
    def __init__(self, member_id: int) -> None:
        self.id = int(member_id)


class _FakeCategory:
    def __init__(self, category_id: int) -> None:
        self.id = int(category_id)


class _FakeChannel:
    def __init__(self, guild, channel_id: int = 50, *,
                 delete_raises: Exception | None = None,
                 edit_raises: Exception | None = None,
                 perms_raises: Exception | None = None) -> None:
        self.guild = guild
        self.id = int(channel_id)
        self.calls: list[tuple] = []
        self._delete_raises = delete_raises
        self._edit_raises = edit_raises
        self._perms_raises = perms_raises

    async def edit(self, *, slowmode_delay=None, reason=None):
        self.calls.append(("edit", slowmode_delay, reason))
        if self._edit_raises is not None:
            raise self._edit_raises

    async def set_permissions(self, target, *, overwrite, reason):
        self.calls.append(("set_permissions", target, overwrite, reason))
        if self._perms_raises is not None:
            raise self._perms_raises

    async def delete(self, *, reason):
        self.calls.append(("delete", reason))
        if self._delete_raises is not None:
            raise self._delete_raises

    async def create_invite(self, *, max_age, max_uses, temporary, unique,
                            reason):
        self.calls.append(("create_invite", max_age, max_uses, temporary,
                           unique, reason))
        return SimpleNamespace(url="https://discord.gg/abc123")


class _FakeGuild:
    def __init__(self, guild_id: int = _GUILD, *,
                 role: _FakeRole | None = None,
                 member: _FakeMember | None = None,
                 category: _FakeCategory | None = None,
                 fetched_member: _FakeMember | None = None) -> None:
        self.id = int(guild_id)
        self._role = role
        self._member = member
        self._category = category
        self._fetched_member = fetched_member
        self.fetched_ids: list[int] = []
        self.calls: list[tuple] = []

    def get_role(self, role_id):
        return self._role

    def get_member(self, member_id):
        return self._member

    async def fetch_member(self, member_id):
        # the REST fallback for an uncached member (post-fence, safe)
        self.fetched_ids.append(int(member_id))
        return self._fetched_member

    def get_channel(self, channel_id):
        return self._category

    async def create_text_channel(self, *, name, overwrites, category, reason):
        self.calls.append(("create_text_channel", name, overwrites, category,
                           reason))
        return _FakeChannel(self, _NEW_CHANNEL_ID)


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
    monkeypatch.setattr(chan_mod, "discord", _FakeDiscord)


def _actions(bot):
    return DiscordChannelStateActions(bot, allowed_guild_id=_GUILD)


# --- set_slowmode ----------------------------------------------------------

def test_set_slowmode_edits_slowmode_delay_and_reason():
    guild = _FakeGuild()
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    run(actions.set_slowmode(50, seconds=30, reason="rate limit"))
    (call,) = channel.calls
    verb, slowmode_delay, reason = call
    assert verb == "edit"
    assert slowmode_delay == 30
    assert reason == "rate limit"


# --- set_overwrite ---------------------------------------------------------

def test_set_overwrite_resolves_role_and_sets_permissions():
    role = _FakeRole(_GUILD)  # @everyone target (id == guild id)
    guild = _FakeGuild(role=role)
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    run(actions.set_overwrite(50, target_id=_GUILD, allow=0, deny=2048,
                              target_type=0, reason="lock"))
    (call,) = channel.calls
    verb, target, overwrite, reason = call
    assert verb == "set_permissions"
    # target_type 0 → role (resolved from the guild cache)
    assert target is role
    # the overwrite is the from_pair(allow, deny) pair, values preserved
    assert overwrite.allow == 0 and overwrite.deny == 2048
    assert reason == "lock"


def test_set_overwrite_resolves_member_for_type_1():
    member = _FakeMember(103)
    guild = _FakeGuild(member=member)
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    run(actions.set_overwrite(50, target_id=103, allow=2048, deny=0,
                              target_type=1, reason="grant"))
    (_verb, target, _ow, _reason) = channel.calls[0]
    assert target is member  # target_type 1 → member


def test_set_overwrite_raises_loudly_on_unresolvable_target():
    guild = _FakeGuild(role=None)  # get_role → None
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    with pytest.raises(RuntimeError):
        run(actions.set_overwrite(50, target_id=_GUILD, allow=0, deny=2048,
                                  target_type=0, reason="x"))


# --- create_text_channel ---------------------------------------------------

def test_create_text_channel_maps_overwrites_resolves_category_returns_id():
    role = _FakeRole(_GUILD)
    category = _FakeCategory(4000)
    guild = _FakeGuild(role=role, category=category)
    actions = _actions(_FakeBot(guild))
    overwrites = (ChannelOverwrite(target_id=_GUILD, target_type=0,
                                   allow=0, deny=2048),)
    new_id = run(actions.create_text_channel(
        _GUILD, name="prizes", overwrites=overwrites, parent_id=4000,
        reason="setup"))
    # ALWAYS creates; the new channel id flows back
    assert new_id == _NEW_CHANNEL_ID
    (call,) = guild.calls
    verb, name, ow_map, cat, reason = call
    assert verb == "create_text_channel"
    assert name == "prizes"
    assert cat is category  # parent_id resolved to the cached category
    assert reason == "setup"
    # the ChannelOverwrite tuple mapped to {role: PermissionOverwrite}
    (target, overwrite), = ow_map.items()
    assert target is role
    assert overwrite.allow == 0 and overwrite.deny == 2048


def test_create_text_channel_no_parent_passes_none_category():
    guild = _FakeGuild()
    actions = _actions(_FakeBot(guild))
    run(actions.create_text_channel(_GUILD, name="general", overwrites=(),
                                    parent_id=None, reason="x"))
    (_verb, _name, ow_map, cat, _reason) = guild.calls[0]
    assert cat is None
    assert ow_map == {}


# --- delete_channel --------------------------------------------------------

def test_delete_channel_deletes_with_reason():
    guild = _FakeGuild()
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    run(actions.delete_channel(50, reason="cleanup"))
    (call,) = channel.calls
    assert call == ("delete", "cleanup")


def test_delete_channel_swallows_notfound_as_success():
    guild = _FakeGuild()
    # channel.delete raises discord.NotFound → the adapter treats it as success
    channel = _FakeChannel(guild, delete_raises=_FakeNotFound("gone"))
    actions = _actions(_FakeBot(channel=channel))
    # no exception propagates — already-gone is the goal state
    run(actions.delete_channel(50, reason="cleanup"))
    assert channel.calls == [("delete", "cleanup")]


# --- create_invite ---------------------------------------------------------

def test_create_invite_returns_the_minted_url():
    guild = _FakeGuild()
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    url = run(actions.create_invite(50, max_age=0, max_uses=1, temporary=False,
                                    unique=True, reason="!invite"))
    assert url == "https://discord.gg/abc123"
    (call,) = channel.calls
    verb, max_age, max_uses, temporary, unique, reason = call
    assert verb == "create_invite"
    assert (max_age, max_uses, temporary, unique) == (0, 1, False, True)
    assert reason == "!invite"


# --- the test-guild allow-list (SAFETY) ------------------------------------

def test_create_text_channel_refuses_a_non_allowed_guild():
    guild = _FakeGuild()
    actions = _actions(_FakeBot(guild))
    with pytest.raises(GuildNotAllowedError) as exc:
        run(actions.create_text_channel(_OTHER_GUILD, name="x", overwrites=(),
                                        parent_id=None, reason="x"))
    # the refusal reads with the CHANNEL domain word, not the moderation/role
    # default it inherits from the shared base
    assert exc.value.effect == "channel"
    assert "channel effect REFUSED" in str(exc.value)
    assert guild.calls == []  # refused BEFORE any Discord call


def test_channel_scoped_methods_refuse_a_channel_in_a_non_allowed_guild():
    # channel resolvable but its guild is NOT the allowed test guild
    channel = _FakeChannel(SimpleNamespace(id=_OTHER_GUILD))
    actions = _actions(_FakeBot(channel=channel))
    with pytest.raises(GuildNotAllowedError) as exc:
        run(actions.set_slowmode(50, seconds=5, reason="x"))
    assert exc.value.effect == "channel"
    with pytest.raises(GuildNotAllowedError):
        run(actions.delete_channel(50, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(actions.create_invite(50, max_age=0, max_uses=1, temporary=False,
                                  unique=True, reason="x"))
    assert channel.calls == []  # nothing mutated


def test_channel_scoped_methods_refuse_an_unresolvable_guild():
    # no channel in cache (get_channel → None): a DM/uncached channel can never
    # be proven to be the test guild, so the effect is REFUSED.
    actions = _actions(_FakeBot(channel=None))
    with pytest.raises(GuildNotAllowedError):
        run(actions.set_slowmode(50, seconds=5, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(actions.delete_channel(50, reason="x"))


# --- finding #2: uncached member overwrite resolves via fetch_member --------

def test_set_overwrite_member_falls_back_to_fetch_member():
    # get_member → None (uncached), fetch_member returns the delegated member.
    fetched = _FakeMember(103)
    guild = _FakeGuild(member=None, fetched_member=fetched)
    channel = _FakeChannel(guild)
    actions = _actions(_FakeBot(channel=channel))
    run(actions.set_overwrite(50, target_id=103, allow=2048, deny=0,
                              target_type=1, reason="grant"))
    assert guild.fetched_ids == [103]          # the REST fallback fired
    (_verb, target, _ow, _reason) = channel.calls[0]
    assert target is fetched                    # the fetched member was used


def test_create_text_channel_member_overwrite_uses_fetch_member():
    # setup builds member-typed overwrites (bot/invoker/delegated); an uncached
    # delegated member must resolve via fetch_member, not break the create.
    fetched = _FakeMember(103)
    guild = _FakeGuild(member=None, fetched_member=fetched)
    actions = _actions(_FakeBot(guild))
    overwrites = (ChannelOverwrite(target_id=103, target_type=1,
                                   allow=2048, deny=0),)
    new_id = run(actions.create_text_channel(
        _GUILD, name="setup", overwrites=overwrites, parent_id=None,
        reason="/setup-advanced"))
    assert new_id == _NEW_CHANNEL_ID
    assert guild.fetched_ids == [103]
    (_verb, _name, ow_map, _cat, _reason) = guild.calls[0]
    (target, _overwrite), = ow_map.items()
    assert target is fetched


# --- finding #1: a live Discord failure renders the shipped copy ------------

def test_set_slowmode_translates_http_failure_to_runtime_error():
    # a raw discord.HTTPException would escape the handlers' `except
    # RuntimeError` to the generic envelope; the adapter translates it so the
    # shipped `❌ Could not set slowmode …` branch renders.
    guild = _FakeGuild()
    channel = _FakeChannel(guild, edit_raises=_FakeForbidden("Missing Perms"))
    actions = _actions(_FakeBot(channel=channel))
    with pytest.raises(RuntimeError) as exc:
        run(actions.set_slowmode(50, seconds=5, reason="x"))
    assert not isinstance(exc.value, _FakeHTTPException)  # translated, not raw
    assert "Missing Perms" in str(exc.value)


def test_set_overwrite_translates_http_failure_to_runtime_error():
    role = _FakeRole(_GUILD)
    guild = _FakeGuild(role=role)
    channel = _FakeChannel(guild, perms_raises=_FakeForbidden("Missing Perms"))
    actions = _actions(_FakeBot(channel=channel))
    with pytest.raises(RuntimeError) as exc:
        run(actions.set_overwrite(50, target_id=_GUILD, allow=0, deny=2048,
                                  target_type=0, reason="lock"))
    assert not isinstance(exc.value, _FakeHTTPException)
    assert "Missing Perms" in str(exc.value)


# --- finding #4: the channel-name lookup guild fence ------------------------

class _RaisingBot:
    """get_guild MUST NOT be reached for a non-allowed guild id."""

    def get_guild(self, guild_id):
        raise AssertionError("get_guild reached past the guild fence")


def test_lookup_refuses_a_non_allowed_guild_without_touching_get_guild():
    lookup = DiscordChannelLookup(_RaisingBot(), allowed_guild_id=_GUILD)
    # a non-allowed guild id resolves to None (a read, refused softly) and
    # never reaches bot.get_guild — the fence is BEFORE the cache read.
    assert run(lookup(_OTHER_GUILD, "general")) is None


def test_lookup_resolves_a_channel_by_name_in_the_allowed_guild():
    target = SimpleNamespace(id=900_001, name="general")
    guild = SimpleNamespace(text_channels=[SimpleNamespace(id=7, name="off"),
                                           target])
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    lookup = DiscordChannelLookup(bot, allowed_guild_id=_GUILD)
    assert run(lookup(_GUILD, "general")) == 900_001
    assert run(lookup(_GUILD, "missing")) is None


# --- finding #1 (end-to-end): a live Discord failure in slowmode/lock/unlock
#     renders the shipped `❌ Could not …` copy, NOT the generic envelope -----

def _channel_handler(name):
    from sb.domain.channel import handlers  # noqa: F401 — registers refs
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _req(argv):
    return SimpleNamespace(args={"argv": tuple(argv)}, guild_id=_GUILD,
                           channel_id=900_001, actor=SimpleNamespace(user_id=7))


def test_slowmode_live_http_failure_renders_shipped_copy_not_envelope():
    from sb.domain.channel import service

    guild = _FakeGuild()
    channel = _FakeChannel(guild, 900_001,
                           edit_raises=_FakeForbidden("Missing Permissions"))
    service.reset_channel_ports_for_tests()
    try:
        service.install_channel_actions(
            _actions(_FakeBot(channel=channel)))
        # `<#900001>` mention → resolve_channel returns 900001 with no lookup
        reply = run(_channel_handler("channel.slowmode")(
            _req(("<#900001>", "5"))))
    finally:
        service.reset_channel_ports_for_tests()
    from sb.spec.outcomes import BLOCKED
    assert reply.outcome == BLOCKED
    # the SHIPPED copy branch fired (adapter translated Forbidden → RuntimeError
    # so the handler's `except RuntimeError` caught it), NOT the generic envelope
    assert reply.user_message.startswith('❌ Could not set slowmode in')
    assert "Missing Permissions" in reply.user_message


def test_lock_live_http_failure_renders_shipped_copy_not_envelope():
    from sb.domain.channel import service

    role = _FakeRole(_GUILD)  # @everyone default role (id == guild id)
    guild = _FakeGuild(role=role)
    channel = _FakeChannel(guild, 900_001,
                           perms_raises=_FakeForbidden("Missing Permissions"))
    service.reset_channel_ports_for_tests()
    try:
        service.install_channel_actions(
            _actions(_FakeBot(channel=channel)))
        reply = run(_channel_handler("channel.lock")(_req(("<#900001>",))))
    finally:
        service.reset_channel_ports_for_tests()
    from sb.spec.outcomes import BLOCKED
    assert reply.outcome == BLOCKED
    assert reply.user_message.startswith('Could not lock')
    assert "Missing Permissions" in reply.user_message
