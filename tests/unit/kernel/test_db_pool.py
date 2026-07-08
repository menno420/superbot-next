"""K3 DB seam — pool module contract tests (spec 05 §3.4).

asyncpg is not installed in this container; these tests cover the
import-safety, the typed-error contract, and the conn-threading of the CRUD
primitives via fake connections. Pool-integration behavior (checked_acquire
ping, command_timeout) is exercised only when asyncpg is present.
"""

from __future__ import annotations

import asyncio

import pytest

from sb.kernel.db import pool


def test_module_imports_without_asyncpg() -> None:
    # The guarded import contract (D-0003 discipline): importable regardless.
    assert hasattr(pool, "ASYNCPG_AVAILABLE")


def test_dbunavailable_is_connectionerror() -> None:
    # Spec 05 fork 5b: routes through spec 02's EXISTING ConnectionError
    # transient row — subclassing IS the seam.
    assert issubclass(pool.DBUnavailable, ConnectionError)
    exc = pool.DBUnavailable("down")
    assert isinstance(exc, ConnectionError)


def test_get_raises_before_init() -> None:
    with pytest.raises(RuntimeError):
        pool.get()


def test_query_label_shapes() -> None:
    assert pool._query_label("SELECT * FROM idempotency_keys WHERE key=$1") == \
        "select:idempotency_keys"
    assert pool._query_label("INSERT INTO event_outbox VALUES (1)") == "insert:event_outbox"
    assert pool._query_label("DELETE FROM foo") == "delete:foo"
    assert pool._query_label("garbage") == "garbage:unknown"


class _FakeConn:
    """Minimal conn double for the conn= threading path."""

    def __init__(self, row: dict | None = None, rows: list[dict] | None = None,
                 raise_exc: BaseException | None = None) -> None:
        self.row = row
        self.rows = rows or []
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, tuple]] = []

    async def fetchrow(self, query: str, *params: object):
        self.calls.append((query, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.row

    async def fetch(self, query: str, *params: object):
        self.calls.append((query, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.rows

    async def execute(self, query: str, *params: object):
        self.calls.append((query, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return "OK"


def test_crud_threads_explicit_conn() -> None:
    conn = _FakeConn(row={"a": 1}, rows=[{"b": 2}])
    assert asyncio.run(pool.fetchone("SELECT 1", (), conn=conn)) == {"a": 1}
    assert asyncio.run(pool.fetchall("SELECT 1", (), conn=conn)) == [{"b": 2}]
    assert asyncio.run(pool.execute("SELECT 1", (), conn=conn)) == "OK"
    assert len(conn.calls) == 3


def test_crud_wraps_connection_errors_as_dbunavailable() -> None:
    conn = _FakeConn(raise_exc=ConnectionResetError("boom"))
    with pytest.raises(pool.DBUnavailable):
        asyncio.run(pool.fetchone("SELECT 1", (), conn=conn))
    conn = _FakeConn(raise_exc=asyncio.TimeoutError())
    with pytest.raises(pool.DBUnavailable):
        asyncio.run(pool.execute("SELECT 1", (), conn=conn))


def test_crud_passes_through_query_level_errors() -> None:
    # A domain-level error (not a connection failure) must NOT be masked.
    conn = _FakeConn(raise_exc=ValueError("bad query"))
    with pytest.raises(ValueError):
        asyncio.run(pool.fetchall("SELECT 1", (), conn=conn))


def test_init_without_asyncpg_raises_dbunavailable() -> None:
    if pool.ASYNCPG_AVAILABLE:
        pytest.skip("asyncpg installed — guarded-absence path not applicable")

    class _Cfg:
        DATABASE_URL = "postgres://u:p@localhost:5432/db"
        DB_COMMAND_TIMEOUT_S = 30.0
        DB_IDLE_LIFETIME_S = 300.0

    with pytest.raises(pool.DBUnavailable):
        asyncio.run(pool.init(_Cfg()))
