"""S10: the version-policy fence + resolve_versioned_load / run_recovery
(frozen L0 spec 09 §3.3/§3.4 — the RPS-forfeit class fix)."""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from sb.kernel.versioning import resolve as vr
from sb.kernel.versioning.compile import check_version_policy
from sb.kernel.workflow.context import WorkflowContext
from sb.spec.refs import (
    ProviderRef,
    WorkflowRef,
    clear_ref_table,
    provider,
    workflow,
)
from sb.spec.versioning import (
    CheckpointClass,
    StoreSpec,
    VersionPolicy,
    VersionedRow,
)

run = asyncio.run


@pytest.fixture(autouse=True)
def _refs():
    clear_ref_table()
    yield
    clear_ref_table()


def store(**kw) -> StoreSpec:
    defaults = dict(
        table="rps_tournament", sole_writer=WorkflowRef("rps.write"),
        retention="session", checkpoint_class=CheckpointClass.SESSION,
        invariant_tag="INV-F", payload_version=3, bears_value=True,
        version_policy=VersionPolicy.REJECT_AND_PRESERVE,
        active_rows_ref=ProviderRef("rps.active_rows"),
        compensation_ref=WorkflowRef("rps.refund_then_retire"))
    defaults.update(kw)
    return StoreSpec(**defaults)


def row(version=1, **kw) -> VersionedRow:
    defaults = dict(row_id="42", version=version,
                    payload={"bet": 100}, guild_id=7)
    defaults.update(kw)
    return VersionedRow(**defaults)


def ctx() -> WorkflowContext:
    return WorkflowContext(actor=object(), guild_id=7, request_id="r")


# --- the fence ---------------------------------------------------------------

def test_fence_drop_on_value_is_unbuildable():
    problems = check_version_policy(store(version_policy=VersionPolicy.DROP))
    assert any("value_bearing_store_cannot_drop" in p for p in problems)


def test_fence_conditional_refs():
    assert any("upcast_needs" in p for p in check_version_policy(
        store(version_policy=VersionPolicy.UPCAST, upcast_ref=None)))
    assert any("needs_compensation" in p for p in check_version_policy(
        store(compensation_ref=None)))
    assert any("retire_path" in p for p in check_version_policy(
        store(bears_value=False, compensation_ref=None, retire_ref=None)))
    assert any("recovery_needs_reader" in p for p in check_version_policy(
        store(active_rows_ref=None)))
    assert check_version_policy(store()) == []


# --- resolve_versioned_load ---------------------------------------------------

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


@pytest.fixture
def env(monkeypatch):
    idem = FakeIdem()
    ran = []

    class FakeResult:
        outcome = "success"
        mutation_id = "m1"

    class FakeEngine:
        @staticmethod
        async def run_ref(ref, wctx, *, conn=None):
            ran.append(ref.name)
            return FakeResult()

    @contextlib.asynccontextmanager
    async def fake_tx():
        yield object()

    monkeypatch.setattr(vr, "transaction", fake_tx)
    monkeypatch.setattr(vr, "once", idem.once)
    monkeypatch.setattr(vr, "record_outcome", idem.record_outcome)
    monkeypatch.setattr(vr, "read_outcome", idem.read_outcome)
    monkeypatch.setattr(vr, "workflow_engine", FakeEngine)
    return idem, ran


def test_current_version_resumes(env):
    disp = run(vr.resolve_versioned_load(store(), row(version=3), ctx=ctx()))
    assert disp.action == "resume" and disp.payload == {"bet": 100}


def test_upcast_chain_resumes(env):
    @workflow("rps.upcast")
    def upcast(from_v, payload):
        return {**payload, f"v{from_v + 1}": True}
    spec = store(version_policy=VersionPolicy.UPCAST,
                 upcast_ref=WorkflowRef("rps.upcast"))
    disp = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp.action == "resume"
    assert disp.payload == {"bet": 100, "v2": True, "v3": True}


def test_broken_upcast_rung_quarantines_never_deletes(env):
    _, ran = env

    @workflow("rps.upcast")
    def upcast(from_v, payload):
        return None if from_v == 2 else {**payload}
    spec = store(version_policy=VersionPolicy.UPCAST,
                 upcast_ref=WorkflowRef("rps.upcast"))
    disp = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp.action == "quarantined"
    assert "upcast_chain_broken" in disp.finding
    assert ran == []                     # no retire, no refund — row left in place


def test_value_reject_compensates_exactly_once(env):
    idem, ran = env
    spec = store()
    disp = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp.action == "compensated_and_retired"
    assert ran == ["rps.refund_then_retire"]     # refund THEN retire — one op
    # replay: once() dedups — NO double refund.
    disp2 = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp2.action == "compensated_and_retired"
    assert ran == ["rps.refund_then_retire"]     # still exactly one
    assert len(idem.keys) == 1
    assert next(iter(idem.keys)).startswith("rps_tournament.version_reject:7:")


def test_nonvalue_reject_just_retires(env):
    _, ran = env
    spec = store(bears_value=False, compensation_ref=None,
                 retire_ref=WorkflowRef("rps.retire"))
    disp = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp.action == "rejected_and_retired"
    assert ran == ["rps.retire"]


def test_drop_retires_audited(env):
    _, ran = env
    spec = store(bears_value=False, version_policy=VersionPolicy.DROP,
                 compensation_ref=None, retire_ref=WorkflowRef("rps.retire"))
    disp = run(vr.resolve_versioned_load(spec, row(version=1), ctx=ctx()))
    assert disp.action == "dropped"
    assert ran == ["rps.retire"]


def test_run_recovery_generated_sweep(env):
    _, ran = env

    @provider("rps.active_rows")
    async def active_rows(spec, *, conn):
        return (row(version=1), row(version=3, row_id="43"))
    spec = store()
    disps = run(vr.run_recovery(spec, ctx_factory=lambda r: ctx()))
    assert [d.action for d in disps] == ["compensated_and_retired", "resume"]

    # a fence-failing spec refuses to sweep at all.
    with pytest.raises(ValueError, match="version_policy_declared"):
        run(vr.run_recovery(store(compensation_ref=None),
                            ctx_factory=lambda r: ctx()))
