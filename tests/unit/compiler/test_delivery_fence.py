"""The delivery_declared fence (S5, spec 08 §3.1 — additive to P6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sb.spec.events import DeliveryClass
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import EngineRef, HandlerRef, handler
from sb.spec.roles import register_field_roles
from tools.manifest_compile import compile_manifests


# Fence-local fixture facets (duck-typed; roles idempotent on re-import).
@dataclass(frozen=True)
class EventSpecFx:
    name: str
    observability_only: bool = False
    delivery: DeliveryClass = DeliveryClass.BEST_EFFORT
    expected_subscribers: tuple = ()


@dataclass(frozen=True)
class StoreSpecFx:
    table: str
    sole_writer: object = None
    checkpoint_class: str = "ledger"
    invariant_tag: str | None = None


register_field_roles("EventSpecFx", name="S", observability_only="S",
                     delivery="S", expected_subscribers="S")
register_field_roles("StoreSpecFx", table="S", sole_writer="S",
                     checkpoint_class="S", invariant_tag="S")


def _manifest(events, stores=()):
    return SubsystemManifest(key="xp", events=tuple(events), stores=tuple(stores))


def _violation_details(result):
    return [v.detail for v in result.violations]


def test_observability_only_cannot_be_at_least_once() -> None:
    m = _manifest(
        [EventSpecFx("xp.observed", observability_only=True,
                     delivery=DeliveryClass.AT_LEAST_ONCE)],
        stores=[StoreSpecFx("xp")],
    )
    result = compile_manifests(manifests=[m])
    assert not result.ok
    assert any("delivery_declared: observability_only" in d
               for d in _violation_details(result))


def test_at_least_once_requires_a_store() -> None:
    m = _manifest([EventSpecFx("xp.awarded", delivery=DeliveryClass.AT_LEAST_ONCE)])
    result = compile_manifests(manifests=[m])
    assert not result.ok
    assert any("writes no store" in d for d in _violation_details(result))


def test_effectful_subscriber_must_accept_reserved_keys() -> None:
    @handler("xp.on_awarded_closed")
    def _closed(user_id: int) -> None:  # pragma: no cover — signature only
        pass

    m = _manifest(
        [EventSpecFx("xp.awarded", delivery=DeliveryClass.AT_LEAST_ONCE,
                     expected_subscribers=(HandlerRef("xp.on_awarded_closed"),))],
        stores=[StoreSpecFx("xp")],
    )
    result = compile_manifests(manifests=[m])
    assert not result.ok
    assert any("_outbox_" in d for d in _violation_details(result))


def test_subscriber_with_kwargs_passes() -> None:
    @handler("xp.on_awarded_open")
    def _open(user_id: int, **_extras) -> None:  # pragma: no cover
        pass

    m = _manifest(
        [EventSpecFx("xp.awarded", delivery=DeliveryClass.AT_LEAST_ONCE,
                     expected_subscribers=(HandlerRef("xp.on_awarded_open"),))],
        stores=[StoreSpecFx("xp")],
    )
    result = compile_manifests(manifests=[m])
    assert result.ok, [f"{v.locus}: {v.detail}" for v in result.violations]
    # The snapshot's events projection carries the delivery class.
    assert result.snapshot["projections"]["events"]["xp.awarded"]["delivery"] == \
        "at_least_once"


def test_best_effort_events_unaffected() -> None:
    m = _manifest([EventSpecFx("xp.observed", observability_only=True)])
    result = compile_manifests(manifests=[m])
    assert result.ok, [f"{v.locus}: {v.detail}" for v in result.violations]
