"""LegOutcome.user_message → WorkflowResult.user_message threading (the
band-2 success-ack seam): DB-leg copy lands in the pending result, EFFECT-leg
copy appends post-commit in leg order, and a failed EFFECT leg contributes
NO line (its copy must never claim an action that did not apply)."""

import asyncio

import pytest

from sb.kernel.authority import owner as owner_mod
from sb.kernel.workflow import engine as engine_mod
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.events import clear_event_registry
from sb.spec.outcomes import PARTIAL, SUCCESS
from sb.spec.refs import WorkflowRef, clear_ref_table, workflow
from tests.unit.workflow.conftest import Actor

pytestmark = pytest.mark.usefixtures("fake_conn")


@pytest.fixture(autouse=True)
def _refs():
    clear_ref_table()
    clear_event_registry()
    owner_mod.reset_for_tests()

    @workflow("copy.record")
    async def _record(conn, ctx):
        return LegOutcome(step=StepResult(1, "record", True),
                          user_message="line one (db leg)")

    @workflow("copy.silent")
    async def _silent(conn, ctx):
        return LegOutcome(step=StepResult(1, "silent", True))

    @workflow("copy.apply")
    async def _apply(conn, ctx):
        if ctx.params.get("boom"):
            raise RuntimeError("effect refused")
        return LegOutcome(step=StepResult(1, "apply", True),
                          user_message="line two (effect leg)")

    yield
    clear_ref_table()
    clear_event_registry()
    owner_mod.reset_for_tests()


def _spec(op_key: str) -> CompoundOpSpec:
    return REGISTRY.register(CompoundOpSpec(
        op_key=op_key,
        domain="copy",
        lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(
            LegSpec("record", LegKind.DB, WorkflowRef("copy.record"),
                    "reversible"),
            LegSpec("silent", LegKind.DB, WorkflowRef("copy.silent"),
                    "reversible"),
            LegSpec("apply", LegKind.EFFECT, WorkflowRef("copy.apply"),
                    "reversible"),
        ),
        idempotency=IdempotencyPosture.NATURAL_KEY,
        dedup_key=None,
        audit_verb="copy_tested",
    ))


def _ctx(**params) -> WorkflowContext:
    return WorkflowContext(actor=Actor(), guild_id=42, request_id="req-1",
                           params=params)


def test_leg_copy_joins_db_then_effect(fake_conn):
    _spec("copy.op_a")
    result = asyncio.run(engine_mod.run(WorkflowRef("copy.op_a"), _ctx()))
    assert result.outcome == SUCCESS
    assert result.user_message == "line one (db leg)\nline two (effect leg)"


def test_failed_effect_leg_contributes_no_copy(fake_conn):
    _spec("copy.op_b")
    result = asyncio.run(engine_mod.run(WorkflowRef("copy.op_b"),
                                        _ctx(boom=True)))
    assert result.outcome == PARTIAL           # fork E: finding, not a crash
    assert result.user_message == "line one (db leg)"


def test_no_copy_means_none(fake_conn):
    REGISTRY.register(CompoundOpSpec(
        op_key="copy.op_c", domain="copy", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("silent", LegKind.DB, WorkflowRef("copy.silent"),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb="copy_tested",
    ))
    result = asyncio.run(engine_mod.run(WorkflowRef("copy.op_c"), _ctx()))
    assert result.outcome == SUCCESS
    assert result.user_message is None
