"""Band 7 — the ORDER-004 walking-skeleton drive for the ai POLICY SCOPE
PICKERS (the slice #160 parked, the policy-mutation slice): boot the replay
composition root (DB-free) and drive the shipped views/ai/policy/* flows
through the REAL pipeline — chooser click → picker page, roster pick →
edit page, Edit… → the shipped scope form (G-10 type 9), the wire-type-5
submit → the audited ``ai.set_*_policy`` op — asserting the shipped bytes
(views/ai/policy/{chooser,channel_view,category_view,role_view,
preview_view,list_view}.py @7f7628e1).

The WRITE legs (scoped upsert + bump_generation + audit in one
transaction) ride the live drive with real Postgres; here the workflow
engine seam is recorded so the suite stays DB-free like its band-7
siblings, while the pick → form → submit → handler → ack path is the real
spine end-to-end. The guild scope roster port gets a fixture world (the
live root installs the discord-backed reader)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

BLURPLE = 5793266
PAGE_FOOTER = "Administrator-only · in-place navigation."

_CHANNEL_ID = 555
_CATEGORY_ID = 777
_ROLE_ID = 888


@pytest.fixture()
def skeleton():
    from sb.adapters.parity.boot import Harness
    from sb.domain.ai.policy_widgets import (
        GuildScopeRoster,
        install_guild_scope_roster,
    )
    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    h = run(Harness.start(require_db=False))

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    async def _roster(guild_id):
        return GuildScopeRoster(
            text_channels=((_CHANNEL_ID, "general", _CATEGORY_ID),),
            categories=((_CATEGORY_ID, "Main"),),
            roles=((_ROLE_ID, "Member"),))

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    install_guild_scope_roster(_roster)
    yield h
    install_guild_scope_roster(None)  # type: ignore[arg-type]
    run(h.close())


@pytest.fixture()
def engine_recorder(monkeypatch):
    """Record the ai.set_*_policy invocations DB-free: the write lane's
    engine seam answers SUCCESS with a generation (the leg's after dict)
    while the pick → form → submit → handler path stays real."""
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []
    after: dict = {"policy_write": {"generation": 1}}

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={}, after=dict(after))

    monkeypatch.setattr(engine, "run", fake_run)
    return SimpleNamespace(calls=calls, after=after)


def _panel_payload(calls):
    assert [c.method for c in calls] == ["interaction_response",
                                         "followup_send"]
    return calls[1].payload


def _rows(payload):
    return [[(c.get("label") or c.get("placeholder"), c.get("style"))
             for c in row["components"]]
            for row in payload["components"]]


def _open_chooser(skeleton):
    run(skeleton.send_command("!aimenu", persona="admin"))
    skeleton.take_calls()
    run(skeleton.click(message_id=940, custom_id="ai:policy",
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


def _button(payload, label: str) -> str:
    return next(c["custom_id"] for row in payload["components"]
                for c in row["components"] if c.get("label") == label)


def _select(payload) -> dict:
    return next(c for row in payload["components"]
                for c in row["components"] if c.get("type") in (3, 8))


def _open_picker(skeleton, label: str, *, message_id: int):
    chooser = _open_chooser(skeleton)
    run(skeleton.click(message_id=message_id, custom_id=_button(chooser,
                                                                label),
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


def _open_edit(skeleton, picker_label: str, value: int, *,
               message_id: int):
    picker = _open_picker(skeleton, picker_label, message_id=message_id)
    run(skeleton.click(message_id=message_id + 1,
                       custom_id=_select(picker)["custom_id"],
                       component_type=3, values=[str(value)],
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


# --- the picker pages (chooser.py _scope_page_embed + the scope selects) -----------


def test_channel_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Channel", message_id=941)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Channel AI policy"
    assert embed["description"] == "Pick a channel to set its AI policy."
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    # the Discord-NATIVE channel picker (wire type 8 — the shipped
    # ChannelSelect shape, the #167 LogChannelSelectView lane): the client
    # supplies the options, none materialize.
    assert select["type"] == 8
    assert select["channel_types"] == [0]
    assert "options" not in select
    assert select["placeholder"] == "Pick a channel to configure…"
    assert _rows(payload)[-1] == [("↩ AI Policy", 2)]


def test_category_and_role_picker_pages_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Category", message_id=942)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Category AI policy"
    assert embed["description"] == "Pick a category to set its AI policy."
    select = _select(payload)
    assert select["type"] == 3          # roster-fed string select
    assert select["placeholder"] == "Pick a category to configure…"
    assert [o["label"] for o in select["options"]] == ["Main"]

    payload = _open_picker(skeleton, "Role", message_id=943)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Role AI policy"
    assert embed["description"] == "Pick a role to set its AI policy."
    select = _select(payload)
    assert select["placeholder"] == "Pick a role to configure…"
    assert [o["label"] for o in select["options"]] == ["@Member"]


def test_preview_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Effective policy", message_id=944)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Effective AI policy (dry-run)"
    assert embed["description"] == ("Pick a channel to see the effective "
                                    "AI policy as your user.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    assert (select["type"], select["channel_types"]) == (8, [0])
    assert select["placeholder"] == "Pick a channel to preview…"


# --- pick → edit page → the G-10 form issue ----------------------------------------


def test_channel_pick_opens_edit_page_and_form(skeleton, engine_recorder):
    payload = _open_edit(skeleton, "Channel", _CHANNEL_ID, message_id=945)
    (embed,) = payload["embeds"]
    assert embed["description"] == (f"Edit AI policy for <#{_CHANNEL_ID}> "
                                    "— **Edit…** opens the form.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    run(skeleton.click(message_id=946, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    calls = skeleton.take_calls()
    assert [c.method for c in calls] == ["interaction_response"]
    assert calls[0].payload["type"] == 9
    assert calls[0].payload["data"]["custom_id"] == "ai.policy_mode_form"
    assert engine_recorder.calls == []       # the open NEVER dispatches


def test_category_pick_carries_roster_name(skeleton):
    payload = _open_edit(skeleton, "Category", _CATEGORY_ID,
                         message_id=947)
    (embed,) = payload["embeds"]
    assert embed["description"] == ("Edit AI policy for category **Main** "
                                    "— **Edit…** opens the form.")


# --- the wire-type-5 submits (the shipped on_submit flows) --------------------------


def test_channel_submit_writes_and_speaks_shipped_ack(skeleton,
                                                      engine_recorder):
    """ChannelPolicyModal.on_submit's ack, verbatim — the optional bits
    only when set, the '(generation N)' tail from the write leg."""
    engine_recorder.after["policy_write"] = {"generation": 7}
    payload = _open_edit(skeleton, "Channel", _CHANNEL_ID, message_id=948)
    run(skeleton.click(message_id=949, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=949,
                              custom_id="ai.policy_mode_form",
                              fields={"mode": "mention_only",
                                      "min_level": "3",
                                      "cooldown_seconds": ""},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        f"✅ Updated AI policy for <#{_CHANNEL_ID}> · mode=`mention_only` "
        "· min_level=`3` (generation 7).")
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_channel_policy"
    assert params["channel_id"] == _CHANNEL_ID
    assert params["mode"] == "mention_only"
    assert params["min_level"] == 3
    assert params["cooldown_seconds"] is None    # blank = inherit (NULL)
    assert params["mutation_id"]


def test_category_submit_writes_and_speaks_shipped_ack(skeleton,
                                                       engine_recorder):
    payload = _open_edit(skeleton, "Category", _CATEGORY_ID,
                         message_id=950)
    run(skeleton.click(message_id=951, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=951,
                              custom_id="ai.policy_mode_form",
                              fields={"mode": "inherit", "min_level": "",
                                      "cooldown_seconds": "60"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "✅ Updated AI policy for category **Main** · mode=`inherit` "
        "· cooldown=`60s` (generation 1).")
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_category_policy"
    assert params["category_id"] == _CATEGORY_ID
    assert params["min_level"] is None
    assert params["cooldown_seconds"] == 60


def test_role_submit_writes_and_speaks_shipped_ack(skeleton,
                                                   engine_recorder):
    """RolePolicyModal.on_submit — decision lowercased (the shipped
    .strip().lower()), bypass_cooldown ALWAYS in the ack tail."""
    payload = _open_edit(skeleton, "Role", _ROLE_ID, message_id=952)
    (embed,) = payload["embeds"]
    assert embed["description"] == (f"Edit AI policy for <@&{_ROLE_ID}> "
                                    "— **Edit…** opens the form.")
    run(skeleton.click(message_id=953, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    calls = skeleton.take_calls()
    assert calls[0].payload["data"]["custom_id"] == "ai.policy_role_form"
    run(skeleton.modal_submit(message_id=953,
                              custom_id="ai.policy_role_form",
                              fields={"decision": " Allow ",
                                      "min_level_override": "",
                                      "bypass_cooldown": "yes"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        f"✅ Updated AI policy for <@&{_ROLE_ID}> · decision=`allow` "
        "· bypass_cooldown=`True` (generation 1).")
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_role_policy"
    assert params["role_id"] == _ROLE_ID
    assert params["decision"] == "allow"
    assert params["min_level_override"] is None
    assert params["bypass_cooldown"] is True


# --- the shipped refusals (validated BEFORE any write) ------------------------------


def _submit_mode(skeleton, fields, *, message_id):
    payload = _open_edit(skeleton, "Channel", _CHANNEL_ID,
                         message_id=message_id)
    run(skeleton.click(message_id=message_id + 1,
                       custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=message_id + 1,
                              custom_id="ai.policy_mode_form",
                              fields=fields, persona="admin"))
    return skeleton.take_calls()


def test_submit_refuses_unknown_mode(skeleton, engine_recorder):
    calls = _submit_mode(skeleton, {"mode": "banana", "min_level": "",
                                    "cooldown_seconds": ""},
                         message_id=954)
    assert calls[-1].payload["content"] == (
        "❌ mode must be one of: `inherit`, `always_reply`, "
        "`mention_only`, `disabled`")
    assert engine_recorder.calls == []


def test_submit_refuses_non_int_and_negative_levels(skeleton,
                                                    engine_recorder):
    calls = _submit_mode(skeleton, {"mode": "inherit", "min_level": "5x",
                                    "cooldown_seconds": ""},
                         message_id=956)
    assert calls[-1].payload["content"] == (
        "❌ min_level: must be an integer (got '5x')")
    calls = _submit_mode(skeleton, {"mode": "inherit", "min_level": "-3",
                                    "cooldown_seconds": ""},
                         message_id=958)
    assert calls[-1].payload["content"] == (
        "❌ min_level: must be >= 0 (got -3)")
    assert engine_recorder.calls == []


def test_role_submit_refuses_bad_decision_and_bypass(skeleton,
                                                     engine_recorder):
    payload = _open_edit(skeleton, "Role", _ROLE_ID, message_id=960)
    run(skeleton.click(message_id=961, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=961,
                              custom_id="ai.policy_role_form",
                              fields={"decision": "maybe",
                                      "min_level_override": "",
                                      "bypass_cooldown": ""},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "❌ decision must be one of: `allow`, `deny`, `inherit`")
    run(skeleton.click(message_id=961, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=961,
                              custom_id="ai.policy_role_form",
                              fields={"decision": "allow",
                                      "min_level_override": "",
                                      "bypass_cooldown": "zz"},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == (
        "❌ bypass_cooldown: expected yes/no (got 'zz')")
    assert engine_recorder.calls == []


def test_submit_without_open_hits_guard(skeleton, engine_recorder):
    """A stash miss (restart/eviction): no scope/target params — the
    guard answers, never a write."""
    run(skeleton.modal_submit(message_id=962,
                              custom_id="ai.policy_mode_form",
                              fields={"mode": "inherit", "min_level": "",
                                      "cooldown_seconds": ""},
                              persona="admin"))
    calls = skeleton.take_calls()
    assert calls[-1].payload["content"] == "❌ Edit requires a guild context."
    assert engine_recorder.calls == []


def test_submit_authority_re_resolves_on_the_modal_surface(skeleton,
                                                           engine_recorder):
    """K6 re-resolves on the SUBMIT re-entry: a plain member driving the
    raw wire bytes is refused before any write."""
    payload = _open_edit(skeleton, "Channel", _CHANNEL_ID, message_id=963)
    run(skeleton.click(message_id=964, custom_id=_button(payload, "Edit…"),
                       persona="admin"))
    skeleton.take_calls()
    run(skeleton.modal_submit(message_id=964,
                              custom_id="ai.policy_mode_form",
                              fields={"mode": "disabled", "min_level": "",
                                      "cooldown_seconds": ""},
                              persona="member"))
    calls = skeleton.take_calls()
    assert engine_recorder.calls == []
    assert "✅" not in (calls[-1].payload.get("content") or "")


# --- the preview + list pages ---------------------------------------------------------


def test_preview_pick_renders_dry_run_embed(skeleton):
    """The shipped chooser Preview path: title 'AI policy preview', the
    dual dry-run fields, NO Context field (snapshot=None on this path) —
    the DB-free root resolves the shipped GUILD_NOT_CONFIGURED deny."""
    picker = _open_picker(skeleton, "Effective policy", message_id=965)
    run(skeleton.click(message_id=966,
                       custom_id=_select(picker)["custom_id"],
                       component_type=3, values=[str(_CHANNEL_ID)],
                       persona="admin"))
    calls = skeleton.take_calls()
    (embed,) = calls[-1].payload["embeds"]
    assert embed["title"] == "AI policy preview"
    assert embed["description"].startswith(
        f"Resolving for <#{_CHANNEL_ID}> as ")
    names = [f["name"] for f in embed["fields"]]
    assert names == ["Without mention", "With @mention"]   # no Context
    assert "GUILD_NOT_CONFIGURED" in embed["fields"][0]["value"]
    assert embed["footer"]["text"] == "dry_run=True · administrator-only"


def test_list_click_renders_shipped_empty_state(skeleton):
    """list_view.build_list_embed's empty page, verbatim (the DB-free
    root reads zero override rows), Prev/Next disabled at the edges."""
    chooser = _open_chooser(skeleton)
    run(skeleton.click(message_id=967,
                       custom_id=_button(chooser, "List overrides"),
                       persona="admin"))
    payload = _panel_payload(skeleton.take_calls())
    (embed,) = payload["embeds"]
    assert embed["title"] == "AI policy overrides"
    assert embed["description"] == ("0 total override(s) across this "
                                    "guild (channel + category + role).")
    (field,) = embed["fields"]
    assert field["name"] == "No overrides"
    assert field["value"] == (
        "The guild uses only the baseline `ai_guild_policy` row. Use the "
        "Policy chooser to add channel / category / role overrides.")
    assert embed["footer"]["text"] == "Page 1 / 1 · administrator-only"
    buttons = {c.get("label"): c for row in payload["components"]
               for c in row["components"]}
    assert buttons["Prev"]["disabled"] is True
    assert buttons["Next"]["disabled"] is True


# --- the pure table (list pagination — shipped _PER_PAGE = 10) --------------------------


def test_list_fields_paginate_like_shipped():
    from sb.domain.ai.policy_widgets import PolicyEntry, build_list_fields

    entries = [PolicyEntry("channel", 100 + i, "mode=`inherit`")
               for i in range(12)]
    fields, page, total = build_list_fields(entries, page=1)
    assert (len(fields), page, total) == (10, 1, 2)
    assert fields[0][0] == "🔵 channel"
    assert fields[0][1] == "<#100> · mode=`inherit`"
    fields, page, total = build_list_fields(entries, page=2)
    assert (len(fields), page, total) == (2, 2, 2)
    # out-of-range pages clamp (the shipped max/min posture).
    fields, page, total = build_list_fields(entries, page=99)
    assert page == 2
    _, page, _ = build_list_fields([], page=5)
    assert page == 1


def test_ai_policy_command_derives_invoking_channel_category(monkeypatch):
    """codex P2 on this PR (verified real): the shipped `!ai policy` dry-ran
    against the REAL channel object, so its category rode into the resolver
    (ai_cog.ai_policy → build_effective_policy_embed's
    `getattr(channel, "category_id", None)`) — with the typed category
    overlays live, the command path must pass the invoking channel's
    category too (the chooser preview already did)."""
    from types import SimpleNamespace

    from sb.domain.ai import operator_cards, service

    seen: dict = {}

    async def fake_build(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(title="x")

    async def fake_card(req, embed, files=()):
        return None

    monkeypatch.setattr(operator_cards, "build_policy_embed", fake_build)
    monkeypatch.setattr(service, "_card", fake_card)

    req = SimpleNamespace(
        guild_id=1, channel_id=2,
        actor=SimpleNamespace(user_id=3, role_ids=(9,)),
        origin=SimpleNamespace(
            channel=SimpleNamespace(id=2, category_id=777)),
        args={})
    run(service.policy_view(req))
    assert seen["category_id"] == 777
    # a category-less channel (the capture world) stays None — the golden
    # trace carries no category line.
    seen.clear()
    req.origin = SimpleNamespace(channel=SimpleNamespace(id=2,
                                                         category_id=None))
    run(service.policy_view(req))
    assert seen["category_id"] is None
