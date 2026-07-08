"""Step 5-6: the dispatch-kind table, the confirm round-trip, the error
envelope, cooldown refund (fork D), the INVOKE_WORKFLOW seam, and the
ephemerality resolver."""

import asyncio

import pytest

from sb.kernel.interaction.errors import ValidatorError, from_exception
from sb.kernel.interaction.request import ActorRef, Surface, TargetRef
from sb.kernel.interaction.resolve import resolve
from sb.kernel.interaction.result import lane_default, resolve_reply_visibility
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.authority import Lane
from sb.spec.confirmation import ConfirmationSpec
from sb.spec.outcomes import (
    BLOCKED,
    DECLINED,
    DISCORD_FAILED,
    SUCCESS,
    DenialReason,
    ErrorClass,
    ReplyVisibility,
)
from sb.spec.refs import HandlerRef, WorkflowRef, clear_ref_table, handler, workflow
from tests.unit.interaction.conftest import FakeResponder, Spec, make_request


@pytest.fixture(autouse=True)
def _refs():
    clear_ref_table()
    REGISTRY.clear_for_tests()
    yield
    clear_ref_table()
    REGISTRY.clear_for_tests()


def _run(req):
    return asyncio.run(resolve(req))


def test_invoke_handler_returns_workflow_result_passthrough():
    @handler("probe.hello")
    async def _hello(req):
        from sb.kernel.workflow.result import WorkflowResult
        return WorkflowResult(mutation_id="m", guild_id=req.guild_id, domain="x",
                              operation="probe", outcome="partial",
                              reversibility="reversible", user_message="hi")

    result = _run(make_request(Spec(route=HandlerRef("probe.hello"))))
    assert result.outcome == "partial"             # copied through UNCHANGED
    assert result.workflow is not None and result.user_message == "hi"


def test_invoke_workflow_dispatches_k7_run(fake_conn=None):
    # a pure in-memory workflow: no DB legs, NATURAL_KEY, no emits.
    @workflow("probe.leg")
    async def _leg(conn, ctx):
        from sb.kernel.workflow.context import LegOutcome
        from sb.kernel.workflow.result import StepResult
        return LegOutcome(step=StepResult(1, "leg", True))

    import contextlib

    from sb.kernel.db import pool

    @contextlib.asynccontextmanager
    async def fake_txn():
        class _C:
            async def fetchrow(self, q, *p):
                return {"outbox_id": "x"}

            async def execute(self, q, *p):
                return "OK"
        yield _C()

    original = pool.transaction
    pool.transaction = fake_txn
    try:
        REGISTRY.register(CompoundOpSpec(
            op_key="probe.op", domain="probe", lane=WorkflowLane.DOMAIN,
            authority_ref="", legs=(LegSpec("leg", LegKind.DB,
                                            WorkflowRef("probe.leg"), "reversible"),),
            idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
            audit_verb="probe"))
        result = _run(make_request(Spec(route=WorkflowRef("probe.op"))))
    finally:
        pool.transaction = original
    assert result.outcome == SUCCESS
    assert result.workflow is not None
    assert result.workflow.operation == "probe.op"


def test_confirm_round_trip_second_dispatch():
    @handler("probe.danger")
    async def _danger(req):
        return None

    spec = Spec(route=HandlerRef("probe.danger"),
                confirm=ConfirmationSpec(reversibility="irreversible"))
    responder = FakeResponder()
    first = _run(make_request(spec, responder=responder))
    assert first.outcome == SUCCESS and first.workflow is None    # confirm-pending
    assert len(responder.confirms) == 1
    prompt = responder.confirms[0]
    assert prompt.target_key == "probe" and prompt.request_id

    # the re-entrant dispatch: same target, confirmed=True, same request_id.
    second = _run(make_request(spec, confirmed=True, request_id=prompt.request_id))
    assert second.outcome == SUCCESS
    # a double-clicked confirm dedups on request_id (§6).
    third = _run(make_request(spec, confirmed=True, request_id=prompt.request_id))
    assert third.outcome == DECLINED
    assert third.reason is DenialReason.CONFIRM_DECLINED


def test_dispatch_exception_maps_through_envelope_and_refunds_cooldown():
    @handler("probe.transient")
    async def _transient(req):
        raise ConnectionError("gateway blip")

    spec = Spec(route=HandlerRef("probe.transient"), cooldown=60.0)
    first = _run(make_request(spec))
    assert first.outcome == DISCORD_FAILED
    assert first.error_class is ErrorClass.TRANSIENT and first.retryable
    # fork D: the transient failure REFUNDED the token — a retry is allowed.
    second = _run(make_request(spec))
    assert second.reason is not DenialReason.COOLDOWN


