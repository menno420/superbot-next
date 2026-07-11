"""Band 7 final slice — the AI surface: review loop + presets, the last
K10 composition seams (guild-policy overlay, preset short-circuit,
message shell, history scanner), the round-cash answer workflow, domain
orchestration profiles, and the BTD6 tool rows."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from sb.domain.ai import ops as ai_ops
from sb.domain.ai import readers, review, round_cash
from sb.domain.ai import normalize
from sb.kernel.ai import flags, orchestration, router, routing, tasks
from sb.kernel.ai import tools_catalogue
from sb.kernel.config import preflight

run = asyncio.run

BASE_ENV = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "x",
    "DATABASE_URL": "postgresql://u@localhost/db",
    "SB_DATA_PLANE": "test",
    "SB_TEST_DB_HOSTS": "localhost",
}


@pytest.fixture(autouse=True)
def _reset_ai_state():
    yield
    flags.reset_flags_for_tests()
    routing.clear_overrides()
    tasks.clear_tasks_for_tests()
    router.clear_probes_for_tests()
    review.reset_registry_for_tests()
    from sb.kernel.ai import feature_facts, nl_engine
    from sb.kernel.ai.gateway import (
        reset_default_gateway,
        reset_guild_policy_reader,
    )
    from sb.kernel.interaction import egress

    feature_facts.clear_gatherers_for_tests()
    nl_engine.reset_nl_engine_for_tests()
    reset_default_gateway()
    reset_guild_policy_reader()
    egress.reset_channel_emitter_for_tests()


def _ctx(params, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"),
        guild_id=gid, request_id="r1", confirmed=True, params=params)


# --- normalize + preset lanes over a fake store --------------------------------------


def test_normalize_question_verbatim_semantics():
    assert normalize.normalize_question("<@123>  How MUCH cash?!") == \
        "how much cash"
    assert normalize.normalize_question(None) == ""
    assert normalize.normalize_question("<a:x:1>") == ""


class FakeAiStore:
    def __init__(self):
        self.entries: dict[int, dict] = {}
        self.presets: dict[tuple[int, str], dict] = {}
        self.next_id = 1

    def install(self, monkeypatch):
        from sb.domain.ai import store as st

        async def insert_entry(conn, **kw):
            eid = self.next_id
            self.next_id += 1
            self.entries[eid] = dict(kw, id=eid, reviewed=False)
            return eid

        async def get_entry(guild_id, entry_id, conn=None):
            row = self.entries.get(entry_id)
            return dict(row) if row and row["guild_id"] == guild_id else None

        async def mark_reviewed(conn, *, guild_id, entry_id):
            self.entries[entry_id]["reviewed"] = True
            return True

        async def upsert_preset(conn, *, guild_id, question_key, question,
                                answer, task, source, created_by):
            for pid, row in self.presets.items():
                if (row["guild_id"], row["question_key"]) == (guild_id,
                                                              question_key):
                    row.update(answer=answer, question=question)
                    return pid
            pid = self.next_id
            self.next_id += 1
            self.presets[pid] = {
                "id": pid, "guild_id": guild_id,
                "question_key": question_key, "question": question,
                "answer": answer, "created_by": created_by}
            return pid

        async def remove_preset(conn, *, guild_id, preset_id):
            row = self.presets.get(preset_id)
            if row is None or row["guild_id"] != guild_id:
                return False
            del self.presets[preset_id]
            return True

        async def get_preset(guild_id, preset_id, conn=None):
            row = self.presets.get(preset_id)
            return (dict(row) if row and row["guild_id"] == guild_id
                    else None)

        async def lookup_preset(guild_id, question_key, conn=None):
            for row in self.presets.values():
                if (row["guild_id"], row["question_key"]) == (guild_id,
                                                              question_key):
                    return row["answer"]
            return None

        async def erase_subject(conn, *, user_id):
            touched = 0
            for eid in [e for e, r in self.entries.items()
                        if r.get("user_id") == user_id
                        or r.get("corrected_by") == user_id]:
                del self.entries[eid]
                touched += 1
            for row in self.presets.values():
                if row.get("created_by") == user_id:
                    row["created_by"] = None
                    touched += 1
            return touched

        for name, fn in (("insert_entry", insert_entry),
                         ("get_entry", get_entry),
                         ("mark_reviewed", mark_reviewed),
                         ("upsert_preset", upsert_preset),
                         ("remove_preset", remove_preset),
                         ("get_preset", get_preset),
                         ("lookup_preset", lookup_preset),
                         ("erase_subject", erase_subject)):
            monkeypatch.setattr(st, name, fn)
        return self


def test_review_and_preset_legs(monkeypatch):
    fake = FakeAiStore().install(monkeypatch)

    out = run(ai_ops._record_entry(None, _ctx(
        {"kind": "unknown", "channel_id": 5, "user_id": 42,
         "reason_code": "grounding_failed", "task": "btd6.answer",
         "question": "q", "answer": None})))
    assert out.after["entry_id"] == 1

    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):
        run(ai_ops._record_entry(None, _ctx({"kind": "bogus"})))

    out = run(ai_ops._resolve_entry(None, _ctx({"entry_id": 1})))
    assert fake.entries[1]["reviewed"] is True
    assert out.after["message"] == "✅ Entry #1 marked reviewed."
    with pytest.raises(ValidatorError):
        run(ai_ops._resolve_entry(None, _ctx({"entry_id": 99})))

    out = run(ai_ops._set_preset(None, _ctx(
        {"question": "How much CASH?", "answer": "Lots."})))
    preset_id = out.after["preset_id"]
    assert out.after["question"] == "How much CASH?"
    with pytest.raises(ValidatorError):
        run(ai_ops._set_preset(None, _ctx({"question": "x", "answer": " "})))

    # The runtime preset short-circuit resolves the same normalized key.
    assert run(readers._preset_lookup(1, "<@99> how much cash")) == "Lots."
    # Fail-safe: a raising store returns None, never raises.
    from sb.domain.ai import store as st

    async def boom(guild_id, key, conn=None):
        raise RuntimeError("db down")

    monkeypatch.setattr(st, "lookup_preset", boom)
    assert run(readers._preset_lookup(1, "how much cash")) is None
    monkeypatch.undo()

    fake.install(monkeypatch)
    out = run(ai_ops._remove_preset(None, _ctx({"preset_id": preset_id})))
    assert out.after["preset_id"] == preset_id
    assert run(readers._preset_lookup(1, "how much cash")) is None
    with pytest.raises(ValidatorError):
        run(ai_ops._remove_preset(None, _ctx({"preset_id": 999})))

    run(ai_ops._set_preset(None, _ctx({"question": "q2", "answer": "a2"})))
    out = run(ai_ops._scrub_subject(None, _ctx({"subject_user_id": 42})))
    assert out.after["rows_touched"] >= 1


# --- the answer registry + correction matching ----------------------------------------


def test_answer_registry_and_correction_dedupe(monkeypatch):
    recorded = []

    async def fake_record(actor, gid, params):
        recorded.append(params)
        return 7

    monkeypatch.setattr(review, "_record", fake_record)
    ctx = review.AnswerContext(
        guild_id=1, channel_id=5, user_id=42, message_id=10,
        question="q", answer="a", task="btd6.answer", route="btd6.answer",
        provider="anthropic", model="m", recorded_at=time.monotonic())
    review.remember_answer(111, ctx)
    assert review.lookup_answer(111) == ctx
    assert run(review.record_correction(
        reply_message_id=111, corrected_by=9, signal="reaction")) == 7
    # Same flagger dedupes; unknown message returns None.
    assert run(review.record_correction(
        reply_message_id=111, corrected_by=9, signal="reaction")) is None
    assert run(review.record_correction(
        reply_message_id=999, corrected_by=9, signal="reaction")) is None
    assert recorded[0]["kind"] == "correction"


# --- guild policy overlay ---------------------------------------------------------------


def test_guild_policy_overlay_reads_declared_settings(monkeypatch):
    from sb.kernel import settings as ksettings

    values = {"default_provider": "anthropic", "default_model": ""}

    async def resolve(guild_id, subsystem, name):
        assert subsystem == "ai"
        return values[name]

    monkeypatch.setattr(ksettings, "resolve", resolve)
    overlay = run(readers._guild_policy_overlay(1))
    assert overlay == {"default_provider": "anthropic"}

    async def missing(guild_id, subsystem, name):
        raise LookupError(name)

    monkeypatch.setattr(ksettings, "resolve", missing)
    assert run(readers._guild_policy_overlay(1)) is None


# --- round-cash workflow ------------------------------------------------------------------


def test_round_cash_plan_recognisers():
    assert round_cash.plan_question("what a nice day") is None
    plan = round_cash.plan_question("how much cash from round 81 to round 83")
    assert (plan["round_start"], plan["round_end"]) == (81, 83)
    # r-shorthand + clause-separated anchors + completion shift + balance.
    plan = round_cash.plan_question(
        "how much do I have on r70 if I had 26,932 at the end of r53")
    assert plan["round_start"] == 54  # end-of-r53 shifts the start
    assert plan["round_end"] == 70
    assert plan["starting_balance"] == 26932.0
    # ABR cue + modifier honesty.
    plan = round_cash.plan_question(
        "how much cash in abr from r25 to r83 with double cash")
    assert plan["roundset"] == "abr"
    assert plan["unsupported_modifier"] == "double"


def test_round_cash_run_complete_and_inclusive():
    answer = run(round_cash.run("how much cash from round 81 to round 83"))
    assert answer is not None and answer.status == "complete"
    assert answer.inclusive_range
    ev = answer.evidence[0]
    assert ev.normalized_inputs == {"round_start": 81, "round_end": 83,
                                    "roundset": "default"}
    # The evidence total equals the dataset sum r81+r82+r83.
    from sb.domain.btd6 import dataset

    rows = {int(r["round"]): r for r in
            (dataset.read_blob("rounds.json") or {}).get("rounds", ())}
    expected = sum(float(rows[n]["cash"]) for n in (81, 82, 83))
    assert ev.outputs["range_cash"] == expected
    assert f"${expected:,.0f}" in answer.result_text


def test_round_cash_unrecognised_returns_none_and_workflow_registered():
    assert run(round_cash.run("tell me a joke")) is None
    round_cash.register_round_cash_workflow()
    got = run(orchestration.run_answer_workflow(
        "analyze_execute_verify", "how much cash from round 81 to round 82"))
    assert got is not None and got.status == "complete"


# --- orchestration profiles + tools ----------------------------------------------------------


def test_domain_profiles_registered():
    from sb.domain.ai import orchestration_presets

    orchestration_presets.register_domain_profiles()
    keys = {p.key for p in orchestration.registered_profiles()}
    assert {"btd6_grounded", "btd6_grounded_strict", "no_tools"} <= keys
    strict = orchestration.get_profile("btd6_grounded_strict")
    assert strict.enabled_toolsets == \
        orchestration_presets.BTD6_FACTUAL_TOOLSETS


def test_btd6_tools_registered_and_handlers_run():
    from sb.domain.ai import tools as ai_tools

    ai_tools.register_btd6_tools()
    names = {t.spec.name for t in tools_catalogue.registered_tools()}
    assert "btd6_lookup" in names and "btd6_round_cash" in names
    # Grounding allowlist derives from grounding_domain metadata.
    assert "btd6_lookup" in tools_catalogue.grounding_tool_names("btd6")
    lookup = tools_catalogue.registered_tool("btd6_lookup")
    handler = lookup.handler_factory()
    result = run(handler({"query": "what is a ddt immune to"}))
    assert any("immune to Sharp" in f for f in result["facts"])
    cash = tools_catalogue.registered_tool("btd6_round_cash")
    out = run(cash.handler_factory()({"round_start": 81, "round_end": 81}))
    assert out["inclusive"] is True and out["missing_rounds"] == []


# --- the NL message shell -------------------------------------------------------------------


class FakeEmitter:
    def __init__(self):
        self.sent = []

    async def send(self, channel_id, content, *, guild_id):
        from sb.kernel.interaction.egress import EmitResult

        self.sent.append((channel_id, content.body))
        return EmitResult(sent=True, message_id=555)


def test_nl_shell_delivers_and_remembers(monkeypatch):
    from sb.adapters.discord import nl_shell
    from sb.kernel.ai import nl_engine
    from sb.kernel.interaction import egress

    emitter = FakeEmitter()
    egress.install_channel_emitter(emitter)

    async def fake_handle(msg, *, gateway=None, route_ctx=None):
        assert msg.is_mention and msg.text == "hello there"
        return nl_engine.NLOutcome(
            decision="replied", reason="none", reply_text="hi!",
            task="general.nl_answer", route="general.nl_answer")

    monkeypatch.setattr(nl_engine, "handle_message", fake_handle)
    message = SimpleNamespace(
        guild_id=1, channel_id=5, category_id=None, user_id=42,
        message_id=10, content="<@777> hello there", author_is_bot=False,
        display_name="P1")
    outcome = run(nl_shell.handle_gateway_message(
        message, bot_user_id=777))
    assert outcome.decision == "replied"
    assert emitter.sent == [(5, "hi!")]
    assert review.lookup_answer(555) is not None  # remembered for 👎

    # Bot-author + empty messages are pre-filtered.
    bot_msg = SimpleNamespace(content="x", author_is_bot=True)
    assert run(nl_shell.handle_gateway_message(bot_msg, bot_user_id=777)) is None


def test_nl_shell_history_scanner(monkeypatch):
    from sb.adapters.discord import nl_shell
    from sb.kernel.ai import conversation

    async def reader(guild_id, channel_id):
        return [(42, "P1", "earlier question", False),
                (777, None, "earlier answer", True)]

    nl_shell.install_channel_history_reader(reader)
    conversation.reset_conversation_for_tests()
    count = run(nl_shell._scan(1, 5))
    assert count == 2
    nl_shell.reset_history_reader_for_tests()
    assert run(nl_shell._scan(1, 5)) == 0


# --- surface + manifest -----------------------------------------------------------------------


def test_ai_manifest_imports_and_registers():
    import sb.manifest.ai as manifest
    from sb.spec.settings import BindingSpec, SettingSpec

    names = [c.qualified_name for c in manifest.MANIFEST.commands]
    assert "ai" in names and "ai status" in names
    assert "aireview preset add" in names
    assert names.count("aimenu") == 2          # the shipped prefix + slash twin
    scalars = [s for s in manifest.MANIFEST.settings
               if isinstance(s, SettingSpec)]
    bindings = [s for s in manifest.MANIFEST.settings
                if isinstance(s, BindingSpec)]
    # the shipped schema roster (10) + the KV-only ai_review_channel; the
    # shipped audit_log_channel binding rides along (cogs/ai/schemas.py).
    assert len(scalars) == 11 and len(bindings) == 1
    keys = {s.settings_key for s in scalars}
    assert "ai_enabled" in keys and "ai_review_channel" in keys
    assert bindings[0].name == "audit_log_channel"
    # the shipped defaults, verbatim (goldens/ai/sweep_ai_settings pins
    # them: default='deterministic', min level 2, cooldown 30, allowance 1).
    by_name = {s.name: s for s in scalars}
    assert by_name["default_provider"].default == "deterministic"
    assert by_name["minimum_level_default"].default == 2
    assert by_name["cooldown_seconds"].default == 30
    assert by_name["fresh_user_mention_allowance"].default == 1
    tables = {s.table for s in manifest.MANIFEST.stores}
    assert tables == {"ai_review_log", "ai_answer_presets",
                      # the policy-mutation slice: the shipped migration
                      # 039 override shapes (migrations/0028_ai_policy).
                      "ai_channel_policy", "ai_category_policy",
                      "ai_role_policy"}
    events = {e.name for e in manifest.MANIFEST.events}
    assert events == {"ai.policy.channel_changed",
                      "ai.policy.category_changed",
                      "ai.policy.role_changed"}
    panel_ids = {p.panel_id for p in manifest.MANIFEST.panels}
    assert panel_ids == {
        "ai.hub", "ai.settings", "ai.card",
        # the settings-mutation slice: the shipped chooser PAGES + the
        # S6/S7 edit widget pages (+ the modal-arming slice's free-text
        # editor page).
        "ai.policy_chooser", "ai.behavior_chooser", "ai.tools_chooser",
        "ai.settings_edit_presets", "ai.settings_edit_enum",
        "ai.settings_edit_text",
        # the policy-mutation slice: the shipped scope pickers + the
        # edit pages + the paged override list.
        "ai.policy_channel_picker", "ai.policy_category_picker",
        "ai.policy_role_picker", "ai.policy_preview_picker",
        "ai.policy_scope_edit", "ai.policy_role_edit", "ai.policy_list"}
    manifest.ENSURE_REFS()


def test_ai_operator_cards_shipped_bytes():
    """The shipped embed builders (goldens/ai pin these bytes; the replay
    corpus is the full check — this is the fast in-suite pin)."""
    from sb.domain.ai import operator_cards as cards

    embed = cards.build_panel_embed()
    assert embed.title == "💤 AI Platform"          # disabled state
    assert embed.footer == ("!ai status / !ai diagnostics / !ai providers "
                            "/ !ai routing")
    assert [f[0] for f in embed.fields] == [
        "Enabled", "Default provider", "Setup advisor provider",
        "Active provider (last call)", "Requests / failures", "Redaction"]

    diag = cards.build_diagnostics_embed()
    assert diag.title == "AI Gateway — Diagnostics"
    assert [f[0] for f in diag.fields][:4] == [
        "enabled", "default provider", "setup advisor provider",
        "provider active"]

    routing = cards.build_routing_embed()
    assert routing.title == "AI Gateway — Routing"
    assert [f[0] for f in routing.fields] == list(cards.SHIPPED_TASK_ORDER)
    assert routing.fields[0][1] == ("provider: `deterministic`\n"
                                    "model: `gpt-4o-mini`\n"
                                    "timeout: `20.0s`\nenabled: `False`")

    providers = cards.build_providers_embed()
    assert [f[1] for f in providers.fields] == ["deterministic"] * 3


def test_ai_policy_card_unconfigured_guild():
    """No policy reader armed → the shipped GUILD_NOT_CONFIGURED dry-run
    trace (goldens/ai/sweep_ai_policy pins the copy)."""
    from sb.domain.ai import operator_cards as cards

    embed = run(cards.build_policy_embed(
        guild_id=1, channel_id=5, user_id=42, user_role_ids=(9,)))
    assert embed.title == "AI Effective Policy"
    assert embed.footer == "dry_run=True · administrator-only"
    body = dict((f[0], f[1]) for f in embed.fields)
    assert body["Without mention"].startswith(
        "⛔ **hard-disabled** · `guild_not_configured`")
    assert ("guild_ai_gate: no ai_guild_policy row → deny "
            "GUILD_NOT_CONFIGURED") in body["Without mention"]
    assert "min_level=`2` · cooldown=`30s`" in body["Without mention"]
    assert body["Context"] == ("Overrides: 0 channel · 0 category · 0 role\n"
                               "Provider: `deterministic` · model: `—`")


def test_ai_forget_view_clears_channel_buffer():
    from sb.domain.ai import service
    from sb.kernel.ai import conversation

    conversation.reset_conversation_for_tests()
    req = SimpleNamespace(args={"argv": ()}, guild_id=1, channel_id=5,
                          request_id="r1", confirmed=True,
                          actor=SimpleNamespace(user_id=42))
    out = run(service.forget_view(req))
    assert out.user_message == "No chat memory cached for <#5>."
    conversation.append(1, 5, user_id=42, role="user", text="hello")
    out = run(service.forget_view(req))
    assert out.user_message == "✅ Cleared chat memory for <#5>."
    conversation.reset_conversation_for_tests()
