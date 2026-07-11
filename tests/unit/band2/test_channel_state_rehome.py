"""The moderation/channel `_unmapped` strays re-home — the channel-state
handlers (`!slowmode` / `!lock` / `!unlock`) + the modlogs card.

Byte truth lives in the goldens (goldens/channel/sweep_slowmode +
sweep_lock + sweep_unlock, goldens/moderation/sweep_modlogs); these units
pin the port seams the replay can't isolate: the wire-shaped port calls,
the shared-mutation_id event companions, the uninstalled-port honest
refusal (NO events on refusal), and the shipped summary phrases."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.spec.outcomes import BLOCKED, SUCCESS


def run(coro):
    return asyncio.run(coro)


class FakeActions:
    def __init__(self, fail: Exception | None = None) -> None:
        self.slowmodes: list[tuple] = []
        self.overwrites: list[tuple] = []
        self._fail = fail

    async def set_slowmode(self, channel_id, *, seconds, reason):
        if self._fail:
            raise self._fail
        self.slowmodes.append((channel_id, seconds, reason))

    async def set_overwrite(self, channel_id, *, target_id, allow, deny,
                            target_type, reason):
        if self._fail:
            raise self._fail
        self.overwrites.append(
            (channel_id, target_id, allow, deny, target_type, reason))


class Bus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, name, **payload):
        self.events.append((name, payload))


def _req(argv):
    return SimpleNamespace(args={"argv": tuple(argv)}, guild_id=42,
                           channel_id=1, actor=SimpleNamespace(user_id=7))


def _arm(monkeypatch=None, fail=None):
    from sb.domain.channel import service

    service.reset_channel_ports_for_tests()
    actions = FakeActions(fail=fail)
    bus = Bus()
    service.install_channel_actions(actions)
    service.subscribe(bus)

    async def lookup(guild_id, name):
        return 900_001 if name == "test" else None

    service.install_channel_lookup(lookup)
    return actions, bus


def _handler(name):
    from sb.domain.channel import handlers  # noqa: F401 — registers refs
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def test_slowmode_records_edit_and_companions():
    from sb.domain.channel import service

    actions, bus = _arm()
    reply = run(_handler("channel.slowmode")(_req(("test", "3"))))
    assert reply.outcome == SUCCESS
    # shipped success copy, verbatim (goldens/channel/sweep_slowmode)
    assert reply.user_message == 'Slowmode set to **3s** in "test".'
    assert actions.slowmodes == [(900_001, 3, None)]
    names = [n for n, _ in bus.events]
    assert names == ["audit.action_recorded", "channel.lifecycle_changed"]
    audit, lifecycle = bus.events[0][1], bus.events[1][1]
    # the shared mutation_id + the shipped summary/mutation_type bytes
    assert audit["mutation_id"] == lifecycle["mutation_id"]
    assert audit["mutation_type"] == "channel_set_slowmode"
    assert audit["new_value"] == "set slowmode 3s on channel 'test' (1/1 applied)"
    assert audit["target"] == "channel:900001"
    assert audit["actor_type"] == "admin" and audit["scope"] == "guild"
    assert lifecycle["operation"] == "set_slowmode"
    assert lifecycle["outcome"] == "success"
    assert lifecycle["applied"] == [900_001] and lifecycle["failed"] == []
    service.reset_channel_ports_for_tests()


def test_slowmode_zero_renders_disabled_copy():
    from sb.domain.channel import service

    actions, _bus = _arm()
    reply = run(_handler("channel.slowmode")(_req(("test", "0"))))
    assert reply.outcome == SUCCESS
    assert reply.user_message == 'Slowmode disabled in "test".'
    assert actions.slowmodes == [(900_001, 0, None)]
    service.reset_channel_ports_for_tests()


def test_lock_and_unlock_flip_the_send_messages_overwrite():
    from sb.domain.channel import service

    actions, bus = _arm()
    reply = run(_handler("channel.lock")(_req(("test",))))
    assert reply.outcome == SUCCESS
    assert reply.user_message == '"test" locked.'
    # deny send_messages (2048) for the default role (id == guild id)
    assert actions.overwrites == [(900_001, 42, 0, 2048, 0, None)]
    audit = bus.events[0][1]
    assert audit["mutation_type"] == "channel_set_overwrite"
    assert audit["new_value"] == ("set overwrite [send_messages] on 1 "
                                  "channel(s) for role 42 (1/1 applied)")

    reply = run(_handler("channel.unlock")(_req(("test",))))
    assert reply.outcome == SUCCESS
    assert reply.user_message == '"test" unlocked.'
    assert actions.overwrites[-1] == (900_001, 42, 2048, 0, 0, None)
    service.reset_channel_ports_for_tests()


def test_uninstalled_port_refuses_honestly_with_no_events():
    from sb.domain.channel import service

    service.reset_channel_ports_for_tests()
    bus = Bus()
    service.subscribe(bus)

    async def lookup(guild_id, name):
        return 900_001

    service.install_channel_lookup(lookup)
    reply = run(_handler("channel.lock")(_req(("test",))))
    assert reply.outcome == BLOCKED
    assert reply.user_message.startswith('Could not lock "test": ')
    reply = run(_handler("channel.slowmode")(_req(("test", "3"))))
    assert reply.outcome == BLOCKED
    assert reply.user_message.startswith('❌ Could not set slowmode in "test"')
    assert bus.events == []          # a refused edit emits NOTHING
    service.reset_channel_ports_for_tests()


def test_modlogs_card_renders_the_shipped_empty_state(monkeypatch):
    from sb.domain.moderation import panels, store

    async def no_rows(target_id, guild_id, limit=10):
        return []

    monkeypatch.setattr(store, "get_mod_logs", no_rows)
    ctx = SimpleNamespace(params={"modlogs_target_id": 5}, guild_id=42,
                          actor=SimpleNamespace(user_id=7))
    rendered = run(panels._render_modlogs_card(panels.modlogs_card_spec(), ctx))
    assert rendered.components == ()
    assert rendered.embed.title.startswith("📋 Mod Logs — ")
    # shipped empty-state byte, verbatim (goldens/moderation/sweep_modlogs)
    assert rendered.embed.description == "No moderation history found."
    assert rendered.embed.style_token == "orange"
    assert rendered.embed.fields == ()


def test_modlogs_card_renders_history_fields(monkeypatch):
    from sb.domain.moderation import panels, store

    async def rows(target_id, guild_id, limit=10):
        return [{"action": "warn", "timestamp": "2026-01-01 12:00:00",
                 "moderator_id": 9, "reason": "spam"}]

    monkeypatch.setattr(store, "get_mod_logs", rows)
    ctx = SimpleNamespace(params={"modlogs_target_id": 5}, guild_id=42,
                          actor=SimpleNamespace(user_id=7))
    rendered = run(panels._render_modlogs_card(panels.modlogs_card_spec(), ctx))
    assert rendered.embed.description == ""
    # the shipped field shape (cogs/moderation_cog.py modlogs loop)
    assert rendered.embed.fields == (
        ("WARN — 2026-01-01 12:00:00", "By <@9> | spam", False),)
