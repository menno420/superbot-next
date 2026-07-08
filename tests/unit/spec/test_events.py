"""K4 event grammar tests (frozen L0 spec 08 §3.1)."""

from __future__ import annotations

import pytest

from sb.spec.events import (
    AUDIT_ACTION_RECORDED,
    EVT_AUDIT_ACTION_RECORDED,
    KNOWN_EVENTS,
    DeliveryClass,
    EventRedefined,
    EventSpec,
    FieldSpec,
    clear_event_registry,
    register_event_specs,
)


@pytest.fixture(autouse=True)
def fresh_registry():
    clear_event_registry()
    yield
    clear_event_registry()


def test_delivery_class_two_members() -> None:
    assert {m.value for m in DeliveryClass} == {"best_effort", "at_least_once"}


def test_eventspec_default_is_best_effort() -> None:
    # Zero behavior change for the observability fleet (spec 08 fork A).
    spec = EventSpec(name="xp.awarded")
    assert spec.delivery is DeliveryClass.BEST_EFFORT
    assert spec.audited is False


def test_audit_canary_seeded_durable() -> None:
    # The kernel seed: audit.action_recorded opts in from birth (§11 item 5).
    assert EVT_AUDIT_ACTION_RECORDED in KNOWN_EVENTS
    spec = KNOWN_EVENTS[EVT_AUDIT_ACTION_RECORDED]
    assert spec.delivery is DeliveryClass.AT_LEAST_ONCE
    assert spec.audited is True
    assert len(spec.payload_schema) == 11  # the frozen 11-field payload
    assert spec is AUDIT_ACTION_RECORDED


def test_register_identical_is_noop_different_raises() -> None:
    spec = EventSpec(name="economy.balance_changed", owner_subsystem="economy")
    register_event_specs([spec])
    register_event_specs([spec])  # identical re-registration: no-op
    with pytest.raises(EventRedefined):
        register_event_specs([EventSpec(name="economy.balance_changed",
                                        owner_subsystem="treasury")])


def test_field_spec_defaults() -> None:
    f = FieldSpec("guild_id", type="int", required=False)
    assert (f.name, f.type, f.required) == ("guild_id", "int", False)
    assert FieldSpec("mutation_id").required is True
