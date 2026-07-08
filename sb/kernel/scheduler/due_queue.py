"""The ``DueQueueLane`` + the fire (K9/S10 — frozen L0 spec 09 §3.7/§3.8).

The whole fire is ONE scheduler-owned txn: ``once()`` (deterministic
``task_id:fire_epoch`` — the fix for the shipped uuid4-defeated claim) +
K7 ``run_ref(ref, ctx, conn=conn)`` (pure-DB legs + central audit +
AT_LEAST_ONCE enqueue on MY conn) + ``mark_fired``/advance commit together —
no crash window in either direction.

S10 obligations honored here:
- ``check_atomic_db_only(spec)`` runs for EVERY armed WorkflowRef handler
  (at declare/arm time when the workflow is registered) — a scheduler-fired
  spec must be pure-DB (Discord output rides the outbox, never an EFFECT leg).
- The task-fire audit fence: a mutating fire must target a WorkflowRef.
- A-13: user-scoped fires carry the CREATOR's ActorRef (re-resolving K6 at
  fire time inside K7) — never the SYSTEM_ACTOR scripted bypass; quiet-hours
  filter fires (DEFER pushes to window end; SKIP drops the occurrence;
  a one-shot never SKIPs — pinned DEFER, a one-shot must not silently lose
  its only fire).
- R-17: a CONDITION trigger evaluates its registered predicate each poll;
  the handler fires only when it holds (else the slot advances forward).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from sb.kernel.db import scheduler as scheduler_db
from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.db.pool import transaction
from sb.kernel.db.scheduler import MAX_FIRE_ATTEMPTS, DueTimer
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.scheduler.misfire import MisfireDecision, apply_misfire, next_slot
from sb.kernel.scheduler.poll import LaneTickResult, SYSTEM_CLOCK
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.compile import check_atomic_db_only
from sb.kernel.workflow.context import WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.spec.refs import HandlerRef, WorkflowRef, resolve as resolve_ref
from sb.spec.scheduler import (
    ConditionTrigger,
    Cron,
    EventTrigger,
    Interval,
    ManagedTaskSpec,
    OneShot,
    QuietHours,
    QuietHoursPolicy,
    TaskDurability,
    TaskScope,
)

logger = logging.getLogger("sb.kernel.scheduler.due_queue")

__all__ = [
    "DueQueueLane",
    "SYSTEM_ACTOR",
    "SchedulerFenceError",
    "clear_declared_tasks_for_tests",
    "declare_task",
    "declared_tasks",
]

# the canonical system-actor sentinel (spec 09 §3.7 — actor_type="system"
# rides the K6 scripted bypass). Imported lazily to avoid the interaction
# package's module-level workflow import chain at leaf level.
from sb.kernel.interaction.request import ActorRef  # noqa: E402

SYSTEM_ACTOR = ActorRef(user_id=None, is_guild_operator=False,
                        is_bot_owner=False, is_dm=False,
                        actor_type="system", member_tier=None)

DEFAULT_LEASE_S = 60
CLAIM_LIMIT = 50
BOOT_BATCH = 20
DISABLE_AFTER_N = 3


class SchedulerFenceError(Exception):
    """A declare/arm-time fence violation (SEMANTIC_VIOLATION class)."""


# --- the declared-task registry (manifest-declared ManagedTaskSpecs) ------------

_DECLARED: dict[str, ManagedTaskSpec] = {}


def _check_task(spec: ManagedTaskSpec) -> None:
    # task-fire audit fence (spec 09 §3.4, mirrors ③.4): a mutating fire
    # must be a WorkflowRef (the audited engine), never a bare HandlerRef.
    effect = getattr(spec, "effect", None)
    if effect == "mutating" and not isinstance(spec.handler, WorkflowRef):
        raise SchedulerFenceError(
            f"{spec.name}: a mutating task fire must target a WorkflowRef")
    if isinstance(spec.trigger, EventTrigger):
        # bus-armed, never polled — declaring it DURABLE on the due-queue
        # is a category error.
        if spec.durability is TaskDurability.DURABLE:
            raise SchedulerFenceError(
                f"{spec.name}: an EventTrigger task is armed by the bus, "
                f"never persisted in the due-queue")
    if spec.quiet_hours is not None:
        qh = spec.quiet_hours
        if not (0 <= qh.start_hour <= 23 and 0 <= qh.end_hour <= 23):
            raise SchedulerFenceError(f"{spec.name}: quiet_hours hours must be 0-23")
    # the S10 obligation: check_atomic_db_only for every armed WorkflowRef
    # (resolvable now ⇒ fenced now; unresolved refs are boot's P2/ref failure).
    if isinstance(spec.handler, WorkflowRef):
        try:
            op = REGISTRY.resolve(spec.handler)
        except LookupError:
            op = None
        if op is not None:
            problems = check_atomic_db_only(op)
            if problems:
                raise SchedulerFenceError(
                    f"{spec.name}: handler {spec.handler.name!r} violates "
                    f"atomic_db_only: {problems}")


def declare_task(spec: ManagedTaskSpec) -> ManagedTaskSpec:
    """Register a manifest-declared task (arm_declared_tasks arms the
    DURABLE recurring ones at boot). Fences run here."""
    _check_task(spec)
    prior = _DECLARED.get(spec.name)
    if prior is not None and prior != spec:
        raise SchedulerFenceError(f"task {spec.name!r} declared twice with differing specs")
    _DECLARED[spec.name] = spec
    return spec


def declared_tasks() -> tuple[ManagedTaskSpec, ...]:
    return tuple(_DECLARED.values())


def clear_declared_tasks_for_tests() -> None:
    _DECLARED.clear()


# --- helpers --------------------------------------------------------------------

def _once_namespace(task_key: str) -> str:
    """K3's IdempotencyKey.namespace is colon-free; task_key is
    '<subsystem>:<purpose>' — fold ':' to '.' deterministically."""
    return task_key.replace(":", ".")


def _actor_for(timer: DueTimer) -> ActorRef:
    """A-13: a user-scoped fire carries the CREATOR's actor (K6 re-resolves
    at fire time inside K7); system tasks ride SYSTEM_ACTOR."""
    creator = timer.payload.get("_creator_actor")
    if isinstance(creator, Mapping) and creator.get("user_id") is not None:
        return ActorRef(
            user_id=int(creator["user_id"]),
            is_guild_operator=bool(creator.get("is_guild_operator", False)),
            is_bot_owner=False, is_dm=False, actor_type="user",
            member_tier=creator.get("member_tier"),
            role_ids=frozenset(int(r) for r in creator.get("role_ids", ())))
    return SYSTEM_ACTOR


def _quiet_hours_of(timer: DueTimer) -> QuietHours | None:
    raw = timer.payload.get("_quiet_hours")
    if not isinstance(raw, Mapping):
        return None
    return QuietHours(start_hour=int(raw["start_hour"]), end_hour=int(raw["end_hour"]),
                      tz=str(raw.get("tz", "UTC")),
                      policy=QuietHoursPolicy(raw.get("policy", "defer")))


def _in_quiet_window(qh: QuietHours, now: datetime) -> bool:
    local_hour = now.astimezone(ZoneInfo(qh.tz)).hour
    if qh.start_hour == qh.end_hour:
        return False
    if qh.start_hour < qh.end_hour:
        return qh.start_hour <= local_hour < qh.end_hour
    return local_hour >= qh.start_hour or local_hour < qh.end_hour   # wraps midnight


def _quiet_window_end(qh: QuietHours, now: datetime) -> datetime:
    local = now.astimezone(ZoneInfo(qh.tz))
    end = local.replace(hour=qh.end_hour, minute=0, second=0, microsecond=0)
    if end <= local:
        end += timedelta(days=1)
    return end.astimezone(now.tzinfo)


async def _condition_holds(timer: DueTimer) -> bool:
    condition = timer.payload.get("_condition")
    if not condition:
        return True
    from sb.kernel.interaction.predicates import EvalContext, evaluate
    return await evaluate(str(condition), EvalContext(guild_id=timer.guild_id or 0))


# --- the lane -------------------------------------------------------------------

class DueQueueLane:
    """A PollLane. tick = claim → misfire → quiet-hours → fire each;
    reconcile_on_boot = arm declared → reap leases → BOUNDED claim loop."""

    name = "due_queue"

    def __init__(self, *, instance_id: str | None = None, clock=SYSTEM_CLOCK,
                 lease_s: int = DEFAULT_LEASE_S) -> None:
        self.instance_id = instance_id or f"sb-{uuid.uuid4().hex[:8]}"
        self.clock = clock
        self.lease_s = lease_s

    # -- arming -------------------------------------------------------------

    async def arm_declared_tasks(self, now: datetime) -> int:
        """First-boot arm of every DURABLE recurring ManagedTaskSpec —
        idempotent via arm's ON CONFLICT DO NOTHING on the COALESCE slot."""
        armed = 0
        for spec in declared_tasks():
            if spec.durability is not TaskDurability.DURABLE:
                continue
            if isinstance(spec.trigger, (OneShot, EventTrigger)):
                continue   # one-shots are producer-armed; events are bus-armed
            await self.arm_task(spec, now=now)
            armed += 1
        return armed

    def _timer_from_spec(self, spec: ManagedTaskSpec, *, fire_at: datetime,
                         now: datetime, guild_id: int | None,
                         payload: Mapping[str, Any] | None,
                         recurring: bool) -> DueTimer:
        payload = dict(payload or {})
        if spec.quiet_hours is not None:
            payload["_quiet_hours"] = {
                "start_hour": spec.quiet_hours.start_hour,
                "end_hour": spec.quiet_hours.end_hour,
                "tz": spec.quiet_hours.tz,
                "policy": spec.quiet_hours.policy.value}
        interval_seconds = None
        cron_expr = None
        if isinstance(spec.trigger, Interval):
            interval_seconds = spec.trigger.seconds
        elif isinstance(spec.trigger, Cron):
            cron_expr = spec.trigger.expr
        elif isinstance(spec.trigger, ConditionTrigger):
            interval_seconds = spec.trigger.poll_interval_s
            payload["_condition"] = spec.trigger.condition
        if isinstance(spec.handler, WorkflowRef):
            payload["_handler_workflow"] = spec.handler.name
        else:
            payload["_handler_ref"] = spec.handler.name
        return DueTimer(
            task_id=str(uuid.uuid4()), task_key=spec.name, guild_id=guild_id,
            trigger_kind=spec.trigger_kind.value, fire_at=fire_at,
            payload=payload, payload_version=1, recurring=recurring,
            misfire_policy=spec.misfire_policy.value, catch_up=spec.catch_up,
            grace_s=spec.grace_s, max_catchup=spec.max_catchup,
            interval_seconds=interval_seconds, cron_expr=cron_expr,
            error_policy=spec.error_policy.value, created_at=now, updated_at=now)

    async def arm_task(self, spec: ManagedTaskSpec, *, guild_id: int | None = None,
                       payload: Mapping[str, Any] | None = None,
                       now: datetime | None = None) -> str:
        """Arm a recurring task (idempotent slot upsert)."""
        _check_task(spec)
        now = now or self.clock()
        if spec.scope is TaskScope.GUILD and guild_id is None:
            raise SchedulerFenceError(f"{spec.name}: GUILD scope requires guild_id")
        if isinstance(spec.trigger, Interval):
            fire_at = now + timedelta(seconds=spec.trigger.seconds)
        elif isinstance(spec.trigger, ConditionTrigger):
            fire_at = now + timedelta(seconds=spec.trigger.poll_interval_s)
        elif isinstance(spec.trigger, Cron):
            probe = self._timer_from_spec(spec, fire_at=now, now=now,
                                          guild_id=guild_id, payload=payload,
                                          recurring=True)
            fire_at = next_slot(probe, after=now)
        else:
            raise SchedulerFenceError(
                f"{spec.name}: arm_task is for recurring triggers "
                f"(use arm_one_shot / the event bus)")
        timer = self._timer_from_spec(spec, fire_at=fire_at, now=now,
                                      guild_id=guild_id, payload=payload,
                                      recurring=True)
        async with transaction() as conn:
            await scheduler_db.arm(timer, conn=conn)
        return timer.task_id

    async def arm_one_shot(self, spec: ManagedTaskSpec, fire_at: datetime, *,
                           guild_id: int | None = None,
                           payload: Mapping[str, Any] | None = None) -> str:
        _check_task(spec)
        now = self.clock()
        timer = self._timer_from_spec(spec, fire_at=fire_at, now=now,
                                      guild_id=guild_id, payload=payload,
                                      recurring=False)
        async with transaction() as conn:
            await scheduler_db.arm(timer, conn=conn)
        return timer.task_id

    async def cancel_task(self, task_id: str) -> None:
        async with transaction() as conn:
            await scheduler_db.cancel(task_id, conn=conn)

    # -- the poll body --------------------------------------------------------

    async def tick(self, now: datetime) -> LaneTickResult:
        async with transaction() as conn:
            batch = await scheduler_db.claim_due(
                now, limit=CLAIM_LIMIT, lease_s=self.lease_s,
                instance_id=self.instance_id, conn=conn)
        fired = failed = skipped = 0
        for timer in batch:
            f, fl, sk = await self._fire(timer, apply_misfire(timer, now), now)
            fired += f
            failed += fl
            skipped += sk
        return LaneTickResult(lane=self.name, claimed=len(batch), fired=fired,
                              failed=failed, skipped=skipped)

    async def reconcile_on_boot(self, now: datetime) -> None:
        """arm declared → reap crashed leases → BOUNDED claim loop (same
        SKIP-LOCKED path as steady state — never a stampede)."""
        await self.arm_declared_tasks(now)
        async with transaction() as conn:
            await scheduler_db.reap_expired_leases(now, conn=conn)
        while True:
            async with transaction() as conn:
                batch = await scheduler_db.claim_due(
                    now, limit=BOOT_BATCH, lease_s=self.lease_s,
                    instance_id=self.instance_id, conn=conn)
            if not batch:
                break
            for timer in batch:
                await self._fire(timer, apply_misfire(timer, now), now)

    # -- the fire --------------------------------------------------------------

    async def _fire(self, timer: DueTimer, decision: MisfireDecision,
                    now: datetime) -> tuple[int, int, int]:
        """→ (fired, failed, skipped). Drives _fire_one per epoch; the LAST
        epoch carries next_fire_at so the recurring slot advances exactly
        once after the replay set."""
        if decision.truncated:
            record_operator_finding(
                source="scheduler", severity="warning",
                summary=f"FIRE_ALL truncated for {timer.task_key}",
                detail=f"missed fires beyond max_catchup={timer.max_catchup} dropped")

        # quiet hours (A-13): filter BEFORE any epoch fires.
        qh = _quiet_hours_of(timer)
        if qh is not None and decision.fire_epochs and _in_quiet_window(qh, now):
            if qh.policy is QuietHoursPolicy.SKIP and timer.recurring:
                decision = replace(decision, fire_epochs=())
            else:
                # DEFER (and every one-shot): push the fire to the window end
                # (mark_fired with a datetime re-schedules the row to pending;
                # the DELETE branch only triggers on next_fire_at=None).
                async with transaction() as conn:
                    await scheduler_db.mark_fired(
                        timer, _quiet_window_end(qh, now), conn=conn)
                return (0, 0, len(decision.fire_epochs))

        # R-17 condition-poll: evaluate; a non-holding condition advances forward.
        if decision.fire_epochs and timer.payload.get("_condition"):
            try:
                holds = await _condition_holds(timer)
            except Exception:  # noqa: BLE001 — a broken predicate never wedges the lane
                logger.warning("condition eval failed for %s", timer.task_key,
                               exc_info=True)
                holds = False
            if not holds:
                decision = replace(decision, fire_epochs=())

        if not decision.fire_epochs:
            # nothing to fire — advance the slot (or delete a one-shot that
            # somehow had no epoch, which cannot happen by construction).
            async with transaction() as conn:
                await scheduler_db.mark_fired(timer, decision.next_fire_at, conn=conn)
            return (0, 0, 1)

        fired = failed = 0
        for i, epoch in enumerate(decision.fire_epochs):
            last = i == len(decision.fire_epochs) - 1
            ok = await self._fire_one(
                timer, epoch, decision.next_fire_at if last else None, now)
            if ok:
                fired += 1
            else:
                failed += 1
                break   # error handling already routed the slot
        return (fired, failed, 0)

    def _resolve_handler(self, timer: DueTimer):
        spec = _DECLARED.get(timer.task_key)
        if spec is not None:
            return spec.handler
        wf = timer.payload.get("_handler_workflow")
        if wf:
            return WorkflowRef(str(wf))
        hr = timer.payload.get("_handler_ref")
        if hr:
            return HandlerRef(str(hr))
        raise LookupError(f"timer {timer.task_key!r} has no resolvable handler")

    async def _fire_one(self, timer: DueTimer, fire_epoch: int,
                        next_fire_at: datetime | None, now: datetime) -> bool:
        """ONE scheduler-owned txn: once() + run_ref(conn) + record_outcome +
        mark_fired/advance — all-or-nothing (spec 09 §3.7)."""
        key = IdempotencyKey(namespace=_once_namespace(timer.task_key),
                             guild_id=timer.guild_id or 0,
                             dedup_token=f"{timer.task_id}:{fire_epoch}")
        handler = self._resolve_handler(timer)
        params = {k: v for k, v in timer.payload.items() if not k.startswith("_")}
        ctx = WorkflowContext(actor=_actor_for(timer), guild_id=timer.guild_id or 0,
                              request_id=key.render(), params=params,
                              clock=self.clock, correlation_id=None)
        try:
            async with transaction() as conn:
                if not await once(key, conn=conn):
                    prior = await read_outcome(key, conn=conn)
                    logger.info("fire replay no-op for %s (%s)", timer.task_key,
                                prior.outcome if prior else "in-flight")
                    await scheduler_db.mark_fired(timer, next_fire_at, conn=conn)
                    return True
                if isinstance(handler, WorkflowRef):
                    result = await workflow_engine.run_ref(handler, ctx, conn=conn)
                    await record_outcome(key, result.outcome,
                                         result_ref=result.mutation_id, conn=conn)
                else:
                    # a declared non-mutating HandlerRef fire (log/metrics tasks)
                    out = await resolve_ref(handler)(ctx)
                    await record_outcome(key, "success",
                                         result_ref=str(out) if out else None,
                                         conn=conn)
                await scheduler_db.mark_fired(timer, next_fire_at, conn=conn)
            return True
        except Exception as exc:  # noqa: BLE001 — classified, never raised out
            await self._route_failure(timer, exc, next_fire_at, now)
            return False

    async def _route_failure(self, timer: DueTimer, exc: Exception,
                             next_fire_at: datetime | None, now: datetime) -> None:
        from sb.kernel.interaction.errors import from_exception
        from sb.kernel.interaction.request import Surface
        from sb.spec.outcomes import ErrorClass
        envelope = from_exception(exc, surface=Surface.MAINTENANCE, target=None)
        if envelope.error_class is ErrorClass.TRANSIENT:
            async with transaction() as conn:
                if timer.attempts >= MAX_FIRE_ATTEMPTS:
                    await scheduler_db.mark_dead(
                        timer.task_id, f"transient cap hit: {exc}", conn=conn)
                    record_operator_finding(
                        source="scheduler", severity="error",
                        summary=f"timer dead: {timer.task_key}",
                        detail=f"{MAX_FIRE_ATTEMPTS} transient attempts; last: {exc}")
                else:
                    await scheduler_db.mark_failed(timer.task_id, str(exc),
                                                   retryable=True, conn=conn)
            return
        # non-retryable: error_policy routes the slot (spec 09 §3.8).
        async with transaction() as conn:
            row = await scheduler_db.mark_failed(timer.task_id, str(exc),
                                                 retryable=False, conn=conn)
            failures = row.consecutive_failures if row else 1
            if timer.error_policy == "disable_after_n" and failures >= DISABLE_AFTER_N:
                await scheduler_db.cancel(timer.task_id, conn=conn)
                record_operator_finding(
                    source="scheduler", severity="error",
                    summary=f"timer disabled: {timer.task_key}",
                    detail=f"{failures} consecutive non-retryable failures; last: {exc}")
                return
            if timer.error_policy == "escalate_finding":
                record_operator_finding(
                    source="scheduler", severity="error",
                    summary=f"timer fire failed: {timer.task_key}", detail=str(exc))
            else:
                logger.warning("timer fire failed (%s): %s", timer.task_key, exc)
            # LOG / ESCALATE / pre-N DISABLE: advance past the bad slot.
            await scheduler_db.mark_fired(timer, next_fire_at, conn=conn)
