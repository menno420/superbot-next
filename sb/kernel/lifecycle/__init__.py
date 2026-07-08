"""Process lifecycle state machine (K5) — ported from shipped
`disbot/core/runtime/lifecycle.py` (superbot main 7f7628e1, LP-2 lineage).

Owns the canonical state for "is this process accepting commands? draining?
restarting?". The composition root drives phases; this module records intent
and does nothing else (the actual exec/exit happens in the entry point).

Phases (the frozen 7):
  STARTING       initial state before on_ready; commands admitted
  RUNNING        on_ready fired; commands accepted normally
  DRAINING       shutdown/restart requested; new commands rejected
  SHUTTING_DOWN  cleanup in progress
  RESTARTING     cleanup complete, awaiting exec/respawn
  STOPPED        terminal: cleanup done, process about to exit
  FAILED_STARTUP terminal: startup raised before RUNNING (preflight
                 StartupError / MigrationDrift map here — spec 05 §3.9)

RC-9 note: `can_accept_commands()` is True in {STARTING, RUNNING} — the
shipped semantics, still valid for its own callers (command admission). The
K5 `/ready` probe does NOT use it: readiness is RUNNING-only 200 (spec 05
§3.8 — a deliberate semantics change from the shipped {STARTING,RUNNING}=>200
gate; see sb/adapters/http/health.py).

Metric mirrors (`lifecycle_phase` gauge, `lifecycle_event_total` counter,
`lifecycle_startup_seconds` histogram) go through the guarded registry —
observability never blocks a transition. The shipped diagnostics_service
self-registration is NOT ported: the findings/diagnostics engine folds at K5
minimally (sb/kernel/observability/findings.py) and grows later (F-3.4);
`diagnostics_snapshot()` is the same shape the /lifecycle route serves.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "LifecycleEvent",
    "PendingShutdown",
    "Phase",
    "can_accept_commands",
    "diagnostics_snapshot",
    "get_pending",
    "get_phase",
    "get_recent_events",
    "is_shutting_down",
    "record_close_completed",
    "record_close_executing",
    "record_close_timeout",
    "remaining_shutdown_seconds",
    "request_restart",
    "request_shutdown",
    "reset_for_tests",
    "restart_requested",
    "set_phase",
]


class Phase(enum.Enum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DRAINING = "DRAINING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    RESTARTING = "RESTARTING"
    STOPPED = "STOPPED"
    FAILED_STARTUP = "FAILED_STARTUP"


_DRAINING_PHASES: frozenset[Phase] = frozenset(
    {Phase.DRAINING, Phase.SHUTTING_DOWN, Phase.RESTARTING, Phase.STOPPED},
)
_ADMITTING_PHASES: frozenset[Phase] = frozenset(
    {Phase.STARTING, Phase.RUNNING},
)


@dataclass(frozen=True)
class LifecycleEvent:
    """One transition or request recorded in the ring buffer."""

    name: str
    phase: Phase
    at: float  # time.monotonic() seconds
    actor: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PendingShutdown:
    """The shutdown / restart request currently in flight, if any."""

    kind: str  # "shutdown" or "restart"
    reason: str
    actor: str | None
    requested_at: float
    grace_seconds: float | None


_EVENT_BUFFER_SIZE = 128

_phase: Phase = Phase.STARTING
_pending: PendingShutdown | None = None
_events: deque[LifecycleEvent] = deque(maxlen=_EVENT_BUFFER_SIZE)

# Wall-clock anchor for lifecycle_startup_seconds: stamped at import, observed
# exactly once on the first STARTING -> RUNNING (a gateway reconnect re-fires
# on_ready and must not double-count).
_module_loaded_at: float = time.monotonic()
_startup_duration_observed: bool = False


def _registry():
    try:
        from sb.kernel.observability import metrics as _metrics

        return _metrics.active_registry()
    except Exception:  # noqa: BLE001 — metrics are observability only
        return None


def get_phase() -> Phase:
    """Return the current lifecycle phase."""
    return _phase


def _publish_phase_gauge(phase: Phase) -> None:
    """Update `lifecycle_phase` so exactly one phase label is 1.0."""
    registry = _registry()
    if registry is None:
        return
    try:
        gauge = registry.gauge("lifecycle_phase")
        for p in Phase:
            gauge.labels(phase=p.value).set(1.0 if p is phase else 0.0)
    except Exception:  # noqa: BLE001 — observability, not control plane
        pass


def set_phase(phase: Phase, *, reason: str | None = None) -> None:
    """Record a phase transition (composition-root / this module only —
    domains use request_shutdown / request_restart)."""
    global _phase
    if _phase == phase:
        return
    _phase = phase
    _record_event(f"phase:{phase.value}", reason=reason)
    _publish_phase_gauge(phase)
    if phase is Phase.RUNNING:
        _maybe_observe_startup_duration()


def _maybe_observe_startup_duration() -> None:
    global _startup_duration_observed
    if _startup_duration_observed:
        return
    _startup_duration_observed = True
    registry = _registry()
    if registry is None:
        return
    try:
        registry.histogram("lifecycle_startup_seconds").observe(
            time.monotonic() - _module_loaded_at,
        )
    except Exception:  # noqa: BLE001
        pass


def is_shutting_down() -> bool:
    """True if draining, shutting down, restarting, or stopped."""
    return _phase in _DRAINING_PHASES


def restart_requested() -> bool:
    """True if a restart (rather than a plain shutdown) is pending."""
    return _pending is not None and _pending.kind == "restart"


def can_accept_commands() -> bool:
    """True only in STARTING and RUNNING (shipped semantics, RC-9).

    Every other phase — including terminal FAILED_STARTUP — rejects new
    commands. NOT the `/ready` gate (that is RUNNING-only, spec 05 §3.8).
    """
    return _phase in _ADMITTING_PHASES


def request_shutdown(
    reason: str,
    *,
    actor: str | None = None,
    grace_seconds: float | None = None,
) -> bool:
    """Request a graceful shutdown. True if this call established the pending
    request; False if one was already in flight (coalesced — first intent
    wins)."""
    global _pending
    if _pending is not None:
        _record_event("shutdown_requested_coalesced", reason=reason, actor=actor)
        return False
    _pending = PendingShutdown(
        kind="shutdown", reason=reason, actor=actor,
        requested_at=time.monotonic(), grace_seconds=grace_seconds,
    )
    _record_event("shutdown_requested", reason=reason, actor=actor)
    if _phase in (Phase.STARTING, Phase.RUNNING):
        set_phase(Phase.DRAINING, reason=reason)
    return True


def request_restart(
    reason: str,
    *,
    actor: str | None = None,
    grace_seconds: float | None = None,
) -> bool:
    """Request a graceful restart. Coalesces like request_shutdown — even if
    the existing pending intent was a plain shutdown (first intent wins; no
    race to upgrade the kind)."""
    global _pending
    if _pending is not None:
        _record_event("restart_requested_coalesced", reason=reason, actor=actor)
        return False
    _pending = PendingShutdown(
        kind="restart", reason=reason, actor=actor,
        requested_at=time.monotonic(), grace_seconds=grace_seconds,
    )
    _record_event("restart_requested", reason=reason, actor=actor)
    if _phase in (Phase.STARTING, Phase.RUNNING):
        set_phase(Phase.DRAINING, reason=reason)
    return True


def record_close_executing(pending: PendingShutdown) -> None:
    """The close-driver reached close() — captures execution vs intent."""
    _record_event("close_executing", reason=pending.reason, actor=pending.actor,
                  metadata={"kind": pending.kind})


def record_close_completed(pending: PendingShutdown, *, duration_seconds: float) -> None:
    """close() returned cleanly within the timeout window."""
    _record_event("close_completed", reason=pending.reason, actor=pending.actor,
                  metadata={"kind": pending.kind,
                            "duration_seconds": float(duration_seconds)})


def record_close_timeout(pending: PendingShutdown, *, timeout_seconds: float) -> None:
    """close() exceeded the close-driver timeout (the force-exit branch)."""
    _record_event("close_timeout", reason=pending.reason, actor=pending.actor,
                  metadata={"kind": pending.kind,
                            "timeout_seconds": float(timeout_seconds)})


def get_pending() -> PendingShutdown | None:
    """Return the current pending request, or None."""
    return _pending


def remaining_shutdown_seconds() -> float | None:
    """Seconds left in the grace window; None when not applicable."""
    if _pending is None or _pending.grace_seconds is None:
        return None
    elapsed = time.monotonic() - _pending.requested_at
    return max(0.0, _pending.grace_seconds - elapsed)


def get_recent_events(limit: int = 20) -> list[LifecycleEvent]:
    """Most recent lifecycle events, newest last. limit <= 0 => []."""
    if limit <= 0:
        return []
    return list(_events)[-limit:]


def _record_event(
    name: str,
    *,
    reason: str | None = None,
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    registry = _registry()
    if registry is not None:
        try:
            registry.counter("lifecycle_event_total").labels(event=name).inc()
        except Exception:  # noqa: BLE001
            pass
    _events.append(LifecycleEvent(
        name=name, phase=_phase, at=time.monotonic(),
        actor=actor, reason=reason, metadata=metadata or {},
    ))


def reset_for_tests() -> None:
    """Reset to STARTING with no pending request. Test-only."""
    global _phase, _pending, _module_loaded_at, _startup_duration_observed
    _phase = Phase.STARTING
    _pending = None
    _events.clear()
    _module_loaded_at = time.monotonic()
    _startup_duration_observed = False
    _publish_phase_gauge(_phase)


def diagnostics_snapshot() -> dict[str, Any]:
    """Sync snapshot of current lifecycle state (the /lifecycle route body).

    Same shape as the shipped LP-6 snapshot; sync by design — no DB or I/O.
    """
    pending = get_pending()
    events = get_recent_events(limit=20)
    return {
        "phase": _phase.value,
        "is_shutting_down": is_shutting_down(),
        "can_accept_commands": can_accept_commands(),
        "restart_requested": restart_requested(),
        "remaining_shutdown_seconds": remaining_shutdown_seconds(),
        "startup_duration_observed": _startup_duration_observed,
        "module_load_age_seconds": time.monotonic() - _module_loaded_at,
        "pending": (
            {
                "kind": pending.kind,
                "reason": pending.reason,
                "actor": pending.actor,
                "requested_at_monotonic": pending.requested_at,
                "grace_seconds": pending.grace_seconds,
            }
            if pending
            else None
        ),
        "recent_events": [
            {
                "name": event.name,
                "phase": event.phase.value,
                "at_monotonic": event.at,
                "actor": event.actor,
                "reason": event.reason,
                "metadata": dict(event.metadata),
            }
            for event in events
        ],
    }


# Initialise the phase gauge so STARTING reads as current from process start.
_publish_phase_gauge(_phase)
