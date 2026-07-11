"""Band 7 — the ORDER-004 walking-skeleton drive for the ai POLICY/SETTINGS-
MUTATION surface (the slice #151/#155 parked): boot the replay composition
root (DB-free) and drive the shipped chooser PAGES + the S6/S7 settings
edit/reset widget flow through the REAL pipeline — hub click → chooser page,
settings select pick → widget page / dispatch — asserting the shipped bytes
(views/ai/{policy,behavior,tools}/chooser.py + views/settings/
subsystem_view.py dispatch_edit_setting @7f7628e1).

Click routes are golden-UNPINNED (no ai golden drives a click), so the
ORACLE sources pin these bytes directly; the WRITE legs (settings.set_scalar
— DB + audit in one transaction) ride the live drive with real Postgres,
this suite stays DB-free like its band-7 siblings.
"""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run

BLURPLE = 5793266
CHOOSER_FOOTER = "Administrator-only · ephemeral follow-up."


@pytest.fixture()
def skeleton():
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


def _panel_payload(calls):
    """The chooser/widget panel payload of a component click (ack +
    followup in the capture twin)."""
    assert [c.method for c in calls] == ["interaction_response",
                                         "followup_send"]
    return calls[1].payload


def _rows(payload):
    return [[(c.get("label") or c.get("placeholder"), c.get("style"))
             for c in row["components"]]
            for row in payload["components"]]


def _open_settings(skeleton):
    """`!ai settings` → (message payload, edit select cid, reset cid)."""
    run(skeleton.send_command("!ai settings", persona="admin"))
    calls = skeleton.take_calls()
    payload = calls[0].payload
    selects = [c["custom_id"] for row in payload["components"]
               for c in row["components"] if c.get("type") == 3]
    assert len(selects) == 2
    return payload, selects[0], selects[1]


def _click_hub(skeleton, action: str):
    """Open the hub, then click one shipped ai:* button (the verbatim
    persistent custom_id — the live component feed's route)."""
    run(skeleton.send_command("!aimenu", persona="admin"))
    skeleton.take_calls()
    run(skeleton.click(message_id=900, custom_id=f"ai:{action}",
                       persona="admin"))
    return skeleton.take_calls()


# --- the chooser PAGES (the shipped views/ai/* intro embeds) ----------------------


def test_policy_button_opens_shipped_policy_chooser(skeleton):
    payload = _panel_payload(_click_hub(skeleton, "policy"))
    (embed,) = payload["embeds"]
    assert embed["title"] == "AI Policy"
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == CHOOSER_FOOTER
    assert embed["description"].startswith(
        "Override the guild's AI policy for specific channels,")
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Channel"] == (
        "Pick a channel and set its mode "
        "(`inherit` / `always_reply` / `mention_only` / `disabled`).")
    assert fields["Role"] == ("Allow / deny / inherit and optional "
                              "min-level override per role.")
    assert "List overrides" in fields
    # the shipped button rows: the primary scope trio, the secondary
    # preview/list pair, the ↩ AI home back-route.
    assert _rows(payload) == [
        [("Channel", 1), ("Category", 1), ("Role", 1)],
        [("Effective policy", 2), ("List overrides", 2)],
        [("↩ AI home", 2)],
    ]


def test_behavior_button_opens_shipped_behavior_chooser(skeleton):
    payload = _panel_payload(_click_hub(skeleton, "behavior"))
    (embed,) = payload["embeds"]
    assert embed["title"] == "AI Behavior"
    assert embed["footer"]["text"] == CHOOSER_FOOTER
    assert embed["description"].startswith("Pick **what the AI should do")
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Channel"] == "Bind a preset to a single text channel."
    assert fields["Advanced"].startswith("Open the raw policy editor")
    assert _rows(payload) == [
        [("Channel", 1), ("Category", 1)],
        [("Preview (dry-run)", 2), ("Routing matrix", 2)],
        [("Advanced", 2)],
        [("↩ AI home", 2)],
    ]


