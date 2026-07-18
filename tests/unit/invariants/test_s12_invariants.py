"""S12: the invariant fence, the sweep lane (epoch dedup, dispatch table,
circuit breaker, quarantine-on-failure), and the verify-import seam."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from sb.kernel import settings as settings_mod
from sb.kernel.invariants import sweep as sw
from sb.kernel.invariants.compile import check_invariant, check_invariant_coverage
from sb.spec.invariants import (
    InvariantKind,
    InvariantSpec,
    Severity,
    SweepCadence,
    Violation,
    clear_invariants_for_tests,
    declare_invariant,
    declared_invariants,
)
from sb.spec.refs import (
    HandlerRef,
    ProviderRef,
    WorkflowRef,
    clear_ref_table,
    provider,
)
from sb.spec.versioning import CheckpointClass, StoreSpec

run = asyncio.run
T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def inv(**kw) -> InvariantSpec:
    defaults = dict(
        invariant_id="economy.coins_reconcile", kind=InvariantKind.RECONCILIATION,
        owner_subsystem="economy", stores=("xp", "economy_audit_log"),
        check_ref=ProviderRef("economy.coins_check"),
        severity=Severity.QUARANTINE_ONLY,
        baseline_ref=ProviderRef("economy.coins_baseline"), bears_value=True)
    defaults.update(kw)
    return InvariantSpec(**defaults)


def violation(row_id="7:42", **kw) -> Violation:
    defaults = dict(stores=("xp",), primary_store="xp", guild_id=42,
                    fingerprint="fp1", detail="drift +20 > tol 0")
    defaults.update(kw)
    return Violation(row_id=row_id, **defaults)


@pytest.fixture(autouse=True)
def _clean():
    clear_invariants_for_tests()
    clear_ref_table()
    settings_mod.clear_for_tests()
    sw.reset_sweep_ports_for_tests()
    yield
    clear_invariants_for_tests()
    clear_ref_table()
    settings_mod.clear_for_tests()
    sw.reset_sweep_ports_for_tests()


# --- the fence ---------------------------------------------------------------

def test_fence_rules():
    assert check_invariant(inv()) == []
    assert any("repairable_needs_repair_ref" in p for p in check_invariant(
        inv(severity=Severity.REPAIRABLE, ground_truth_store="xp")))
    assert any("repair_must_be_workflow_ref" in p for p in check_invariant(
        inv(severity=Severity.REPAIRABLE, repair_ref=HandlerRef("economy.fix"),
            ground_truth_store="xp")))
    assert any("reconciliation_needs_baseline" in p for p in check_invariant(
        inv(baseline_ref=None)))
    # Q3/Q-D13: value-bearing repairable reconciliation NEEDS a declared
    # money direction — else QUARANTINE_ONLY is the only legal severity.
    assert any("value_repair_needs_direction" in p for p in check_invariant(
        inv(severity=Severity.REPAIRABLE, repair_ref=WorkflowRef("economy.fix"))))
    assert check_invariant(inv(severity=Severity.REPAIRABLE,
                               repair_ref=WorkflowRef("economy.fix"),
                               ground_truth_store="economy_audit_log")) == []
    assert any("is not one of" in p for p in check_invariant(
        inv(severity=Severity.REPAIRABLE, repair_ref=WorkflowRef("economy.fix"),
            ground_truth_store="elsewhere")))


def test_coverage_fence_keyed_on_checkpoint_class():
    money = StoreSpec(table="xp", sole_writer=WorkflowRef("xp.write"),
                      retention="permanent", checkpoint_class=CheckpointClass.AGGREGATE,
                      invariant_tag="INV-F", bears_value=True)
    escrow = StoreSpec(table="game_state", sole_writer=WorkflowRef("game.write"),
                       retention="session", checkpoint_class=CheckpointClass.SESSION,
                       invariant_tag="INV-F", bears_value=True)
    assert len(check_invariant_coverage((money, escrow), ())) == 2
    # RECONCILIATION covers the aggregate; but a SESSION escrow needs
    # REFERENTIAL/TERMINAL_ONCE — reconciliation does NOT cover it.
    problems = check_invariant_coverage((money, escrow), (inv(),))
    assert len(problems) == 1 and "game_state" in problems[0]
    referential = inv(invariant_id="game.escrow_live", kind=InvariantKind.REFERENTIAL,
                      stores=("game_state",), baseline_ref=None)
    assert check_invariant_coverage((money, escrow), (inv(), referential)) == []


def test_declare_invariant_runs_fence_and_dedups():
    with pytest.raises(ValueError, match="fence"):
        declare_invariant(inv(baseline_ref=None))
    declare_invariant(inv())
    declare_invariant(inv())   # identical redeclare = no-op
    with pytest.raises(ValueError, match="differing"):
        declare_invariant(inv(tolerance=5))
    assert len(declared_invariants()) == 1


# --- the sweep lane -----------------------------------------------------------

class FakeIdem:
    def __init__(self):
        self.keys = {}

    async def once(self, key, *, conn):
        if key.render() in self.keys:
            return False
        self.keys[key.render()] = None
        return True

    async def record_outcome(self, key, outcome, *, result_ref=None, conn):
        self.keys[key.render()] = outcome

    async def read_outcome(self, key, *, conn):
        return None


@dataclass
class FakeInvDb:
    quarantined: list = field(default_factory=list)
    sweep_logs: list = field(default_factory=list)

    async def quarantine_row(self, **kw):
        self.quarantined.append(kw)
        return "q1"

    async def write_sweep_log(self, run, *, conn):
        self.sweep_logs.append(run)

    async def list_quarantined(self, invariant_id=None, *, conn=None):
        return list(self.quarantined)

    # dataclass passthrough
    SweepRun = None


@pytest.fixture
def env(monkeypatch):
    idem = FakeIdem()
    db = FakeInvDb()
    ran = []

    class FakeResult:
        outcome = "success"
        mutation_id = "m1"

    class FakeEngine:
        @staticmethod
        async def run_ref(ref, ctx, *, conn=None):
            ran.append((ref.name, ctx.actor.actor_type))
            return FakeResult()

    @contextlib.asynccontextmanager
    async def fake_tx():
        yield object()

    from sb.kernel.db.invariants import SweepRun
    db.SweepRun = SweepRun
    monkeypatch.setattr(sw, "transaction", fake_tx)
    monkeypatch.setattr(sw, "once", idem.once)
    monkeypatch.setattr(sw, "record_outcome", idem.record_outcome)
    monkeypatch.setattr(sw, "read_outcome", idem.read_outcome)
    monkeypatch.setattr(sw, "workflow_engine", FakeEngine)
    monkeypatch.setattr(sw.inv_db, "quarantine_row", db.quarantine_row)
    monkeypatch.setattr(sw.inv_db, "write_sweep_log", db.write_sweep_log)
    monkeypatch.setattr(sw.inv_db, "list_quarantined", db.list_quarantined)
    sw.install_guild_source(lambda: (42,))
    return idem, db, ran


def _register_check(violations):
    @provider("economy.coins_check")
    async def check(spec, *, guild_id, conn):
        return tuple(violations)

    @provider("economy.coins_baseline")
    async def baseline(spec, *, guild_id, conn):
        return {}


def test_report_only_default_counts_but_never_mutates(env):
    idem, db, ran = env
    _register_check([violation()])
    declare_invariant(inv())
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    result = run(lane.tick(T0))
    assert result.fired == 1
    assert db.quarantined == [] and ran == []          # report-only: zero mutation
    assert db.sweep_logs[0].violations_found == 1
    assert db.sweep_logs[0].enforce_effective is False


def test_epoch_once_guard_dedups_across_instances(env):
    idem, db, _ = env
    _register_check([])
    declare_invariant(inv())
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    run(lane.tick(T0))       # same cadence window: the once() guard skips
    assert len(db.sweep_logs) == 1


def test_enforced_quarantine_only_preserves_evidence(env):
    idem, db, ran = env
    _register_check([violation()])
    declare_invariant(inv())
    sw.register_enforce_setting(inv())
    # flip the runtime one-way door.
    async def reader(guild_id, key):
        return True if key == "invariants.enforce.economy.coins_reconcile" else settings_mod.UNSET
    settings_mod.install_settings_reader(reader)
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    assert len(db.quarantined) == 1 and ran == []       # never auto-mutates money
    assert db.quarantined[0]["row_id"] == "7:42"


def test_enforced_repair_is_once_guarded_backfill_actor(env):
    idem, db, ran = env
    _register_check([violation()])
    spec = inv(invariant_id="xp.dupes", kind=InvariantKind.UNIQUENESS,
               stores=("xp_ledger",), severity=Severity.REPAIRABLE,
               repair_ref=WorkflowRef("xp.dedupe"), bears_value=False,
               baseline_ref=None,
               check_ref=ProviderRef("economy.coins_check"))
    declare_invariant(spec)
    sw.register_enforce_setting(spec)
    async def reader(guild_id, key):
        return True if key == "invariants.enforce.xp.dupes" else settings_mod.UNSET
    settings_mod.install_settings_reader(reader)
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    assert ran == [("xp.dedupe", "backfill")]           # RC-18 SWEEP_ACTOR
    assert db.sweep_logs[0].repairs_applied == 1
    # second window: the repair once() key dedups (same fingerprint).
    run(lane.tick(datetime(2026, 7, 9, 13, 0, tzinfo=timezone.utc)))
    assert ran == [("xp.dedupe", "backfill")]           # no double-fix


def test_repair_failure_quarantines_never_half_fixed(env):
    idem, db, ran = env
    _register_check([violation()])
    spec = inv(invariant_id="xp.dupes", kind=InvariantKind.UNIQUENESS,
               stores=("xp_ledger",), severity=Severity.REPAIRABLE,
               repair_ref=WorkflowRef("xp.dedupe"), bears_value=False,
               baseline_ref=None, check_ref=ProviderRef("economy.coins_check"))
    declare_invariant(spec)
    sw.register_enforce_setting(spec)
    async def reader(guild_id, key):
        return True if key.startswith("invariants.enforce.") else settings_mod.UNSET
    settings_mod.install_settings_reader(reader)

    class Boom:
        @staticmethod
        async def run_ref(ref, ctx, *, conn=None):
            raise RuntimeError("repair broke")
    import pytest as _p
    sw.workflow_engine = Boom
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    assert len(db.quarantined) == 1                     # quarantined, not half-fixed


def test_circuit_breaker_bounds_both_postures(env):
    idem, db, _ = env
    _register_check([violation(row_id=str(i), fingerprint=f"f{i}")
                     for i in range(10)])
    declare_invariant(inv(max_actions_per_run=3))
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    log = db.sweep_logs[0]
    assert log.breaker_tripped
    assert log.violations_found == 3                    # STOPPED at the cap


def test_verify_import_report_stop_codes(env):
    idem, db, _ = env
    _register_check([violation()])
    declare_invariant(inv())
    report = run(sw.run_verify_import(now=T0))
    assert not report.clean
    assert "invariant_violation" in report.stop_codes
    assert report.invariant_violations_by_id == {"economy.coins_reconcile": 1}


def test_empty_installed_guild_source_diverges_between_sweep_and_verify_import(env):
    """Characterization: with an *installed but empty* guild source the live
    sweep and verify-import intentionally diverge on their scan targets.

    `_run_sweep` uses `targets = guilds or (None,)` — the trailing `(None,)`
    is a bookkeeping heartbeat so a zero-guild tick still writes ONE SweepRun
    row. `run_verify_import` omits that fallback (it writes no log), so an empty
    installed source scans nothing. A guild-agnostic check (returns a violation
    regardless of guild_id) makes the divergence observable; in production every
    invariant is scope=GUILD (`WHERE guild_id=$1`), so the None target matches
    zero rows and the divergence is inert. Pin it: aligning the two paths (e.g.
    adding `or (None,)` to verify-import) must consciously update this test.
    """
    idem, db, _ = env
    _register_check([violation()])          # returns the violation for ANY guild_id
    declare_invariant(inv())
    sw.install_guild_source(lambda: ())     # installed, but zero guilds

    # live sweep: the (None,) heartbeat pass still runs the check once.
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    assert db.sweep_logs[0].guilds_scanned == 1
    assert db.sweep_logs[0].violations_found == 1

    # verify-import: empty tuple ⇒ no pass ⇒ scans nothing ⇒ clean.
    report = run(sw.run_verify_import(now=T0))
    assert report.clean
    assert report.invariant_violations_by_id == {}
    assert report.stop_codes == ()


# --- the ON_BOOT reconciliation entry (the boot ready-gate) -------------------

def test_reconcile_on_boot_runs_on_boot_only_and_crash_loop_guards(env):
    idem, db, _ = env
    _register_check([violation()])
    # An ON_BOOT invariant (reconcile_on_boot's sole scope) alongside a DAILY
    # one that reconcile_on_boot must SKIP (steady-state tick's scope).
    boot_spec = inv(invariant_id="xp.boot_check", kind=InvariantKind.UNIQUENESS,
                    stores=("xp_ledger",), severity=Severity.QUARANTINE_ONLY,
                    bears_value=False, baseline_ref=None,
                    cadence=SweepCadence.ON_BOOT,
                    check_ref=ProviderRef("economy.coins_check"))
    declare_invariant(boot_spec)
    declare_invariant(inv())        # default cadence DAILY — must be skipped
    lane = sw.InvariantSweepLane(clock=lambda: T0)

    run(lane.reconcile_on_boot(T0))
    assert len(db.sweep_logs) == 1                      # ONLY the ON_BOOT invariant
    assert db.sweep_logs[0].invariant_id == "xp.boot_check"
    assert db.sweep_logs[0].violations_found == 1

    # Crash-loop guard: a second boot within the SAME hour (epoch = ts//3600)
    # is deduped by the once() epoch key — a restart never re-sweeps.
    run(lane.reconcile_on_boot(datetime(2026, 7, 8, 12, 30, tzinfo=timezone.utc)))
    assert len(db.sweep_logs) == 1                      # no re-sweep this hour

    # A boot in a LATER hour is a new epoch — reconciliation runs again.
    run(lane.reconcile_on_boot(datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)))
    assert len(db.sweep_logs) == 2


# --- the ALERT_ONLY dispatch branch (metric/finding, no state change) --------

def test_alert_only_dispatch_records_finding_never_mutates(env):
    idem, db, ran = env
    _register_check([violation()])
    spec = inv(invariant_id="xp.alerting", kind=InvariantKind.UNIQUENESS,
               stores=("xp_ledger",), severity=Severity.ALERT_ONLY,
               bears_value=False, baseline_ref=None,
               check_ref=ProviderRef("economy.coins_check"))
    declare_invariant(spec)
    sw.register_enforce_setting(spec)
    # ALERT_ONLY still needs enforce=True to leave the report-only path.
    async def reader(guild_id, key):
        return True if key == "invariants.enforce.xp.alerting" else settings_mod.UNSET
    settings_mod.install_settings_reader(reader)
    lane = sw.InvariantSweepLane(clock=lambda: T0)
    run(lane.tick(T0))
    assert db.quarantined == [] and ran == []           # metric/finding only
    assert db.sweep_logs[0].alerts == 1
