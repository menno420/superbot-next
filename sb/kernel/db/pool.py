"""asyncpg pool + the sanctioned transaction seam (K3, frozen L0 spec 05 §3.4).

Ported from shipped `disbot/utils/db/pool.py` (superbot main 7f7628e1) with the
spec-05 hardening applied:

  - `command_timeout=cfg.DB_COMMAND_TIMEOUT_S` (bounds a wedged query) and
    `max_inactive_connection_lifetime=cfg.DB_IDLE_LIFETIME_S` on the pool;
  - `checked_acquire()` — validate-or-reacquire on checkout (closes the "dead
    connection handed to caller after a DB restart" class);
  - `transaction()` — THE sanctioned txn seam `once()` atomicity depends on;
  - `DBUnavailable(ConnectionError)` — the ONE typed signal for every raw
    asyncpg connection/pool error. It subclasses ConnectionError ON PURPOSE:
    spec 02 §3.3's `from_exception` transient row already lists
    ConnectionError, so DBUnavailable classifies transient/retryable=True/
    DISCORD_FAILED through that EXISTING row — no new row, no seam edit
    (spec 05 §3.9, fork 5b). Refuse-with-notice is centralized HERE (T2-14):
    no domain ever fails-open with empty/stale rows.

asyncpg is import-guarded so the module stays importable in containers
without it (metrics-style _NoOp discipline, D-0003); every runtime entry
point raises DBUnavailable if asyncpg is absent.

Raw `conn.execute` / `conn.transaction()` stay banned outside `sb/kernel/db`
(spec 05 §7) — domains use `fetchone/fetchall/execute` (autocommit) or
`db.transaction()` (explicit txn), never raw asyncpg.

NOTE (spec 08 §12.3, recorded for K4): best-effort bus.emit belongs after
commit; `AT_LEAST_ONCE` events are captured in-txn via `outbox.enqueue(conn,…)`
and delivered post-commit by the relay.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.config import Config

try:
    import asyncpg

    ASYNCPG_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in containers without asyncpg
    asyncpg = None  # type: ignore[assignment]
    ASYNCPG_AVAILABLE = False

logger = logging.getLogger("sb.db.pool")

__all__ = [
    "DBUnavailable",
    "checked_acquire",
    "close",
    "execute",
    "fetchall",
    "fetchone",
    "get",
    "init",
    "transaction",
]


class DBUnavailable(ConnectionError):
    """The pool could not serve — down, timed out, or checkout failed.

    The ONE typed signal the DB seam raises for every raw asyncpg
    connection/pool error (spec 05 §3.4). Subclasses ConnectionError so the
    resolver's `from_exception` (spec 02 §3.3) classifies it through its
    existing transient row — transient / retryable=True / DISCORD_FAILED.
    Layer ownership: the DB seam owns raw asyncpg -> DBUnavailable; the
    resolver owns typed exception -> ErrorEnvelope.
    """


# Module-level singleton. Tests may swap via monkeypatch (shipped pattern).
_pool: "asyncpg.Pool | None" = None

# Checkout-liveness threshold: a connection not seen for this long is pinged
# (SELECT 1) before being handed out (spec 05 §3.4 checked_acquire).
_PING_IDLE_S = 30.0
_last_seen: dict[int, float] = {}


def _connection_error_types() -> tuple[type[BaseException], ...]:
    """The raw error classes the seam converts to DBUnavailable.

    Connection/pool-level only — query-level PostgresError (syntax,
    constraint) is a bug/domain signal and passes through untouched.
    """
    types: list[type[BaseException]] = [ConnectionError, asyncio.TimeoutError, OSError]
    if ASYNCPG_AVAILABLE:
        types.extend([
            asyncpg.InterfaceError,             # pool/protocol misuse incl. ConnectionDoesNotExist
            asyncpg.PostgresConnectionError,    # cannot-connect family
            asyncpg.ConnectionFailureError,     # dropped mid-statement
        ])
    return tuple(types)


async def init_connection(conn: "asyncpg.Connection") -> None:
    """Register the JSONB codec on a new connection (shipped codec, ported).

    Every connection round-trips `jsonb` columns as plain dicts/lists (the
    K4 outbox payload column relies on this). Fresh chain — the shipped
    legacy double-encode shim is NOT ported (no pre-migration-012 rows).
    """
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog",
    )


async def init(cfg: "Config") -> None:
    """Create the pool, then run migrations (spec 05 §3.4/§3.6, boot order §6).

    Precondition: `assert_data_plane(cfg)` already passed inside preflight().
    """
    global _pool
    if not ASYNCPG_AVAILABLE:
        raise DBUnavailable("asyncpg is not installed — the DB seam cannot serve")
    try:
        _pool = await asyncpg.create_pool(
            cfg.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=cfg.DB_COMMAND_TIMEOUT_S,
            max_inactive_connection_lifetime=cfg.DB_IDLE_LIFETIME_S,
            init=init_connection,
        )
    except _connection_error_types() as exc:
        raise DBUnavailable(f"pool creation failed: {exc}") from exc
    # Lazy import — migrations.py imports this module for the CRUD helpers.
    from sb.kernel.db import migrations

    await migrations.ensure_migrations_table()
    await migrations.run_migrations()
    await migrations.verify_applied_checksums()
    logger.info("PostgreSQL pool initialised (%s)", cfg.DATABASE_URL.split("@")[-1])


async def close() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
    _last_seen.clear()


def get() -> "asyncpg.Pool":
    """Return the active pool; raise if init() has not run yet."""
    if _pool is None:
        raise RuntimeError("Database not initialised — call db.init(cfg) first.")
    return _pool


@asynccontextmanager
async def checked_acquire() -> AsyncIterator["asyncpg.Connection"]:
    """Acquire + validate-or-reacquire (spec 05 §3.4).

    On checkout, if the connection has been idle past `_PING_IDLE_S`,
    `SELECT 1`; on failure release-and-reacquire ONCE; a second failure
    raises DBUnavailable.
    """
    p = get()
    err_types = _connection_error_types()

    async def _acquire_validated() -> "asyncpg.Connection":
        conn = await p.acquire()
        now = time.monotonic()
        last = _last_seen.get(id(conn))
        if last is not None and (now - last) > _PING_IDLE_S:
            await conn.execute("SELECT 1")
        _last_seen[id(conn)] = time.monotonic()
        return conn

    try:
        conn = await _acquire_validated()
    except err_types:
        try:
            conn = await _acquire_validated()  # reacquire ONCE
        except err_types as exc:
            raise DBUnavailable(f"connection checkout failed twice: {exc}") from exc
    try:
        yield conn
    finally:
        _last_seen[id(conn)] = time.monotonic()
        await p.release(conn)


@asynccontextmanager
async def transaction() -> AsyncIterator["asyncpg.Connection"]:
    """THE sanctioned transaction seam (spec 05 §3.4, fork 7b).

    `async with db.transaction() as conn:` acquires via checked_acquire(),
    opens `conn.transaction()`, yields the txn-bound Connection, commits on
    clean exit / rolls back on exception. This is the ONLY sanctioned way a
    domain runs `once()` atomically with its effect: `once(key, conn=conn)`
    plus the action's own writes share ONE connection and ONE transaction,
    so the guard row and the effect commit-or-roll-back together. asyncpg
    connection failures inside the block surface as DBUnavailable (the
    rollback has already happened when the context unwinds).
    """
    err_types = _connection_error_types()
    async with checked_acquire() as conn:
        try:
            async with conn.transaction():
                yield conn
        except DBUnavailable:
            raise
        except err_types as exc:
            raise DBUnavailable(f"transaction failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Generic CRUD primitives — shipped signatures preserved verbatim; the
# refuse-with-notice posture (T2-14) is centralized here: asyncpg
# connection/pool errors re-raise as DBUnavailable, never fake results.
# ---------------------------------------------------------------------------

# Low-cardinality query label (shipped `_TABLE_RE` pattern preserved; its
# bound is DECLARED as db_query_seconds' query_name max_cardinality).
_TABLE_RE = re.compile(
    r"\b(?:FROM|INTO|UPDATE|DELETE\s+FROM)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)


def _query_label(query: str) -> str:
    """Extract an `<op>:<table>` label for histogram observation."""
    stripped = query.lstrip()
    op = stripped.split(None, 1)[0].lower() if stripped else "unknown"
    match = _TABLE_RE.search(query)
    table = match.group(1).lower() if match else "unknown"
    return f"{op}:{table}"


def _observe_query(query: str, elapsed_s: float) -> None:
    """Observe db_query_seconds; observability never blocks the seam."""
    try:
        from sb.kernel.observability import metrics as _metrics

        registry = _metrics.active_registry()
        if registry is not None:
            registry.histogram("db_query_seconds").labels(
                query_name=_query_label(query),
            ).observe(elapsed_s)
    except Exception:  # noqa: BLE001 — metrics are observability only
        pass


async def fetchone(
    query: str,
    params: tuple = (),
    *,
    conn: "asyncpg.Connection | None" = None,
) -> dict | None:
    start = time.monotonic()
    try:
        target = conn if conn is not None else get()
        try:
            row = await target.fetchrow(query, *params)
        except _connection_error_types() as exc:
            raise DBUnavailable(f"fetchone failed: {exc}") from exc
        return dict(row) if row else None
    finally:
        _observe_query(query, time.monotonic() - start)


async def fetchall(
    query: str,
    params: tuple = (),
    *,
    conn: "asyncpg.Connection | None" = None,
) -> list[dict]:
    start = time.monotonic()
    try:
        target = conn if conn is not None else get()
        try:
            rows = await target.fetch(query, *params)
        except _connection_error_types() as exc:
            raise DBUnavailable(f"fetchall failed: {exc}") from exc
        return [dict(r) for r in rows]
    finally:
        _observe_query(query, time.monotonic() - start)


async def execute(
    query: str,
    params: tuple = (),
    *,
    conn: "asyncpg.Connection | None" = None,
) -> str | None:
    start = time.monotonic()
    try:
        target = conn if conn is not None else get()
        try:
            return await target.execute(query, *params)
        except _connection_error_types() as exc:
            raise DBUnavailable(f"execute failed: {exc}") from exc
    finally:
        _observe_query(query, time.monotonic() - start)
