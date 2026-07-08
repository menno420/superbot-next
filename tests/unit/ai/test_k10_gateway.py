"""K10 gateway pipeline: flags→safety→redaction→routing→provider→metrics→
degrade, never-raises."""

from __future__ import annotations

import asyncio
import json

import pytest

from sb.kernel.ai import flags, routing, tasks
from sb.kernel.ai.contracts import (
    AIRequest,
    AIRequestContext,
    AIResponseMode,
    AIScope,
    AIToolBudget,
    AIToolSpec,
)
from sb.kernel.ai.gateway import AIGateway, install_guild_policy_reader
from sb.kernel.ai.providers import ProviderUnavailableError
from tests.unit.ai.conftest import make_config


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


class FakeProvider:
    def __init__(self, name="fake", text="ok", exc=None, delay=0.0):
        self.name = name
        self._text = text
        self._exc = exc
        self._delay = delay
        self.seen_requests = []
        self.seen_dispatch = None

    async def execute(self, request, *, model, dispatch=None):
        self.seen_requests.append((request, model))
        self.seen_dispatch = dispatch
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc is not None:
            raise self._exc
        if dispatch is not None and request.tools:
            # Call the first offered tool once, then answer with its result.
            result = await dispatch(request.tools[0].name, {"q": 1})
            return f"{self._text}:{result}"
        return self._text


def _request(task="general.nl_answer", **kw):
    defaults = dict(
        context=AIRequestContext(task=task, scope=AIScope.USER, guild_id=None),
        system_prompt="You are a test.",
        payload={"question": "hi"},
    )
    defaults.update(kw)
    return AIRequest(**defaults)


def _gateway(provider, name="fake"):
    return AIGateway(providers={name: provider, "deterministic": provider})


