"""The K7 engine core (spec 07 §3.3): run() happy path, the durable-once
replay (§3.7), the error-return contract (fork G), the confirm backstop,
EFFECT-leg compensation (fork E), the external-conn variant, and the
farm-collect-shaped canary's dry-run oracle (§3.5)."""

import asyncio
import uuid as uuid_mod

import pytest

from sb.kernel.authority import owner as owner_mod
from sb.kernel.workflow import engine as engine_mod
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    DedupKeySpec,
    EmptyResultSpec,
    EventEmitSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.confirmation import ConfirmationSpec
from sb.spec.events import (
    DeliveryClass,
    EventSpec,
    FieldSpec,
    clear_event_registry,
    register_event_specs,
)
from sb.spec.outcomes import BLOCKED, PARTIAL, SUCCESS
from sb.spec.refs import WorkflowRef, clear_ref_table, workflow
from tests.unit.workflow.conftest import Actor

pytestmark = pytest.mark.usefixtures("fake_conn")


@pytest.fixture(autouse=True)
def _refs_and_events():
    clear_ref_table()
    clear_event_registry()
    owner_mod.reset_for_tests()

    calls = {"credit": 0, "reset": 0, "xp": 0, "notify": 0, "compensate": 0}

    @workflow("farm.credit")
    async def _credit(conn, ctx):
        calls["credit"] += 1
        return LegOutcome(step=StepResult(1, "credit", True),
                          before={"balance": 100}, after={"balance": 150},
                          payload=150)

    @workflow("farm.reset")
    async def _reset(conn, ctx):
        calls["reset"] += 1
        return LegOutcome(step=StepResult(1, "coop_reset", True),
                          before={"eggs": 5}, after={"eggs": 0})

    @workflow("farm.notify")
    async def _notify(conn, ctx):
        calls["notify"] += 1
        return LegOutcome(step=StepResult(1, "notify", True))

    @workflow("farm.compensate_notify")
    async def _compensate(conn, ctx):
        calls["compensate"] += 1
        return LegOutcome(step=StepResult(1, "compensate", True))

    @workflow("farm.empty")
    def _empty(ctx):
        return bool(ctx.params.get("empty"))

    @workflow("farm.payload")
    def _payload(ctx, result):
        return {"balance": 150}

    register_event_specs([EventSpec(
        name="economy.balance_changed",
        payload_schema=(FieldSpec("balance", "int"),),
        owner_subsystem="economy",
        delivery=DeliveryClass.AT_LEAST_ONCE,
    )])

    yield calls
    clear_ref_table()
    clear_event_registry()
    owner_mod.reset_for_tests()


def _spec(**overrides) -> CompoundOpSpec:
    kwargs = dict(
        op_key="economy.farm.collect",
        domain="economy",
        lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(
            LegSpec("credit", LegKind.DB, WorkflowRef("farm.credit"), "reversible"),
            LegSpec("coop_reset", LegKind.DB, WorkflowRef("farm.reset"), "reversible"),
        ),
        idempotency=IdempotencyPosture.DURABLE_ONCE,
        dedup_key=DedupKeySpec(source=("user_id", "interaction_id")),
        audit_verb="farm_collect",
        emits=(EventEmitSpec("economy.balance_changed",
                             WorkflowRef("farm.payload"),
                             DeliveryClass.AT_LEAST_ONCE),),
        empty_result=EmptyResultSpec(WorkflowRef("farm.empty"), "Nothing to collect."),
    )
    kwargs.update(overrides)
    return CompoundOpSpec(**kwargs)


def _ctx(**overrides) -> WorkflowContext:
    kwargs = dict(
        actor=Actor(), guild_id=42, request_id="req-1",
        params={"user_id": 1, "interaction_id": "int-9"},
    )
    kwargs.update(overrides)
    return WorkflowContext(**kwargs)


def _register(spec):
    return REGISTRY.register(spec)


