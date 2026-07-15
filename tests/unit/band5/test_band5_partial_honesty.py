"""Band-5 partial-honesty fixes (the live-drive follow-through): a
compensated PARTIAL must never render the withdrawn leg's success copy
— the speaking-compensator engine seam REPLACES it (a silent
compensator leaves the D-0058 warn-partial ack untouched) — and the
proof-channel success acks read ``result.after`` by the leg's
StepResult target_name (``record_lock``/``record_unlock``; the
``"record"`` LegSpec id was never the after key, so armed-port grants
rendered ``<#0>``)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

run = asyncio.run


def _ctx(params, *, uid=42, gid=1):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params)


# --- the engine seam ----------------------------------------------------------------

def _mini_result(user_message):
    from sb.kernel.workflow.result import StepResult, WorkflowResult

    return WorkflowResult(
        mutation_id="m1", guild_id=1, domain="proof_channel",
        operation="proof_channel.grant_access", outcome="success",
        reversibility="", user_message=user_message,
        steps=(StepResult(7, "record_lock", True),))


def _effect_spec(compensator_speaks: bool):
    from sb.kernel.workflow.spec import (
        CompoundOpSpec,
        IdempotencyPosture,
        LegKind,
        LegSpec,
        WorkflowLane,
    )
    from sb.spec.refs import WorkflowRef, is_registered, workflow

    name = "spk" if compensator_speaks else "sil"

    if not is_registered(WorkflowRef(f"b5ph.effect_boom_{name}")):
        @workflow(f"b5ph.effect_boom_{name}")
        async def _boom(conn, ctx):
            raise RuntimeError("port refused")

        @workflow(f"b5ph.compensate_{name}")
        async def _comp(conn, ctx):
            from sb.kernel.workflow.context import LegOutcome
            from sb.kernel.workflow.result import StepResult

            return LegOutcome(
                step=StepResult(0, "compensate", True),
                user_message=("rolled back." if compensator_speaks
                              else None))

    return CompoundOpSpec(
        op_key=f"b5ph.op_{name}", domain="proof_channel",
        lane=WorkflowLane.DOMAIN, authority_ref="",
        legs=(LegSpec("apply", LegKind.EFFECT,
                      WorkflowRef(f"b5ph.effect_boom_{name}"),
                      "compensatable",
                      compensator=WorkflowRef(f"b5ph.compensate_{name}")),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb="b5ph", emits=())


def test_speaking_compensator_replaces_withdrawn_success_copy():
    from sb.kernel.workflow import engine as engine_mod

    spec = _effect_spec(compensator_speaks=True)
    out = run(engine_mod._run_effect_legs(
        spec, _ctx({}), _mini_result("<@7> has access to <#55>!")))
    assert out.outcome == "partial"
    assert out.user_message == "rolled back."      # the lie never renders


def test_silent_compensator_keeps_partial_copy_d0058():
    from sb.kernel.workflow import engine as engine_mod

    spec = _effect_spec(compensator_speaks=False)
    out = run(engine_mod._run_effect_legs(
        spec, _ctx({}), _mini_result("warn recorded (3/3)")))
    assert out.outcome == "partial"
    assert out.user_message == "warn recorded (3/3)"   # D-0058 ack survives


# --- the band-5 compensators speak ---------------------------------------------------

def test_proof_and_role_compensators_carry_honest_copy(monkeypatch):
    from sb.domain.proof_channel import ops as pops
    from sb.domain.proof_channel import store as pstore
    from sb.domain.role import ops as rops
    from sb.domain.role import store as rstore

    async def delete_lock_if_match(conn, **kw):
        return True

    async def insert_lock_if_absent(conn, **kw):
        return True

    async def list_grants_for_member(gid, mid, conn=None):
        return []

    monkeypatch.setattr(pstore, "delete_lock_if_match", delete_lock_if_match)
    monkeypatch.setattr(pstore, "insert_lock_if_absent",
                        insert_lock_if_absent)
    monkeypatch.setattr(rstore, "list_grants_for_member",
                        list_grants_for_member)

    out = run(pops._compensate_lock(None, _ctx(
        {"_unlock_at": "2026-07-15T12:00:00+00:00", "channel_id": 55,
         "winner_id": 7})))
    assert "Could not grant proof-channel access" in out.user_message
    assert "rolled back" in out.user_message

    out = run(pops._compensate_lock(None, _ctx({})))   # permanent, no row
    assert "Could not grant proof-channel access" in out.user_message

    out = run(pops._compensate_unlock(None, _ctx(
        {"_deleted_lock": {"winner_id": 7,
                           "unlock_at": "2026-07-15T12:00:00+00:00"},
         "channel_id": 55})))
    assert "Could not end the prize session" in out.user_message
    assert "sweep will retry" in out.user_message

    out = run(rops._compensate_grant_temp(None, _ctx(
        {"member_id": 7, "role_id": 9})))
    assert "Could not grant the temporary role" in out.user_message


# --- proof success acks read the real after keys -------------------------------------

def _req(argv):
    return SimpleNamespace(
        guild_id=1, channel_id=2, request_id="r1", confirmed=False,
        actor=SimpleNamespace(user_id=42, actor_type="user",
                              member_tier="administrator",
                              role_ids=frozenset(), is_dm=False),
        args={"argv": argv}, surface=None, target=None, interaction_id="i1")


def test_proof_success_acks_read_the_leg_after(monkeypatch):
    import sb.domain.proof_channel.handlers  # noqa: F401 — refs registered
    from sb.kernel.workflow import engine
    from sb.spec.refs import HandlerRef, resolve

    async def fake_run(ref, ctx):
        return SimpleNamespace(
            outcome="success",
            after={"record_lock": {"channel_id": 55, "winner_id": 7,
                                   "duration_minutes": 30,
                                   "unlock_at": "2026-07-15T12:00:00+00:00"},
                   "record_unlock": {"channel_id": 55, "removed": True}},
            user_message=None)

    monkeypatch.setattr(engine, "run", fake_run)

    reply = run(resolve(HandlerRef("proof_channel.grant"))(
        _req(("<@900000000000000601>",))))
    assert "<#55>" in reply.user_message          # was <#0> pre-fix

    reply = run(resolve(HandlerRef("proof_channel.timed_grant"))(
        _req(("<@900000000000000601>", "30"))))
    assert "<#55>" in reply.user_message
    assert "2026-07-15T12:00:00+00:00" in reply.user_message   # was '?'

    reply = run(resolve(HandlerRef("proof_channel.end"))(_req(())))
    assert "<#55> is now read-only" in reply.user_message
