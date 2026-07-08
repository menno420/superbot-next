"""AI gateway (K10) — the single never-raises chokepoint for provider calls.

Ported from shipped ``disbot/core/runtime/ai/gateway.py`` @7f7628e1 onto
the kernel seams. Pipeline order (canonical plan K10 row):

1. Task admission — the task id must be REGISTERED
   (:mod:`sb.kernel.ai.tasks`; replaces the closed-enum guarantee) and the
   feature flags must allow it (:mod:`sb.kernel.ai.flags`) — else degraded
   without invoking a provider.
2. Safety prechecks (:mod:`sb.kernel.ai.safety`) — empty / oversized →
   degraded.
3. Redaction — scrub the payload before ANY external call. Imports from
   ``sb.kernel.observability.redaction`` (the S6 hoist: redaction is a
   kernel obligation, not an AI detail).
4. Routing (:mod:`sb.kernel.ai.routing`) — task → provider, model, timeout
   (+ the per-guild policy overlay via the installable reader port).
5. Provider call wrapped in ``asyncio.wait_for``.
6. Metrics observation (``ai_request_total`` / ``ai_request_seconds``,
   guarded — observability never blocks a reply).
7. Parse text into :class:`AIResponse` (JSON parse for JSON mode).
8. On any exception or timeout: degraded :class:`AIResponse` — NEVER
   raises to the caller.

The gateway is the only place anything in the system asks "talk to an AI
provider". The per-guild provider/model overlay reads through
:func:`install_guild_policy_reader` (the settings/AI band installs the
real reader; default = no overlay) so the gateway has no DB coupling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from typing import Any

from sb.kernel.ai import flags, tasks
from sb.kernel.ai.contracts import AIRequest, AIResponse, AIResponseMode
from sb.kernel.ai.diagnostics import DiagnosticsCollector, get_default_collector
from sb.kernel.ai.providers import (
    AnthropicProvider,
    DeterministicFallbackError,
    DeterministicProvider,
    OpenAIProvider,
    Provider,
    ProviderUnavailableError,
)
from sb.kernel.ai.providers.base import ToolDispatch, ToolHandler
from sb.kernel.ai.routing import (
    RoutingTarget,
    default_model_for,
    model_matches_provider,
    resolve,
)
from sb.kernel.ai.safety import precheck
from sb.kernel.observability import redaction

__all__ = [
    "AIGateway",
    "GuildPolicyReader",
    "get_default_gateway",
    "install_guild_policy_reader",
    "reset_default_gateway",
    "reset_guild_policy_reader",
]

logger = logging.getLogger("sb.kernel.ai.gateway")

# ---------------------------------------------------------------------------
# Installable per-guild policy overlay port (replaces the shipped
# ``utils.db.ai.get_guild_policy`` coupling). The reader returns a mapping
# with optional ``default_provider`` / ``default_model`` keys, or None.
# ---------------------------------------------------------------------------

GuildPolicyReader = Callable[[int], Awaitable[Mapping[str, Any] | None]]

_guild_policy_reader: GuildPolicyReader | None = None


def install_guild_policy_reader(reader: GuildPolicyReader) -> None:
    global _guild_policy_reader
    _guild_policy_reader = reader


def reset_guild_policy_reader() -> None:
    global _guild_policy_reader
    _guild_policy_reader = None


def _observe(task_id: str, *, outcome: str, provider: str, seconds: float) -> None:
    """Guarded metric emission — observability never blocks a reply."""
    try:
        from sb.kernel.observability import metrics as _metrics

        registry = _metrics.active_registry()
        if registry is not None:
            registry.counter("ai_request_total").labels(
                task=task_id,
                outcome=outcome,
            ).inc()
            registry.histogram("ai_request_seconds").labels(
                task=task_id,
                provider=provider,
            ).observe(seconds)
    except Exception:  # noqa: BLE001 — metrics are observability only
        pass


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact secrets from every string value in ``payload``."""
    result = redaction.redact_payload(payload)
    return result.value if isinstance(result.value, dict) else dict(result.value)


def _redact_string(value: str) -> str:
    return redaction.redact_text(value).value


def _degraded_response(
    request: AIRequest,
    *,
    provider_name: str,
    reason: str,
    latency_ms: float | None = None,
) -> AIResponse:
    return AIResponse(
        task=request.context.task,
        provider=provider_name,
        model="",
        text=None,
        data=None,
        suggestions=(),
        latency_ms=latency_ms,
        degraded=True,
        fallback_reason=reason,
    )