def test_run_happy_path_full_spine(fake_conn, _refs_and_events):
    spec = _register(_spec())
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == SUCCESS
    assert result.operation == result.op_key == "economy.farm.collect"
    assert result.committed_at is not None
    assert result.audit_emitted and result.event_emitted
    assert result.before == {"credit": {"balance": 100}, "coop_reset": {"eggs": 5}}
    # ONE central audit row, mutation_id-keyed; legs as detail, never N rows.
    assert len(fake_conn.audit_rows) == 1
    row = next(iter(fake_conn.audit_rows.values()))
    assert row["mutation_type"] == "farm_collect" and row["scope"] == "guild"
    # guard row under namespace=op_key + recorded outcome.
    keys = list(fake_conn.idempotency)
    assert keys == ["economy.farm.collect:42:1:int-9"]  # actor-encoded token
    assert fake_conn.idempotency[keys[0]]["outcome"] == SUCCESS
    # in-txn AT_LEAST_ONCE rows: the audit twin + the declared emit.
    assert len(fake_conn.outbox) == 2
    # derived rollup stamped by the registry.
    assert spec.reversibility == "reversible"
    uuid_mod.UUID(result.mutation_id)  # a real uuid


def test_durable_once_replay_reproduces_without_reeffect(fake_conn, _refs_and_events):
    _register(_spec())
    ref = WorkflowRef("economy.farm.collect")
    first = asyncio.run(engine_mod.run(ref, _ctx()))
    calls = _refs_and_events
    assert calls["credit"] == 1
    second = asyncio.run(engine_mod.run(ref, _ctx()))   # same interaction_id
    assert calls["credit"] == 1                          # NO re-effect
    assert second.outcome == first.outcome == SUCCESS
    assert second.mutation_id == first.mutation_id       # reproduced, not re-minted
    assert second.user_message == "This action was already completed."
    assert len(fake_conn.outbox) == 2                    # no new emits
    # a DIFFERENT user is a DIFFERENT key — both credited (cross-user fix).
    third = asyncio.run(engine_mod.run(ref, _ctx(
        params={"user_id": 2, "interaction_id": "int-9"})))
    assert third.mutation_id != first.mutation_id and calls["credit"] == 2


def test_empty_state_short_circuits_no_txn_no_audit(fake_conn, _refs_and_events):
    _register(_spec())
    result = asyncio.run(engine_mod.run(
        WorkflowRef("economy.farm.collect"), _ctx(params={
            "user_id": 1, "interaction_id": "i", "empty": True})))
    assert result.outcome == SUCCESS
    assert result.user_message == "Nothing to collect."
    assert not fake_conn.audit_rows and not fake_conn.idempotency


def test_authority_deny_returns_blocked(fake_conn, _refs_and_events):
    _register(_spec(authority_ref="administrator"))
    result = asyncio.run(engine_mod.run(
        WorkflowRef("economy.farm.collect"),
        _ctx(actor=Actor(member_tier="user"))))
    assert result.outcome == BLOCKED
    assert result.user_message  # the K6 engine-generated denial copy
    assert not fake_conn.audit_rows


def test_scripted_actor_bypasses_authority(fake_conn, _refs_and_events):
    _register(_spec(authority_ref="administrator"))
    result = asyncio.run(engine_mod.run(
        WorkflowRef("economy.farm.collect"),
        _ctx(actor=Actor(user_id=None, actor_type="system", member_tier=None))))
    assert result.outcome == SUCCESS  # RC-18: system hits the step-1 bypass


def test_required_leg_failure_rolls_back_and_returns(fake_conn, _refs_and_events):
    @workflow("farm.boom")
    async def _boom(conn, ctx):
        raise RuntimeError("db leg exploded")

    _register(_spec(legs=(
        LegSpec("credit", LegKind.DB, WorkflowRef("farm.credit"), "reversible"),
        LegSpec("boom", LegKind.DB, WorkflowRef("farm.boom"), "reversible"),
    )))
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == BLOCKED            # bug row -> BLOCKED (fork G: RETURNED)
    assert result.user_message == "Something went wrong on our end — it's been logged."
    assert fake_conn.rolled_back                # txn aborted
    assert not fake_conn.audit_rows and not fake_conn.outbox


