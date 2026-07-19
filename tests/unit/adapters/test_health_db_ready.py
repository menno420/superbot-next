"""K5 `db_ready()` probe-wrapper contract (frozen L0 spec 05 §3.8).

`readiness_decision` — the PURE state table — is covered by
`tests/unit/kernel/test_health_readiness.py`. This file covers the *async
probe* that feeds its `db_up` argument: the ~1s result cache (whose stated
purpose is "probe storms don't hammer the pool"), the bounded
`asyncio.wait_for` timeout, and the broad `except` that folds down / timeout /
uninitialised into a single "not up".

Every assertion here was reproduced against a live run of the real function
before being committed. Tests patch `sb.kernel.db.pool.checked_acquire` — the
one seam `db_ready` reaches through (`from sb.kernel.db import pool` inside the
function) — and use the module's own `reset_probe_cache_for_tests()`, which
until now had no consumer.

Async bodies are driven through a single `asyncio.run()` per test, matching the
suite convention (e.g. `tests/integration/test_mining_structure_build_race.py`);
the suite has no `asyncio_mode = auto`, so a bare `async def test_` would be a
silent skip.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

import pytest

from sb.adapters.http import health
from sb.kernel.db import pool
from sb.kernel.db.pool import DBUnavailable


@pytest.fixture(autouse=True)
def fresh_probe_cache():
    health.reset_probe_cache_for_tests()
    yield
    health.reset_probe_cache_for_tests()


def _counting_ok(counter: dict):
    """A `checked_acquire` stand-in: acquires cleanly, counts invocations."""

    @contextlib.asynccontextmanager
    async def _cm():
        counter["n"] += 1

        class _Conn:
            async def execute(self, _query):  # `SELECT 1` succeeds
                return None

        yield _Conn()

    return _cm


def test_success_returns_true_and_caches(monkeypatch):
    """Clean probe → True; a second call inside the window does NOT re-probe."""
    calls = {"n": 0}
    monkeypatch.setattr(pool, "checked_acquire", _counting_ok(calls))

    async def _run():
        first = await health.db_ready()
        second = await health.db_ready()
        return first, second

    first, second = asyncio.run(_run())

    assert first is True and second is True
    # THE anti-storm contract: one physical probe served both readers.
    assert calls["n"] == 1


def test_cache_expiry_reprobes(monkeypatch):
    """Window check is load-bearing: a lapsed cache re-probes."""
    calls = {"n": 0}
    monkeypatch.setattr(pool, "checked_acquire", _counting_ok(calls))
    # Collapse the window so any elapsed time counts as expired
    # ((now - cached_at) < 0.0 is always False -> always re-probe).
    monkeypatch.setattr(health, "_PROBE_CACHE_S", 0.0)

    async def _run():
        a = await health.db_ready()
        b = await health.db_ready()
        return a, b

    a, b = asyncio.run(_run())

    assert a is True and b is True
    assert calls["n"] == 2


def test_db_down_returns_false_and_caches_the_failure(monkeypatch):
    """DBUnavailable → False; the negative result is cached like the positive."""
    calls = {"n": 0}

    @contextlib.asynccontextmanager
    async def _down():
        calls["n"] += 1
        raise DBUnavailable("pool refused checkout")
        yield  # pragma: no cover - unreachable, satisfies the CM protocol

    monkeypatch.setattr(pool, "checked_acquire", _down)

    async def _run():
        first = await health.db_ready()
        second = await health.db_ready()
        return first, second

    first, second = asyncio.run(_run())

    assert first is False and second is False
    # A storm of *failing* probes is bounded too — only one reached the pool.
    assert calls["n"] == 1


def test_uninitialised_pool_reads_not_up():
    """No mock: an uninitialised pool raises inside checkout, folds to False.

    `pool.get()` raises RuntimeError when `init()` has not run; `db_ready`'s
    broad `except` reads that as "not up" — the docstring's `uninitialised`
    leg. The unit suite never calls `pool.init()`, so the pool is genuinely
    down here.
    """
    assert asyncio.run(health.db_ready()) is False


def test_bounded_probe_times_out_to_not_up(monkeypatch):
    """A wedged pool cannot hang /ready: wait_for bound → False, at the bound."""

    @contextlib.asynccontextmanager
    async def _slow():
        class _Conn:
            async def execute(self, _query):
                await asyncio.sleep(0.5)  # far past the bound below

        yield _Conn()

    monkeypatch.setattr(pool, "checked_acquire", _slow)
    monkeypatch.setattr(health, "_PROBE_TIMEOUT_S", 0.02)

    async def _run():
        started = time.monotonic()
        result = await health.db_ready()
        return result, time.monotonic() - started

    result, elapsed = asyncio.run(_run())

    assert result is False
    # Returned at the timeout bound, not after the 0.5s sleep.
    assert elapsed < 0.4
