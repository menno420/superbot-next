"""In-process gateway diagnostics (K10) — ported from shipped
``disbot/core/runtime/ai/diagnostics.py``. The gateway updates a
:class:`DiagnosticsCollector` on every call; the operator ``ai status``
surface (band 7) reads :meth:`snapshot`."""

from __future__ import annotations

import threading

from sb.kernel.ai import flags
from sb.kernel.ai.contracts import AIDiagnosticsSnapshot

__all__ = [
    "DiagnosticsCollector",
    "get_default_collector",
    "reset_default_collector",
]


class DiagnosticsCollector:
    """Counts requests and failures observed by the gateway. Thread-safe
    via a coarse lock — call counts are negligible next to an LLM
    round-trip."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = 0
        self._failures = 0
        self._last_provider_active = flags.default_provider()
        self._last_error_type: str | None = None
        self._last_fallback_reason: str | None = None
        self._degraded = False

    def record_request(self, *, provider_active: str) -> None:
        with self._lock:
            self._requests += 1
            self._last_provider_active = provider_active

    def record_failure(
        self,
        *,
        provider_active: str,
        error_type: str,
        fallback_reason: str,
    ) -> None:
        with self._lock:
            self._failures += 1
            self._last_provider_active = provider_active
            self._last_error_type = error_type
            self._last_fallback_reason = fallback_reason
            self._degraded = True

    def record_success(self, *, provider_active: str) -> None:
        with self._lock:
            self._last_provider_active = provider_active
            self._degraded = False

    def snapshot(self) -> AIDiagnosticsSnapshot:
        with self._lock:
            return AIDiagnosticsSnapshot(
                provider_requested=flags.default_provider(),
                provider_active=self._last_provider_active,
                model="",  # populated by the operator surface from routing
                enabled=flags.ai_enabled(),
                redaction_enabled=True,
                degraded=self._degraded,
                last_error_type=self._last_error_type,
                last_fallback_reason=self._last_fallback_reason,
                requests_observed=self._requests,
                failures_observed=self._failures,
            )


_DEFAULT_COLLECTOR: DiagnosticsCollector | None = None


def get_default_collector() -> DiagnosticsCollector:
    """Process-wide singleton collector. Lazy-initialised."""
    global _DEFAULT_COLLECTOR
    if _DEFAULT_COLLECTOR is None:
        _DEFAULT_COLLECTOR = DiagnosticsCollector()
    return _DEFAULT_COLLECTOR


def reset_default_collector() -> None:
    """Test seam — drop the process-wide collector."""
    global _DEFAULT_COLLECTOR
    _DEFAULT_COLLECTOR = None