def test_bug_class_renders_generic_copy():
    @handler("probe.bug")
    async def _bug(req):
        raise RuntimeError("unhandled")

    result = _run(make_request(Spec(route=HandlerRef("probe.bug"))))
    assert result.outcome == BLOCKED and result.error_class is ErrorClass.BUG
    assert result.user_message == "Something went wrong on our end — it's been logged."


# --- from_exception table (spec 02 §3.3, frozen rows) -------------------------


def _envelope(exc, target="t"):
    tgt = TargetRef(key=target, spec=Spec()) if target else None
    return from_exception(exc, surface=Surface.SLASH, target=tgt)


def test_from_exception_frozen_rows():
    user = _envelope(ValidatorError("amount"))
    assert (user.error_class, user.reason, user.retryable, user.outcome) == (
        ErrorClass.USER_ERROR, DenialReason.USER_ERROR, True, BLOCKED)
    assert "`amount`" in user.user_message and "!help t" in user.user_message

    denied = _envelope(PermissionError("no"))
    assert (denied.error_class, denied.reason, denied.outcome) == (
        ErrorClass.DENIED, DenialReason.AUTHORITY, BLOCKED)

    transient = _envelope(ConnectionError("pool"))
    assert (transient.error_class, transient.reason, transient.retryable,
            transient.outcome) == (ErrorClass.TRANSIENT,
                                   DenialReason.DISPATCH_ERROR, True, DISCORD_FAILED)

    bug = _envelope(RuntimeError("x"))
    assert (bug.error_class, bug.reason, bug.outcome) == (
        ErrorClass.BUG, DenialReason.DISPATCH_ERROR, BLOCKED)


def test_from_exception_headless_maintenance_target_none():
    envelope = from_exception(ConnectionError("x"), surface=Surface.MAINTENANCE,
                              target=None)
    assert envelope.outcome == DISCORD_FAILED     # classifier core target-independent
    assert envelope.user_message                  # canonical copy verbatim


def test_from_exception_wizard_section_fold_in():
    envelope = from_exception(PermissionError("x"), surface=Surface.SETUP,
                              target=TargetRef(key="setup", spec=Spec()),
                              section_label="Support Tickets")
    assert envelope.user_message.startswith("[Support Tickets]")
    assert "Retry or Skip" in envelope.user_message


# --- ephemerality resolver (spec 02 §3.4, T2-17) ------------------------------


def test_lane_default_rc3():
    assert lane_default(Lane.CAPABILITY) is ReplyVisibility.EPHEMERAL
    assert lane_default(Lane.TIER) is ReplyVisibility.PUBLIC
    assert lane_default(Lane.ROLE_SET) is ReplyVisibility.EPHEMERAL


def test_resolve_reply_visibility_table():
    kw = dict(lane=Lane.TIER, declared=None, committed=None)
    assert resolve_reply_visibility(outcome=BLOCKED,
                                    reason=DenialReason.DRAINING,
                                    **kw) is ReplyVisibility.SILENT
    assert resolve_reply_visibility(outcome=BLOCKED,
                                    reason=DenialReason.AUTHORITY,
                                    **kw) is ReplyVisibility.EPHEMERAL
    assert resolve_reply_visibility(outcome=SUCCESS,
                                    reason=DenialReason.ALLOWED,
                                    **kw) is ReplyVisibility.PUBLIC
    assert resolve_reply_visibility(
        outcome=SUCCESS, reason=DenialReason.ALLOWED, lane=Lane.TIER,
        declared=ReplyVisibility.EPHEMERAL, committed=None,
    ) is ReplyVisibility.EPHEMERAL                # declared beats lane default
    # a committed defer flag binds EVERY post-defer render.
    assert resolve_reply_visibility(
        outcome=DISCORD_FAILED, reason=DenialReason.DISPATCH_ERROR,
        lane=Lane.TIER, declared=None, committed=ReplyVisibility.PUBLIC,
    ) is ReplyVisibility.PUBLIC
    # uncommitted post-dispatch failure falls to EPHEMERAL.
    assert resolve_reply_visibility(
        outcome=DISCORD_FAILED, reason=DenialReason.DISPATCH_ERROR,
        lane=Lane.TIER, declared=None, committed=None,
    ) is ReplyVisibility.EPHEMERAL


def test_scripted_actor_rides_resolve_untouched():
    @handler("probe.sys")
    async def _sys(req):
        return None

    result = _run(make_request(
        Spec(authority_ref="administrator", route=HandlerRef("probe.sys")),
        actor=ActorRef(user_id=None, is_guild_operator=False, is_bot_owner=False,
                       is_dm=False, actor_type="system")))
    assert result.outcome == SUCCESS               # RC-18 scripted bypass
