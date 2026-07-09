"""Confirmation-fenced ops behind command routes (band-2 finding, D-0052):
the resolver reads the OP's ConfirmationSpec for WorkflowRef routes (the
CommandSpec carries no confirm field), and the `sb.confirm:` re-entry
resolves prefix/slash-only command keys through the component adapter."""

from __future__ import annotations

import asyncio

from sb.kernel.interaction.adapters import install_target_index
from sb.kernel.interaction.adapters.component import request_from_component
from sb.kernel.interaction.request import Surface, TargetRef
from sb.kernel.interaction.resolve import _op_confirmation
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.confirmation import Challenge, ConfirmationSpec
from sb.spec.refs import HandlerRef, WorkflowRef, workflow
from tests.unit.interaction.conftest import FakeResponder, Spec


def _register_confirm_op(op_key: str = "probe.confirm_op") -> CompoundOpSpec:
    @workflow(f"{op_key}.leg")
    async def _leg(conn, ctx):  # pragma: no cover — never run here
        raise AssertionError("leg must not run")

    return REGISTRY.register(CompoundOpSpec(
        op_key=op_key, domain="probe", lane=WorkflowLane.DOMAIN,
        authority_ref="",
        legs=(LegSpec("leg", LegKind.DB, WorkflowRef(f"{op_key}.leg"),
                      "irreversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb="probe_confirmed",
        confirmation=ConfirmationSpec(reversibility="irreversible",
                                      challenge=Challenge.TYPED_PHRASE),
    ))


def test_op_confirmation_reads_registry():
    spec = _register_confirm_op("probe.confirm_op_a")
    assert _op_confirmation(WorkflowRef("probe.confirm_op_a")) is spec.confirmation
    assert _op_confirmation(WorkflowRef("probe.not_an_op")) is None
    assert _op_confirmation(HandlerRef("probe.handler")) is None
    assert _op_confirmation(None) is None


def test_workflow_route_issues_confirm_prompt():
    """A command routed at a confirmation-fenced op issues the interactive
    prompt at the resolver's gate — the op (and its legs) must NOT run and
    the engine's headless backstop must NOT be the reply."""
    from tests.unit.interaction.conftest import make_request
    from sb.kernel.interaction.resolve import resolve

    _register_confirm_op("probe.confirm_op_b")
    spec = Spec(route=WorkflowRef("probe.confirm_op_b"))
    responder = FakeResponder(Surface.PREFIX)
    result = asyncio.run(resolve(make_request(
        spec, surface=Surface.PREFIX, responder=responder)))
    assert result.workflow is None                    # confirm-pending
    assert len(responder.confirms) == 1
    prompt = responder.confirms[0]
    assert prompt.target_key == "probe"
    assert prompt.challenge is Challenge.TYPED_PHRASE
    assert responder.rendered == [] or all(
        getattr(r, "user_message", None) is None for r in responder.rendered)


def test_confirm_reentry_falls_back_to_command_surfaces():
    """sb.confirm:<key>:<rid> for a PREFIX-only command resolves through the
    component adapter's surface fallback."""
    cmd_spec = Spec(route=WorkflowRef("probe.confirm_op_c"))
    index = {("kickprobe", Surface.PREFIX): TargetRef(key="kickprobe",
                                                      spec=cmd_spec)}
    install_target_index(lambda key, surface: index.get((key, surface)))

    class _Interaction:
        id = 99
        user = None
        guild = None
        guild_id = None
        channel_id = 5
        data = {"custom_id": "sb.confirm:kickprobe:rid-1",
                "component_type": 2}

    req = request_from_component(_Interaction(), responder=FakeResponder())
    assert req is not None
    assert req.target.key == "kickprobe"
    assert req.confirmed is True
    assert req.request_id == "rid-1"
    # an UNCONFIRMED unknown component id still misses (no fallback)
    class _Plain(_Interaction):
        data = {"custom_id": "kickprobe", "component_type": 2}

    assert request_from_component(_Plain(), responder=FakeResponder()) is None
