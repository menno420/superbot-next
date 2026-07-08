"""K4 enqueue-side tests (frozen L0 spec 08 §3.3/§3.5/§6.5)."""

from __future__ import annotations

import asyncio
import datetime as dt
import enum
import uuid
from dataclasses import dataclass, field

import pytest

from sb.kernel.outbox.enqueue import (
    BestEffortBatch,
    UnknownEventError,
    enqueue,
    enqueue_all,
    enqueue_audit_action,
    to_jsonable,
)
from sb.spec.events import DeliveryClass, EventSpec, clear_event_registry, register_event_specs


class _FakeStore:
    """Records insert calls; simulates ON CONFLICT via dedup_key memory."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.keys: set[str] = set()

    async def insert(self, conn, *, dedup_key, event_name, payload, guild_id,
                     now, correlation_id=None) -> bool:
        if dedup_key in self.keys:
            return False
        self.keys.add(dedup_key)
        self.rows.append({
            "dedup_key": dedup_key, "event_name": event_name,
            "payload": payload, "guild_id": guild_id,
            "correlation_id": correlation_id,
        })
        return True


@pytest.fixture(autouse=True)
def fresh_registry():
    clear_event_registry()
    yield
    clear_event_registry()


class _Color(enum.Enum):
    RED = "red"


def test_to_jsonable_codec() -> None:
    stamp = dt.datetime(2026, 7, 8, 12, 0, tzinfo=dt.timezone.utc)
    uid = uuid.uuid4()
    out = to_jsonable({
        "when": stamp, "color": _Color.RED, "id": uid,
        "n": 3, "ok": True, "nested": {"t": stamp}, "seq": [stamp],
    })
    assert out["when"] == stamp.isoformat()
    assert out["color"] == "red"
    assert out["id"] == str(uid)
    assert out["n"] == 3 and out["ok"] is True
    assert out["nested"]["t"] == stamp.isoformat()
    assert out["seq"] == [stamp.isoformat()]


def test_enqueue_unknown_name_hard_raises() -> None:
    # Fork D: a mis-named guaranteed event rolls back the whole effect.
    store = _FakeStore()
    with pytest.raises(UnknownEventError):
        asyncio.run(enqueue(
            None, event_name="no.such.event", payload={}, guild_id=1,
            dedup_token="t", _store=store,
        ))
    assert store.rows == []


def test_enqueue_missing_required_payload_key_raises() -> None:
    register_event_specs([EventSpec(
        name="xp.awarded",
        payload_schema=(
            __import__("sb.spec.events", fromlist=["FieldSpec"]).FieldSpec("user_id"),
        ),
        delivery=DeliveryClass.AT_LEAST_ONCE,
    )])
    with pytest.raises(ValueError):
        asyncio.run(enqueue(
            None, event_name="xp.awarded", payload={}, guild_id=1,
            dedup_token="t", _store=_FakeStore(),
        ))


def test_enqueue_idempotent_by_key() -> None:
    store = _FakeStore()
    register_event_specs([EventSpec(name="economy.balance_changed",
                                    delivery=DeliveryClass.AT_LEAST_ONCE)])

    async def scenario() -> None:
        first = await enqueue(None, event_name="economy.balance_changed",
                              payload={"delta": 5}, guild_id=9,
                              dedup_token="mut-1:economy.balance_changed",
                              namespace="economy", _store=store)
        dup = await enqueue(None, event_name="economy.balance_changed",
                            payload={"delta": 5}, guild_id=9,
                            dedup_token="mut-1:economy.balance_changed",
                            namespace="economy", _store=store)
        assert first is True and dup is False   # False = already captured, not an error

    asyncio.run(scenario())
    assert len(store.rows) == 1
    assert store.rows[0]["dedup_key"] == "economy:9:mut-1:economy.balance_changed"


def test_enqueue_audit_action_twin_payload() -> None:
    store = _FakeStore()
    stamp = dt.datetime(2026, 7, 8, 12, 0, tzinfo=dt.timezone.utc)
    mutation_id = str(uuid.uuid4())

    ok = asyncio.run(enqueue_audit_action(
        None, mutation_id=mutation_id, subsystem="settings",
        mutation_type="update", target="xp.enabled", scope="guild",
        guild_id=5, prev_value="false", new_value="true",
        actor_id=42, actor_type="member", occurred_at=stamp,
        _store=store,
    ))
    assert ok is True
    row = store.rows[0]
    assert row["event_name"] == "audit.action_recorded"
    # namespace="audit", dedup_token=mutation_id (the frozen audit link)
    assert row["dedup_key"] == f"audit:5:{mutation_id}"
    # occurred_at rides as the ISO string — byte-identical to the shipped bus.
    assert row["payload"]["occurred_at"] == stamp.isoformat()
    assert set(row["payload"]) == {
        "mutation_id", "subsystem", "mutation_type", "target", "scope",
        "guild_id", "prev_value", "new_value", "actor_id", "actor_type",
        "occurred_at",
    }
    assert row["correlation_id"] == uuid.UUID(mutation_id)


@dataclass
class _Emit:
    event: str
    delivery: DeliveryClass
    payload_builder: object = None


@dataclass
class _Ctx:
    guild_id: int = 7
    op_key: str = "economy.farm_collect"


@dataclass
class _Result:
    mutation_id: str = "mut-77"
    dedup_key: object = None


class _Bus:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict]] = []

    async def emit(self, name: str, **payload: object) -> None:
        self.emitted.append((name, payload))


def test_enqueue_all_two_call_protocol() -> None:
    store = _FakeStore()
    bus = _Bus()
    register_event_specs([
        EventSpec(name="xp.awarded", delivery=DeliveryClass.AT_LEAST_ONCE),
        EventSpec(name="xp.level_up", delivery=DeliveryClass.AT_LEAST_ONCE),
        EventSpec(name="ui.refresh"),  # best-effort
    ])
    emits = (
        _Emit("xp.awarded", DeliveryClass.AT_LEAST_ONCE,
              lambda ctx, res: {"amount": 10}),
        _Emit("xp.level_up", DeliveryClass.AT_LEAST_ONCE,
              lambda ctx, res: {"level": 2}),
        _Emit("ui.refresh", DeliveryClass.BEST_EFFORT,
              lambda ctx, res: {"panel": "xp"}),
    )

    async def scenario() -> None:
        batch = await enqueue_all(emits, _Ctx(), _Result(), conn=None,
                                  bus=bus, _store=store)
        # In-txn half: both AT_LEAST_ONCE rows written NOW, distinct keys
        # via the :{emit_index} disambiguator (finding 2).
        assert [r["dedup_key"] for r in store.rows] == [
            "economy.farm_collect:7:mut-77:0",
            "economy.farm_collect:7:mut-77:1",
        ]
        assert bus.emitted == []          # nothing emitted pre-commit
        emitted = await batch.emit_after_commit()   # the step-6 call
        assert emitted == 1
        assert bus.emitted == [("ui.refresh", {"panel": "xp"})]

    asyncio.run(scenario())


def test_best_effort_batch_without_bus_drops_loudly() -> None:
    batch = BestEffortBatch(_events=[("ui.refresh", {})], _bus=None)
    assert asyncio.run(batch.emit_after_commit()) == 0
