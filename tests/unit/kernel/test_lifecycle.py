"""K5 lifecycle state machine tests (ported contract, RC-9)."""

from __future__ import annotations

import pytest

from sb.kernel import lifecycle
from sb.kernel.lifecycle import Phase


@pytest.fixture(autouse=True)
def fresh_lifecycle():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


def test_seven_phases_frozen() -> None:
    assert {p.value for p in Phase} == {
        "STARTING", "RUNNING", "DRAINING", "SHUTTING_DOWN",
        "RESTARTING", "STOPPED", "FAILED_STARTUP",
    }


def test_initial_phase_and_admission() -> None:
    assert lifecycle.get_phase() is Phase.STARTING
    # RC-9: can_accept_commands is {STARTING, RUNNING} — shipped semantics.
    assert lifecycle.can_accept_commands() is True
    assert lifecycle.is_shutting_down() is False


def test_set_phase_records_event() -> None:
    lifecycle.set_phase(Phase.RUNNING, reason="on_ready")
    assert lifecycle.get_phase() is Phase.RUNNING
    events = lifecycle.get_recent_events()
    assert events[-1].name == "phase:RUNNING"
    assert events[-1].reason == "on_ready"


def test_request_shutdown_drains_and_coalesces() -> None:
    lifecycle.set_phase(Phase.RUNNING)
    assert lifecycle.request_shutdown("deploy", actor="ops") is True
    assert lifecycle.get_phase() is Phase.DRAINING
    assert lifecycle.can_accept_commands() is False
    assert lifecycle.is_shutting_down() is True
    # Coalesce: second request no-ops; a restart does NOT upgrade the kind.
    assert lifecycle.request_shutdown("again") is False
    assert lifecycle.request_restart("upgrade") is False
    assert lifecycle.get_pending().kind == "shutdown"
    assert lifecycle.restart_requested() is False


def test_request_restart_sets_kind() -> None:
    lifecycle.set_phase(Phase.RUNNING)
    assert lifecycle.request_restart("code update") is True
    assert lifecycle.restart_requested() is True
    assert lifecycle.get_pending().kind == "restart"


def test_failed_startup_rejects_commands() -> None:
    lifecycle.set_phase(Phase.FAILED_STARTUP, reason="preflight StartupError")
    assert lifecycle.can_accept_commands() is False
    # FAILED_STARTUP is terminal-before-RUNNING, not a draining phase.
    assert lifecycle.is_shutting_down() is False


def test_grace_window() -> None:
    lifecycle.set_phase(Phase.RUNNING)
    assert lifecycle.remaining_shutdown_seconds() is None
    lifecycle.request_shutdown("bye", grace_seconds=30.0)
    remaining = lifecycle.remaining_shutdown_seconds()
    assert remaining is not None and 0 < remaining <= 30.0


def test_close_driver_events() -> None:
    lifecycle.set_phase(Phase.RUNNING)
    lifecycle.request_shutdown("bye")
    pending = lifecycle.get_pending()
    lifecycle.record_close_executing(pending)
    lifecycle.record_close_completed(pending, duration_seconds=1.5)
    names = [e.name for e in lifecycle.get_recent_events()]
    assert "close_executing" in names and "close_completed" in names
    completed = [e for e in lifecycle.get_recent_events()
                 if e.name == "close_completed"][0]
    assert completed.metadata == {"kind": "shutdown", "duration_seconds": 1.5}


def test_diagnostics_snapshot_shape() -> None:
    lifecycle.set_phase(Phase.RUNNING)
    snap = lifecycle.diagnostics_snapshot()
    assert snap["phase"] == "RUNNING"
    assert snap["can_accept_commands"] is True
    assert snap["pending"] is None
    assert isinstance(snap["recent_events"], list)
