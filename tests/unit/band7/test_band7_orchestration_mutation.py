"""Band 7 — the ORDER-004 walking-skeleton drive for the ai TOOLS
PROFILE PICKERS (the slice D-0070 parked — the orchestration-mutation
slice, D-0072): boot the replay composition root (DB-free) and drive the
shipped views/ai/tools/* flows through the REAL pipeline — chooser click
→ scope-picker page, guild profile pick / channel/category pick → the
profile-choice page → the audited ``ai.set_*_orchestration`` op — plus
the shipped dry-run preview analyzer, asserting the shipped bytes
(reconstructed via search_code fragments; no golden pins these clicks).

The write lane's engine seam is recorded like the policy/behavior
skeletons; the pick → page → pick → handler → ack path is the real spine
end-to-end, and the ops/store/reader seams get their own pure tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

BLURPLE = 5793266
PAGE_FOOTER = "Administrator-only · in-place navigation."

_CHANNEL_ID = 555
_CATEGORY_ID = 777

#: the shipped _profile_options roster order (all_presets(): the
#: compatible default FIRST — the kernel seeds + the domain btd6/no_tools
#: registrations, alphabetical after the default).
_PROFILE_LABELS = [
    "Compatible (shipped behaviour)",
    "Balanced helper",
    "BTD6 grounded",
    "BTD6 grounded (strict)",
    "No tools (conversational)",
]
_PROFILE_KEYS = [
    "compatible_default", "balanced_helper", "btd6_grounded",
    "btd6_grounded_strict", "no_tools",
]


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
            roles=())

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    install_guild_scope_roster(_roster)
    yield h
    install_guild_scope_roster(None)  # type: ignore[arg-type]
    run(h.close())


@pytest.fixture()
def engine_recorder(monkeypatch):
    """Record the ai.set_*_orchestration invocations DB-free (the
    policy/behavior-picker skeletons' seam)."""
    from sb.kernel.workflow import engine
    from sb.spec.outcomes import SUCCESS

    calls: list = []

    async def fake_run(ref, ctx):
        calls.append((getattr(ref, "name", str(ref)), dict(ctx.params)))
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               before={},
                               after={"orchestration_write":
                                      {"generation": 1}})

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
    run(skeleton.click(message_id=960, custom_id="ai:tools",
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


def _open_profile_page(skeleton, scope_label: str, value: int, *,
                       message_id: int):
    picker = _open_picker(skeleton, scope_label, message_id=message_id)
    run(skeleton.click(message_id=message_id + 1,
                       custom_id=_select(picker)["custom_id"],
                       component_type=3, values=[str(value)],
                       persona="admin"))
    return _panel_payload(skeleton.take_calls())


# --- the scope-picker pages (chooser.py _tools_page_embed bytes) ---------------------


def test_tools_guild_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Guild", message_id=961)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Tools · guild default"
    assert embed["description"] == ("Pick the guild-default orchestration "
                                    "profile.")
    assert embed["color"] == BLURPLE
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    # the shipped GuildToolsProfileView select — presets only, NO clear
    # option (_profile_options(include_clear=scope != "guild")).
    assert select["type"] == 3
    assert select["placeholder"] == "Pick an orchestration profile…"
    assert [o["label"] for o in select["options"]] == _PROFILE_LABELS
    assert [o["value"] for o in select["options"]] == _PROFILE_KEYS
    assert select["options"][1]["description"].startswith(
        "General-purpose. Every scope-allowed tool")
    assert _rows(payload)[-1] == [("↩ AI Tools", 2)]


def test_tools_channel_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Channel", message_id=962)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Tools · channel"
    assert embed["description"] == ("Pick a channel — the next step lists "
                                    "the orchestration profiles.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    # the shipped ChannelToolsSelectView (native ChannelSelect, text only).
    assert select["type"] == 8
    assert select["channel_types"] == [0]
    assert "options" not in select
    assert select["placeholder"] == "Pick a channel to configure…"
    assert _rows(payload)[-1] == [("↩ AI Tools", 2)]


def test_tools_category_picker_page_shipped_bytes(skeleton):
    payload = _open_picker(skeleton, "Category", message_id=963)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Tools · category"
    assert embed["description"] == ("Pick a category — the next step lists "
                                    "the orchestration profiles.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    assert select["type"] == 3          # the D-0070 roster string select
    assert select["placeholder"] == "Pick a category to configure…"
    assert [o["label"] for o in select["options"]] == ["Main"]
    assert _rows(payload)[-1] == [("↩ AI Tools", 2)]


# --- the profile-choice page (scope_view.py _ProfileChoiceView) ----------------------


def test_channel_pick_opens_profile_page_shipped_bytes(skeleton):
    payload = _open_profile_page(skeleton, "Channel", _CHANNEL_ID,
                                 message_id=964)
    (embed,) = payload["embeds"]
    # the shipped _ProfileChoiceView prompt byte (the ephemeral content).
    assert embed["description"] == (
        f"Pick an orchestration profile for <#{_CHANNEL_ID}>.")
    assert embed["footer"]["text"] == PAGE_FOOTER
    select = _select(payload)
    assert select["type"] == 3
    assert select["placeholder"] == "Pick an orchestration profile…"
    options = select["options"]
    # presets + the shipped Clear (inherit) option, LAST.
    assert [o["label"] for o in options] == [*_PROFILE_LABELS,
                                             "Clear (inherit)"]
    assert options[-1]["value"] == "__inherit__"
    assert options[-1]["description"] == ("Remove this scope's profile; "
                                          "inherit the next layer.")
    assert _rows(payload)[-1] == [("↩ AI Tools", 2)]


# --- the profile picks (the audited writes + the shipped ack bytes) ------------------


def test_guild_profile_pick_runs_audited_op(skeleton, engine_recorder):
    payload = _open_picker(skeleton, "Guild", message_id=966)
    run(skeleton.click(message_id=967,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["balanced_helper"],
                       persona="admin"))
    calls = skeleton.take_calls()
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_guild_orchestration"
    assert params["profile_key"] == "balanced_helper"
    assert params["mutation_id"]
    assert calls[-1].payload["content"] == (
        "✅ Set **balanced_helper** as the orchestration profile for "
        "the guild (generation 1).")


def test_channel_profile_pick_runs_audited_op(skeleton, engine_recorder):
    payload = _open_profile_page(skeleton, "Channel", _CHANNEL_ID,
                                 message_id=968)
    run(skeleton.click(message_id=969,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["no_tools"],
                       persona="admin"))
    calls = skeleton.take_calls()
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_channel_orchestration"
    assert params["channel_id"] == _CHANNEL_ID
    assert params["profile_key"] == "no_tools"
    assert calls[-1].payload["content"] == (
        f"✅ Set **no_tools** as the orchestration profile for "
        f"<#{_CHANNEL_ID}> (generation 1).")


def test_category_clear_pick_writes_null(skeleton, engine_recorder):
    payload = _open_profile_page(skeleton, "Category", _CATEGORY_ID,
                                 message_id=970)
    run(skeleton.click(message_id=971,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["__inherit__"],
                       persona="admin"))
    calls = skeleton.take_calls()
    (op_name, params), = engine_recorder.calls
    assert op_name == "ai.set_category_orchestration"
    assert params["category_id"] == _CATEGORY_ID
    # the shipped clear semantics: NULL clears the override.
    assert params["profile_key"] is None
    assert calls[-1].payload["content"] == (
        f"✅ Cleared the orchestration profile for <#{_CATEGORY_ID}> "
        "(generation 1).")


def test_unknown_profile_key_refused_before_any_write(skeleton,
                                                      engine_recorder):
    payload = _open_picker(skeleton, "Guild", message_id=972)
    run(skeleton.click(message_id=973,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["bogus"],
                       persona="admin"))
    calls = skeleton.take_calls()
    # the shipped seam sentence on the shipped view echo shape
    # (❌ {type(exc).__name__}: {exc}).
    assert calls[-1].payload["content"] == (
        "❌ InvalidAIOrchestrationValueError: unknown orchestration "
        "profile 'bogus'; must be one of ['balanced_helper', "
        "'btd6_grounded', 'btd6_grounded_strict', 'compatible_default', "
        "'no_tools'] (or null to clear)")
    assert engine_recorder.calls == []


def test_profile_pick_gated_to_staff(skeleton, engine_recorder):
    """K6 re-resolves on the pick: a plain member driving the raw wire
    bytes is refused before any write (the shipped _require_admin gate's
    engine twin)."""
    payload = _open_picker(skeleton, "Guild", message_id=974)
    run(skeleton.click(message_id=975,
                       custom_id=_select(payload)["custom_id"],
                       component_type=3, values=["balanced_helper"],
                       persona="member"))
    calls = skeleton.take_calls()
    assert engine_recorder.calls == []
    assert "✅" not in (calls[-1].payload.get("content") or "")


# --- the dry-run preview (preview_view.py bytes) --------------------------------------


def test_preview_pick_renders_shipped_analyzer(skeleton):
    payload = _open_picker(skeleton, "Preview (dry-run)", message_id=976)
    (embed,) = payload["embeds"]
    assert embed["title"] == "Tools · preview (dry-run)"
    assert embed["description"] == ("Pick a channel to preview the "
                                    "resolved AI tool orchestration.")
    select = _select(payload)
    assert (select["type"], select["channel_types"]) == (8, [0])
    assert select["placeholder"] == "Pick a channel to preview…"
    run(skeleton.click(message_id=977,
                       custom_id=select["custom_id"],
                       component_type=3, values=[str(_CHANNEL_ID)],
                       persona="admin"))
    calls = skeleton.take_calls()
    (preview,) = calls[-1].payload["embeds"]
    assert preview["title"] == "AI Tools & Workflows — preview"
    assert preview["description"] == (
        f"Resolving orchestration for <#{_CHANNEL_ID}>.\n"
        "_Dry-run only — no provider call, no state touched._")
    fields = {f["name"]: f["value"] for f in preview["fields"]}
    # the DB-free root resolves the compatible default (the shipped
    # all-NULL guild posture).
    assert fields["Resolved profile"] == (
        "profile `compatible_default` (source `default`)\n"
        "toolsets: all\n"
        "tool choice: `auto`\n"
        "budget: hops=`4` calls=`∞` workflow=`analyze_execute_verify`")
    from sb.kernel.ai import tools_catalogue

    count = len(tools_catalogue.registered_tools())
    offered = fields[f"Offered tools ({count})"]
    assert (offered == "_(none)_") == (count == 0)
    assert "Withheld by profile" not in " ".join(fields)  # nothing narrowed
    assert fields["Precedence"] == (
        "· selected: key=compatible_default source=default\n"
        "· resolved: profile=compatible_default source=default "
        "toolsets=all tool_choice=auto budget(hops=4,calls=None)")
    assert preview["footer"]["text"] == (
        "dry_run=True · administrator-only · tools shown at full scope "
        "(per-caller scope narrows further)")


# --- the pure seams (ops validation + the store SQL + the K10 reader) -----------------


def test_leg_re_checks_profile_key_in_txn():
    """§4.1 seam authority: the leg refuses an unregistered key with the
    shipped InvalidAIOrchestrationValueError sentence body."""
    from sb.domain.ai import orchestration_ops as ops
    from sb.kernel.interaction.errors import ValidatorError

    ops.validate_profile_key(None)                    # clear always passes
    ops.validate_profile_key("no_tools")
    with pytest.raises(ValidatorError) as exc:
        ops.validate_profile_key("bogus")
    assert "unknown orchestration profile 'bogus'" in str(exc.value)
    assert "(or null to clear)" in str(exc.value)


def test_orchestration_upsert_is_column_only(monkeypatch):
    """The shipped migration-062 setter contract at the SQL seam: a fresh
    row is minted mode='inherit' and a conflicting row's mode/min_level/
    cooldown/instruction_profile_id are NEVER touched — only
    orchestration_profile (+ the audit stamps) move."""
    from sb.domain.ai import policy_store as store

    executed: list = []

    async def _fetchone(sql, params, conn=None):
        return None

    async def _execute(sql, params, conn=None):
        executed.append((sql, params))

    monkeypatch.setattr(store, "fetchone", _fetchone)
    monkeypatch.setattr(store, "execute", _execute)

    run(store.upsert_channel_orchestration(
        None, guild_id=1, channel_id=2, orchestration_profile="no_tools",
        updated_by=9))
    sql, params = executed[-1]
    assert "VALUES ($1, $2, 'inherit', $3, NOW(), $4)" in sql
    conflict = sql.split("ON CONFLICT")[1]
    assert "orchestration_profile=EXCLUDED.orchestration_profile" in conflict
    assert "mode=" not in conflict
    assert "min_level" not in conflict
    assert "instruction_profile_id" not in conflict
    assert params == (1, 2, "no_tools", 9)

    # the guild KV twin: clear (None) stores the empty string.
    run(store.set_guild_orchestration_profile(None, guild_id=1,
                                              profile_key=None))
    sql, params = executed[-1]
    assert "guild_settings" in sql
    assert params == (1, store.AI_ORCHESTRATION_PROFILE_KEY, "")


def test_profile_key_reader_widened_with_overlays(monkeypatch):
    """The K10 reader consumes the typed rows most-specific-first (the
    kernel applies channel → category → guild) and degrades to the
    band-1 answer on a store miss."""
    from sb.domain.ai import policy_store, readers

    async def _overlays(guild_id):
        return {10: "no_tools"}, {20: "btd6_grounded"}

    async def _guild_key(guild_id, conn=None):
        return True, "balanced_helper"

    monkeypatch.setattr(policy_store, "load_orchestration_overlays",
                        _overlays)
    monkeypatch.setattr(policy_store, "read_guild_orchestration_profile",
                        _guild_key)
    assert run(readers._profile_key_with_overlays(1, 10, 20)) == (
        "no_tools", "btd6_grounded", "balanced_helper")
    assert run(readers._profile_key_with_overlays(1, 11, None)) == (
        None, None, "balanced_helper")

    async def _boom(guild_id):
        raise RuntimeError("no db")

    monkeypatch.setattr(policy_store, "load_orchestration_overlays", _boom)
    base = run(readers._profile_key_with_overlays(1, 10, 20))
    # the band-1 fallback: no overlays, the declared-settings guild read
    # (None in the DB-free root).
    assert base == (None, None, None)


def test_explicit_guild_clear_suppresses_band1_fallback(monkeypatch):
    """codex #187 P2: a PRESENT-but-cleared KV row is authoritative — the
    band-1 guild_instruction_profile approximation serves ONLY while the
    orchestration row was never written (the ORACLE's clear resolved
    straight to the compatible default)."""
    from sb.domain.ai import policy_store, readers
    from sb.domain.settings import ai_readers as band1

    async def _overlays(guild_id):
        return {}, {}

    async def _band1(guild_id, channel_id, category_id):
        return None, None, "legacy_instruction_profile"

    monkeypatch.setattr(policy_store, "load_orchestration_overlays",
                        _overlays)
    monkeypatch.setattr(band1, "_profile_key", _band1)

    async def _cleared(guild_id, conn=None):
        return True, None            # row present, explicit clear

    monkeypatch.setattr(policy_store, "read_guild_orchestration_profile",
                        _cleared)
    assert run(readers._profile_key_with_overlays(1, 10, None)) == (
        None, None, None)
    assert run(readers.guild_orchestration_default(1)) is None

    async def _absent(guild_id, conn=None):
        return False, None           # never written → band-1 serves

    monkeypatch.setattr(policy_store, "read_guild_orchestration_profile",
                        _absent)
    assert run(readers._profile_key_with_overlays(1, 10, None)) == (
        None, None, "legacy_instruction_profile")
    assert (run(readers.guild_orchestration_default(1))
            == "legacy_instruction_profile")


def test_clear_option_survives_a_grown_registry(monkeypatch):
    """codex #187 P3: the 25-option cap truncates PRESETS, never the
    clear option."""
    from sb.domain.ai import orchestration_widgets as widgets

    fakes = tuple(SimpleNamespace(key=f"p{i:02d}", label=f"P {i}",
                                  description="d") for i in range(30))
    monkeypatch.setattr(widgets, "_profiles_shipped_order", lambda: fakes)
    rows = widgets._profile_option_rows(include_clear=True)
    assert len(rows) == 25
    assert rows[-1]["value"] == "__inherit__"
    assert [r["value"] for r in rows[:-1]] == [f"p{i:02d}"
                                               for i in range(24)]
    rows = widgets._profile_option_rows(include_clear=False)
    assert len(rows) == 25
    assert all(r["value"] != "__inherit__" for r in rows)


def test_chooser_current_mirrors_the_resolver(skeleton, monkeypatch):
    """codex #187 P2 twin: the tools chooser's Current field shows the
    SAME guild default the K10 reader serves (band-1 fallback included),
    never a divergent read."""
    from sb.domain.ai import readers

    async def _default(guild_id):
        return "no_tools"

    monkeypatch.setattr(readers, "guild_orchestration_default", _default)
    payload = _open_chooser(skeleton)
    fields = {f["name"]: f["value"]
              for f in payload["embeds"][0]["fields"]}
    assert fields["Current"].startswith("guild default: `no_tools`")


def test_orchestration_event_payload_shape():
    """The shipped _emit kwargs verbatim (guild_id + mutation_id — the
    events_catalogue contract the compat pin freezes)."""
    from sb.domain.ai import orchestration_ops as ops

    ctx = SimpleNamespace(guild_id=42, params={"mutation_id": "abc"})
    assert ops._changed_payload(ctx, None) == {"guild_id": 42,
                                               "mutation_id": "abc"}
