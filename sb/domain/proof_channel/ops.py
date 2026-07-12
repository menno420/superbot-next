"""Proof-channel K7 lanes (band 5): lock (record + post-commit channel
EFFECT), timed lock (same + the durable deadline row), unlock, and the
erasure body. Authority = staff (the registry visibility_tier; shipped
gate was perms_or_owner(manage_channels=True) — manage_channels has no
tier bit, staff/manage_guild is the nearest floor, D-0041)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sb.domain.proof_channel import store
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
from sb.spec.refs import WorkflowRef, workflow

__all__ = ["ensure_ops_refs", "register_ops"]


def _verr(message: str):
    """Copy-only ValidatorError — the raise-site sentence IS the user copy,
    rendered bare (the D-0060/D-0061 refusal-copy posture; the one-arg
    param form wrapped every sentence in the missing-argument
    boilerplate)."""
    from sb.kernel.interaction.errors import ValidatorError

    return ValidatorError("", message)


#: the shipped guard copies, per command, VERBATIM — the cog carried
#: DIFFERENT literals per flow: timedprize / -prize / prizestatus sent the
#: bare sentence (goldens/proof_channel/sweep_timedprize +
#: sweep_-prize pin the byte), while +prize (the PERMANENT grant)
#: appended "Please create one first." (goldens/proof_channel/
#: sweep_+prize pins that byte; codex review on #145).
MISSING_CHANNEL = "Channel '#proof' not found."
MISSING_CHANNEL_CREATE = "Channel '#proof' not found. Please create one first."


async def _resolve_channel(ctx: WorkflowContext,
                           missing_copy: str = MISSING_CHANNEL) -> int:
    from sb.domain.proof_channel.service import bound_proof_channel

    cid = int(ctx.params.get("channel_id", 0) or 0)
    if not cid:
        cid = await bound_proof_channel(int(ctx.guild_id or 0)) or 0
    if not cid:
        raise _verr(missing_copy)
    ctx.params["channel_id"] = cid
    return cid


@workflow("proof_channel.record_lock")
async def _record_lock(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    winner_id = int(ctx.params.get("winner_id", 0) or 0)
    if not winner_id:
        raise _verr("Usage: `+prize @winner`")
    minutes = int(ctx.params.get("duration_minutes", 0) or 0)
    # the permanent grant (+prize) carried the shipped longer guard copy;
    # the timed grant kept the bare sentence (see the literals above).
    cid = await _resolve_channel(
        ctx, MISSING_CHANNEL if minutes else MISSING_CHANNEL_CREATE)
    if minutes:
        unlock_at = ctx.clock() + timedelta(minutes=minutes)
        await store.upsert_lock(conn, guild_id=gid, channel_id=cid,
                                winner_id=winner_id, unlock_at=unlock_at)
        ctx.params["_unlock_at"] = unlock_at.isoformat()
    # the sanctioned DB-leg ack channel (D-0052/D-0057): the panel/modal
    # path routes this WorkflowRef directly — without leg copy a granted
    # lock succeeds SILENTLY there (prefix handlers compose their own
    # Reply and ignore this line).
    copy = (f"<@{winner_id}> has access to <#{cid}> for {minutes} "
            f"minute(s) — auto-unlocks at {ctx.params.get('_unlock_at')}."
            if minutes else
            f"<@{winner_id}> has been granted access to <#{cid}>!")
    return LegOutcome(
        step=StepResult(winner_id, "record_lock", True),
        before={},
        after={"channel_id": cid, "winner_id": winner_id,
               "duration_minutes": minutes,
               "unlock_at": ctx.params.get("_unlock_at")},
        user_message=copy)


@workflow("proof_channel.apply_lock")
async def _apply_lock(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.proof_channel.service import active_channel_actions

    await active_channel_actions().lock_channel_for_winner(
        int(ctx.guild_id or 0), int(ctx.params.get("channel_id", 0) or 0),
        int(ctx.params.get("winner_id", 0) or 0))
    return LegOutcome(step=StepResult(0, "apply_lock", True),
                      before={}, after={"applied": "lock"})


@workflow("proof_channel.compensate_lock")
async def _compensate_lock(conn, ctx: WorkflowContext) -> LegOutcome:
    """Lock's compensator (fork E; conn=None): withdraw the deadline row
    record_lock wrote, so the DB stops promising an auto-unlock for access
    Discord never granted. A PERMANENT grant (minutes == 0) wrote NO row —
    no-op, never touch whatever timed row may exist for the slot.

    DELETE-IF-MATCH (the compensate_unlock insert-only fix's symmetric
    twin, codex 4673572674): record_lock's upsert commits before apply_lock
    runs and grant_access is NATURAL_KEY, so a concurrent re-grant can land
    a NEWER row for the same guild+channel before this compensator fires —
    a key-only delete would destroy that legitimate grant. Only the exact
    row this grant wrote (winner_id + unlock_at match) is withdrawn."""
    unlock_iso = ctx.params.get("_unlock_at")
    if not unlock_iso:
        return LegOutcome(step=StepResult(0, "compensate_lock", True),
                          before={}, after={"compensated": "nothing"})
    removed = await store.delete_lock_if_match(
        conn, guild_id=int(ctx.guild_id or 0),
        channel_id=int(ctx.params.get("channel_id", 0) or 0),
        winner_id=int(ctx.params.get("winner_id", 0) or 0),
        unlock_at=datetime.fromisoformat(str(unlock_iso)))
    return LegOutcome(step=StepResult(0, "compensate_lock", True),
                      before={}, after={"compensated": "lock",
                                        "removed": removed})


@workflow("proof_channel.record_unlock")
async def _record_unlock(conn, ctx: WorkflowContext) -> LegOutcome:
    gid = int(ctx.guild_id or 0)
    cid = await _resolve_channel(ctx)
    # compensation handle: stash the deadline row BEFORE deleting it so a
    # Discord-refused unlock can re-insert it (the sweep then retries the
    # unlock instead of stranding a locked channel with no deadline row).
    prior = await store.get_lock(gid, cid, conn=conn)
    if prior:
        ctx.params["_deleted_lock"] = {
            "winner_id": int(prior["winner_id"]),
            "unlock_at": prior["unlock_at"].isoformat(),
        }
    removed = await store.delete_lock(conn, guild_id=gid, channel_id=cid)
    return LegOutcome(
        step=StepResult(gid, "record_unlock", True),
        before={"lock_present": removed},
        after={"channel_id": cid, "removed": removed,
               "reason": str(ctx.params.get("reason", "manual") or "manual")},
        # panel-path ack (the sweep's SYSTEM run renders nowhere — harmless)
        user_message=f"<#{cid}> is now read-only for everyone.")


@workflow("proof_channel.apply_unlock")
async def _apply_unlock(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.domain.proof_channel.service import active_channel_actions

    await active_channel_actions().unlock_channel(
        int(ctx.guild_id or 0), int(ctx.params.get("channel_id", 0) or 0))
    return LegOutcome(step=StepResult(0, "apply_unlock", True),
                      before={}, after={"applied": "unlock"})


@workflow("proof_channel.compensate_unlock")
async def _compensate_unlock(conn, ctx: WorkflowContext) -> LegOutcome:
    """end_access's compensator (fork E; conn=None): a Discord-refused
    unlock re-inserts the deadline row record_unlock deleted, so the DB
    stops claiming the channel is open and the sweep retries the unlock at
    the deadline. A permanent grant has no row to restore — no-op.

    INSERT-ONLY (codex 4673572674): the delete commits before the EFFECT
    runs and grant_access is NATURAL_KEY (nothing serializes it against
    end_access), so a concurrent re-grant can land a newer row for the same
    guild+channel before this compensator fires — the stale stash must not
    clobber it. insert_lock_if_absent restores the row only while the slot
    is empty; otherwise the newer grant wins and its own deadline governs.
    (GRANT_PRIZE's _compensate_lock is the delete-if-match twin of this
    same class.)"""
    deleted = ctx.params.get("_deleted_lock")
    if not deleted:
        return LegOutcome(step=StepResult(0, "compensate_unlock", True),
                          before={}, after={"compensated": "nothing"})
    gid = int(ctx.guild_id or 0)
    cid = int(ctx.params.get("channel_id", 0) or 0)
    restored = await store.insert_lock_if_absent(
        None, guild_id=gid, channel_id=cid,
        winner_id=int(deleted["winner_id"]),
        unlock_at=datetime.fromisoformat(str(deleted["unlock_at"])))
    try:
        from sb.kernel.observability.findings import record_operator_finding

        record_operator_finding(
            source="workflow:proof_channel.end_access", severity="warning",
            summary=(f"unlock of channel {cid} blocked by Discord — "
                     + ("deadline row restored, sweep will retry" if restored
                        else "newer grant already holds the slot, "
                             "stash discarded")),
            detail="", correlation_id=None)
    except Exception:  # noqa: BLE001 — findings are observability only
        pass
    return LegOutcome(step=StepResult(0, "compensate_unlock", True),
                      before={}, after={"compensated": "unlock",
                                        "restored": restored,
                                        "restored_channel_id": cid})


@workflow("proof_channel.erase_subject_locks")
async def _erase_subject_locks(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_locks(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_locks", True),
                      before={}, after={"rows": rows})


GRANT_PRIZE = CompoundOpSpec(
    op_key="proof_channel.grant_access", domain="proof_channel",
    lane=WorkflowLane.DOMAIN, authority_ref="staff",
    legs=(
        LegSpec("record", LegKind.DB,
                WorkflowRef("proof_channel.record_lock"), "reversible"),
        LegSpec("apply", LegKind.EFFECT,
                WorkflowRef("proof_channel.apply_lock"), "compensatable",
                compensator=WorkflowRef("proof_channel.compensate_lock")),
    ),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="proof_access_granted", emits=())

RECORD_UNLOCK = CompoundOpSpec(
    op_key="proof_channel.record_unlock_row", domain="proof_channel",
    lane=WorkflowLane.DOMAIN, authority_ref="",
    legs=(LegSpec("record", LegKind.DB,
                  WorkflowRef("proof_channel.record_unlock"), "reversible"),),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="proof_access_revoked", emits=())

END_PRIZE = CompoundOpSpec(
    op_key="proof_channel.end_access", domain="proof_channel",
    lane=WorkflowLane.DOMAIN, authority_ref="staff",
    legs=(
        LegSpec("record", LegKind.DB,
                WorkflowRef("proof_channel.record_unlock"), "reversible"),
        LegSpec("apply", LegKind.EFFECT,
                WorkflowRef("proof_channel.apply_unlock"), "compensatable",
                compensator=WorkflowRef("proof_channel.compensate_unlock")),
        # a refused unlock re-inserts the deadline row record_unlock
        # deleted (same class as GRANT_PRIZE's compensate_lock)
    ),
    idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
    audit_verb="proof_access_revoked", emits=())

_OPS = (GRANT_PRIZE, RECORD_UNLOCK, END_PRIZE)

_REF_TABLE = (
    ("proof_channel.record_lock", _record_lock),
    ("proof_channel.apply_lock", _apply_lock),
    ("proof_channel.compensate_lock", _compensate_lock),
    ("proof_channel.record_unlock", _record_unlock),
    ("proof_channel.apply_unlock", _apply_unlock),
    ("proof_channel.compensate_unlock", _compensate_unlock),
    ("proof_channel.erase_subject_locks", _erase_subject_locks),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
