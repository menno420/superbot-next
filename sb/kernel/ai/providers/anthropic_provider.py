"""Anthropic (Claude) provider adapter (K10) — ported from shipped
``disbot/core/runtime/ai/providers/anthropic_provider.py``.

One of the only two production modules permitted to import a provider SDK
(guarded — the ``anthropic`` package is NOT installed in CI containers;
tests inject a duck-typed ``client``). The API key comes from the
installed Config via ``flags.api_key_for`` (never a raw env read).

Maps the provider-neutral :class:`AIRequest` onto the Messages API:
``system_prompt`` → a cache-marked ``system`` block; ``payload`` → one
JSON user message; ``tools`` + ``dispatch`` → a bounded
``tool_use``/``tool_result`` loop; JSON mode + schema → structured output.
Thinking / effort intentionally unset (must work across model tiers).
"""

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

__all__ = ["AnthropicProvider"]

logger = logging.getLogger("sb.kernel.ai.providers.anthropic")

# Anthropic's Messages API requires ``max_tokens``; fallback when the
# request does not set one.
_DEFAULT_MAX_TOKENS = 1024


class AnthropicProvider:
    """Async Anthropic Messages-API adapter with tool use + prompt caching."""

    name = "anthropic"

    def __init__(self, *, client: Any = None, api_key: str | None = None) -> None:
        self._client = client
        self._api_key = api_key

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from anthropic import AsyncAnthropic  # noqa: PLC0415 — guarded SDK import
        except ImportError as exc:
            raise ProviderUnavailableError(
                "anthropic package is not installed; install "
                "``anthropic>=0.40,<1.0`` or set the AI provider to "
                "``openai`` / ``deterministic``.",
            ) from exc
        api_key = self._api_key or flags.api_key_for("anthropic")
        if not api_key:
            raise ProviderUnavailableError(
                "ANTHROPIC_API_KEY is not configured; cannot construct client.",
            )
        self._client = AsyncAnthropic(api_key=api_key)
        return self._client

    async def execute(
        self,
        request: AIRequest,
        *,
        model: str,
        dispatch: ToolDispatch | None = None,
    ) -> str:
        client = self._ensure_client()
        system = _system_blocks(request.system_prompt)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": json.dumps(request.payload, default=str)},
        ]
        output_config = _output_config(request)
        choice = request.tool_choice
        budget = request.tool_budget
        offer_tools = (
            bool(request.tools)
            and dispatch is not None
            and choice.mode is not ToolRequirementMode.NONE
        )
        tool_params = _to_anthropic_tools(request.tools) if offer_tools else None
        max_tokens = request.max_output_tokens or _DEFAULT_MAX_TOKENS
        state = ToolLoopState(budget)

        for hop in range(budget.max_hops + 1):
            allow_tools = tool_params is not None and state.may_offer_tools(hop)
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            }
            if output_config is not None:
                kwargs["output_config"] = output_config
            if allow_tools:
                kwargs["tools"] = tool_params
                kwargs["tool_choice"] = _anthropic_tool_choice(choice, hop)

            response = await client.messages.create(**kwargs)
            blocks = _blocks_of(response)
            tool_uses = _tool_uses(blocks) if allow_tools else []

            if not tool_uses:
                text = _extract_text(blocks)
                if text is None:
                    raise RuntimeError("anthropic: empty response (no text content)")
                return text

            # The model asked for one or more tools. Echo its turn, append
            # each tool result, loop. ``dispatch`` never raises — failures
            # come back as a JSON error string the model can react to.
            messages.append(
                {"role": "assistant", "content": getattr(response, "content", blocks)},
            )
            tool_results: list[dict[str, Any]] = []
            for tool_use in tool_uses:
                raw_input = getattr(tool_use, "input", None)
                arguments = raw_input if isinstance(raw_input, dict) else {}
                state.record_call()
                result = cap_tool_result(
                    await dispatch(  # type: ignore[misc]
                        getattr(tool_use, "name", "") or "",
                        arguments,
                    ),
                    budget.max_result_chars,
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": getattr(tool_use, "id", ""),
                        "content": result,
                    },
                )
            messages.append({"role": "user", "content": tool_results})

        # Unreachable: the final hop sets allow_tools=False and returns
        # above. Guard anyway so a contract change is loud.
        raise RuntimeError("anthropic: tool loop did not terminate")


def _system_blocks(system_prompt: str) -> list[dict[str, Any]]:
    """Wrap the system prompt as a cache-marked text block (prompt caching;
    a no-op when shorter than the model's minimum cacheable length)."""
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _to_anthropic_tools(specs: tuple[AIToolSpec, ...]) -> list[dict[str, Any]]:
    """Anthropic tool shape: flat ``{name, description, input_schema}``."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.parameters,
        }
        for spec in specs
    ]


def _anthropic_tool_choice(choice: AIToolChoice, hop: int) -> dict[str, Any]:
    """AUTO every hop is the historical default. A REQUIRED_* policy forces
    a tool only on the FIRST tool-offering hop, then relaxes to auto so a
    later hop can produce the final answer."""
    if choice.mode is ToolRequirementMode.AUTO or hop > 0:
        return {"type": "auto"}
    if choice.mode is ToolRequirementMode.REQUIRED_TOOL and choice.tool_name:
        return {"type": "tool", "name": choice.tool_name}
    return {"type": "any"}


def _output_config(request: AIRequest) -> dict[str, Any] | None:
    """Build ``output_config`` for JSON mode with a schema. The neutral
    contract carries the OpenAI ``json_schema`` wrapper; Anthropic wants
    the bare JSON Schema."""
    if request.mode is not AIResponseMode.JSON or not request.response_schema:
        return None
    schema = request.response_schema
    if isinstance(schema, dict) and "schema" in schema:
        schema = schema["schema"]
    return {"format": {"type": "json_schema", "schema": schema}}


def _blocks_of(response: Any) -> list[Any]:
    content = getattr(response, "content", None)
    return list(content) if content else []


def _tool_uses(blocks: list[Any]) -> list[Any]:
    return [b for b in blocks if getattr(b, "type", None) == "tool_use"]


def _extract_text(blocks: list[Any]) -> str | None:
    parts = [
        getattr(b, "text", "") for b in blocks if getattr(b, "type", None) == "text"
    ]
    text = "".join(part for part in parts if part)
    return text or None