async def _overlay_guild_policy(
    target: RoutingTarget,
    guild_id: int,
    task_id: str,
) -> RoutingTarget:
    """Apply per-guild provider/model overrides from the installed reader.

    Precedence: typed guild policy (non-empty) → routed target (input).
    Missing reader / row, or a read failure: keep ``target`` unchanged —
    the gateway contract requires ``execute`` cannot raise.
    """
    if _guild_policy_reader is None:
        return target
    try:
        policy = await _guild_policy_reader(guild_id)
    except Exception:  # noqa: BLE001 — DB failure is non-fatal here
        logger.warning(
            "ai gateway: guild policy read failed for guild_id=%s; "
            "keeping config / default routing",
            guild_id,
            exc_info=True,
        )
        return target
    if not policy:
        return target

    provider = str(policy.get("default_provider") or "").strip().lower()
    model = str(policy.get("default_model") or "").strip()
    if not provider and not model:
        return target
    resolved_provider = provider or target.provider
    if model:
        resolved_model = model
    elif provider:
        # Provider overridden without an explicit model — pick that
        # provider's default for the task so an OpenAI model string never
        # reaches Anthropic (or vice versa).
        resolved_model = default_model_for(resolved_provider, task_id)
    else:
        resolved_model = target.model
    # Provider-aware safety net: a stored model outside the resolved
    # provider's family would 404 at the provider.
    if not model_matches_provider(resolved_provider, resolved_model):
        logger.warning(
            "ai gateway: guild=%s default_model=%r does not match provider "
            "%r; using the per-task default instead",
            guild_id,
            resolved_model,
            resolved_provider,
        )
        resolved_model = default_model_for(resolved_provider, task_id)
    return RoutingTarget(
        provider=resolved_provider,
        model=resolved_model,
        timeout_seconds=target.timeout_seconds,
    )


