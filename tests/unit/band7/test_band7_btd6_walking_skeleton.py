"""Band 7 — the ORDER-004 walking-skeleton drive for the btd6 oracle
surface: boot the replay composition root (DB-free) and drive shipped
`!btd6` commands through the REAL pipeline — dispatch → handler → card
panel → presenter — asserting the golden-pinned wire bytes.

The same drives replay against real Postgres via the golden corpus
(goldens/btd6, 39/39 green at the flip — tools/run_golden_parity.py)."""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

GREEN = 3066993       # discord.Color.green()
LIGHT_GREY = 9936031  # discord.Color.light_grey()


@pytest.fixture()
def skeleton():
    """The replay composition root, DB-free (the band-6 skeleton pattern —
    dataset-backed btd6 lookups need no store)."""
    from sb.adapters.parity.boot import Harness
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h
    run(h.close())


def test_walking_skeleton_btd6_round_end_to_end(skeleton):
    """`!btd6 round 3` → the shipped round card, byte-for-byte
    (goldens/btd6/sweep_btd6_round)."""
    run(skeleton.send_command("!btd6 round 3", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "Round 3 — danger: trivial"
    assert embed["color"] == GREEN
    assert embed["description"] == "25 Red Bloon, 5 Blue Bloon. RBE 35."
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Economy"] == (
        "RBE **35** · Cash **$138** (cumulative **$1,046**) · XP **80**")
    assert fields["Bloons this round — 30 spawned"] == (
        "`   10×` Red Bloon\n`    5×` Blue Bloon\n`   15×` Red Bloon")
    assert embed["footer"]["text"] == "BTD6 data v1.0 (game v55.1)"
    assert calls[0].payload["components"] == []


def test_walking_skeleton_btd6_hub_end_to_end(skeleton):
    """`!btd6` bare → the shipped hub panel: three rows on the PERSISTENT
    btd6:* ids + the standard-nav Help slot (goldens/btd6/sweep_btd6menu)."""
    run(skeleton.send_command("!btd6", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == "🐵 BTD6 Assistant"
    assert embed["color"] == GREEN
    assert embed["footer"]["text"] == (
        "!btd6 ask <q> · !btd6 tower <n> · !btd6 round <N> · "
        "!btd6 leaderboard <race|boss> · !btd6 status • ctx=btd6_hub:main")
    rows = [[c["custom_id"] for c in row["components"]]
            for row in payload["components"]]
    assert rows == [
        ["btd6:ask", "btd6:events", "btd6:units", "btd6:rounds"],
        ["btd6:maps", "btd6:strategy", "btd6:status", "btd6:admin"],
        ["nav:help"],
    ]
    ask = payload["components"][0]["components"][0]
    assert (ask["label"], ask["style"], ask["emoji"]["name"]) == (
        "Ask", 3, "🧠")


def test_walking_skeleton_btd6_unresolved_ask(skeleton):
    """`!btd6 tower test` → the shipped low-confidence refusal card
    (goldens/btd6/sweep_btd6_tower — the version-stamped honesty floor)."""
    run(skeleton.send_command("!btd6 tower test", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "No BTD6 entities recognised"
    assert embed["color"] == LIGHT_GREY
    assert embed["footer"]["text"] == "BTD6 data v1.0 (game v55.1)"


def test_walking_skeleton_btd6_bare_group_is_silent(skeleton):
    """`!btd6 events` (bare group) replies nothing — the shipped
    send_help produced no captured call (goldens/btd6/sweep_btd6_events)."""
    run(skeleton.send_command("!btd6 events", persona="admin"))
    assert skeleton.take_calls() == []
