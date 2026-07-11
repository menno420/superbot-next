"""Band 7 — the ORDER-004 walking-skeleton drive for the projmoon oracle
surface: boot the replay composition root (DB-free) and drive shipped
`!pm` commands (+ the `/pm` slash front door) through the REAL pipeline —
dispatch → handler → card/hub panel → presenter — asserting the
golden-pinned wire bytes.

The same drives replay against real Postgres via the golden corpus
(goldens/project_moon 10/10 + goldens/projectmoon 1/1 green at the
flip — tools/run_golden_parity.py)."""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

PURPLE = 10181046   # discord.Color.purple() — the shipped GAME_COLOR
GREYPLE = 10070709  # discord.Color.greyple() — the miss cards
FOOTER = "Project Moon · Limbus Company — summarized facts (verify-at-ingest)"


@pytest.fixture()
def skeleton():
    """The replay composition root, DB-free (the band-6 skeleton pattern —
    fixture-backed Limbus lookups need no store)."""
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


def test_walking_skeleton_pm_hub_end_to_end(skeleton):
    """`!pm` bare → the shipped LimbusBrowseView: the overview embed +
    eight session-minted buttons in rows 5+3, no nav row
    (goldens/project_moon/sweep_pm)."""
    run(skeleton.send_command("!pm", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == "🌑 Project Moon — Limbus knowledge"
    assert embed["color"] == PURPLE
    assert embed["footer"]["text"] == FOOTER
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Sinners (12)"] == (
        "Yi Sang, Faust, Don Quixote, Ryōshū, Meursault, Hong Lu, …")
    assert fields["Damage types (3)"] == "Slash, Pierce, Blunt"
    rows = [[(c["label"], c["style"]) for c in row["components"]]
            for row in payload["components"]]
    assert rows == [
        [("Overview", 1), ("Sinners", 2), ("Sins", 2),
         ("Damage types", 2), ("Mechanics", 2)],
        [("E.G.O grades", 2), ("Statuses", 2), ("Origins", 2)],
    ]
    overview = payload["components"][0]["components"][0]
    assert overview["emoji"]["name"] == "🌑"
    origins = payload["components"][1]["components"][-1]
    assert origins["emoji"]["name"] == "📖"


def test_walking_skeleton_pm_lookup_miss(skeleton):
    """`!pm lookup` (no query) → the shipped greyple footer-LESS miss
    card with the em-dash (goldens/project_moon/sweep_pm_lookup)."""
    run(skeleton.send_command("!pm lookup", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "🌑 Limbus lookup"
    assert embed["color"] == GREYPLE
    assert embed["description"] == (
        "I don't have a Limbus entry matching **—**. "
        "Try `!pm` to browse what I know.")
    assert "footer" not in embed
    assert calls[0].payload["components"] == []


def test_walking_skeleton_pm_sinner_list(skeleton):
    """`!pm sinner` (no name) → the shipped 12-field Sinners kind embed
    (goldens/project_moon/sweep_pm_sinner)."""
    run(skeleton.send_command("!pm sinner", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "🌑 Limbus — Sinners"
    assert embed["color"] == PURPLE
    assert embed["footer"]["text"] == FOOTER
    assert [f["name"] for f in embed["fields"]][:3] == [
        "Yi Sang", "Faust", "Don Quixote"]
    assert len(embed["fields"]) == 12


def test_walking_skeleton_pm_entry_hit(skeleton):
    """`!pm lookup don quixote` → the shipped entry card with the
    literary-origin field (the resolver's longest-token win)."""
    run(skeleton.send_command("!pm lookup don quixote", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "🌑 Don Quixote"
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Category"] == "Sinners"
    assert fields["Literary origin"] == (
        "*Don Quixote* — Miguel de Cervantes")


def test_walking_skeleton_slash_pm_ephemeral(skeleton):
    """`/pm` → the SAME browse panel as an ephemeral type-4 interaction
    response, flags 64 (goldens/projectmoon/sweep_slash_pm)."""
    run(skeleton.invoke_slash("pm", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response"]
    payload = calls[0].payload
    assert payload["type"] == 4
    assert payload["data"]["flags"] == 64
    (embed,) = payload["data"]["embeds"]
    assert embed["title"] == "🌑 Project Moon — Limbus knowledge"
    assert len(payload["data"]["components"]) == 2
