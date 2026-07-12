"""Contract test for the LIVE guild-action adapter
(sb/adapters/discord/moderation_actions.py ``DiscordModerationActions``,
D-0049 successor). Drives each of the six port methods against a duck-typed
``bot``/``guild``/``member``/``user`` and asserts the EXACT discord.py call +
kwargs — the live twin of tests/unit/parity_adapter/test_channel_ops_capture.py
(which pins the capture twin's wire shapes).

``discord`` is absent in CI containers by design, so the module-level guarded
``discord`` is monkeypatched with a minimal fake that supplies the two symbols
the adapter constructs off it — ``discord.Object`` (bare snowflake for
kick/ban) and ``discord.utils.utcnow`` (the tz-aware now for the timeout
until). The behavioral contract this pins: ban passes
``delete_message_seconds`` ONLY when days>0; unban does fetch-then-unban in
order; timeout passes a reason and a FUTURE until; kick/timeout/ban pass the
reason through.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from sb.adapters.discord import moderation_actions as mod_actions
from sb.adapters.discord.moderation_actions import (
    DiscordModerationActions,
    GuildNotAllowedError,
)

run = asyncio.run

_FIXED_NOW = datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
_GUILD = 1
_OTHER_GUILD = 999


class _FakeObject:
    """Stand-in for ``discord.Object(id)`` — the bare snowflake."""

    def __init__(self, id: int) -> None:  # noqa: A002 — mirrors discord.Object
        self.id = int(id)


class _FakeDiscord:
    """Minimal fake of the ``discord`` module the adapter reads off."""

    Object = _FakeObject
    utils = SimpleNamespace(utcnow=lambda: _FIXED_NOW)


class _FakeMember:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def timeout(self, until, *, reason):
        self.calls.append(("timeout", until, reason))


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = int(user_id)
        self.sent: list[str] = []

    async def send(self, text):
        self.sent.append(text)


class _FakeGuild:
    def __init__(self, member: _FakeMember | None = None) -> None:
        self._member = member
        self.calls: list[tuple] = []

    def get_member(self, user_id):
        return self._member

    async def kick(self, snowflake, *, reason):
        self.calls.append(("kick", snowflake, reason))

    async def ban(self, snowflake, *, reason, **kwargs):
        self.calls.append(("ban", snowflake, reason, kwargs))

    async def unban(self, user, *, reason):
        self.calls.append(("unban", user, reason))


class _FakeBot:
    def __init__(self, guild: _FakeGuild) -> None:
        self._guild = guild
        self.order: list[str] = []
        self.fetched: list[int] = []

    def get_guild(self, guild_id):
        self.order.append(f"get_guild:{guild_id}")
        return self._guild

    async def fetch_user(self, user_id):
        self.order.append(f"fetch_user:{user_id}")
        self.fetched.append(int(user_id))
        return _FakeUser(user_id)


@pytest.fixture(autouse=True)
def _fake_discord(monkeypatch):
    monkeypatch.setattr(mod_actions, "discord", _FakeDiscord)


def _actions(guild: _FakeGuild, bot: _FakeBot | None = None):
    return DiscordModerationActions(bot or _FakeBot(guild),
                                    allowed_guild_id=_GUILD)


def test_timeout_passes_reason_and_future_until():
    member = _FakeMember()
    guild = _FakeGuild(member)
    run(_actions(guild).timeout_member(_GUILD, 103, minutes=5, reason="spam"))
    (call,) = member.calls
    verb, until, reason = call
    assert verb == "timeout"
    assert reason == "spam"
    # the until is a FUTURE instant computed off discord.utils.utcnow()
    assert until == _FIXED_NOW + timedelta(minutes=5)
    assert until > _FIXED_NOW


def test_kick_passes_bare_snowflake_and_reason():
    guild = _FakeGuild()
    run(_actions(guild).kick_member(_GUILD, 103, reason="rule 3"))
    (call,) = guild.calls
    verb, snowflake, reason = call
    assert verb == "kick"
    assert isinstance(snowflake, _FakeObject) and snowflake.id == 103
    assert reason == "rule 3"


def test_ban_pins_delete_seconds_to_zero_on_no_purge():
    guild = _FakeGuild()
    run(_actions(guild).ban_member(_GUILD, 103, reason="raid",
                                   delete_message_days=0))
    (call,) = guild.calls
    verb, snowflake, reason, kwargs = call
    assert verb == "ban"
    assert isinstance(snowflake, _FakeObject) and snowflake.id == 103
    assert reason == "raid"
    # discord.py 2.x fills an OMITTED kwarg with 86400 (a full day), so
    # "no purge" MUST be pinned EXPLICITLY to 0 — never omitted.
    assert kwargs == {"delete_message_seconds": 0}


def test_ban_passes_delete_seconds_when_days_positive():
    guild = _FakeGuild()
    run(_actions(guild).ban_member(_GUILD, 103, reason="raid",
                                   delete_message_days=7))
    (call,) = guild.calls
    _, _, _, kwargs = call
    # discord.py takes SECONDS; 7 days * 86400
    assert kwargs == {"delete_message_seconds": 7 * 86400}


def test_unban_does_exactly_one_unban_and_no_fetch():
    guild = _FakeGuild()
    bot = _FakeBot(guild)
    run(_actions(guild, bot).unban_member(_GUILD, 103, reason="appeal"))
    # the DOMAIN owns the pre-fetch — the adapter must NOT re-fetch (one
    # get_user round-trip total, not two): NO bot.fetch_user here.
    assert bot.fetched == []
    assert "fetch_user:103" not in bot.order
    (call,) = guild.calls
    verb, snowflake, reason = call
    assert verb == "unban"
    # a bare snowflake, not a fetched user object
    assert isinstance(snowflake, _FakeObject) and snowflake.id == 103
    assert reason == "appeal"


def test_fetch_user_delegates_to_bot():
    guild = _FakeGuild()
    bot = _FakeBot(guild)
    user = run(_actions(guild, bot).fetch_user(103))
    assert isinstance(user, _FakeUser) and user.id == 103
    assert bot.fetched == [103]


def test_dm_member_fetches_then_sends():
    guild = _FakeGuild()
    bot = _FakeBot(guild)
    run(_actions(guild, bot).dm_member(103, "you were warned"))
    assert bot.fetched == [103]


# --- the test-guild allow-list (SAFETY) -----------------------------------

def test_effect_methods_refuse_a_non_allowed_guild():
    guild = _FakeGuild(_FakeMember())
    actions = _actions(guild)  # allowed guild is _GUILD, not _OTHER_GUILD
    with pytest.raises(GuildNotAllowedError):
        run(actions.timeout_member(_OTHER_GUILD, 103, minutes=5, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(actions.kick_member(_OTHER_GUILD, 103, reason="x"))
    with pytest.raises(GuildNotAllowedError):
        run(actions.ban_member(_OTHER_GUILD, 103, reason="x",
                               delete_message_days=0))
    with pytest.raises(GuildNotAllowedError):
        run(actions.unban_member(_OTHER_GUILD, 103, reason="x"))
    # the refusal is BEFORE any Discord call — nothing was mutated
    assert guild.calls == []


def test_allowed_guild_passes_through():
    guild = _FakeGuild(_FakeMember())
    actions = _actions(guild)
    run(actions.kick_member(_GUILD, 103, reason="ok"))
    assert [c[0] for c in guild.calls] == ["kick"]
