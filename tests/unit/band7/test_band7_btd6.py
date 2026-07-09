"""Band 7 slice 1 — BTD6 knowledge domain onto K10: the QA-accuracy
corpus grounds offline through the REAL retrieval, the A-17 eval gate
runs the registered suite under the deterministic provider with sockets
denied, and the route probe / grounding verifier / strategy lanes carry
their shipped semantics."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.domain.btd6 import ai_tasks as btd6_ai
from sb.domain.btd6 import context as btd6_context
from sb.domain.btd6 import grounding as btd6_grounding
from sb.domain.btd6 import ops as btd6_ops
from sb.domain.btd6.evals import GROUNDING_PROBES, register_eval_suite
from sb.kernel.ai import evals, flags, router, routing, tasks
from sb.kernel.ai.grounding import absence_guard, verify
from sb.kernel.ai.providers.deterministic import DeterministicProvider
from sb.kernel.config import preflight

run = asyncio.run

BASE_ENV = {
    "DISCORD_BOT_TOKEN_PRODUCTION": "x",
    "DATABASE_URL": "postgresql://u@localhost/db",
    "SB_DATA_PLANE": "test",
    "SB_TEST_DB_HOSTS": "localhost",
}


def _enable_ai():
    flags.install_ai_config(preflight(dict(BASE_ENV, AI_ENABLED="1")))


@pytest.fixture(autouse=True)
def _reset_ai_state():
    yield
    flags.reset_flags_for_tests()
    routing.clear_overrides()
    tasks.clear_tasks_for_tests()
    router.clear_probes_for_tests()
    verify.clear_verifiers_for_tests()
    absence_guard.clear_attributes_for_tests()
    evals.clear_suites_for_tests()
    from sb.kernel.ai import feature_facts, instructions

    feature_facts.clear_gatherers_for_tests()
    instructions.clear_task_contracts_for_tests()
    from sb.kernel.ai.gateway import reset_default_gateway

    reset_default_gateway()


# --- the offline corpus layer (the oracle test_btd6_qa_corpus twin) ---------------


@pytest.mark.parametrize("probe", GROUNDING_PROBES, ids=lambda p: p.question)
def test_corpus_question_grounds_its_answer(probe):
    ctx = run(btd6_context.build(probe.question))
    blob = "\n".join(ctx.facts).lower()
    for needle in probe.expect:
        assert needle.lower() in blob, (
            f"{probe.question!r}: expected grounded fact containing "
            f"{needle!r}{' — ' + probe.note if probe.note else ''}"
        )
    for bad in probe.forbid:
        assert bad.lower() not in blob, (
            f"{probe.question!r}: grounding must NOT contain {bad!r}"
        )


def test_corpus_is_nontrivial():
    assert len(GROUNDING_PROBES) >= 10  # the A-17(d) floor
    assert all(p.expect for p in GROUNDING_PROBES)


# --- the A-17 deterministic eval gate ----------------------------------------------


def test_btd6_eval_suite_passes_deterministic_gate():
    _enable_ai()
    btd6_ai.register_btd6_ai()
    from sb.kernel.ai.gateway import AIGateway

    suite = next(
        s for s in evals.registered_suites() if s.suite_id == "btd6_qa_accuracy"
    )
    assert len(suite.cases) >= suite.min_cases
    assert suite.content_version.startswith("btd6@")
    result = run(
        evals.run_suite(
            suite, gateway=AIGateway(), provider=DeterministicProvider(),
        ),
    )
    assert result.passed, [
        (c.case_id, [g for g in c.grades if not g.passed and not g.advisory])
        for c in result.cases
        if not c.passed
    ]
    # The llm_judge rubric tier is recorded but never gates.
    assert result.advisory_failures


def test_eval_suite_registration_idempotent():
    a = register_eval_suite()
    b = register_eval_suite()
    assert a.suite_id == b.suite_id == "btd6_qa_accuracy"


# --- K10 registrations ---------------------------------------------------------------


def test_legacy_task_ids_claimed_verbatim():
    btd6_ai.register_btd6_ai()
    assert tasks.task_registered("btd6.answer")
    assert tasks.task_registered("btd6.strategy_review")
    spec = tasks.get_task("btd6.strategy_review")
    assert spec.owner_subsystem == "btd6"
    assert spec.knowledge_domain == "btd6"
    # K10(b)/D-0033: the Sonnet reservation lives in the routing table.
    assert routing.default_model_for(
        "anthropic", "btd6.strategy_review") == "claude-sonnet-4-6"
    assert routing.default_model_for(
        "anthropic", "btd6.answer") == "claude-haiku-4-5"


def test_verifiers_and_absence_attribute_registered():
    btd6_ai.register_btd6_ai()
    assert "btd6.answer" in verify.registered_verifier_tasks()
    assert "btd6.strategy_review" in verify.registered_verifier_tasks()
    assert any(a.name == "paragon" for a in absence_guard.registered_attributes())


# --- route probe (shipped classify semantics) ----------------------------------------


def _classify(text, **ctx_kwargs):
    btd6_ai.register_btd6_ai()
    return router.classify(text, router.RouteContext(**ctx_kwargs))


def test_probe_keyword_and_entity_routes():
    assert _classify("how do I beat round 63 in btd6").task == "btd6.answer"
    assert _classify("what does gwendolin do").task == "btd6.answer"
    # BUG-0003: the possessive/plural fold + the despo shorthand.
    assert _classify("how much is a despo on impop").task == "btd6.answer"
    assert _classify("what are geraldos items").task == "btd6.answer"


def test_probe_round_money_degree_and_mk_legs():
    assert _classify("how much do I have on r70 if I had 26932 at r53").task \
        == "btd6.answer"
    assert _classify("how much money does a 420 farm make").task == "btd6.answer"
    assert _classify("what is the damage of a d67 dart paragon").task \
        == "btd6.answer"
    assert _classify("which mk affects the sniper").task == "btd6.answer"


def test_probe_followup_needs_conversation_cue():
    q = "does it make coins at the end of the round?"
    assert _classify(q).task == "general.nl_answer"
    routed = _classify(q, conversation_context_domains=frozenset({"btd6"}))
    assert routed.task == "btd6.answer"
    assert routed.via_conversation_cue


def test_probe_strategy_intake_channel():
    routed = _classify(
        "here is my chimps strategy for round 100",
        intake_kinds=frozenset({"btd6_strategy"}),
    )
    assert routed.task == "btd6.strategy_review"


def test_probe_ordinary_chat_stays_general():
    assert _classify("good morning everyone").task == "general.nl_answer"
    assert _classify("a paragon of virtue, that man").task == "general.nl_answer"


# --- grounding verifier ----------------------------------------------------------------


def test_validate_reply_blocks_ungrounded_name_and_number():
    facts = ("[btd6_tower] Dart Monkey — base cost: 200 (medium difficulty)",)
    verdict = btd6_grounding.validate_btd6_reply(
        "The Glaive Dominus costs 999999.", facts, ())
    assert not verdict.grounded
    assert "glaive dominus" in verdict.offending_names
    assert "999999" in verdict.offending_numbers


def test_validate_reply_accepts_grounded_reply():
    facts = ("[btd6_tower] Dart Monkey — base cost: 200 (medium difficulty)",)
    verdict = btd6_grounding.validate_btd6_reply(
        "A Dart Monkey costs 200 on Medium.", facts, ())
    assert verdict.grounded


def test_absence_claim_contradicted_by_grounding():
    btd6_ai.register_btd6_ai()
    facts = (
        "[btd6_paragon] Monkey Buccaneer's Paragon (tier 6) is Navarch of "
        "the Seas, costing 500000 on Medium (source: bloonswiki)",
    )
    verdict = btd6_grounding.validate_btd6_reply(
        "The Monkey Buccaneer does not have a paragon.", facts, (),
        check_numbers=False)
    assert not verdict.grounded
    assert verdict.offending_absence_claims


def test_refusal_floor_is_version_stamped():
    text = btd6_context.no_data_refusal()
    from sb.domain.btd6 import dataset

    assert dataset.game_version() in text
    assert "won't state names or numbers" in text


# --- strategy lanes (leg functions over a fake store) -----------------------------------


class FakeStrategyStore:
    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.next_id = 1

    def install(self, monkeypatch):
        from sb.domain.btd6 import store as st

        async def insert_strategy(conn, *, guild_id, title, summary,
                                  map_name, mode, hero, submitted_by,
                                  submitter_display):
            sid = self.next_id
            self.next_id += 1
            self.rows[sid] = {
                "id": sid, "origin_guild_id": guild_id,
                "current_guild_id": guild_id, "visibility": "guild",
                "approval_status": "pending", "title": title,
                "summary": summary, "map": map_name, "mode": mode,
                "hero": hero, "submitted_by": submitted_by,
                "submitter_display_snapshot": submitter_display,
                "submitter_identity_state": "present"}
            return sid

        async def get_strategy(strategy_id, conn=None):
            row = self.rows.get(strategy_id)
            return dict(row) if row else None

        async def set_review(conn, *, strategy_id, approval_status,
                             approved_by, approved_by_id,
                             review_notes=None):
            self.rows[strategy_id]["approval_status"] = approval_status
            self.rows[strategy_id]["approved_by"] = approved_by
            return True

        async def anonymize_submitter(conn, *, user_id):
            touched = 0
            for row in self.rows.values():
                if row.get("submitted_by") == user_id:
                    row["submitted_by"] = None
                    row["submitter_display_snapshot"] = None
                    row["submitter_identity_state"] = "anonymized"
                    touched += 1
            return touched

        monkeypatch.setattr(st, "insert_strategy", insert_strategy)
        monkeypatch.setattr(st, "get_strategy", get_strategy)
        monkeypatch.setattr(st, "set_review", set_review)
        monkeypatch.setattr(st, "anonymize_submitter", anonymize_submitter)
        return self


def _ctx(params, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"),
        guild_id=gid, request_id="r1", confirmed=True, params=params)


def test_submit_review_and_scrub_legs(monkeypatch):
    fake = FakeStrategyStore().install(monkeypatch)

    out = run(btd6_ops._record_submit(None, _ctx(
        {"title": "Sub commander CHIMPS", "summary": "Energizer carry.",
         "_display_name": "Player One"})))
    assert out.after["strategy_id"] == 1
    assert fake.rows[1]["approval_status"] == "pending"
    assert fake.rows[1]["submitter_display_snapshot"] == "Player One"

    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):
        run(btd6_ops._record_submit(None, _ctx({"title": "x", "summary": ""})))

    out = run(btd6_ops._record_review(None, _ctx(
        {"strategy_id": 1, "approval_status": "approved",
         "approved_by": "staff"})))
    assert out.after["approval_status"] == "approved"
    with pytest.raises(ValidatorError):
        run(btd6_ops._record_review(None, _ctx(
            {"strategy_id": 99, "approval_status": "approved"})))

    out = run(btd6_ops._scrub_submitter(None, _ctx({"subject_user_id": 42})))
    assert out.after == {"rows_touched": 1, "disposition": "anonymized"}
    assert fake.rows[1]["submitted_by"] is None
    assert fake.rows[1]["submitter_identity_state"] == "anonymized"


# --- reference views over the dataset ---------------------------------------------------


def _req(argv=(), args=None, gid=1, uid=42):
    base = {"argv": tuple(argv)}
    base.update(args or {})
    return SimpleNamespace(
        args=base, guild_id=gid, channel_id=5, request_id="r1",
        confirmed=True, actor=SimpleNamespace(user_id=uid))


def test_reference_views():
    from sb.domain.btd6 import service

    out = run(service.ref_tower_view(_req(["dart", "monkey"])))
    assert "Dart Monkey" in out.user_message
    out = run(service.ref_hero_view(_req(["quincy"])))
    assert "Quincy" in out.user_message
    out = run(service.ref_round_view(_req(["81"])))
    assert "Round 81" in out.user_message
    out = run(service.ref_rbe_view(_req(["81"])))
    assert "RBE" in out.user_message
    out = run(service.ref_income_view(_req(["81", "83"])))
    assert "Round cash r81–r83" in out.user_message
    out = run(service.ref_relic_view(_req(["abilitized"])))
    assert "Abilitized" in out.user_message
    out = run(service.events_grounding_view(_req(["what", "is", "a", "ddt"])))
    assert "Grounded facts" in out.user_message


def test_manifest_imports_and_registers():
    import sb.manifest.btd6 as manifest

    names = [c.qualified_name for c in manifest.MANIFEST.commands]
    assert "btd6menu" in names
    assert "btd6ref tower" in names
    assert "btd6strat submit" in names
    assert "btd6ops seed-data" in names
    assert manifest.MANIFEST.stores[0].table == "btd6_strategies"
    manifest.ENSURE_REFS()
