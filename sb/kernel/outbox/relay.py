"""The relay side: post-commit delivery lanes (K4, frozen L0 spec 08 §3.4).

The relay is NOT a standalone loop. `OutboxRelayLane` / `OutboxReaperLane`
implement the scheduler's `PollLane` port (spec 09 §3.6) and are REGISTERED
on the ONE shared `PollSupervisor` in the composition root at/after K5
(authored-at-K4 / registered-at-K5, F-1/RC-20). The supervisor owns the loop,
the 5s cadence, the RUNNING/drain gate, and per-lane exception isolation; the
lane owns what one cycle does.

`reconcile_on_boot` is a NO-OP (spec 08 fork E): the first post-RUNNING tick
IS the reconcile — a normal claim picks up every pre-crash PENDING row.

The two reserved delivery kwargs `_outbox_dedup_key` / `_outbox_correlation_id`
ride ALONGSIDE the frozen payload (never inside payload_schema); effectful
subscribers MUST self-dedup on `_outbox_dedup_key`, observability subscribers
ignore them via `**kwargs` (spec 08 §6.3).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Protocol

from sb.kernel.outbox.store import OutboxStore
from sb.kernel.scheduler.poll import LaneTickResult

logger = logging.getLogger("sb.outbox.relay")

__all__ = ["MAX_ATTEMPTS", "OutboxRelayLane", "OutboxReaperLane", "backoff"]

#: Gates DELIVERY_ATTEMPTS (bus-level failures) -> DEAD + operator finding.
#: NEVER gates claims (finding 6: a crash-looping relay must not dead-letter
#: a healthy event).
MAX_ATTEMPTS = 12


def backoff(delivery_attempts: int, *, base_s: int = 5, cap_s: int = 300) -> int:
    """min(base * 2**(n-1), cap) — the retry backoff (spec 08 §3.4)."""
    if delivery_attempts < 1:
        return base_s
    return min(base_s * 2 ** (delivery_attempts - 1), cap_s)


class _EventBusPort(Protocol):  # the shipped-bus shape the relay assumes (spec 08 §4)
    async def emit(self, name: str, **payload: object) -> object: ...


def _inc(metric_name: str, n: int = 1) -> None:
    """Guarded counter bump — observability never blocks delivery."""
    try:
        from sb.kernel.observability import metrics as _metrics

        registry = _metrics.active_registry()
        if registry is not None:
            registry.counter(metric_name).inc(n)
    except Exception:  # noqa: BLE001 — metrics are observability only
        pass


class OutboxRelayLane:
    """One claim->deliver cycle per tick (spec 08 §3.4, the fixed table)."""

    name = "outbox:relay"

    def __init__(
        self,
        *,
        bus: _EventBusPort,
        store: OutboxStore,
        findings=None,          # record_operator_finding(*, source, severity, summary, detail, correlation_id)
        batch_size: int = 100,
        lease_s: int = 30,
    ) -> None:
        self._bus = bus
        self._store = store
        self._findings = findings
        self._batch_size = batch_size
        self._lease_s = lease_s

    async def tick(self, now: datetime) -> LaneTickResult:
        # Step 0 (readiness gate) is SUPERVISOR-OWNED — no lane-local gate.
        # Step 1: atomic claim (SKIP LOCKED + lease; claims++, never attempts).
        rows = await self._store.claim(
            now, batch_size=self._batch_size, lease_s=self._lease_s,
        )
        _inc("outbox_claims_total", len(rows))
        delivered = 0
        failed = 0
        for row in rows:
            try:
                # Step 2: deliver — publish-accepted (a subscriber failure
                # never raises out of the shipped bus).
                await self._bus.emit(
                    row.event_name,
                    **dict(row.payload),
                    _outbox_dedup_key=row.dedup_key,
                    _outbox_correlation_id=(
                        str(row.correlation_id) if row.correlation_id else None
                    ),
                )
            except Exception as exc:  # noqa: BLE001 — step 3: bus-level failure
                failed += 1
                attempts_after = row.delivery_attempts + 1
                went_dead = await self._store.mark_retry_or_dead(
                    row,
                    now=now,
                    error=str(exc),
                    max_attempts=MAX_ATTEMPTS,
                    backoff_s=backoff(attempts_after),
                )
                if went_dead:
                    _inc("outbox_dead_letter_total")
                    self._record_dead_finding(row, exc)
            else:
                await self._store.mark_delivered(row.outbox_id, now)
                delivered += 1
                _inc("outbox_delivered_total")
        # Step 4 (crash/timeout mid-cycle) needs no code here: the lapsed
        # lease makes the row claimable again; supervisor isolates exceptions.
        return LaneTickResult(
            lane=self.name, claimed=len(rows), fired=delivered,
            failed=failed, skipped=0,
        )

    async def reconcile_on_boot(self, now: datetime) -> None:
        """NO-OP (fork E): the first post-RUNNING tick IS the reconcile."""
        return None

    def _record_dead_finding(self, row, exc: BaseException) -> None:
        if self._findings is None:
            logger.error("outbox row %s DEAD after %d delivery failures: %s",
                         row.outbox_id, MAX_ATTEMPTS, exc)
            return
        try:
            self._findings(
                source="sb.kernel.outbox",
                severity="error",
                summary=f"outbox dead-letter: {row.event_name}",
                detail=(f"row {row.outbox_id} dead after {MAX_ATTEMPTS} "
                        f"bus-level delivery failures; last error: {exc}"),
                correlation_id=row.correlation_id,
            )
        except Exception:  # noqa: BLE001 — findings must not break the cycle
            logger.exception("record_operator_finding failed for %s", row.outbox_id)


class OutboxReaperLane:
    """The retention pruner (spec 08 §3.4/finding 11): bounded
    delivered:7d / dead:90d sweep each tick."""

    name = "outbox:reaper"

    def __init__(self, *, store: OutboxStore, batch: int = 500) -> None:
        self._store = store
        self._batch = batch

    async def tick(self, now: datetime) -> LaneTickResult:
        pruned = await self._store.prune(now, batch=self._batch)
        return LaneTickResult(lane=self.name, claimed=pruned, fired=0,
                              failed=0, skipped=0)

    async def reconcile_on_boot(self, now: datetime) -> None:
        return None
