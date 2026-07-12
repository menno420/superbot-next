"""Channel-ops capture shapes (the D-0030 successor's enabler, D-0077).

Byte truth for the create/delete wire verbs lives in the CORPUS — the
setup/quicksetup slash goldens themselves record NO channel calls (the
trap-17 leaked-workspace reuse), so the vocabulary is pinned by the
sweeps that DID capture the ops (re-homed at the setup flip +
the D-0030 batch): goldens/setup/
sweep_setup.json (create_channel with the overwrite set AT creation,
INT masks, the created id minting off the shared allocator as
``<msg:1>``) and sweep_del.json (delete_channel, bare
channel_id+reason). These units pin the twin against exactly those
shapes (fake_http.create_channel / delete_channel mirrored)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sb.adapters.parity.transport import (
    ParityChannelStateActions,
    ParityTransport,
)
from sb.domain.channel.service import ChannelOverwrite

run = asyncio.run


class _Ids:
    def __init__(self) -> None:
        self._next = 100

    def allocate(self) -> int:
        self._next += 1
        return self._next


def _transport() -> ParityTransport:
    return ParityTransport(ids=_Ids(), clock=SimpleNamespace(now=None))


def test_create_text_channel_records_the_corpus_wire_shape():
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    cid = run(actions.create_text_channel(
        42, name="superbot-setup",
        overwrites=(ChannelOverwrite(42, 0, 0, 1024),
                    ChannelOverwrite(77, 0, 0, 1024),
                    ChannelOverwrite(88, 1, 93184, 0),
                    ChannelOverwrite(99, 1, 68608, 0)),
        parent_id=None, reason=None))
    (call,) = transport.calls
    assert call.method == "create_channel"
    # fake_http.create_channel args verbatim (type 0 = text channel)
    assert call.args == {"guild_id": 42, "type": 0, "reason": None}
    # the discord.py create options: overwrites ride IN the create
    # payload with INT masks (goldens/setup/sweep_setup.json pins
    # all four entries: @everyone deny-view, admin-role deny-view,
    # bot allow, invoker allow)
    assert call.payload == {
        "name": "superbot-setup",
        "parent_id": None,
        "permission_overwrites": [
            {"allow": 0, "deny": 1024, "id": 42, "type": 0},
            {"allow": 0, "deny": 1024, "id": 77, "type": 0},
            {"allow": 93184, "deny": 0, "id": 88, "type": 1},
            {"allow": 68608, "deny": 0, "id": 99, "type": 1},
        ]}
    # the minted id came off the allocator (the golden's `<msg:1>`)
    assert cid == 101
    assert transport.gaps == []


def test_created_channel_id_shares_the_message_id_allocator():
    """The golden weaves the created channel id into later sends
    (`Setup is ready in <#<msg:1>> …` with the step card minting
    `<msg:2>`) — ONE allocator, interleaved draws."""
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    cid = run(actions.create_text_channel(
        42, name="superbot-setup", overwrites=(), parent_id=None,
        reason=None))
    mid = transport.record_send(cid, {"content": "step card"})
    assert (cid, mid) == (101, 102)


def test_delete_channel_records_the_corpus_wire_shape():
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    run(actions.delete_channel(9001, reason=None))
    (call,) = transport.calls
    assert call.method == "delete_channel"
    # goldens/channel/sweep_del.json: bare args, no payload
    assert call.args == {"channel_id": 9001, "reason": None}
    assert call.payload is None


def test_rename_channel_records_edit_channel_with_name():
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    run(actions.rename_channel(9001, name="test", reason=None))
    (call,) = transport.calls
    # goldens/channel/sweep_rename.json: an edit_channel PATCH carrying
    # only `name`
    assert call.method == "edit_channel"
    assert call.args == {"channel_id": 9001, "reason": None}
    assert call.payload == {"name": "test"}


def test_set_topic_clear_records_an_explicit_null_topic():
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    run(actions.set_topic(9001, topic=None, reason=None))
    (call,) = transport.calls
    # goldens/channel/sweep_topic.json pins `{"topic": null}`
    assert call.method == "edit_channel"
    assert call.args == {"channel_id": 9001, "reason": None}
    assert call.payload == {"topic": None}


def test_move_channel_records_edit_channel_with_parent_id():
    transport = _transport()
    actions = ParityChannelStateActions(transport)
    run(actions.move_channel(9001, category_id=777, reason=None))
    (call,) = transport.calls
    assert call.method == "edit_channel"
    assert call.args == {"channel_id": 9001, "reason": None}
    assert call.payload == {"parent_id": 777}


def test_clone_channel_records_the_full_source_option_set():
    from sb.domain.channel.service import ChannelSnapshot

    transport = _transport()
    actions = ParityChannelStateActions(transport)
    source = ChannelSnapshot(channel_id=9001, name="test")
    cid = run(actions.clone_channel(42, name="test", source=source,
                                    reason=None))
    (call,) = transport.calls
    assert call.method == "create_channel"
    assert call.args == {"guild_id": 42, "type": 0, "reason": None}
    # goldens/channel/sweep_clone.json pins the discord.py
    # TextChannel.clone() body — all eight keys, the source's defaults
    assert call.payload == {
        "default_auto_archive_duration": 1440,
        "default_thread_rate_limit_per_user": 0,
        "name": "test",
        "nsfw": False,
        "parent_id": None,
        "permission_overwrites": [],
        "rate_limit_per_user": 0,
        "topic": None,
    }
    # the created id came off the shared allocator (the golden's <msg:N>)
    assert cid == 101


def test_collision_safe_name_matches_the_pinned_datapoint():
    from sb.domain.channel.service import collision_safe_name

    # goldens/channel/sweep_create.json: `test` taken -> `test-2`
    assert collision_safe_name("test", {"test"}) == "test-2"
    assert collision_safe_name("test", set()) == "test"
    assert collision_safe_name("test", {"test", "test-2"}) == "test-3"
