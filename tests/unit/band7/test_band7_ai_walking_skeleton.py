"""Band 7 — the ORDER-004 walking-skeleton drive for the ai operator
surface: boot the replay composition root (DB-free) and drive the shipped
`!ai` / `!aimenu` commands (+ the `/aimenu` slash front door) through the
REAL pipeline — dispatch → handler → hub/card/settings panel → presenter —
asserting the golden-pinned wire bytes.

The same drives replay against real Postgres via the golden corpus
(goldens/ai 20/20 green at the flip — tools/run_golden_parity.py)."""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

BLURPLE = 5793266   # discord.Color.blurple() — the shipped AI panel accent
HUB_FOOTER = "!ai status / !ai diagnostics / !ai providers / !ai routing"


@pytest.fixture()
def skeleton():
    """The replay composition root, DB-free (the projmoon skeleton
    pattern — the operator views fail soft on the absent audit store)."""
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


def _hub_asserts(payload):
    (embed,) = payload["embeds"]
    assert embed["title"] == "💤 AI Platform"      # disabled-state emoji
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == HUB_FOOTER
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Enabled"] == "no"
    assert fields["Default provider"] == "deterministic"
    assert fields["Requests / failures"] == "0 / 0"
    rows = [[(c["custom_id"], c["label"], c["style"])
             for c in row["components"]]
            for row in payload["components"]]
    assert rows == [
        [("ai:refresh", "Refresh", 2), ("ai:diagnostics", "Diagnostics", 1),
         ("ai:providers", "Providers", 1), ("ai:routing", "Routing", 1)],
        [("ai:settings", "Settings", 3), ("ai:policy", "Policy", 3),
         ("ai:behavior", "Behavior", 3), ("ai:tools", "Tools", 3)],
        [("nav:help", "📚 Help", 2),
         ("nav:hub:admin", "↩ Administration", 2)],
    ]


def test_walking_skeleton_aimenu_hub(skeleton):
    """`!aimenu` → the shipped AIPanelView: the 💤 overview embed + the
    verbatim ai:* button rows + the standard nav row
    (goldens/ai/sweep_aimenu)."""
    run(skeleton.send_command("!aimenu", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    _hub_asserts(calls[0].payload)


def test_walking_skeleton_bare_ai_opens_hub(skeleton):
    """bare `!ai` → the SAME panel (the shipped invoke_without_command —
    goldens/ai/sweep_ai)."""
    run(skeleton.send_command("!ai", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    _hub_asserts(calls[0].payload)


def test_walking_skeleton_routing_card(skeleton):
    """`!ai routing` → the 17-task table in the shipped enum order with
    the deterministic-provider rows (goldens/ai/sweep_ai_routing)."""
    run(skeleton.send_command("!ai routing", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "AI Gateway — Routing"
    assert embed["color"] == BLURPLE
    assert [f["name"] for f in embed["fields"]][:3] == [
        "setup.suggest", "setup.explain", "platform.explain_status"]
    assert len(embed["fields"]) == 17
    assert embed["fields"][0]["value"] == (
        "provider: `deterministic`\nmodel: `gpt-4o-mini`\n"
        "timeout: `20.0s`\nenabled: `False`")


def test_walking_skeleton_policy_dry_run(skeleton):
    """`!ai policy` → the dual dry-run embed with the shipped
    GUILD_NOT_CONFIGURED trace (goldens/ai/sweep_ai_policy)."""
    run(skeleton.send_command("!ai policy", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "AI Effective Policy"
    assert embed["footer"]["text"] == "dry_run=True · administrator-only"
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Without mention"].startswith(
        "⛔ **hard-disabled** · `guild_not_configured`")
    assert ("guild_ai_gate: no ai_guild_policy row → deny "
            "GUILD_NOT_CONFIGURED") in fields["With @mention"]


def test_walking_skeleton_settings_page(skeleton):
    """`!ai settings` → the shipped SubsystemSettingsView page: the 🤖
    embed with the shipped defaults + the Back-to-Hub/Open-Panel row +
    the two session-minted selects (goldens/ai/sweep_ai_settings)."""
    run(skeleton.send_command("!ai settings", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == "🤖 AI Platform"
    assert embed["footer"]["text"].startswith(
        "Scalar edit + reset live · use the selects below.  guild_id=")
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert ("`ai_default_provider` = `'deterministic'` (`default`, "
            "default=`'deterministic'`, valid)") in fields["Scalar settings"]
    assert fields["Bindings"] == ("`audit_log_channel` — kind=`channel` "
                                  "(optional) cap=`ai.settings.configure`")
    assert fields["Existing command panels"] == "`!ai`, `!aimenu`"
    rows = payload["components"]
    assert [(c["custom_id"], c["label"]) for c in rows[0]["components"]] == [
        ("settings_subsystem.back_to_hub", "Back to Hub"),
        ("settings_subsystem.open_panel", "Open Panel")]
    edit = rows[1]["components"][0]
    assert edit["type"] == 3 and edit["placeholder"] == "Edit a setting…"
    assert [o["label"] for o in edit["options"]][:2] == [
        "ai_enabled", "ai_natural_language_enabled"]
    reset = rows[2]["components"][0]
    assert reset["placeholder"] == "Reset a setting to its default…"
    assert reset["options"][4]["description"] == "default=2"


def test_walking_skeleton_forget_after_chat(skeleton):
    """A plain chat message is observed into the K10 conversation buffer
    (the shipped bystander record); `!ai forget` then clears it — the
    shipped ✅ byte (goldens/ai/sweep_ai_forget's cross-case state)."""
    run(skeleton.send_command("hello walking skeleton", persona="member"))
    skeleton.take_calls()
    run(skeleton.send_command("!ai forget", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    assert calls[0].payload["content"].startswith(
        "✅ Cleared chat memory for <#")
    # a second forget finds the buffer gone.
    run(skeleton.send_command("!ai forget", persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["content"].startswith("No chat memory cached")


def test_walking_skeleton_slash_aimenu_ephemeral(skeleton):
    """`/aimenu` → the SAME panel as an ephemeral type-4 interaction
    response, flags 64 (goldens/ai/sweep_slash_aimenu)."""
    run(skeleton.invoke_slash("aimenu", persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response"]
    payload = calls[0].payload
    assert payload["type"] == 4
    assert payload["data"]["flags"] == 64
    (embed,) = payload["data"]["embeds"]
    assert embed["title"] == "💤 AI Platform"
    assert len(payload["data"]["components"]) == 3


def test_walking_skeleton_grouped_slash_drops(skeleton):
    """`/ai forget` (a grouped name no slash command carries) is DROPPED
    exactly like discord.py's unknown-interaction path — zero calls
    (goldens/ai/sweep_slash_ai_forget is empty for this reason)."""
    run(skeleton.invoke_slash("ai forget", persona="admin"))
    assert skeleton.take_calls() == []
