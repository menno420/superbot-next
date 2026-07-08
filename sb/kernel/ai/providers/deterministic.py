"""Deterministic fallback provider (K10) — never makes an external call.

``execute`` always raises :class:`DeterministicFallbackError`, which the
gateway converts into a degraded :class:`AIResponse` with
``fallback_reason='provider=deterministic'``. Consumers wanting a
deterministic baseline check ``degraded`` and apply their own local logic.

This provider is the default everywhere no LLM key is configured — it
keeps the gateway boot-safe AND it is the provider the A-17 eval harness
pins requests to inside required CI (with the socket-deny guard armed).
"""

from __future__ import annotations

from sb.kernel.ai.contracts import AIRequest
from sb.kernel.ai.providers.base import ToolDispatch

__all__ = ["DeterministicFallbackError", "DeterministicProvider"]


class DeterministicFallbackError(RuntimeError):
    """Signal that no LLM provider is willing or able to serve this request."""


class DeterministicProvider:
    """Always-available no-op provider."""

    name = "deterministic"

    async def execute(
        self,
        request: AIRequest,
        *,
        model: str,
        dispatch: ToolDispatch | None = None,
    ) -> str:
        raise DeterministicFallbackError(
            "deterministic provider selected; no external call performed",
        )
