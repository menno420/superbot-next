"""Provider adapters (K10) — the ONLY modules permitted to import LLM SDKs
(guarded imports; SDKs absent in CI containers by design)."""

from __future__ import annotations

from sb.kernel.ai.providers.anthropic_provider import AnthropicProvider
from sb.kernel.ai.providers.base import (
    Provider,
    ProviderUnavailableError,
    ToolDispatch,
    ToolHandler,
    ToolLoopState,
    cap_tool_result,
)
from sb.kernel.ai.providers.deterministic import (
    DeterministicFallbackError,
    DeterministicProvider,
)
from sb.kernel.ai.providers.openai_provider import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "DeterministicFallbackError",
    "DeterministicProvider",
    "OpenAIProvider",
    "Provider",
    "ProviderUnavailableError",
    "ToolDispatch",
    "ToolHandler",
    "ToolLoopState",
    "cap_tool_result",
]
