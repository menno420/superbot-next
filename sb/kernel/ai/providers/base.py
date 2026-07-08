"""Provider protocol for the AI gateway (K10) — ported from shipped
``disbot/core/runtime/ai/providers/base.py``.

A provider implements one method, ``execute``, converting a typed
:class:`AIRequest` into raw response text. The gateway handles redaction,
routing, timeout, parsing, metrics, and degradation around it. Providers
may raise :class:`ProviderUnavailableError` (missing SDK / key / config)
or any other exception — the gateway is the single fault boundary.

Modules under ``sb/kernel/ai/providers/`` are the ONLY production modules
permitted to import external LLM SDKs (guarded imports; the SDKs are not
installed in CI containers).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from sb.kernel.ai.contracts import AIRequest, AIToolBudget

__all__ = [
    "Provider",
    "ProviderUnavailableError",
    "ToolDispatch",
    "ToolHandler",
    "ToolLoopState",
    "cap_tool_result",
]

#: A read-only tool handler: parsed arguments → JSON-serialisable result
#: (or a string). Handlers live above the gateway; the alias is declared
#: here so gateway and providers reference the type without importing them.
ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]

#: Gateway-provided callback a provider invokes during a tool loop. Given a
#: tool name and parsed arguments, returns the (already redacted) tool
#: result string to feed back into the model context. It never raises —
#: failures come back as a JSON error string so the loop can continue.
ToolDispatch = Callable[[str, dict[str, Any]], Awaitable[str]]


def cap_tool_result(result: str, max_chars: int | None) -> str:
    """Bound a tool-result string to the request budget (no-op when
    ``max_chars`` is None — the historical behaviour)."""
    if max_chars is None or len(result) <= max_chars:
        return result
    return result[:max_chars] + " …[tool result truncated]"


@dataclass
class ToolLoopState:
    """Per-request accounting that bounds a provider's model<->tool loop by
    its budget. Shared by both network adapters so the rule is enforced
    (and tested) once. The default budget reproduces the historical
    hop-only bound."""

    budget: AIToolBudget
    calls_made: int = 0
    started_monotonic: float = field(default_factory=time.monotonic)

    def may_offer_tools(self, hop: int) -> bool:
        """True if this hop may still offer tools, given hop / call /
        wall-time caps."""
        budget = self.budget
        if hop >= budget.max_hops:
            return False
        if budget.max_calls is not None and self.calls_made >= budget.max_calls:
            return False
        if budget.max_wall_seconds is not None:
            elapsed = time.monotonic() - self.started_monotonic
            if elapsed >= budget.max_wall_seconds:
                return False
        return True

    def record_call(self) -> None:
        """Count one dispatched tool call against the budget."""
        self.calls_made += 1


class ProviderUnavailableError(RuntimeError):
    """The provider cannot execute the request (missing SDK package,
    missing API key, configuration mismatch). The gateway converts this
    into a degraded :class:`AIResponse` rather than propagating it."""


@runtime_checkable
class Provider(Protocol):
    """Provider adapter contract."""

    name: str

    async def execute(
        self,
        request: AIRequest,
        *,
        model: str,
        dispatch: ToolDispatch | None = None,
    ) -> str:
        """Run the provider call and return the raw text response.

        ``request`` is already redacted by the gateway. ``dispatch``, when
        provided AND ``request.tools`` is non-empty, lets the provider run
        a bounded tool-call loop; ``None`` = plain single-shot completion.
        """
        ...
