"""The kernel reaction ingress seam (band 6) — consumer registry +
dispatch posture, and the live adapter's duck-typed payload mapping."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.interaction.reactions import (
    ReactionEvent,
    dispatch_reaction,
    register_reaction_consumer,
    registered_reaction_consumers,
    reset_reaction_consumers_for_tests,
)

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = {name: None for name in registered_reaction_consumers()}
    reset_reaction_consumers_for_tests()
    yield
    reset_reaction_consumers_for_tests()
    # re-arm the manifests' import-time consumers for later suites
    from sb.domain.rps import tournament

    tournament.register_reaction_signup()
    del saved


def _event(**kw) -> ReactionEvent:
    base = dict(guild_id=1, channel_id=2, message_id=3, user_id=4,
                emoji="✅", added=True)
    base.update(kw)
    return ReactionEvent(**base)


def test_dispatch_fans_out_and_counts():
    seen: list[tuple[str, ReactionEvent]] = []

    async def a(event):
        seen.append(("a", event))

    async def b(event):
        seen.append(("b", event))

    register_reaction_consumer("a", a)
    register_reaction_consumer("b", b)
    assert registered_reaction_consumers() == ("a", "b")
    event = _event()
    assert run(dispatch_reaction(event)) == 2
    assert [name for name, _ in seen] == ["a", "b"]
    assert all(e is event for _, e in seen)


def test_consumer_fault_never_raises_and_others_still_run():
    ran = []

    async def bad(event):
        raise RuntimeError("boom")

    async def good(event):
        ran.append(event)

    register_reaction_consumer("bad", bad)
    register_reaction_consumer("good", good)
    assert run(dispatch_reaction(_event())) == 1   # only the clean one
    assert len(ran) == 1


def test_reregistration_is_idempotent_by_name():
    async def a(event):
        pass

    register_reaction_consumer("dup", a)
    register_reaction_consumer("dup", a)
    assert registered_reaction_consumers() == ("dup",)


# --- the live adapter's payload mapping + bot guards -------------------------------


class _Payload:
    def __init__(self, *, user_id=4, member=None):
        self.guild_id = 1
        self.channel_id = 2
        self.message_id = 3
        self.user_id = user_id
        self.member = member

        class _Emoji:
            name = "✅"

        self.emoji = _Emoji()


def test_live_feed_maps_raw_payload():
    from sb.adapters.discord.reaction_feed import handle_raw_reaction

    got = []

    async def consumer(event):
        got.append(event)

    register_reaction_consumer("probe", consumer)
    assert run(handle_raw_reaction(_Payload(), bot_user_id=999,
                                   added=True)) == 1
    (event,) = got
    assert (event.guild_id, event.channel_id, event.message_id,
            event.user_id, event.emoji, event.added) == (1, 2, 3, 4, "✅",
                                                         True)


def test_live_feed_ignores_bot_reactors():
    from sb.adapters.discord.reaction_feed import handle_raw_reaction

    got = []

    async def consumer(event):
        got.append(event)

    register_reaction_consumer("probe", consumer)

    class _BotMember:
        bot = True

    # the bot's own ✅ primer (user_id == bot id)
    assert run(handle_raw_reaction(_Payload(user_id=999), bot_user_id=999,
                                   added=True)) is None
    # any other bot member
    assert run(handle_raw_reaction(_Payload(member=_BotMember()),
                                   bot_user_id=999, added=True)) is None
    assert got == []
