"""The K7 declaration fences (spec 07 §3.6 + Q-D24), the registry, and the
Result grammar (design-spec §2.7 adoption)."""

import pytest

from sb.kernel.workflow.compile import check_atomic_db_only, check_spec, derive_reversibility
from sb.kernel.workflow.registry import WorkflowRegistry
from sb.kernel.workflow.result import (
    REVERSIBILITY_ORDER,
    StepResult,
    WorkflowResult,
    classify_outcome,
)
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    DedupKeySpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.confirmation import ConfirmationSpec
from sb.spec.events import DeliveryClass
from sb.spec.outcomes import DISCORD_FAILED, PARTIAL, SUCCESS
from sb.spec.refs import WorkflowRef, clear_ref_table, workflow


@pytest.fixture(autouse=True)
def _clean_refs():
    clear_ref_table()
    yield
    clear_ref_table()


def _spec(**overrides):
    kwargs = dict(
        op_key="x.y.z", domain="x", lane=WorkflowLane.DOMAIN, authority_ref="",
        legs=(LegSpec("a", LegKind.DB, WorkflowRef("x.a"), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb="z",
    )
    kwargs.update(overrides)
    return CompoundOpSpec(**kwargs)


def test_posture_companion_fences():
    assert check_spec(_spec()) == []
    assert "DURABLE_ONCE requires dedup_key" in "".join(check_spec(
        _spec(idempotency=IdempotencyPosture.DURABLE_ONCE)))
    assert "only meaningful under DURABLE_ONCE" in "".join(check_spec(
        _spec(dedup_key=DedupKeySpec(source=("a",)))))
    assert "requires idempotency_justification" in "".join(check_spec(
        _spec(idempotency=IdempotencyPosture.NONE_JUSTIFIED)))
    assert "MUST be None unless NONE_JUSTIFIED" in "".join(check_spec(
        _spec(idempotency_justification="why")))
    assert "requires single_flight_scope" in "".join(check_spec(
        _spec(idempotency=IdempotencyPosture.SINGLE_FLIGHT)))


def test_qd24_session_transition_requires_natural_key():
    assert check_spec(_spec(session_transition=True)) == []
    problems = check_spec(_spec(
        session_transition=True,
        idempotency=IdempotencyPosture.DURABLE_ONCE,
        dedup_key=DedupKeySpec(source=("user_id",))))
    assert any("Q-D24" in p for p in problems)


def test_reversibility_is_derived_never_authored():
    assert REVERSIBILITY_ORDER == ("reversible", "compensatable", "irreversible")
    assert any("derived" in p for p in check_spec(_spec(reversibility="reversible")))
    rolled = derive_reversibility(_spec(legs=(
        LegSpec("a", LegKind.DB, WorkflowRef("x.a"), "reversible"),
        LegSpec("b", LegKind.DB, WorkflowRef("x.b"), "irreversible"),
    )))
    assert rolled.reversibility == "irreversible"


def test_irreversible_requires_confirmation():
    bad = _spec(legs=(LegSpec("a", LegKind.DB, WorkflowRef("x.a"), "irreversible"),))
    assert any("ConfirmationSpec" in p for p in check_spec(bad))
    ok = _spec(legs=(LegSpec("a", LegKind.DB, WorkflowRef("x.a"), "irreversible"),),
               confirmation=ConfirmationSpec(reversibility="irreversible"))
    assert check_spec(ok) == []


def test_compensatable_effect_leg_requires_compensator():
    bad = _spec(legs=(LegSpec("e", LegKind.EFFECT, WorkflowRef("x.e"), "compensatable"),))
    assert any("compensator" in p for p in check_spec(bad))


def test_registry_registers_freezes_and_resolves():
    reg = WorkflowRegistry()
    frozen = reg.register(_spec())
    assert frozen.reversibility == "reversible"     # rollup stamped
    assert reg.resolve(WorkflowRef("x.y.z")) is frozen
    assert reg.resolve_op_kind("x.y.z") is frozen
    with pytest.raises(ValueError, match="duplicate"):
        reg.register(_spec())
    with pytest.raises(LookupError):
        reg.resolve(WorkflowRef("nope"))
    with pytest.raises(ValueError, match="fence violations"):
        reg.register(_spec(op_key="bad.op",
                           idempotency=IdempotencyPosture.DURABLE_ONCE))


def test_atomic_db_only_external_conn_fence():
    @workflow("x.pure")
    async def _pure(conn, ctx):
        return None

    @workflow("x.dirty")
    async def _dirty(conn, ctx):
        import discord  # noqa: F401, PLC0415
        return None

    ok = _spec(legs=(LegSpec("a", LegKind.DB, WorkflowRef("x.pure"), "reversible"),))
    assert check_atomic_db_only(ok) == []

    effectful = _spec(legs=(
        LegSpec("e", LegKind.EFFECT, WorkflowRef("x.pure"), "reversible"),))
    assert any("EFFECT leg" in p for p in check_atomic_db_only(effectful))

    dirty = _spec(legs=(LegSpec("d", LegKind.DB, WorkflowRef("x.dirty"), "reversible"),))
    assert any("banned I/O" in p for p in check_atomic_db_only(dirty))

    @workflow("x.payload")
    def _payload(ctx, result):
        return {}

    besteffort = _spec(emits=(EventEmitSpec(
        "e.v", WorkflowRef("x.payload"), DeliveryClass.BEST_EFFORT),))
    assert any("post-commit home" in p for p in check_atomic_db_only(besteffort))

    confirmy = _spec(confirmation=ConfirmationSpec(reversibility="reversible"))
    assert any("headless" in p for p in check_atomic_db_only(confirmy))


def test_workflow_result_is_the_shipped_superset():
    r = WorkflowResult(
        mutation_id="m", guild_id=1, domain="economy", operation="economy.op",
        outcome=SUCCESS, reversibility="reversible",
        steps=(StepResult(1, "a", True), StepResult(2, "b", False, "boom")),
    )
    # shipped LifecycleResult helpers, verbatim semantics
    assert r.applied == (StepResult(1, "a", True),)
    assert r.failed == (StepResult(2, "b", False, "boom"),)
    assert r.first_error == "boom"
    assert r.op_key == "economy.op"             # the outbox namespace carrier
    # shipped classify_outcome verbatim
    assert classify_outcome(()) == DISCORD_FAILED
    assert classify_outcome((StepResult(1, "a", True),)) == SUCCESS
    assert classify_outcome((StepResult(1, "a", True),
                             StepResult(2, "b", False))) == PARTIAL
    assert classify_outcome((StepResult(1, "a", False),)) == DISCORD_FAILED


def test_from_legacy_adapters_name_for_name():
    class LegacyLifecycleResult:
        mutation_id = "m-1"
        guild_id = 9
        domain = "channel"
        operation = "archive"
        outcome = "partial"
        reversibility = "compensatable"
        steps = (StepResult(1, "c", True),)
        committed_at = None
        audit_emitted = True
        event_emitted = False
        warnings = ("w",)

    legacy = LegacyLifecycleResult()
    r = WorkflowResult.from_lifecycle(legacy)
    assert (r.mutation_id, r.guild_id, r.domain, r.operation) == ("m-1", 9, "channel", "archive")
    assert r.outcome == "partial" and r.audit_emitted and not r.event_emitted
    assert r.lane is WorkflowLane.LIFECYCLE
    assert r.source is legacy                    # the ORIGINAL object, typed
    assert WorkflowResult.from_settings(legacy).lane is WorkflowLane.SCALAR
    assert WorkflowResult.from_treasury(legacy).lane is WorkflowLane.DOMAIN
