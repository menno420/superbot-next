"""OpenAI provider adapter (K10) — ported from shipped
``disbot/core/runtime/ai/providers/openai_provider.py``. The other of the
only two production modules permitted to import a provider SDK (guarded);
API key via ``flags.api_key_for`` (never a raw env read)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sb.kernel.ai import flags
from sb.kernel.ai.contracts import (
    AIRequest,
    AIResponseMode,
    AIToolChoice,
    AIToolSpec,
    ToolRequirementMode,
)
from sb.kernel.ai.providers.base import (
    ProviderUnavailableError,
    ToolDispatch,
    ToolLoopState,
    cap_tool_result,
)

__all__ = ["OpenAIProvider"]

logger = logging.getLogger("sb.kernel.ai.providers.openai")


class OpenAIProvider:
    """Async OpenAI chat-completions adapter with strict JSON schema and a
    bounded tool-call loop. A test injects a duck-typed ``client`` shaped
    like ``AsyncOpenAI`` — the SDK is never imported during tests."""

    name = "openai"

    def __init__(self, *, client: Any = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI  # noqa: PLC0415 — guarded SDK import
        except ImportError as exc:
            raise ProviderUnavailableError(
                "openai package is not installed; install ``openai>=1.40,<2.0`` "
                "or set the AI provider to ``deterministic``.",
            ) from exc
        api_key = self._api_key or flags.api_key_for("openai")
        if not api_key:
            raise ProviderUnavailableError(
                "OPENAI_API_KEY is not configured; cannot construct client.",
            )
        self._client = AsyncOpenAI(api_key=api_key)
        return self._client

    async def execute(
        self,
        request: AIRequest,
        *,
        model: str,
        dispatch: ToolDispatch | None = None,
    ) -> str:
        client = self._ensure_client()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": json.dumps(request.payload, default=str)},
        ]
        response_format = _response_format(request)
        choice = request.tool_choice
        budget = request.tool_budget
        offer_tools = (
            bool(request.tools)
            and dispatch is not None
            and choice.mode is not ToolRequirementMode.NONE
        )
        tool_params = _to_openai_tools(request.tools) if offer_tools else None
        state = ToolLoopState(budget)

        for hop in range(budget.max_hops + 1):
            allow_tools = tool_params is not None and state.may_offer_tools(hop)
            kwargs: dict[str, Any] = {"model": model, "messages": messages}
            if request.max_output_tokens:
                kwargs["max_tokens"] = request.max_output_tokens
            if response_format is not None:
                kwargs["response_format"] = response_format
            if allow_tools:
                kwargs["tools"] = tool_params
                kwargs["tool_choice"] = _openai_tool_choice(choice, hop)

            response = await client.chat.completions.create(**kwargs)
            message = _message_of(response)
            tool_calls = getattr(message, "tool_calls", None) if message else None

            if not allow_tools or not tool_calls:
                text = _extract_response_text(response)
                if text is None:
                    raise RuntimeError(
                        "openai: empty response (no choices/message/content)",
                    )
                return text

            messages.append(_assistant_tool_call_turn(message, tool_calls))
            for call in tool_calls:
                state.record_call()
                result = cap_tool_result(
                    await dispatch(  # type: ignore[misc]
                        _call_name(call),
                        _call_arguments(call),
                    ),
                    budget.max_result_chars,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": getattr(call, "id", ""),
                        "content": result,
                    },
                )

        raise RuntimeError("openai: tool loop did not terminate")


def _response_format(request: AIRequest) -> dict[str, Any] | None:
    if request.mode is not AIResponseMode.JSON:
        return None
    if request.response_schema:
        return {"type": "json_schema", "json_schema": request.response_schema}
    return {"type": "json_object"}


def _to_openai_tools(specs: tuple[AIToolSpec, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in specs
    ]


def _openai_tool_choice(choice: AIToolChoice, hop: int) -> Any:
    """AUTO every hop is the historical default. A REQUIRED_* policy forces
    a tool only on the first tool-offering hop, then relaxes to auto."""
    if choice.mode is ToolRequirementMode.AUTO or hop > 0:
        return "auto"
    if choice.mode is ToolRequirementMode.REQUIRED_TOOL and choice.tool_name:
        return {"type": "function", "function": {"name": choice.tool_name}}
    return "required"


def _assistant_tool_call_turn(message: Any, tool_calls: Any) -> dict[str, Any]:
    """Reconstruct the assistant message that requested ``tool_calls``."""
    return {
        "role": "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": [
            {
                "id": getattr(call, "id", ""),
                "type": "function",
                "function": {
                    "name": _call_name(call),
                    "arguments": getattr(
                        getattr(call, "function", None),
                        "arguments",
                        "",
                    )
                    or "{}",
                },
            }
            for call in tool_calls
        ],
    }


def _call_name(call: Any) -> str:
    return getattr(getattr(call, "function", None), "name", "") or ""


def _call_arguments(call: Any) -> dict[str, Any]:
    raw = getattr(getattr(call, "function", None), "arguments", "") or "{}"
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _message_of(response: Any) -> Any:
    choices = getattr(response, "choices", None)
    if not choices:
        return None
    return getattr(choices[0], "message", None)


def _extract_response_text(response: Any) -> str | None:
    message = _message_of(response)
    if message is None:
        return None
    content = getattr(message, "content", None)
    if not content:
        return None
    return content
