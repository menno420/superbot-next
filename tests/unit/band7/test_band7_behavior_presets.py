"""Band 7 — the ORDER-004 walking-skeleton drive for the ai BEHAVIOR
PRESET PICKERS (the slice D-0070 parked — D-0071): boot the replay
composition root (DB-free) and drive the shipped views/ai/behavior/*
flows through the REAL pipeline — chooser click → scope-picker page,
channel/category pick → the preset-picker page, preset pick → the
audited ``ai.set_*_policy`` op with the profile binding — asserting the
shipped bytes (reconstructed via search_code fragments; no golden pins
these clicks).

The catalog reads ride a fixture twin of the migration-0030 seed rows
(the DB-free posture — the live drive proves the row-bearing reads);
the write lane's engine seam is recorded like the policy-picker
skeleton, while the pick → page → pick → handler → ack path is the real
spine end-to-end."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

BLURPLE = 5793266
PAGE_FOOTER = "Administrator-only · in-place navigation."

_CHANNEL_ID = 555
_CATEGORY_ID = 777

#: the migration-0030 seed twin (ids in the seed's insert order; names +
#: is_preset the oracle 044 shape).
_SEED_ROWS = [
    {"id": 1, "guild_id": None, "name": "disabled", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 2, "guild_id": None, "name": "mention_only_helper", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 3, "guild_id": None, "name": "helpful_channel", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 4, "guild_id": None, "name": "btd6_focused", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 5, "guild_id": None, "name": "quiet_btd6_focused", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 6, "guild_id": None, "name": "staff_diagnostics", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
    {"id": 7, "guild_id": None, "name": "support_triage", "body": "…",
     "scope": "system", "feature_key": None, "is_preset": True},
]


@pytest.fixture()
def seed_rows(monkeypatch):
    """The DB-free catalog: policy_store's preset reads answer the
    migration-0030 seed (alphabetical, is_preset only — the real reads'
    contract)."""
    from sb.domain.ai import policy_store

    rows = sorted(_SEED_ROWS, key=lambda r: r["name"])

    async def _list(conn=None):
        return [dict(r) for r in rows]

    async def _get(preset_id, conn=None):
        for r in rows:
            if r["id"] == int(preset_id) and r["is_preset"]:
                return dict(r)
        return None

    monkeypatch.setattr(policy_store, "list_preset_profiles", _list)
    monkeypatch.setattr(policy_store, "get_preset_profile", _get)
    return rows


@pytest.fixture()
def skeleton(seed_rows):
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
            roles=())

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    install_guild_scope_roster(_roster)
    yield h
    install_guild_scope_roster(None)  # type: ignore[arg-type]
    run(h.close())


@pytest.fixture()
def engine_recorder(monkeypatch):
    """Record the ai.set_*_policy invocations DB-free (the policy-picker
    skeleton's seam)."""
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={},
                               after={"policy_write": {"generation": 1}})

    monkeypatch.setattr(engine, "run", fake_run)
    return SimpleNamespace(calls=calls)


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
    run(skeleton.click(message_id=940, custom_id="ai:behavior",
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
    run(skeleton.click(message_id=message_id,
                       custom_id=_button(chooser, label),
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


def _open_preset_page(skeleton, scope_label: str, value: int, *,
                      message_id: int):
    picker = _open_picker(skeleton, scope_label, message_id=message_id)
    run(skeleton.click(message_id=message_id + 1,
                       custom_id=_select(picker)["custom_id"],
                       component_type=3, values=[str(value)],
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


# --- the scope-picker pages (chooser.py _behavior_page_embed bytes) -----------------


def test_behavior_channel_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Channel", message_id=941)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Behavior · channel"
    assert embed["description"] == ("Pick a channel — the next step lists "
                                    "the available presets.")
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    # the shipped _BehaviorChannelSelect (native ChannelSelect, text only).
    assert select["type"] == 8
    assert select["channel_types"] == [0]
    assert "options" not in select
    assert select["placeholder"] == "Pick a channel…"
    assert _rows(payload)[-1] == [("↩ AI Behavior", 2)]


def test_behavior_category_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Category", message_id=942)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Behavior · category"
    assert embed["description"] == ("Pick a category — the next step lists "
                                    "the available presets.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    assert select["type"] == 3          # the D-0070 roster string select
    assert select["placeholder"] == "Pick a category…"
    assert [o["label"] for o in select["options"]] == ["Main"]
    assert _rows(payload)[-1] == [("↩ AI Behavior", 2)]


def test_behavior_preview_page_reuses_dry_run(skeleton):
    payload = _open_picker(skeleton, "Preview (dry-run)", message_id=943)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Behavior · preview (dry-run)"
    assert embed["description"] == ("Pick a channel to preview the "
                                    "effective AI policy as your user.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    assert (select["type"], select["channel_types"]) == (8, [0])
    assert select["placeholder"] == "Pick a channel to preview…"
    # the pick runs the SAME shipped dry-run the policy preview runs
    # (behavior/chooser.py imported PreviewChannelSelectView verbatim).
    run(skeleton.click(message_id=944,
                       custom_id=select["custom_id"],
                       component_type=3, values=[str(_CHANNEL_ID)],
                       persona="admin"))
    calls = skeleton.take_calls()
    (preview,) = calls[-1].payload["embeds"]
    assert preview["title"] == "AI policy preview"
    names = [f["name"] for f in preview["fields"]]
    assert names == ["Without mention", "With @mention"]


# --- the preset-picker page (preset_picker.py build_preset_picker_embed) ------------


def test_channel_pick_opens_preset_page_shipped_bytes(skeleton):
    payload = _open_preset_page(skeleton, "Channel", _CHANNEL_ID,
                                message_id=945)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Pick a Behavior preset"
    assert embed["description"] == (
        f"Selecting a preset binds it to **channel <#{_CHANNEL_ID}>** and "
        "writes through the existing policy chokepoint. Existing "
        "min_level / cooldown overrides for that scope are preserved.")
    # one field per seeded preset, alphabetical, the shipped shape.
    names = [f["name"] for f in embed["fields"]]
    assert names == [
        "`btd6_focused` · mode=`always_reply`",
        "`disabled` · mode=`disabled`",
        "`helpful_channel` · mode=`always_reply`",
        "`mention_only_helper` · mode=`mention_only`",
        "`quiet_btd6_focused` · mode=`mention_only`",
        "`staff_diagnostics` · mode=`mention_only`",
        "`support_triage` · mode=`mention_only`",
    ]
    assert embed["fields"][1]["value"] == "No AI replies in this scope"
    select = _select(payload)
    assert select["type"] == 3
    assert select["placeholder"] == "Pick a preset…"
    options = select["options"]
    assert [o["label"] for o in options] == [
        "btd6_focused", "disabled", "helpful_channel",
        "mention_only_helper", "quiet_btd6_focused", "staff_diagnostics",
        "support_triage"]
    assert options[2]["description"] == "Full natural-language behavior"
    assert _rows(payload)[-1] == [("↩ AI Behavior", 2)]


def test_category_pick_carries_roster_name(skeleton):
    payload = _open_preset_page(skeleton, "Category", _CATEGORY_ID,
                                message_id=947)
    (embed,) = payload["embeds"]
    assert embed["description"].startswith(
        "Selecting a preset binds it to **category **Main**** ")


# --- the preset pick (the audited apply + the shipped ack bytes) --------------------


def test_preset_pick_applies_channel_scope(skeleton, engine_recorder):
    payload = _open_preset_page(skeleton, "Channel", _CHANNEL_ID,
                                message_id=949)
    run(skeleton.click(message_id=950,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["helpful_channel"],
                       persona="admin"))
    calls = skeleton.take_calls()
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_channel_policy"
    assert params["channel_id"] == _CHANNEL_ID
    assert params["mode"] == "always_reply"
    assert params["instruction_profile_id"] == 3
    # the preservation contract: min_level/cooldown keys ABSENT → the
    # store's UNCHANGED sentinel (the shipped picker copy byte).
    assert "min_level" not in params
    assert "cooldown_seconds" not in params
    assert params["mutation_id"]
    assert calls[-1].payload["content"] == (
        "✅ Bound preset `helpful_channel` (mode `always_reply`) to "
        f"channel **<#{_CHANNEL_ID}>**. "
        f"mutation_id=`{params['mutation_id']}`.")


def test_preset_pick_applies_category_scope(skeleton, engine_recorder):
    payload = _open_preset_page(skeleton, "Category", _CATEGORY_ID,
                                message_id=951)
    run(skeleton.click(message_id=952,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["quiet_btd6_focused"],
                       persona="admin"))
    calls = skeleton.take_calls()
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_category_policy"
    assert params["category_id"] == _CATEGORY_ID
    assert params["mode"] == "mention_only"
    assert params["instruction_profile_id"] == 5
    assert calls[-1].payload["content"] == (
        "✅ Bound preset `quiet_btd6_focused` (mode `mention_only`) to "
        "category **Main**. "
        f"mutation_id=`{params['mutation_id']}`.")


def test_unknown_preset_key_refused_before_any_write(skeleton,
                                                     engine_recorder):
    payload = _open_preset_page(skeleton, "Channel", _CHANNEL_ID,
                                message_id=953)
    run(skeleton.click(message_id=954,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["nope"],
                       persona="admin"))
    calls = skeleton.take_calls()
    # the shipped refusal byte, verbatim.
    assert calls[-1].payload["content"] == "❌ Unknown preset `nope`."
    assert engine_recorder.calls == []


def test_preset_pick_gated_to_staff(skeleton, engine_recorder):
    """K6 re-resolves on the pick: a plain member driving the raw wire
    bytes is refused before any write (the shipped member_is_admin
    gate's engine twin)."""
    payload = _open_preset_page(skeleton, "Channel", _CHANNEL_ID,
                                message_id=955)
    run(skeleton.click(message_id=956,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["helpful_channel"],
                       persona="member"))
    calls = skeleton.take_calls()
    assert engine_recorder.calls == []
    assert "✅" not in (calls[-1].payload.get("content") or "")


# --- the pure seams (catalog + apply_preset + the store sentinel) --------------------


def test_catalog_carries_the_seven_shipped_presets():
    from sb.domain.ai.behavior_presets import _PRESET_CATALOG

    assert {k: e.recommended_mode for k, e in _PRESET_CATALOG.items()} == {
        "disabled": "disabled",
        "mention_only_helper": "mention_only",
        "helpful_channel": "always_reply",
        "btd6_focused": "always_reply",
        "quiet_btd6_focused": "mention_only",
        "staff_diagnostics": "mention_only",
        "support_triage": "mention_only",
    }
    assert (_PRESET_CATALOG["staff_diagnostics"].headline
            == "Operator diagnostics, mention-only")


def test_list_behavior_presets_surfaces_uncatalogued_rows(seed_rows,
                                                           monkeypatch):
    """The shipped fallback: a DB row the catalog does not recognise is
    surfaced, never dropped."""
    from sb.domain.ai import behavior_presets as presets
    from sb.domain.ai import policy_store

    rows = [dict(r) for r in seed_rows] + [{
        "id": 99, "guild_id": None, "name": "mystery", "body": "…",
        "scope": "system", "feature_key": None, "is_preset": True}]

    async def _list(conn=None):
        return rows

    monkeypatch.setattr(policy_store, "list_preset_profiles", _list)
    out = run(presets.list_behavior_presets())
    mystery = next(p for p in out if p.key == "mystery")
    assert mystery.headline == "(uncatalogued preset 'mystery')"
    assert mystery.recommended_mode == "mention_only"


def test_apply_preset_refuses_bad_scope_and_unknown_preset(seed_rows):
    from sb.domain.ai import behavior_presets as presets

    req = SimpleNamespace(guild_id=1, request_id="r", confirmed=False,
                          actor=SimpleNamespace(user_id=3), args={})
    with pytest.raises(presets.InvalidBehaviorPresetScopeError) as exc:
        run(presets.apply_preset(req, scope="guild", target_id=1,
                                 preset_id=1))
    assert "scope must be one of ['category', 'channel']" in str(exc.value)
    with pytest.raises(presets.UnknownBehaviorPresetError) as exc:
        run(presets.apply_preset(req, scope="channel", target_id=1,
                                 preset_id=404))
    assert str(exc.value) == ("preset_id=404 not found or not flagged "
                              "is_preset=True")


def test_upsert_sentinel_keeps_unowned_columns_out_of_the_write(monkeypatch):
    """The PR-C-pre UNCHANGED contract at the SQL seam: an UNCHANGED
    column is neither inserted nor conflict-touched — the modal lane
    (explicit min_level/cooldown, no profile) and the preset lane
    (profile, no min_level/cooldown) build disjoint column sets."""
    from sb.domain.ai import policy_store as store

    executed: list = []

    async def _fetchone(sql, params, conn=None):
        return None

    async def _execute(sql, params, conn=None):
        executed.append((sql, params))

    monkeypatch.setattr(store, "fetchone", _fetchone)
    monkeypatch.setattr(store, "execute", _execute)

    # the #177 modal lane — byte-identical column set to the pre-slice SQL.
    run(store.upsert_channel_policy(
        None, guild_id=1, channel_id=2, mode="inherit", min_level=3,
        cooldown_seconds=None, updated_by=9))
    sql, params = executed[-1]
    assert "min_level" in sql and "cooldown_seconds" in sql
    assert "instruction_profile_id" not in sql
    assert params == (1, 2, "inherit", 3, None, 9)

    # the behavior-preset lane — profile in, min_level/cooldown untouched.
    run(store.upsert_category_policy(
        None, guild_id=1, category_id=4, mode="always_reply",
        instruction_profile_id=7, updated_by=9))
    sql, params = executed[-1]
    assert "instruction_profile_id=EXCLUDED.instruction_profile_id" in sql
    assert "min_level" not in sql.split("ON CONFLICT")[1]
    assert "cooldown_seconds" not in sql
    assert params == (1, 4, "always_reply", 7, 9)


def test_profile_binding_re_checked_in_txn(monkeypatch):
    """§4.1 seam authority: the leg refuses a profile id that names no
    seeded is_preset row (the shipped UnknownBehaviorPresetError sentence
    on the ValidatorError)."""
    from sb.domain.ai import policy_ops, policy_store
    from sb.kernel.interaction.errors import ValidatorError

    async def _get(preset_id, conn=None):
        return None

    monkeypatch.setattr(policy_store, "get_preset_profile", _get)
    ctx = SimpleNamespace(params={"instruction_profile_id": 404})
    with pytest.raises(ValidatorError) as exc:
        run(policy_ops._profile_binding(None, ctx))
    # ValidatorError's envelope prefixes "invalid argument: " — the
    # shipped sentence body rides inside it.
    assert str(exc.value).endswith(
        "preset_id=404 not found or not flagged is_preset=True")
    # ABSENT key → the UNCHANGED sentinel (the modal lane's posture).
    ctx = SimpleNamespace(params={})
    assert run(policy_ops._profile_binding(None, ctx)) is policy_store.UNCHANGED