class TestPipelineGates:
    def test_disabled_flag_degrades_without_provider_call(self):
        flags.install_ai_config(make_config())  # AI off
        provider = FakeProvider()
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(_gateway(provider).execute(_request()))
        assert response.degraded
        assert response.fallback_reason.startswith("feature_flag:disabled:")
        assert provider.seen_requests == []

    def test_unregistered_task_degrades_deterministically(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider()
        routing.override("nowhere.answer", routing.RoutingTarget("fake", "m", 5))
        response = run(_gateway(provider).execute(_request(task="nowhere.answer")))
        assert response.degraded
        assert response.fallback_reason == "task_unregistered:nowhere.answer"
        assert provider.seen_requests == []

    def test_safety_precheck_blocks_empty_prompt(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider()
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(
            _gateway(provider).execute(_request(system_prompt="   ")),
        )
        assert response.degraded
        assert response.fallback_reason.startswith("safety:")
        assert provider.seen_requests == []

    def test_redaction_applied_before_provider(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider()
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        request = _request(
            system_prompt="key sk-proj-abcdefghijklmnop is here",
            payload={"dsn": "postgres://user:pw@host/db"},
        )
        run(_gateway(provider).execute(request))
        sent, _model = provider.seen_requests[0]
        assert "sk-proj-abcdefghijklmnop" not in sent.system_prompt
        assert "postgres://" not in json.dumps(sent.payload)

    def test_provider_missing_degrades(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        routing.override("general.nl_answer", routing.RoutingTarget("ghost", "m", 5))
        gateway = AIGateway(providers={"fake": FakeProvider()})
        response = run(gateway.execute(_request()))
        assert response.degraded
        assert response.fallback_reason == "provider_missing:ghost"


class TestFaultBoundary:
    def test_provider_exception_degrades(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider(exc=RuntimeError("boom"))
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(_gateway(provider).execute(_request()))
        assert response.degraded
        assert "boom" in response.fallback_reason

    def test_provider_unavailable_degrades(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider(exc=ProviderUnavailableError("no key"))
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(_gateway(provider).execute(_request()))
        assert response.degraded
        assert response.fallback_reason == "no key"

    def test_timeout_degrades(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider(delay=0.2)
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(
            _gateway(provider).execute(_request(timeout_seconds=0.01)),
        )
        assert response.degraded
        assert response.fallback_reason.startswith("timeout:")

    def test_fallback_provider_rescues_transport_fault(self):
        flags.install_ai_config(
            make_config(AI_ENABLED="1", AI_FALLBACK_PROVIDER="backup"),
        )
        primary = FakeProvider(name="fake", exc=ProviderUnavailableError("down"))
        backup = FakeProvider(name="backup", text="rescued")
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        gateway = AIGateway(providers={"fake": primary, "backup": backup})
        response = run(gateway.execute(_request()))
        assert not response.degraded
        assert response.text == "rescued"
        assert response.provider == "backup"

    def test_invalid_json_not_retried_on_fallback(self):
        flags.install_ai_config(
            make_config(AI_ENABLED="1", AI_FALLBACK_PROVIDER="backup"),
        )
        primary = FakeProvider(name="fake", text="not-json")
        backup = FakeProvider(name="backup", text='{"a": 1}')
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        gateway = AIGateway(providers={"fake": primary, "backup": backup})
        response = run(gateway.execute(_request(mode=AIResponseMode.JSON)))
        assert response.degraded
        assert response.fallback_reason.startswith("invalid_json:")
        assert backup.seen_requests == []


class TestJSONAndTools:
    def test_json_mode_parses_dict(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider(text='{"answer": 42}')
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        response = run(_gateway(provider).execute(_request(mode=AIResponseMode.JSON)))
        assert not response.degraded
        assert response.data == {"answer": 42}

    def test_tools_inert_without_flag(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider()
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        spec = AIToolSpec(name="t", description="d", parameters={})

        async def handler(args):
            return {"r": 1}

        request = _request(tools=(spec,))
        run(_gateway(provider).execute(request, tool_handlers={"t": handler}))
        assert provider.seen_dispatch is None

    def test_tool_dispatch_redacts_and_survives_faults(self):
        flags.install_ai_config(make_config(AI_ENABLED="1", AI_TOOLS_ENABLED="1"))
        provider = FakeProvider(text="ans")
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        spec = AIToolSpec(name="t", description="d", parameters={})

        async def handler(args):
            return {"dsn": "postgres://u:p@h/db"}

        request = _request(tools=(spec,))
        response = run(
            _gateway(provider).execute(request, tool_handlers={"t": handler}),
        )
        assert not response.degraded
        assert "postgres://" not in (response.text or "")
        assert response.text.startswith("ans:")

    def test_tool_fault_returns_json_error_to_model(self):
        flags.install_ai_config(make_config(AI_ENABLED="1", AI_TOOLS_ENABLED="1"))
        provider = FakeProvider(text="ans")
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        spec = AIToolSpec(name="t", description="d", parameters={})

        async def handler(args):
            raise RuntimeError("tool blew up")

        request = _request(tools=(spec,))
        response = run(
            _gateway(provider).execute(request, tool_handlers={"t": handler}),
        )
        assert not response.degraded
        assert '"tool_failed"' in response.text

    def test_unoffered_tool_not_callable(self):
        flags.install_ai_config(make_config(AI_ENABLED="1", AI_TOOLS_ENABLED="1"))
        provider = FakeProvider(text="ans")
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        offered = AIToolSpec(name="offered", description="d", parameters={})

        captured = {}

        class Probe(FakeProvider):
            async def execute(self, request, *, model, dispatch=None):
                captured["result"] = await dispatch("not_offered", {})
                return "done"

        probe = Probe(name="fake")

        async def handler(args):  # registered but NOT offered
            return "secret"

        request = _request(tools=(offered,))
        run(_gateway(probe).execute(request, tool_handlers={"not_offered": handler}))
        assert json.loads(captured["result"])["error"] == "tool_not_available"


class TestGuildPolicyOverlay:
    def test_overlay_applied_and_family_corrected(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        tasks.register_task(
            tasks.AITaskSpec(task_id="btd6.answer", owner_subsystem="btd6"),
        )
        provider = FakeProvider(name="anthropic")

        async def reader(guild_id):
            assert guild_id == 7
            return {"default_provider": "anthropic", "default_model": "gpt-4o-mini"}

        install_guild_policy_reader(reader)
        gateway = AIGateway(providers={"anthropic": provider})
        request = _request(
            task="btd6.answer",
            context=AIRequestContext(
                task="btd6.answer", scope=AIScope.USER, guild_id=7,
            ),
        )
        response = run(gateway.execute(request))
        assert not response.degraded
        # Cross-family model corrected to the task's anthropic default.
        assert provider.seen_requests[0][1] == "claude-haiku-4-5"
        assert response.model == "claude-haiku-4-5"

    def test_reader_fault_keeps_routing(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        provider = FakeProvider()

        async def reader(guild_id):
            raise RuntimeError("db down")

        install_guild_policy_reader(reader)
        routing.override("general.nl_answer", routing.RoutingTarget("fake", "m", 5))
        request = _request(
            context=AIRequestContext(
                task="general.nl_answer", scope=AIScope.USER, guild_id=7,
            ),
        )
        response = run(_gateway(provider).execute(request))
        assert not response.degraded


class TestDeterministicDefault:
    def test_deterministic_provider_degrades_cleanly(self):
        flags.install_ai_config(make_config(AI_ENABLED="1"))
        gateway = AIGateway()  # real default trio
        response = run(gateway.execute(_request()))
        assert response.degraded
        assert response.fallback_reason == "provider=deterministic"

    def test_budget_default_matches_shipped_hop_limit(self):
        assert AIToolBudget().max_hops == 4
