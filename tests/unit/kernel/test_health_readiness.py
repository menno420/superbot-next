"""K5 readiness/drain contract tests (frozen L0 spec 05 §3.8 state table)."""

from __future__ import annotations

import pytest

from sb.adapters.http.health import readiness_decision
from sb.kernel import lifecycle
from sb.kernel.lifecycle import Phase


@pytest.fixture(autouse=True)
def fresh_lifecycle():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


def test_gateway_not_ready_always_503() -> None:
    for phase in Phase:
        status, payload = readiness_decision(
            gateway_ready=False, phase=phase, db_up=True)
        assert status == 503
        assert payload["reason"] == "gateway_not_ready"


def test_running_db_up_is_the_only_200() -> None:
    status, payload = readiness_decision(
        gateway_ready=True, phase=Phase.RUNNING, db_up=True)
    assert status == 200 and payload["status"] == "ready"


def test_running_db_down_503_db_unavailable() -> None:
    # NEW vs shipped: closes the DB-blind gap.
    status, payload = readiness_decision(
        gateway_ready=True, phase=Phase.RUNNING, db_up=False)
    assert status == 503 and payload["reason"] == "db_unavailable"


def test_starting_503_still_starting() -> None:
    # THE deliberate semantics change (RC-9): shipped returned 200 here.
    status, payload = readiness_decision(
        gateway_ready=True, phase=Phase.STARTING, db_up=True)
    assert status == 503 and payload["reason"] == "still_starting"


@pytest.mark.parametrize("phase", [
    Phase.DRAINING, Phase.SHUTTING_DOWN, Phase.RESTARTING, Phase.STOPPED,
])
def test_draining_family_503(phase: Phase) -> None:
    status, payload = readiness_decision(
        gateway_ready=True, phase=phase, db_up=True)
    assert status == 503 and payload["reason"] == "draining"


def test_failed_startup_503() -> None:
    status, payload = readiness_decision(
        gateway_ready=True, phase=Phase.FAILED_STARTUP, db_up=True)
    assert status == 503 and payload["reason"] == "failed_startup"


def test_payload_always_carries_phase() -> None:
    lifecycle.set_phase(Phase.DRAINING)
    status, payload = readiness_decision(
        gateway_ready=True, phase=Phase.DRAINING, db_up=False)
    assert payload["phase"] == "DRAINING"
    assert payload["accepting_commands"] is False
