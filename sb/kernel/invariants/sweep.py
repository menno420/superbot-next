"""``InvariantSweepLane`` (S12 — frozen L0 spec 11 §2.2): a ``PollLane`` on
09's one ``PollSupervisor``, PEER to the due-queue + draft janitor — NOT a
second due-queue claim loop, NOT a ManagedTaskSpec fire (a sweep is a
bounded loop of independent idempotent repairs, not one atomic op).

- Dual-instance cadence guard = the frozen ④ ``once()`` substrate:
  ``{invariant_id}.sweep : {cadence_epoch}`` — at-most-once per window per
  invariant across instances, zero sb_due_queue contention.
- Per-violation dispatch: report-only default (the operative enforce state
  is the settings-backed ``invariants.enforce.<id>`` runtime toggle, never
  the manifest constant); REPAIRABLE repairs ride the 09 ``_fire_one``
  pattern verbatim (once + run_ref(conn) + record_outcome, ONE txn);
  QUARANTINE_ONLY / failed repairs soft-quarantine (evidence-preserving,
  never destroy); the ``max_actions_per_run`` circuit breaker bounds BOTH
  postures and escalates ``mass_corruption``.
- ``SWEEP_ACTOR.actor_type = "backfill"`` (RC-18) — the data-repair member
  of the scripted-bypass set, distinguishing sweep-repairs from 09's
  ``system`` fires in the audit trail. Errors classify under the ONE frozen
  background surface: ``from_exception(exc, surface=MAINTENANCE, target=None)``
  (RC-19/PIN-4).
- ``run_verify_import`` — the CUT-2 stage-3.5 / CUT-3 verified-restore
  entry: the SAME sweep, dry-run FORCED, returning the machine-readable
  stop-codes (``invariant_violation`` / ``unrepaired_quarantine``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sb.kernel import settings as settings_mod
from sb.kernel.db import invariants as inv_db
from sb.kernel.db.idempotency import IdempotencyKey, once, read_outcome, record_outcome
from sb.kernel.db.pool import transaction
from sb.kernel.interaction.request import ActorRef
from sb.kernel.observability.findings import record_operator_finding
from sb.kernel.scheduler.poll import LaneTickResult, SYSTEM_CLOCK
from sb.kernel.workflow import engine as workflow_engine
from sb.kernel.workflow.context import WorkflowContext
from sb.spec.invariants import (
    CADENCE_SECONDS,
    InvariantSpec,
    Severity,
    SweepCadence,
    Violation,
    declared_invariants,
)
from sb.spec.outcomes import SUCCESS
from sb.spec.refs import resolve as resolve_ref

logger = logging.getLogger("sb.kernel.invariants.sweep")

__all__ = [
    "SWEEP_ACTOR",
    "InvariantSweepLane",
    "VerifyImportReport",
    "install_guild_source",
    "register_enforce_setting",
    "reset_sweep_ports_for_tests",
    "run_verify_import",
]

# RC-18: the data-repair scripted-bypass sentinel (mirrors 09's SYSTEM_ACTOR;
# actor_type="backfill" makes "which mutations were sweep-driven?" filterable).
SWEEP_ACTOR = ActorRef(user_id=None, is_guild_operator=False,
                       is_bot_owner=False, is_dm=False,
                       actor_type="backfill", member_tier=None)

# guild-enumeration port (per-guild batched sweeps); the gateway band installs
# the real source. Default: no guilds — the sweep is a structural no-op.
_guild_source = None


def install_guild_source(source) -> None:
    global _guild_source
    _guild_source = source


def reset_sweep_ports_for_tests() -> None:
    global _guild_source
    _guild_source = None


def register_enforce_setting(spec: InvariantSpec) -> None:
    """The per-invariant one-way-door runtime toggle (spec 11 §2.4):
    `invariants.enforce.<id>` — settings-backed, flipped live, never a
    manifest edit. Idempotent per id."""
    try:
        settings_mod.register_setting(settings_mod.SettingDeclaration(
            subsystem="invariants", name=f"enforce.{spec.invariant_id}",
            default=spec.default_enforce))
    except ValueError:
        pass   # already declared (module re-import)


async def _effective_enforce(spec: InvariantSpec) -> bool:
    try:
        return bool(await settings_mod.resolve(
            0, "invariants", f"enforce.{spec.invariant_id}"))
    except LookupError:
        return spec.default_enforce


@dataclass
class _SweepCounts:
    rows_read: int = 0
    violations: int = 0
    repairs: int = 0
    quarantined: int = 0
    alerts: int = 0
    breaker: bool = False


class InvariantSweepLane:
    name = "invariant_sweep"

    def __init__(self, *, clock=SYSTEM_CLOCK) -> None:
        self.clock = clock

    async def tick(self, now: datetime) -> LaneTickResult:
        fired = failed = 0
        for spec in declared_invariants():
            seconds = CADENCE_SECONDS[spec.cadence]
            if seconds is None:
                continue   # ON_BOOT — reconcile only
            epoch = int(now.timestamp()) // seconds
            if not await self._claim_epoch(spec, epoch):
                continue
            ok = await self._run_sweep(spec, epoch, now, force_report_only=False)
            fired += 1 if ok else 0
            failed += 0 if ok else 1
        return LaneTickResult(lane=self.name, claimed=fired + failed,
                              fired=fired, failed=failed, skipped=0)

    async def reconcile_on_boot(self, now: datetime) -> None:
        """Run ON_BOOT invariants once per boot (epoch = boot timestamp //
        3600 keeps a crash-loop from re-sweeping every restart)."""
        for spec in declared_invariants():
            if spec.cadence is not SweepCadence.ON_BOOT:
                continue
            epoch = int(now.timestamp()) // 3600
            if await self._claim_epoch(spec, epoch):
                await self._run_sweep(spec, epoch, now, force_report_only=False)

    async def _claim_epoch(self, spec: InvariantSpec, epoch: int) -> bool:
        key = IdempotencyKey(namespace=f"{spec.invariant_id}.sweep",
                             guild_id=0, dedup_token=str(epoch))
        async with transaction() as conn:
            return await once(key, conn=conn)

    async def _run_sweep(self, spec: InvariantSpec, epoch: int, now: datetime,
                         *, force_report_only: bool) -> bool:
        enforce = (False if force_report_only
                   else await _effective_enforce(spec))
        run = inv_db.SweepRun(invariant_id=spec.invariant_id,
                              cadence_epoch=epoch, started_at=now,
                              enforce_effective=enforce)
        counts = _SweepCounts()
        try:
            check = resolve_ref(spec.check_ref)
            guilds = tuple(_guild_source()) if _guild_source else ()
            targets = guilds or (None,)
            for guild_id in targets:
                run.guilds_scanned += 1
                async with transaction() as conn:
                    violations = await check(spec, guild_id=guild_id, conn=conn)
                counts.rows_read += len(violations)
                for v in violations:
                    if counts.violations >= spec.max_actions_per_run:
                        counts.breaker = True
                        record_operator_finding(
                            source="invariant_sweep", severity="critical",
                            summary=f"mass_corruption: {spec.invariant_id}",
                            detail=f"actions/findings cap {spec.max_actions_per_run} "
                                   f"hit — sweep STOPPED, overflow "
                                   f"{'quarantined' if enforce else 'reported'}")
                        if enforce:
                            await self._quarantine(spec, v, now)
                            counts.quarantined += 1
                        break
                    counts.violations += 1
                    await self._dispatch(spec, v, enforce, now, counts)
                if counts.breaker:
                    break
            run.outcome = SUCCESS
            ok = True
        except Exception:  # noqa: BLE001 — a broken check never wedges the lane
            logger.warning("sweep failed for %s", spec.invariant_id, exc_info=True)
            run.outcome = "blocked"
            ok = False
        run.rows_read = counts.rows_read
        run.violations_found = counts.violations
        run.repairs_applied = counts.repairs
        run.quarantined = counts.quarantined
        run.alerts = counts.alerts
        run.breaker_tripped = counts.breaker
        run.finished_at = self.clock()
        key = IdempotencyKey(namespace=f"{spec.invariant_id}.sweep",
                             guild_id=0, dedup_token=str(epoch))
        async with transaction() as conn:
            await record_outcome(key, run.outcome, result_ref=run.run_id, conn=conn)
            await inv_db.write_sweep_log(run, conn=conn)
        return ok

    async def _dispatch(self, spec: InvariantSpec, v: Violation, enforce: bool,
                        now: datetime, counts: _SweepCounts) -> None:
        if not enforce:
            logger.info("[report-only] %s: %s %s — %s", spec.invariant_id,
                        v.primary_store, v.row_id, v.detail)
            return
        if spec.severity is Severity.ALERT_ONLY:
            counts.alerts += 1
            record_operator_finding(
                source="invariant_sweep", severity="warning",
                summary=f"{spec.invariant_id}: {v.primary_store}:{v.row_id}",
                detail=v.detail)
            return
        if spec.severity is Severity.QUARANTINE_ONLY or spec.repair_ref is None:
            await self._quarantine(spec, v, now)
            counts.quarantined += 1
            return
        # REPAIRABLE — the 09 _fire_one pattern verbatim.
        try:
            repaired = await self._repair(spec, v)
            if repaired:
                counts.repairs += 1
        except Exception as exc:  # noqa: BLE001 — quarantine, never half-fixed
            from sb.kernel.interaction.errors import from_exception
            from sb.kernel.interaction.request import Surface
            envelope = from_exception(exc, surface=Surface.MAINTENANCE, target=None)
            logger.warning("repair failed (%s / %s): %s", spec.invariant_id,
                           v.row_id, envelope.error_class)
            await self._quarantine(spec, v, now)
            counts.quarantined += 1

    async def _repair(self, spec: InvariantSpec, v: Violation) -> bool:
        key = IdempotencyKey(namespace=f"{spec.invariant_id}.repair",
                             guild_id=v.guild_id or 0,
                             dedup_token=f"{v.row_id}:{v.fingerprint}")
        async with transaction() as conn:
            if not await once(key, conn=conn):
                await read_outcome(key, conn=conn)
                return False   # already repaired — no double-fix
            ctx = WorkflowContext(actor=SWEEP_ACTOR, guild_id=v.guild_id or 0,
                                  request_id=key.render(),
                                  params={"violation": v.__dict__})
            result = await workflow_engine.run_ref(spec.repair_ref, ctx, conn=conn)
            await record_outcome(key, result.outcome,
                                 result_ref=result.mutation_id, conn=conn)
        return True

    async def _quarantine(self, spec: InvariantSpec, v: Violation,
                          now: datetime) -> None:
        """Evidence-preserving soft-quarantine: snapshot into sb_quarantine +
        operator finding. v1 = visible-but-flagged (read-exclusion is the
        labeled deferral behind a per-StoreSpec opt-in)."""
        async with transaction() as conn:
            await inv_db.quarantine_row(
                invariant_id=spec.invariant_id, primary_store=v.primary_store,
                stores=v.stores, row_id=v.row_id, guild_id=v.guild_id,
                snapshot={"detail": v.detail, "fingerprint": v.fingerprint},
                now=now, conn=conn)
        record_operator_finding(
            source="invariant_sweep", severity="error",
            summary=f"quarantined: {spec.invariant_id} {v.primary_store}:{v.row_id}",
            detail=f"{v.detail} — disposition is owner-signed "
                   f"(repair | carry_as_is | declared_loss)")


# --- the CUT-2 / CUT-3 seam -------------------------------------------------------

@dataclass(frozen=True)
class VerifyImportReport:
    """The machine-readable read-off (spec 11 §2.5): two stop-codes + the
    two compat-scoreboard lines."""

    clean: bool
    stop_codes: tuple[str, ...]                 # invariant_violation | unrepaired_quarantine
    invariant_violations_by_id: dict[str, int]
    quarantined_rows: int


async def run_verify_import(*, now: datetime | None = None) -> VerifyImportReport:
    """Stage 3.5 (verify-import) / the CUT-3 verified-restore check: the
    SAME declared-invariant sweep, dry-run FORCED (violating rows are
    imported as-is but flagged — never auto-repaired into the new DB; the
    owner reviews the quarantine manifest and signs dispositions)."""
    now = now or SYSTEM_CLOCK()
    by_id: dict[str, int] = {}
    for spec in declared_invariants():
        check = resolve_ref(spec.check_ref)
        # DELIBERATE asymmetry with the live sweep's `targets = guilds or
        # (None,)` (_run_sweep): there the trailing `(None,)` is a bookkeeping
        # heartbeat so a zero-guild tick still writes ONE SweepRun row — this
        # read-off writes no log, so an empty *installed* source correctly
        # scans nothing. It stays inert because every declared invariant is
        # scope=GUILD (checks are `WHERE guild_id=$1`, so a None target matches
        # zero rows anyway); GLOBAL scan is a deferred band (see
        # sb/spec/invariants.py `scope`) that reworks BOTH paths when it ships.
        # The `else (None,)` below covers only the *uninstalled* source (tests /
        # pre-gateway boot), mirroring _run_sweep's zero-guild degenerate pass.
        guilds = tuple(_guild_source()) if _guild_source else (None,)
        count = 0
        for guild_id in guilds:
            async with transaction() as conn:
                violations = await check(spec, guild_id=guild_id, conn=conn)
            count += len(violations)
        if count:
            by_id[spec.invariant_id] = count
    quarantined = len(await inv_db.list_quarantined())
    stop_codes = []
    if by_id:
        stop_codes.append("invariant_violation")
    if quarantined:
        stop_codes.append("unrepaired_quarantine")
    return VerifyImportReport(clean=not stop_codes, stop_codes=tuple(stop_codes),
                              invariant_violations_by_id=by_id,
                              quarantined_rows=quarantined)
