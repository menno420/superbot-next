"""Shared fakes for the K7 engine tests: a fake txn-bound conn that services
the idempotency/audit/outbox SQL (the test_idempotency _Conn pattern widened)
and a monkeypatched db.transaction()."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field

import pytest

from sb.kernel.db import pool
from sb.kernel.workflow.registry import REGISTRY


@dataclass
class FakeConn:
    """Duck-types asyncpg Connection for pool.fetchone/fetchall/execute."""

    idempotency: dict = field(default_factory=dict)   # key -> row
    audit_rows: dict = field(default_factory=dict)    # mutation_id -> row
    outbox: list = field(default_factory=list)        # captured event rows
    executed: list = field(default_factory=list)
    rolled_back: bool = False

    async def fetchrow(self, query: str, *params):
        self.executed.append((query, params))
        if query.startswith("INSERT INTO idempotency_keys"):
            key, namespace, first_seen = params
            if key in self.idempotency:
                return None
            self.idempotency[key] = {"key": key, "namespace": namespace,
                                     "first_seen_at": first_seen,
                                     "outcome": None, "result_ref": None}
            return {"key": key}
        if query.startswith("SELECT outcome"):
            row = self.idempotency.get(params[0])
            if row is None:
                return None
            return {"outcome": row["outcome"], "result_ref": row["result_ref"],
                    "first_seen_at": row["first_seen_at"]}
        if query.startswith("SELECT prev_value"):
            row = self.audit_rows.get(params[0])
            return dict(row) if row else None
        if query.startswith("INSERT INTO event_outbox"):
            self.outbox.append(params)
            return {"outbox_id": params[0]}
        raise AssertionError(f"unexpected fetchrow: {query}")

    async def fetch(self, query: str, *params):
        raise AssertionError(f"unexpected fetch: {query}")

    async def execute(self, query: str, *params):
        self.executed.append((query, params))
        if query.startswith("UPDATE idempotency_keys"):
            key, outcome, result_ref = params
            self.idempotency[key]["outcome"] = outcome
            self.idempotency[key]["result_ref"] = result_ref
            return "UPDATE 1"
        if query.startswith("INSERT INTO audit_log"):
            (mutation_id, subsystem, mutation_type, target, scope, guild_id,
             prev_value, new_value, actor_id, actor_type, occurred_at, detail,
             correlation_id) = params
            self.audit_rows[mutation_id] = {
                "mutation_id": mutation_id, "subsystem": subsystem,
                "mutation_type": mutation_type, "target": target,
                "scope": scope, "guild_id": guild_id,
                "prev_value": prev_value, "new_value": new_value,
                "actor_id": actor_id, "actor_type": actor_type,
                "occurred_at": occurred_at, "detail": detail,
                "correlation_id": correlation_id,
            }
            return "INSERT 1"
        raise AssertionError(f"unexpected execute: {query}")

    def snapshot(self) -> tuple:
        """Byte-identical-state probe for the dry-run oracle."""
        return (dict(self.idempotency), dict(self.audit_rows), list(self.outbox))

    def restore(self, snap: tuple) -> None:
        self.idempotency, self.audit_rows, self.outbox = (
            dict(snap[0]), dict(snap[1]), list(snap[2]))
        self.rolled_back = True


@pytest.fixture()
def fake_conn(monkeypatch):
    """Installs a rollback-honoring fake db.transaction(); yields the conn."""
    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        snap = conn.snapshot()
        try:
            yield conn
        except Exception:
            conn.restore(snap)   # rollback semantics
            raise

    monkeypatch.setattr(pool, "transaction", fake_transaction)
    return conn


@pytest.fixture(autouse=True)
def _clean_registry():
    REGISTRY.clear_for_tests()
    yield
    REGISTRY.clear_for_tests()


@dataclass(frozen=True)
class Actor:
    user_id: int | None = 1
    actor_type: str = "user"
    member_tier: str | None = "administrator"
    role_ids: frozenset = frozenset()
    is_dm: bool = False
