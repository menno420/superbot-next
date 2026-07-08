"""K4 relay-lane tests (frozen L0 spec 08 §3.4/§3.6) — fake store + bus."""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid

from sb.kernel.outbox.relay import (
    MAX_ATTEMPTS,
    OutboxReaperLane,
    OutboxRelayLane,
    backoff,
)
from sb.kernel.outbox.store import OutboxRow, OutboxStatus
from sb.kernel.scheduler.poll import LaneTickResult, PollLane

NOW = dt.datetime(2026, 7, 8, 12, 0, tzinfo=dt.timezone.utc)


def _row(event: str = "audit.action_recorded", attempts: int = 0,
         payload: dict | None = None) -> OutboxRow:
    return OutboxRow(
        outbox_id=uuid.uuid4(),
        dedup_key=f"audit:1:{uuid.uuid4()}",
        event_name=event,
        payload=payload or {"mutation_id": "m-1"},
        guild_id=1,
        created_at=NOW,
        available_at=NOW,
        claims=1,
        delivery_attempts=attempts,
        status=OutboxStatus.PENDING,
        delivered_at=None,
        last_error=None,
        correlation_id=uuid.uuid4(),
    )


class _FakeStore:
    def __init__(self, rows: list[OutboxRow] | None = None) -> None:
        self.rows = rows or []
        self.delivered: list[uuid.UUID] = []
        self.retried: list[tuple[uuid.UUID, str, int]] = []
        self.dead: list[uuid.UUID] = []
        self.pruned = 0

    async def claim(self, now, *, batch_size, lease_s):
        batch, self.rows = self.rows[:batch_size], self.rows[batch_size:]
        return tuple(batch)

    async def mark_delivered(self, outbox_id, now):
        self.delivered.append(outbox_id)

    async def mark_retry_or_dead(self, row, *, now, error, max_attempts, backoff_s):
        if row.delivery_attempts + 1 >= max_attempts:
            self.dead.append(row.outbox_id)
            return True
        self.retried.append((row.outbox_id, error, backoff_s))
        return False

    async def prune(self, now, *, batch=500):
        self.pruned += 1
        return 3


class _Bus:
    def __init__(self, fail_names: set[str] | None = None) -> None:
        self.fail_names = fail_names or set()
        self.emitted: list[tuple[str, dict]] = []

    async def emit(self, name: str, **payload: object):
        if name in self.fail_names:
            raise RuntimeError("bus down")
        self.emitted.append((name, payload))


def test_backoff_curve() -> None:
    assert backoff(1) == 5
    assert backoff(2) == 10
    assert backoff(3) == 20
    assert backoff(12) == 300  # capped


def test_lanes_satisfy_the_poll_port() -> None:
    relay = OutboxRelayLane(bus=_Bus(), store=_FakeStore())
    reaper = OutboxReaperLane(store=_FakeStore())
    assert isinstance(relay, PollLane)
    assert isinstance(reaper, PollLane)
    assert relay.name == "outbox:relay"
    assert reaper.name == "outbox:reaper"


def test_tick_delivers_and_carries_reserved_keys() -> None:
    row = _row()
    store = _FakeStore([row])
    bus = _Bus()
    lane = OutboxRelayLane(bus=bus, store=store)

    result = asyncio.run(lane.tick(NOW))
    assert result == LaneTickResult(lane="outbox:relay", claimed=1, fired=1,
                                    failed=0, skipped=0)
    assert store.delivered == [row.outbox_id]
    name, payload = bus.emitted[0]
    assert name == "audit.action_recorded"
    assert payload["mutation_id"] == "m-1"           # named payload byte-identical
    assert payload["_outbox_dedup_key"] == row.dedup_key       # §6.3 carriers
    assert payload["_outbox_correlation_id"] == str(row.correlation_id)


def test_tick_bus_failure_retries_with_backoff() -> None:
    row = _row(attempts=0)
    store = _FakeStore([row])
    lane = OutboxRelayLane(bus=_Bus(fail_names={"audit.action_recorded"}), store=store)

    result = asyncio.run(lane.tick(NOW))
    assert result.failed == 1 and result.fired == 0
    assert store.dead == []
    (outbox_id, error, backoff_s) = store.retried[0]
    assert outbox_id == row.outbox_id
    assert "bus down" in error
    assert backoff_s == backoff(1)


def test_tick_dead_letters_after_max_attempts_and_records_finding() -> None:
    row = _row(attempts=MAX_ATTEMPTS - 1)
    store = _FakeStore([row])
    findings: list[dict] = []

    def record_finding(**kwargs):
        findings.append(kwargs)

    lane = OutboxRelayLane(bus=_Bus(fail_names={"audit.action_recorded"}),
                           store=store, findings=record_finding)
    result = asyncio.run(lane.tick(NOW))
    assert result.failed == 1
    assert store.dead == [row.outbox_id]
    assert findings[0]["source"] == "sb.kernel.outbox"
    assert findings[0]["severity"] == "error"
    assert "dead-letter" in findings[0]["summary"]


def test_reconcile_on_boot_is_noop() -> None:
    # Fork E: the first post-RUNNING tick IS the reconcile.
    lane = OutboxRelayLane(bus=_Bus(), store=_FakeStore())
    assert asyncio.run(lane.reconcile_on_boot(NOW)) is None


def test_reaper_tick_prunes() -> None:
    store = _FakeStore()
    lane = OutboxReaperLane(store=store)
    result = asyncio.run(lane.tick(NOW))
    assert result == LaneTickResult(lane="outbox:reaper", claimed=3, fired=0,
                                    failed=0, skipped=0)
    assert store.pruned == 1
