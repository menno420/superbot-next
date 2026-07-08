"""K10 provider adapters against duck-typed fake SDK clients (the SDKs are
NOT installed in this container — guarded-import discipline is under test)."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from sb.kernel.ai import flags
from sb.kernel.ai.contracts import (
    AIRequest,
    AIRequestContext,
    AIResponseMode,
    AIScope,
    AIToolBudget,
    AIToolChoice,
    AIToolSpec,
    ToolRequirementMode,
)
from sb.kernel.ai.providers import (
    AnthropicProvider,
    DeterministicFallbackError,
    DeterministicProvider,
    OpenAIProvider,
    ProviderUnavailableError,
)
from sb.kernel.ai.providers.base import ToolLoopState, cap_tool_result


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _request(**kw):
    defaults = dict(
        context=AIRequestContext(task="general.nl_answer", scope=AIScope.USER),
        system_prompt="sys",
        payload={"q": "hi"},
    )
    defaults.update(kw)
    return AIRequest(**defaults)


# --- shared machinery -------------------------------------------------------


class TestToolLoopState:
    def test_hop_bound(self):
        state = ToolLoopState(AIToolBudget(max_hops=2))
        assert state.may_offer_tools(0) and state.may_offer_tools(1)
        assert not state.may_offer_tools(2)

    def test_call_cap(self):
        state = ToolLoopState(AIToolBudget(max_calls=1))
        assert state.may_offer_tools(0)
        state.record_call()
        assert not state.may_offer_tools(0)

    def test_cap_tool_result(self):
        assert cap_tool_result("abc", None) == "abc"
        capped = cap_tool_result("x" * 100, 10)
        assert capped.startswith("x" * 10) and "truncated" in capped


class TestDeterministic:
    def test_always_raises_fallback(self):
        with pytest.raises(DeterministicFallbackError):
            run(DeterministicProvider().execute(_request(), model="any"))


# --- anthropic adapter ------------------------------------------------------


def _anthropic_text_response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


class FakeAnthropicClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class TestAnthropicAdapter:
    def test_unavailable_without_key(self):
        flags.reset_for_tests()
        with pytest.raises(ProviderUnavailableError):
            run(AnthropicProvider().execute(_request(), model="claude-haiku-4-5"))

    def test_single_shot_text(self):
        client = FakeAnthropicClient([_anthropic_text_response("hello")])
        provider = AnthropicProvider(client=client)
        text = run(provider.execute(_request(), model="claude-haiku-4-5"))
        assert text == "hello"
        kwargs = client.calls[0]
        assert kwargs["model"] == "claude-haiku-4-5"
        # System prompt is a cache-marked block.
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert "tools" not in kwargs

    def test_tool_loop_round_trip(self):
        tool_use = SimpleNamespace(
            type="tool_use", id="tu1", name="lookup", input={"k": "v"},
        )
        first = SimpleNamespace(content=[tool_use])
        second = _anthropic_text_response("final")
        client = FakeAnthropicClient([first, second])
        provider = AnthropicProvider(client=client)

        seen = []

        async def dispatch(name, arguments):
            seen.append((name, arguments))
            return json.dumps({"found": True})

        spec = AIToolSpec(name="lookup", description="d", parameters={"type": "object"})
        text = run(
            provider.execute(
                _request(tools=(spec,)),
                model="claude-haiku-4-5",
                dispatch=dispatch,
            ),
        )
        assert text == "final"
        assert seen == [("lookup", {"k": "v"})]
        # Anthropic tool shape: flat name/description/input_schema.
        assert client.calls[0]["tools"][0]["input_schema"] == {"type": "object"}
        # Second hop carries the tool_result turn.
        follow_up = client.calls[1]["messages"]
        assert follow_up[-1]["content"][0]["type"] == "tool_result"

    def test_required_tool_choice_first_hop_only(self):
        tool_use = SimpleNamespace(type="tool_use", id="t", name="x", input={})
        client = FakeAnthropicClient(
            [SimpleNamespace(content=[tool_use]), _anthropic_text_response("done")],
        )
        provider = AnthropicProvider(client=client)

        async def dispatch(name, arguments):
            return "{}"

        spec = AIToolSpec(name="x", description="d", parameters={})
        run(
            provider.execute(
                _request(
                    tools=(spec,),
                    tool_choice=AIToolChoice(
                        mode=ToolRequirementMode.REQUIRED_TOOL, tool_name="x",
                    ),
                ),
                model="m",
                dispatch=dispatch,
            ),
        )
        assert client.calls[0]["tool_choice"] == {"type": "tool", "name": "x"}
        assert client.calls[1]["tool_choice"] == {"type": "auto"}

    def test_json_schema_unwrapped_for_anthropic(self):
        client = FakeAnthropicClient([_anthropic_text_response('{"a":1}')])
        provider = AnthropicProvider(client=client)
        run(
            provider.execute(
                _request(
                    mode=AIResponseMode.JSON,
                    response_schema={"name": "s", "schema": {"type": "object"}},
                ),
                model="m",
            ),
        )
        assert client.calls[0]["output_config"] == {
            "format": {"type": "json_schema", "schema": {"type": "object"}},
        }


# --- openai adapter ---------------------------------------------------------


def _openai_text_response(text):
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class TestOpenAIAdapter:
    def test_unavailable_without_key(self):
        flags.reset_for_tests()
        with pytest.raises(ProviderUnavailableError):
            run(OpenAIProvider().execute(_request(), model="gpt-4o-mini"))

    def test_single_shot_text(self):
        client = FakeOpenAIClient([_openai_text_response("hi there")])
        provider = OpenAIProvider(client=client)
        text = run(provider.execute(_request(), model="gpt-4o-mini"))
        assert text == "hi there"
        kwargs = client.calls[0]
        assert kwargs["messages"][0]["role"] == "system"
        assert "tools" not in kwargs

    def test_tool_loop_round_trip(self):
        call = SimpleNamespace(
            id="c1",
            function=SimpleNamespace(name="lookup", arguments='{"k": 1}'),
        )
        first_message = SimpleNamespace(content=None, tool_calls=[call])
        first = SimpleNamespace(choices=[SimpleNamespace(message=first_message)])
        client = FakeOpenAIClient([first, _openai_text_response("final")])
        provider = OpenAIProvider(client=client)

        seen = []

        async def dispatch(name, arguments):
            seen.append((name, arguments))
            return "result"

        spec = AIToolSpec(name="lookup", description="d", parameters={})
        text = run(
            provider.execute(
                _request(tools=(spec,)),
                model="gpt-4o-mini",
                dispatch=dispatch,
            ),
        )
        assert text == "final"
        assert seen == [("lookup", {"k": 1})]
        follow_up = client.calls[1]["messages"]
        assert follow_up[-1] == {
            "role": "tool",
            "tool_call_id": "c1",
            "content": "result",
        }

    def test_json_mode_without_schema_uses_json_object(self):
        client = FakeOpenAIClient([_openai_text_response("{}")])
        provider = OpenAIProvider(client=client)
        run(provider.execute(_request(mode=AIResponseMode.JSON), model="m"))
        assert client.calls[0]["response_format"] == {"type": "json_object"}