def test_behavior_advanced_punts_to_policy_chooser(skeleton):
    """The shipped Advanced button swaps to the RAW policy chooser
    (views/ai/behavior/chooser.py advanced_btn)."""
    payload = _panel_payload(_click_hub(skeleton, "behavior"))
    advanced = [c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == "Advanced"]
    run(skeleton.click(message_id=901, custom_id=advanced[0],
                       persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    assert payload["embeds"][0]["title"] == "AI Policy"


def test_tools_button_opens_shipped_tools_chooser_with_current(skeleton):
    payload = _panel_payload(_click_hub(skeleton, "tools"))
    (embed,) = payload["embeds"]
    assert embed["title"] == "AI Tools & Workflows"
    assert embed["footer"]["text"] == CHOOSER_FOOTER
    assert embed["description"].startswith(
        "Choose **which tools the AI may use**")
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Guild / Channel / Category"].startswith(
        "Bind a built-in orchestration profile")
    # the shipped best-effort "Current" decoration: fresh guild → the
    # compatible default + zero overrides.
    assert fields["Current"] == ("guild default: "
                                 "`compatible_default (today)`\n"
                                 "overrides: 0 channel · 0 category")
    assert _rows(payload) == [
        [("Guild", 1), ("Channel", 1), ("Category", 1)],
        [("Preview (dry-run)", 2)],
        [("↩ AI home", 2)],
    ]


def test_chooser_scope_buttons_answer_honest_pending(skeleton):
    """Every scope picker is the policy/orchestration-mutation slices'
    port — the pending terminal names the parked page."""
    payload = _panel_payload(_click_hub(skeleton, "policy"))
    channel_btn = [c["custom_id"] for row in payload["components"]
                   for c in row["components"] if c.get("label") == "Channel"]
    run(skeleton.click(message_id=902, custom_id=channel_btn[0],
                       persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "The per-channel policy picker (mode inherit / always_reply / "
        "mention_only / disabled) ports with the policy-mutation slice.")


# --- the settings edit/reset dispatch (the shipped S6 routing) --------------------


def test_edit_pick_routes_presets_widget_shipped_bytes(skeleton):
    """An int scalar with the shipped input_hint=numeric_presets opens
    the NumericPresetsView page: the dispatcher prompt byte, one button
    per declared preset (current highlighted PRIMARY), Override… and the
    ↩ Back to Settings route."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=903, custom_id=edit_cid, component_type=3,
                       values=["ai_cooldown_seconds"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    (embed,) = payload["embeds"]
    assert embed["description"] == ("Pick a value for `ai.ai_cooldown_"
                                    "seconds` (current=`30`, default=`30`):")
    # the shipped roster (0, 15, 30, 60, 120, 300), five per row, the
    # current value (the declared default 30) primary.
    assert _rows(payload) == [
        [("0", 2), ("15", 2), ("30", 1), ("60", 2), ("120", 2)],
        [("300", 2), ("Override…", 2)],
        [("↩ Back to Settings", 2)],
    ]


def test_edit_pick_routes_enum_widget_shipped_bytes(skeleton):
    """A str scalar with allowed_values opens the enum select page: the
    dispatcher prompt + the shipped placeholder + the current value
    pre-marked (edit_enum.build_enum_select_view)."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=904, custom_id=edit_cid, component_type=3,
                       values=["ai_default_provider"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    (embed,) = payload["embeds"]
    assert embed["description"] == ("Pick a new value for "
                                    "`ai.ai_default_provider`:")
    select = payload["components"][0]["components"][0]
    assert select["type"] == 3
    assert select["placeholder"] == ("Pick a new value for "
                                     "ai_default_provider…")
    options = select["options"]
    assert [o["label"] for o in options] == ["deterministic", "openai",
                                             "anthropic"]
    assert options[0]["default"] is True
    assert options[0]["description"] == "current"
    assert not options[1].get("default")


def test_edit_pick_free_text_parks_on_modal_lane(skeleton):
    """The two free-form str scalars used the shipped TextSettingModal —
    the live modal-submit lane is dormant by design, so the pick answers
    the declared pending terminal."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=905, custom_id=edit_cid, component_type=3,
                       values=["ai_default_model"], persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "The free-form text editor for `ai.ai_default_model` (the shipped "
        "edit modal) ports with the modal-lane arming slice")


def test_edit_and_reset_unknown_setting_bytes(skeleton):
    """The shipped dispatch guard: an unknown pick answers
    ``❌ Unknown setting `ai.<name>`.`` on both selects."""
    _, edit_cid, reset_cid = _open_settings(skeleton)
    run(skeleton.click(message_id=906, custom_id=edit_cid, component_type=3,
                       values=["not_a_setting"], persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == "❌ Unknown setting `ai.not_a_setting`."
    run(skeleton.click(message_id=906, custom_id=reset_cid, component_type=3,
                       values=["not_a_setting"], persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == "❌ Unknown setting `ai.not_a_setting`."


def test_override_button_parks_on_modal_lane(skeleton):
    """The shipped Override… button opened the free-form number modal —
    parked with the modal-arming slice."""
    _, edit_cid, _ = _open_settings(skeleton)
    run(skeleton.click(message_id=907, custom_id=edit_cid, component_type=3,
                       values=["ai_minimum_level_default"], persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    override = [c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == "Override…"]
    run(skeleton.click(message_id=908, custom_id=override[0],
                       persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"].startswith(
        "The free-form override (the shipped number modal) ports with "
        "the modal-lane arming slice")


# --- the shipped routing/serialization tables (pure) ------------------------------


def test_widget_routing_matches_shipped_dispatch_table():
    """dispatch_edit_setting's routing for the WHOLE shipped ai page
    roster (input_hint first, then bool / str+allowed / free-form)."""
    from sb.domain.ai.settings_widgets import spec_for_key, widget_kind

    expected = {
        "ai_enabled": "toggle",
        "ai_natural_language_enabled": "toggle",
        "ai_memory_channel_scan_enabled": "toggle",
        "ai_default_provider": "enum",
        "ai_default_model": "text",
        "ai_guild_instruction_profile": "text",
        "ai_minimum_level_default": "presets",
        "ai_cooldown_seconds": "presets",
        "ai_fresh_user_mention_allowance": "presets",
        "ai_memory_window_minutes": "presets",
    }
    for key, kind in expected.items():
        spec = spec_for_key(key)
        assert spec is not None, key
        assert widget_kind(spec) == kind, key


def test_shipped_preset_rosters_verbatim():
    """The shipped cogs/ai/schemas.py presets, verbatim."""
    from sb.domain.ai.settings_widgets import spec_for_key

    assert spec_for_key("ai_minimum_level_default").presets == (
        0, 1, 2, 3, 5, 10)
    assert spec_for_key("ai_cooldown_seconds").presets == (
        0, 15, 30, 60, 120, 300)
    assert spec_for_key("ai_fresh_user_mention_allowance").presets == (
        0, 1, 3, 5, 10)
    assert spec_for_key("ai_memory_window_minutes").presets == (
        0, 15, 30, 60, 120)


def test_kv_serialization_is_the_read_path_inverse():
    """The shipped `_serialise` spellings — the exact tokens the readers
    coerce back ("true"/"false", str(int))."""
    from sb.domain.ai.settings_widgets import _serialize, spec_for_key

    assert _serialize(spec_for_key("ai_enabled"), True) == "true"
    assert _serialize(spec_for_key("ai_enabled"), False) == "false"
    assert _serialize(spec_for_key("ai_cooldown_seconds"), 60) == "60"
    assert _serialize(spec_for_key("ai_default_provider"),
                      "openai") == "openai"
