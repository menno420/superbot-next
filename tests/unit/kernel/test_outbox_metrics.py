"""D4 P1 — the outbox metric families are armed and emit at the relay seam.

Two gaps this proves closed (D4 observability design, P1):

1. The four `OUTBOX_METRICS` families are only live when the composition root
   unions them into the registry (`METRICS + OUTBOX_METRICS`); with the default
   `METRICS` tuple they are unregistered and the relay's guarded bumps hit a
   swallowed `KeyError`.
2. `outbox_pending_age_seconds` now has an emitter — the relay tick sets it from
   a bounded store read.

The emit-path assertions use a recording registry so they hold whether or not
`prometheus_client` is installed (the code-quality gate runs pytest with no
runtime deps); the end-to-end exposition assertion is prometheus-gated.
"""

from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from sb.kernel.observability import metrics as metrics_mod
from sb.kernel.outbox import store as store_mod
from sb.kernel.outbox.metrics import OUTBOX_METRICS
from sb.kernel.outbox.relay import MAX_ATTEMPTS, OutboxRelayLane
from sb.kernel.outbox.store import OutboxStore
from sb.spec.observability import METRICS

from tests.unit.kernel.test_outbox_relay import _Bus, _FakeStore, _row  # reuse fakes

NOW = dt.datetime(2026, 7, 8, 12, 0, tzinfo=dt.timezone.utc)

_OUTBOX_FAMILIES = {
    "outbox_pending_age_seconds",
    "outbox_delivered_total",
    "outbox_dead_letter_total",
    "outbox_claims_total",
}


# --- registration (composition-root union) -------------------------------


def test_default_registry_leaves_outbox_families_dark() -> None:
    # Pre-fix state / regression guard: the default tuple never instantiates
    # the outbox families, so a relay bump would hit a swallowed KeyError.
    registry = metrics_mod.build_registry(METRICS)
    for family in ("outbox_delivered_total", "outbox_dead_letter_total",
                   "outbox_claims_total"):
        with pytest.raises(KeyError):
            registry.counter(family)
    with pytest.raises(KeyError):
        registry.gauge("outbox_pending_age_seconds")


def test_union_registers_all_four_outbox_families() -> None:
    registry = metrics_mod.build_registry(METRICS + OUTBOX_METRICS)
    # All four resolve without raising (counters + the one gauge).
    assert registry.counter("outbox_delivered_total") is not None
    assert registry.counter("outbox_dead_letter_total") is not None
    assert registry.counter("outbox_claims_total") is not None
    assert registry.gauge("outbox_pending_age_seconds") is not None


# --- emit at the outbox seam (prometheus-independent) ---------------------


class _RecCounter:
    def __init__(self, rec: list, name: str) -> None:
        self._rec, self._name = rec, name

    def inc(self, n: int = 1) -> None:
        self._rec.append(("inc", self._name, n))


class _RecGauge:
    def __init__(self, rec: list, name: str) -> None:
        self._rec, self._name = rec, name

    def set(self, value: float) -> None:
        self._rec.append(("set", self._name, value))


class _RecRegistry:
    """Records the seam calls the relay makes through the active registry."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def counter(self, name: str) -> _RecCounter:
        return _RecCounter(self.calls, name)

    def gauge(self, name: str) -> _RecGauge:
        return _RecGauge(self.calls, name)


def test_relay_tick_emits_claims_delivered_and_pending_age(monkeypatch) -> None:
    rec = _RecRegistry()
    monkeypatch.setattr(metrics_mod, "_ACTIVE", rec)
    store = _FakeStore([_row(), _row()], pending_age=42.0)
    lane = OutboxRelayLane(bus=_Bus(), store=store)

    asyncio.run(lane.tick(NOW))

    assert ("inc", "outbox_claims_total", 2) in rec.calls          # one bump, len(rows)
    delivered = [c for c in rec.calls if c == ("inc", "outbox_delivered_total", 1)]
    assert len(delivered) == 2                                      # one per delivered row
    assert ("set", "outbox_pending_age_seconds", 42.0) in rec.calls  # the previously-dark gauge


def test_relay_tick_emits_dead_letter_counter(monkeypatch) -> None:
    rec = _RecRegistry()
    monkeypatch.setattr(metrics_mod, "_ACTIVE", rec)
    row = _row(attempts=MAX_ATTEMPTS - 1)
    store = _FakeStore([row])
    lane = OutboxRelayLane(bus=_Bus(fail_names={"audit.action_recorded"}),
                           store=store, findings=lambda **_: None)

    asyncio.run(lane.tick(NOW))

    assert ("inc", "outbox_dead_letter_total", 1) in rec.calls


def test_pending_age_emit_never_raises_when_store_read_fails(monkeypatch) -> None:
    rec = _RecRegistry()
    monkeypatch.setattr(metrics_mod, "_ACTIVE", rec)

    class _BoomStore(_FakeStore):
        async def pending_age_seconds(self, now):
            raise RuntimeError("db down")

    lane = OutboxRelayLane(bus=_Bus(), store=_BoomStore([_row()]))
    # Delivery still completes; the gauge emit is swallowed (guarded).
    result = asyncio.run(lane.tick(NOW))
    assert result.fired == 1
    assert not any(c[0] == "set" for c in rec.calls)


# --- the bounded store read that feeds the gauge -------------------------


def _stub_fetchone(oldest):
    async def _fetchone(query, params=(), *, conn=None):
        assert "MIN(available_at)" in query and "'pending'" in query
        return {"oldest": oldest}
    return _fetchone


def test_pending_age_seconds_zero_when_no_pending(monkeypatch) -> None:
    monkeypatch.setattr(store_mod.pool, "fetchone", _stub_fetchone(None))
    age = asyncio.run(OutboxStore().pending_age_seconds(NOW))
    assert age == 0.0


def test_pending_age_seconds_is_now_minus_oldest(monkeypatch) -> None:
    oldest = NOW - dt.timedelta(seconds=125)
    monkeypatch.setattr(store_mod.pool, "fetchone", _stub_fetchone(oldest))
    age = asyncio.run(OutboxStore().pending_age_seconds(NOW))
    assert age == 125.0


def test_pending_age_seconds_clamps_future_available_at_to_zero(monkeypatch) -> None:
    # A row backing off has available_at in the future -> not yet due, reads as
    # no backpressure rather than a negative age.
    future = NOW + dt.timedelta(seconds=30)
    monkeypatch.setattr(store_mod.pool, "fetchone", _stub_fetchone(future))
    age = asyncio.run(OutboxStore().pending_age_seconds(NOW))
    assert age == 0.0


# --- end-to-end exposition (prometheus-gated) ----------------------------


def test_union_registry_renders_outbox_families_on_metrics() -> None:
    pytest.importorskip("prometheus_client")
    orig = metrics_mod._ACTIVE
    try:
        metrics_mod.build_registry(METRICS + OUTBOX_METRICS)  # sets _ACTIVE
        store = _FakeStore([_row()], pending_age=7.0)
        lane = OutboxRelayLane(bus=_Bus(), store=store)
        asyncio.run(lane.tick(NOW))

        body, content_type = metrics_mod.render()
        assert body                                             # not the _NoOp empty body
        assert b"outbox_delivered_total" in body
        assert b"outbox_claims_total" in body
        assert b"outbox_pending_age_seconds 7.0" in body        # the armed gauge value
        assert content_type == metrics_mod.CONTENT_TYPE
    finally:
        metrics_mod._ACTIVE = orig
