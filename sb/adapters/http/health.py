"""HTTP health server: /health, /ready, /lifecycle, /metrics (K5).

Ported from shipped `disbot/healthserver.py` (superbot main 7f7628e1) with
the frozen L0 spec 05 §3.8 readiness/drain contract applied — the FULL state
table, including two deliberate changes from shipped behavior:

  1. **RUNNING-only 200 (RC-9 / §3.8 note).** Shipped `_ready_handler`
     returned 200 while `can_accept_commands()` (= {STARTING, RUNNING}).
     Here STARTING => 503 `still_starting`: a replica still booting (pool not
     up, migrations mid-apply, on_ready not fired) cannot serve commands, so
     the orchestrator must not route to it. `can_accept_commands()` remains
     valid for its own callers (command admission) — it is just not the
     `/ready` gate anymore.
  2. **DB-aware readiness.** RUNNING + DB down => 503 `db_unavailable`
     (closes the shipped DB-blind gap). The probe is a bounded `SELECT 1`
     via `checked_acquire()`, cached ~1s so probe storms don't hammer the
     pool.

The declared consumer (was missing): the orchestrator healthcheck points at
`/ready`; the fast-release deploy handoff (T2-2) reads 503-while-DRAINING as
the stop-routing signal. `/metrics` returns `render()` (spec 05 §3.3) and is
independent of lifecycle phase (a draining replica still exposes metrics).

aiohttp is import-guarded (not installed in CI containers); the DECISION
core (`readiness_decision`) is pure and fully tested without it. Host/port
come from Config (`HEALTH_HOST`/`HEALTH_PORT` — declared ConfigSpecs; no raw
env reads in this module, check_config_usage applies).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Callable

from sb.kernel import lifecycle
from sb.kernel.lifecycle import Phase
from sb.kernel.observability.metrics import render

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sb.kernel.config import Config

try:
    from aiohttp import web

    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in containers without aiohttp
    web = None  # type: ignore[assignment]
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger("sb.http.health")

__all__ = ["db_ready", "readiness_decision", "start_health_server"]

_DRAINING_PHASES = frozenset(
    {Phase.DRAINING, Phase.SHUTTING_DOWN, Phase.RESTARTING, Phase.STOPPED},
)

# DB-probe cache (~1s) + bound (seconds) — spec 05 §3.8.
_PROBE_CACHE_S = 1.0
_PROBE_TIMEOUT_S = 2.0
_probe_cache: tuple[float, bool] | None = None  # (monotonic_at, result)


def readiness_decision(
    *,
    gateway_ready: bool,
    phase: Phase,
    db_up: bool,
) -> tuple[int, dict]:
    """The PURE §3.8 state table: (http_status, payload).

    | gateway | phase                       | DB   | /ready | reason            |
    |---------|-----------------------------|------|--------|-------------------|
    | False   | any                         | any  | 503    | gateway_not_ready |
    | True    | RUNNING                     | up   | 200    | —                 |
    | True    | RUNNING                     | down | 503    | db_unavailable    |
    | True    | STARTING                    | any  | 503    | still_starting    |
    | True    | DRAINING/SHUTDOWN/... phases| any  | 503    | draining          |
    | True    | FAILED_STARTUP              | any  | 503    | failed_startup    |
    """
    base = {"phase": phase.value, "accepting_commands": lifecycle.can_accept_commands()}
    if not gateway_ready:
        return 503, {"status": "not_ready", "reason": "gateway_not_ready", **base}
    if phase is Phase.RUNNING:
        if db_up:
            return 200, {"status": "ready", **base}
        return 503, {"status": "not_ready", "reason": "db_unavailable", **base}
    if phase is Phase.STARTING:
        return 503, {"status": "not_ready", "reason": "still_starting", **base}
    if phase in _DRAINING_PHASES:
        return 503, {"status": "not_ready", "reason": "draining", **base}
    # FAILED_STARTUP (terminal)
    return 503, {"status": "not_ready", "reason": "failed_startup", **base}


async def db_ready() -> bool:
    """Bounded `SELECT 1` via checked_acquire(), cached ~1s (spec 05 §3.8)."""
    global _probe_cache
    now = time.monotonic()
    if _probe_cache is not None and (now - _probe_cache[0]) < _PROBE_CACHE_S:
        return _probe_cache[1]
    from sb.kernel.db import pool

    try:
        async def _probe() -> None:
            async with pool.checked_acquire() as conn:
                await conn.execute("SELECT 1")

        await asyncio.wait_for(_probe(), timeout=_PROBE_TIMEOUT_S)
        result = True
    except Exception:  # noqa: BLE001 — down/timeout/uninitialised all read "not up"
        result = False
    _probe_cache = (time.monotonic(), result)
    return result


def reset_probe_cache_for_tests() -> None:
    global _probe_cache
    _probe_cache = None


# ---------------------------------------------------------------------------
# aiohttp wiring (guarded) — the four routes on ONE server (spec 05 §3.8).
# ---------------------------------------------------------------------------

def _json_response(payload: dict, status: int = 200):
    return web.Response(text=json.dumps(payload), status=status,
                        content_type="application/json")


async def start_health_server(
    cfg: "Config",
    *,
    gateway_ready: Callable[[], bool] = lambda: True,
    ready_event: asyncio.Event | None = None,
) -> None:
    """Start the aiohttp health server and block until cancelled.

    `gateway_ready` is the injected gateway probe (the composition root
    passes `bot.is_ready` once the gateway exists; headless boots pass the
    default). `ready_event` is set after the TCP bind succeeds so the
    composition root can fail fast on a bind error (shipped O-2b pattern —
    a bind failure propagates after cleanup; the event is NOT set).

    Binds `cfg.HEALTH_HOST` (default `::`, IPv6 dual-stack for Railway
    private networking) : `cfg.HEALTH_PORT` (default 8080).
    """
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp is not installed — the health server cannot start")

    started_at = time.monotonic()

    async def _health(request):  # liveness: 200 while the loop is alive
        return _json_response({
            "status": "ok",
            "uptime_seconds": round(time.monotonic() - started_at, 1),
            "phase": lifecycle.get_phase().value,
        })

    async def _ready(request):
        phase = lifecycle.get_phase()
        db_up = await db_ready() if phase is Phase.RUNNING else False
        status, payload = readiness_decision(
            gateway_ready=bool(gateway_ready()), phase=phase, db_up=db_up,
        )
        return _json_response(payload, status)

    async def _lifecycle(request):  # diagnostic dump; always 200
        return _json_response(lifecycle.diagnostics_snapshot())

    async def _metrics(request):
        body, content_type = render()
        # Full Prometheus exposition type carries params ("; version=0.0.4;
        # charset=utf-8") — set the header directly (aiohttp's content_type
        # kwarg rejects parameters).
        return web.Response(body=body, headers={"Content-Type": content_type})

    app = web.Application()
    app.router.add_get("/health", _health)
    app.router.add_get("/ready", _ready)
    app.router.add_get("/lifecycle", _lifecycle)
    app.router.add_get("/metrics", _metrics)

    runner = web.AppRunner(app, access_log=None)
    try:
        await runner.setup()
        site = web.TCPSite(runner, cfg.HEALTH_HOST, int(cfg.HEALTH_PORT))
        await site.start()
        logger.info("Health server listening on %s:%s", cfg.HEALTH_HOST, cfg.HEALTH_PORT)
        if ready_event is not None:
            ready_event.set()
        await asyncio.get_running_loop().create_future()  # until cancelled
    finally:
        await runner.cleanup()
