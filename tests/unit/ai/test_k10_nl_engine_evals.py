"""K10 NL engine end-to-end (fake gateway) + the A-17 eval harness under
the socket-deny guard."""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.ai import (
    conversation,
    evals,
    flags,
    memory,
    nl_engine,
    policy,
    routing,
)
from sb.kernel.ai.contracts import AIResponse, PolicyDenialReason
from sb.kernel.ai.gateway import AIGateway
from sb.kernel.ai.grounding import verify
from sb.kernel.ai.providers import DeterministicProvider
from tests.unit.ai.conftest import make_config


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def _reset_all(monkeypatch):
    # Audit rows go to an in-memory list (no DB in this container).
    # Registry cleanup: conftest.py's dir-wide after-only reset.
    rows = []

    async def fake_insert(**kwargs):
        rows.append(kwargs)
        return len(rows)

    from sb.kernel.db import ai_audit

    monkeypatch.setattr(ai_audit, "insert_decision", fake_insert)
    yield rows


@pytest.fixture()
def audit_rows(_reset_all):
    return _reset_all


class FakeProvider:
    def __init__(self, texts):
        self.name = "fake"
        self._texts = list(texts)

    async def execute(self, request, *, model, dispatch=None):
        return self._texts.pop(0)


def _gateway(*texts):
    provider = FakeProvider(texts)
    return AIGateway(providers={"fake": provider, "deterministic": provider})


def _enable_ai():
    flags.install_ai_config(make_config(AI_ENABLED="1"))
    routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))


def _install_policy(**overrides):
    row = {
        "enabled": True,
        "natural_language_enabled": True,
        "generation": 1,
        "minimum_level_default": 0,
        "cooldown_seconds": 0,
    }
    row.update(overrides)

    async def reader(guild_id):
        return policy.PolicyBundle(policy=row)

    policy.install_policy_bundle_reader(reader)


def _msg(**kw):
    defaults = dict(
        guild_id=1,
        channel_id=10,
        category_id=None,
        user_id=100,
        message_id=555,
        text="what is the answer",
        raw_text="what is the answer",
        is_mention=False,
    )
    defaults.update(kw)
    return nl_engine.NLMessage(**defaults)


class TestNLEngine:
    def test_denied_unconfigured_audits_one_row(self, audit_rows):
        _enable_ai()
        outcome = run(nl_engine.handle_message(_msg(), gateway=_gateway("x")))
        assert outcome.decision == "denied"
        assert outcome.reason == PolicyDenialReason.GUILD_NOT_CONFIGURED.value
        assert outcome.reply_text is None
        assert len(audit_rows) == 1
        assert audit_rows[0]["decision"] == "denied"

    def test_reply_path_end_to_end(self, audit_rows):
        _enable_ai()
        _install_policy()
        outcome = run(
            nl_engine.handle_message(
                _msg(), gateway=_gateway("here is the model answer"),
            ),
        )
        assert outcome.decision == "replied"
        assert outcome.reply_text == "here is the model answer"
        assert audit_rows[-1]["decision"] == "replied"
        assert audit_rows[-1]["reason_code"] == "none"
        # The bot's reply entered memory as an assistant turn.
        turns = conversation.recent_turns(1, 10)
        assert turns[-1].role == "assistant"

    def test_reply_is_redacted_outbound(self):
        _enable_ai()
        _install_policy()
        outcome = run(
            nl_engine.handle_message(
                _msg(),
                gateway=_gateway("dsn is postgres://u:p@h/db ok"),
            ),
        )
        assert "postgres://" not in outcome.reply_text

    def test_cooldown_denial(self, audit_rows):
        _enable_ai()
        _install_policy(cooldown_seconds=60)
        policy.mark_reply_sent(1, 100)
        outcome = run(nl_engine.handle_message(_msg(), gateway=_gateway("x")))
        assert outcome.reason == PolicyDenialReason.COOLDOWN_ACTIVE.value

    def test_bare_mention_empty_skipped(self, audit_rows):
        _enable_ai()
        _install_policy()
        outcome = run(
            nl_engine.handle_message(
                _msg(text="", raw_text="<@42>", is_mention=True),
                gateway=_gateway("x"),
            ),
        )
        assert outcome.decision == "skipped"
        assert outcome.reason == PolicyDenialReason.EMPTY_MESSAGE.value
        # The mention was still recorded to memory.
        assert conversation.recent_turns(1, 10)

    def test_preset_short_circuits_model(self, audit_rows):
        _enable_ai()
        _install_policy()

        async def lookup(guild_id, text):
            return "vetted answer"

        nl_engine.install_preset_lookup(lookup)

        class Boom:
            name = "fake"

            async def execute(self, request, *, model, dispatch=None):
                raise AssertionError("model must not run")

        gateway = AIGateway(providers={"fake": Boom()})
        outcome = run(nl_engine.handle_message(_msg(), gateway=gateway))
        assert outcome.decision == "replied"
        assert outcome.reply_text == "vetted answer"
        assert outcome.route == "preset"

    def test_degraded_provider_audits_degraded(self, audit_rows):
        _enable_ai()
        _install_policy()
        gateway = AIGateway(providers={"fake": DeterministicProvider()})
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        outcome = run(nl_engine.handle_message(_msg(), gateway=gateway))
        assert outcome.decision == "degraded"
        assert outcome.reason == PolicyDenialReason.PROVIDER_UNAVAILABLE.value
        assert outcome.reply_text is None

    def test_grounding_retry_rescue_and_floor(self, audit_rows):
        _enable_ai()
        _install_policy()

        def verifier(reply, facts, tools):
            if "grounded" in reply:
                return verify.GROUNDED
            return verify.GroundingResult(
                grounded=False,
                reason_code="grounding_failed",
                used_fact_keys=(),
                offending_names=("phantom",),
            )

        verify.register_grounding_verifier(
            "general.nl_answer", verifier, owner_subsystem="test",
        )
        # First reply bad, retry grounded → rescued.
        outcome = run(
            nl_engine.handle_message(
                _msg(),
                gateway=_gateway("phantom stat 123", "a grounded answer"),
            ),
        )
        assert outcome.decision == "replied"
        assert outcome.reply_text == "a grounded answer"

        # Both bad → deterministic floor + denied/GROUNDING_FAILED audit.
        nl_engine.register_refusal_floor(
            "general.nl_answer", lambda task, q: "held back (no data)",
        )
        outcome2 = run(
            nl_engine.handle_message(
                _msg(),
                gateway=_gateway("phantom stat 123", "phantom again"),
            ),
        )
        assert outcome2.decision == "denied"
        assert outcome2.reason == PolicyDenialReason.GROUNDING_FAILED.value
        assert outcome2.reply_text == "held back (no data)"

    def test_fresh_allowance_charged_on_delivery_only(self):
        _enable_ai()
        _install_policy(minimum_level_default=10, fresh_user_mention_allowance=1)
        outcome = run(
            nl_engine.handle_message(
                _msg(is_mention=True, is_fresh_user=True, user_level=0),
                gateway=_gateway("answer"),
            ),
        )
        assert outcome.decision == "replied"
        assert outcome.used_fresh_allowance
        assert policy.fresh_allowance_remaining(1, 100, 1) == 1  # not yet spent
        nl_engine.note_reply_delivered(1, 100, used_fresh_allowance=True)
        assert policy.fresh_allowance_remaining(1, 100, 1) == 0
        assert policy.is_on_cooldown(1, 100, 60)