def test_transient_leg_failure_classifies_discord_failed(fake_conn, _refs_and_events):
    @workflow("farm.timeout")
    async def _timeout(conn, ctx):
        raise ConnectionError("pool gone")

    _register(_spec(legs=(
        LegSpec("t", LegKind.DB, WorkflowRef("farm.timeout"), "reversible"),)))
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == "discord_failed"


def test_optional_leg_failure_degrades_to_partial(fake_conn, _refs_and_events):
    @workflow("farm.flaky")
    async def _flaky(conn, ctx):
        raise RuntimeError("optional leg failed")

    _register(_spec(legs=(
        LegSpec("credit", LegKind.DB, WorkflowRef("farm.credit"), "reversible"),
        LegSpec("flaky", LegKind.DB, WorkflowRef("farm.flaky"), "reversible",
                optional=True),
    )))
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == PARTIAL
    assert fake_conn.audit_rows                 # committed, not aborted


def test_confirm_backstop_headless_mapping(fake_conn, _refs_and_events):
    _register(_spec(confirmation=ConfirmationSpec(reversibility="reversible")))
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == BLOCKED
    assert "confirmation" in (result.user_message or "")
    confirmed = asyncio.run(engine_mod.run(
        WorkflowRef("economy.farm.collect"), _ctx(confirmed=True)))
    assert confirmed.outcome == SUCCESS


def test_effect_leg_compensation_fork_e(fake_conn, _refs_and_events):
    @workflow("farm.effect_boom")
    async def _effect_boom(conn, ctx):
        assert conn is None                     # EFFECT legs run post-commit
        raise RuntimeError("discord send failed")

    _register(_spec(legs=(
        LegSpec("credit", LegKind.DB, WorkflowRef("farm.credit"), "reversible"),
        LegSpec("announce", LegKind.EFFECT, WorkflowRef("farm.effect_boom"),
                "compensatable", compensator=WorkflowRef("farm.compensate_notify")),
    )))
    result = asyncio.run(engine_mod.run(WorkflowRef("economy.farm.collect"), _ctx()))
    assert result.outcome == PARTIAL            # degraded, never BLOCKED
    assert _refs_and_events["compensate"] == 1  # compensator ran
    assert fake_conn.audit_rows                 # DB legs committed


def test_external_conn_variant_skips_guard_effects_and_commit_stamp(
        fake_conn, _refs_and_events):
    _register(_spec(
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        emits=(), empty_result=None,
    ))
    result = asyncio.run(engine_mod.run_ref(
        WorkflowRef("economy.farm.collect"), _ctx(), conn=fake_conn))
    assert result.outcome == SUCCESS
    assert result.committed_at is None          # caller owns commit
    assert not fake_conn.idempotency            # caller owns once()/record
    assert fake_conn.audit_rows                 # central audit still in-txn
    assert result.mutation_id                   # for the caller's record_outcome


def test_apply_is_the_op_kind_sibling(fake_conn, _refs_and_events):
    _register(_spec(idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
                    emits=(), empty_result=None))

    class Op:
        op_kind = "economy.farm.collect"
        ctx = _ctx()

    result = asyncio.run(engine_mod.apply(Op(), conn=fake_conn))
    assert result.outcome == SUCCESS


def test_preview_dry_run_oracle_byte_identical_zero_effects(
        fake_conn, _refs_and_events):
    calls = _refs_and_events
    _register(_spec(legs=(
        LegSpec("credit", LegKind.DB, WorkflowRef("farm.credit"), "reversible"),
        LegSpec("announce", LegKind.EFFECT, WorkflowRef("farm.notify"), "reversible"),
    )))
    before = fake_conn.snapshot()
    prev = asyncio.run(engine_mod.preview(WorkflowRef("economy.farm.collect"), _ctx()))
    assert prev.allowed and prev.operation == "economy.farm.collect"
    assert calls["credit"] == 1                 # DB leg RAN (compute path)
    assert calls["notify"] == 0                 # zero effect calls (the oracle)
    assert fake_conn.snapshot() == before       # DB byte-identical (rollback)
    assert not prev.requires_confirmation
    assert any(c.field_name == "credit" for c in prev.diff)