class AIGateway:
    """Provider-neutral entry point for AI requests."""

    def __init__(
        self,
        *,
        providers: dict[str, Provider] | None = None,
        collector: DiagnosticsCollector | None = None,
    ) -> None:
        self._providers: dict[str, Provider] = providers or {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "deterministic": DeterministicProvider(),
        }
        self._collector = collector or get_default_collector()

    def get_provider(self, name: str) -> Provider | None:
        return self._providers.get(name)

    def register_provider(self, provider: Provider) -> None:
        """Install or replace a provider by ``provider.name``."""
        self._providers[provider.name] = provider

    async def execute(
        self,
        request: AIRequest,
        *,
        provider_override: Provider | None = None,
        tool_handlers: Mapping[str, ToolHandler] | None = None,
        model_override: str | None = None,
    ) -> AIResponse:
        """Run a request through the pipeline; never raises.

        ``tool_handlers`` + non-empty ``request.tools`` + tools flag on →
        the provider gets a redaction-wrapped dispatch callback. Tool
        outputs are redacted before re-entering the model context; tool
        faults come back as a JSON error string.

        ``model_override`` forces a specific model independent of routing
        — used to pair a forced ``provider_override`` with a model that
        provider actually serves (evals, A/B, fallback escalation).
        """
        task_id = request.context.task
        target = resolve(task_id)
        if provider_override is None and request.context.guild_id is not None:
            target = await _overlay_guild_policy(
                target,
                request.context.guild_id,
                task_id,
            )
        provider_name = provider_override.name if provider_override else target.provider
        effective_model = model_override or target.model

        # Registry admission: the closed enum made an unknown task
        # unrepresentable; the registry degrades it deterministically.
        if provider_override is None and not tasks.task_registered(task_id):
            return _degraded_response(
                request,
                provider_name=provider_name,
                reason=f"task_unregistered:{task_id}",
            )

        if provider_override is None and not flags.task_enabled(task_id):
            return _degraded_response(
                request,
                provider_name=provider_name,
                reason=f"feature_flag:disabled:{task_id}",
            )

        safety_reason = precheck(request)
        if safety_reason is not None:
            self._collector.record_failure(
                provider_active=provider_name,
                error_type="SafetyCheck",
                fallback_reason=safety_reason,
            )
            return _degraded_response(
                request,
                provider_name=provider_name,
                reason=safety_reason,
            )

        redacted_payload = _redact_payload(request.payload)
        redacted_system = _redact_string(request.system_prompt)
        # Redact only the two free-text fields; ``replace`` carries every
        # other field through untouched, so a new AIRequest field can never
        # again be silently dropped at the redaction seam.
        redacted_request = replace(
            request,
            system_prompt=redacted_system,
            payload=redacted_payload,
        )

        provider = provider_override or self._providers.get(target.provider)
        if provider is None:
            reason = f"provider_missing:{target.provider}"
            logger.warning(
                "ai gateway: resolved provider %r is not registered "
                "(known: %s); degrading. Check AI_DEFAULT_PROVIDER / "
                "AI_TASK_ROUTING configuration.",
                target.provider,
                ", ".join(sorted(self._providers)),
            )
            self._collector.record_failure(
                provider_active=target.provider,
                error_type="ProviderMissing",
                fallback_reason=reason,
            )
            return _degraded_response(
                request,
                provider_name=target.provider,
                reason=reason,
            )

        timeout = request.timeout_seconds or target.timeout_seconds
        response = await self._attempt(
            request,
            redacted_request,
            provider=provider,
            model=effective_model,
            timeout=timeout,
            tool_handlers=tool_handlers,
        )

        # Provider-fault fallback: when no explicit override pins the
        # provider and a distinct AI_FALLBACK_PROVIDER is configured, retry
        # once on a transport fault so a single-provider outage does not
        # take AI down. A bad-JSON degrade is a model-output problem, not
        # an outage — not retried.
        if (
            provider_override is None
            and response.degraded
            and not (response.fallback_reason or "").startswith("invalid_json")
        ):
            fallback = self._resolve_fallback(target.provider, task_id)
            if fallback is not None:
                fb_provider, fb_model = fallback
                fb_response = await self._attempt(
                    request,
                    redacted_request,
                    provider=fb_provider,
                    model=fb_model,
                    timeout=timeout,
                    tool_handlers=tool_handlers,
                )
                if not fb_response.degraded:
                    return fb_response
        return response

    def _resolve_fallback(
        self,
        primary_provider: str,
        task_id: str,
    ) -> tuple[Provider, str] | None:
        """The configured fallback provider + model, or None (unset, equal
        to the primary, or not registered)."""
        name = flags.fallback_provider()
        if not name or name == primary_provider:
            return None
        provider = self._providers.get(name)
        if provider is None:
            logger.warning(
                "ai gateway: AI_FALLBACK_PROVIDER=%r is not a registered "
                "provider; skipping fallback",
                name,
            )
            return None
        return provider, default_model_for(name, task_id)

    async def _attempt(
        self,
        request: AIRequest,
        redacted_request: AIRequest,
        *,
        provider: Provider,
        model: str,
        timeout: float,
        tool_handlers: Mapping[str, ToolHandler] | None,
    ) -> AIResponse:
        """One provider attempt; converts every fault to a degraded
        :class:`AIResponse`. Never raises — this is where the never-raise
        contract is enforced for a single call."""
        task_id = request.context.task
        self._collector.record_request(provider_active=provider.name)
        dispatch: ToolDispatch | None = None
        if tool_handlers is not None and request.tools and flags.ai_tools_enabled():
            dispatch = self._build_dispatch(
                redacted_request,
                tool_handlers,
                provider.name,
            )
        outcome = "success"
        started = time.perf_counter()
        try:
            # Only pass ``dispatch`` when tools are active so the no-tools
            # path stays identical to the legacy signature.
            if dispatch is None:
                provider_call = provider.execute(redacted_request, model=model)
            else:
                provider_call = provider.execute(
                    redacted_request,
                    model=model,
                    dispatch=dispatch,
                )
            raw_text = await asyncio.wait_for(provider_call, timeout=timeout)
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - started) * 1000.0
            _observe(
                task_id,
                outcome="timeout",
                provider=provider.name,
                seconds=latency_ms / 1000.0,
            )
            self._collector.record_failure(
                provider_active=provider.name,
                error_type="TimeoutError",
                fallback_reason=f"timeout:{timeout}s",
            )
            return _degraded_response(
                request,
                provider_name=provider.name,
                reason=f"timeout:{timeout}s",
                latency_ms=latency_ms,
            )
        except DeterministicFallbackError as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            _observe(
                task_id,
                outcome="deterministic",
                provider=provider.name,
                seconds=latency_ms / 1000.0,
            )
            self._collector.record_failure(
                provider_active=provider.name,
                error_type="DeterministicFallbackError",
                fallback_reason=str(exc),
            )
            return _degraded_response(
                request,
                provider_name=provider.name,
                reason=f"provider={provider.name}",
                latency_ms=latency_ms,
            )
        except ProviderUnavailableError as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            _observe(
                task_id,
                outcome="unavailable",
                provider=provider.name,
                seconds=latency_ms / 1000.0,
            )
            self._collector.record_failure(
                provider_active=provider.name,
                error_type=type(exc).__name__,
                fallback_reason=str(exc),
            )
            return _degraded_response(
                request,
                provider_name=provider.name,
                reason=str(exc),
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001 — provider exception boundary
            latency_ms = (time.perf_counter() - started) * 1000.0
            _observe(
                task_id,
                outcome="error",
                provider=provider.name,
                seconds=latency_ms / 1000.0,
            )
            logger.exception(
                "AI provider %r raised on task %s",
                provider.name,
                task_id,
            )
            self._collector.record_failure(
                provider_active=provider.name,
                error_type=type(exc).__name__,
                fallback_reason=f"{type(exc).__name__}: {exc}",
            )
            return _degraded_response(
                request,
                provider_name=provider.name,
                reason=f"{type(exc).__name__}: {exc}",
                latency_ms=latency_ms,
            )

        latency_ms = (time.perf_counter() - started) * 1000.0
        _observe(
            task_id,
            outcome=outcome,
            provider=provider.name,
            seconds=latency_ms / 1000.0,
        )

        text: str | None = raw_text
        data: dict[str, Any] | None = None
        degraded = False
        fallback_reason: str | None = None
        if request.mode is AIResponseMode.JSON:
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                degraded = True
                fallback_reason = f"invalid_json:{exc}"
                self._collector.record_failure(
                    provider_active=provider.name,
                    error_type="JSONDecodeError",
                    fallback_reason=fallback_reason,
                )
            else:
                data = parsed if isinstance(parsed, dict) else {"value": parsed}
                self._collector.record_success(provider_active=provider.name)
        else:
            self._collector.record_success(provider_active=provider.name)

        return AIResponse(
            task=task_id,
            provider=provider.name,
            model=model,
            text=text,
            data=data,
            suggestions=(),
            latency_ms=latency_ms,
            degraded=degraded,
            fallback_reason=fallback_reason,
        )

    def _build_dispatch(
        self,
        request: AIRequest,
        tool_handlers: Mapping[str, ToolHandler],
        provider_name: str,
    ) -> ToolDispatch:
        """Wrap ``tool_handlers`` in a redaction- and fault-safe dispatch.

        Only tools actually offered on ``request.tools`` are callable.
        Each result is JSON-encoded and redacted before re-entering the
        model context. Handler exceptions become a JSON error string so
        the tool loop never breaks the never-raise contract.
        """
        offered = {spec.name for spec in request.tools}

        async def dispatch(name: str, arguments: dict[str, Any]) -> str:
            if name not in offered or name not in tool_handlers:
                return json.dumps({"error": "tool_not_available", "tool": name})
            try:
                result = await tool_handlers[name](arguments)
            except Exception as exc:  # noqa: BLE001 — tool faults must not break the loop
                logger.warning(
                    "ai gateway: tool %r raised: %s",
                    name,
                    exc,
                    exc_info=True,
                )
                self._collector.record_failure(
                    provider_active=provider_name,
                    error_type="ToolError",
                    fallback_reason=f"tool:{name}",
                )
                return json.dumps({"error": "tool_failed", "tool": name})
            payload = (
                result if isinstance(result, str) else json.dumps(result, default=str)
            )
            return _redact_string(payload)

        return dispatch


_DEFAULT_GATEWAY: AIGateway | None = None


def get_default_gateway() -> AIGateway:
    """Process-wide singleton gateway. Lazy-initialised."""
    global _DEFAULT_GATEWAY
    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = AIGateway()
    return _DEFAULT_GATEWAY


def reset_default_gateway() -> None:
    """Test seam — drop the singleton so tests start fresh."""
    global _DEFAULT_GATEWAY
    _DEFAULT_GATEWAY = None