class TestEvalHarness:
    def _suite(self, cases):
        return evals.EvalSuiteSpec(
            suite_id="kernel_smoke",
            owner_subsystem="kernel",
            cases=tuple(cases),
            content_version="v0",
            min_cases=1,
        )

    def _case(self, graders, case_id="c1"):
        return evals.EvalCase(
            case_id=case_id,
            task="general.nl_answer",
            payload={"q": "hi"},
            graders=tuple(graders),
        )

    def test_deterministic_provider_under_socket_deny(self):
        _enable_ai()
        gateway = AIGateway()
        suite = self._suite(
            [
                self._case(
                    [
                        lambda o: evals.GradeResult(
                            "degrades_cleanly",
                            o.degraded
                            and o.response.fallback_reason == "provider=deterministic",
                        ),
                    ],
                ),
            ],
        )
        result = run(
            evals.run_suite(
                suite, gateway=gateway, provider=DeterministicProvider(),
            ),
        )
        assert result.passed

    def test_socket_deny_blocks_network_reaching_grader_path(self):
        _enable_ai()

        class NetworkProvider:
            name = "net"

            async def execute(self, request, *, model, dispatch=None):
                import socket

                socket.create_connection(("example.com", 443))
                return "never"

        gateway = AIGateway()
        suite = self._suite(
            [
                self._case(
                    [
                        lambda o: evals.GradeResult(
                            "degraded_by_socket_deny",
                            o.degraded and "SocketDenied" in (o.response.fallback_reason or ""),
                        ),
                    ],
                ),
            ],
        )
        result = run(
            evals.run_suite(suite, gateway=gateway, provider=NetworkProvider()),
        )
        # The gateway never-raises: the SocketDenied surfaces as a degraded
        # response, and the required gate stays deterministic.
        assert result.passed

    def test_advisory_failure_never_gates(self):
        _enable_ai()
        gateway = AIGateway()

        def judge(outcome):
            return evals.GradeResult("llm_judge", False, "would need a live model")

        suite = self._suite(
            [
                self._case(
                    [
                        lambda o: evals.GradeResult("deterministic_ok", True),
                        evals.advisory(judge),
                    ],
                ),
            ],
        )
        result = run(
            evals.run_suite(
                suite, gateway=gateway, provider=DeterministicProvider(),
            ),
        )
        assert result.passed  # advisory failure recorded, never gating
        assert result.advisory_failures
        assert result.advisory_failures[0][1].grader == "llm_judge"

    def test_corpus_floor_enforced(self):
        _enable_ai()
        gateway = AIGateway()
        suite = evals.EvalSuiteSpec(
            suite_id="thin",
            owner_subsystem="projmoon",
            cases=(self._case([evals.not_degraded()]),),
        )
        result = run(
            evals.run_suite(
                suite, gateway=gateway, provider=DeterministicProvider(),
            ),
        )
        assert not result.passed
        assert "corpus floor" in result.floor_violation

    def test_suite_registry(self):
        suite = self._suite([self._case([evals.not_degraded()])])
        evals.register_suite(suite)
        assert evals.registered_suites() == (suite,)
        with pytest.raises(ValueError):
            evals.register_suite(
                evals.EvalSuiteSpec(
                    suite_id="kernel_smoke",
                    owner_subsystem="other",
                    cases=(),
                ),
            )
