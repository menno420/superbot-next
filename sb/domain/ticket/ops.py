"""The ticket admin mutation lanes (the `_unmapped` ticket-admin re-home)
— every ticket-family DB write as a K7 CompoundOpSpec: the `!ticketlimit`
config upsert and the `!ticketblacklist add|remove` pair (the oracle's
audited ``ticket_mutation`` direct lane: disbot/services/ticket_mutation.py
``update_config`` / ``set_blacklist``).

Audit verbs carry the oracle's own ``mutation_type`` vocabulary verbatim
("config" / "blacklist" — the shipped ``_emit_audit`` fields; the bus
event surface is kernel-owned and disposition-dropped at replay-diff, so
the verb lives here for the audit_log spine's honesty, not for byte
parity).

Authority: the shipped commands were ``perms_or_owner(manage_guild=True)``
— tier "staff" (TIER_DISCORD_PERMISSION: staff = manage_guild, verbatim).
"""

from __future__ import annotations

from sb.domain.ticket import store
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


def _actor_id(ctx: WorkflowContext) -> int:
    return int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)


def _now_epoch() -> int:
    """The shipped ``int(time.time())`` stamp (``added_at``/``updated_at``
    BIGINT epoch columns — the parity boot pins ``time.time`` to the
    logical case clock, so replay stamps the goldens' exact ints)."""
    import time

    return int(time.time())


# --- DB legs ---------------------------------------------------------------------

@workflow("ticket.record_set_limit")
async def _record_set_limit(conn, ctx: WorkflowContext) -> LegOutcome:
    """``update_config(guild_id, actor_id, max_open_per_user=n)`` — the
    fresh-row upsert falls back to the column defaults for unset fields
    (goldens/ticket/sweep_ticketlimit pins the row: enabled/ping TRUE,
    max_open_per_user set, updated_at = the case clock)."""
    gid = int(ctx.guild_id or 0)
    max_open = int(ctx.params.get("max_open", 0) or 0)
    prior = await store.get_config_row(gid, conn=conn)
    await store.upsert_config_fields(conn, guild_id=gid, now=_now_epoch(),
                                     max_open_per_user=max_open)
    return LegOutcome(
        step=StepResult(gid, "set_limit", True),
        before={"max_open_per_user": (prior or {}).get("max_open_per_user")},
        after={"max_open_per_user": max_open})


@workflow("ticket.record_blacklist_add")
async def _record_blacklist_add(conn, ctx: WorkflowContext) -> LegOutcome:
    """``set_blacklist(..., blacklisted=True)`` — the shipped add-or-refresh
    upsert (goldens/ticket/sweep_ticketblacklist_add pins the row:
    reason NULL, added_by = the actor, added_at = the case clock)."""
    gid = int(ctx.guild_id or 0)
    uid = int(ctx.params.get("target_id", 0) or 0)
    await store.add_blacklist(conn, guild_id=gid, user_id=uid,
                              added_by=_actor_id(ctx), reason=None,
                              added_at=_now_epoch())
    return LegOutcome(step=StepResult(gid, "blacklist_add", True),
                      before={}, after={"user_id": uid, "blacklisted": True})


@workflow("ticket.record_blacklist_remove")
async def _record_blacklist_remove(conn, ctx: WorkflowContext) -> LegOutcome:
    """``set_blacklist(..., blacklisted=False)`` — the shipped bare DELETE
    (no-op if absent); the ack is UNCONDITIONAL (the #193 oracle-wins
    class — goldens/ticket/sweep_ticketblacklist_remove pins the success
    copy over an empty table)."""
    gid = int(ctx.guild_id or 0)
    uid = int(ctx.params.get("target_id", 0) or 0)
    removed = await store.remove_blacklist(conn, guild_id=gid, user_id=uid)
    return LegOutcome(step=StepResult(gid, "blacklist_remove", True),
                      before={"present": removed},
                      after={"user_id": uid, "blacklisted": False})


# --- privacy erasure body ----------------------------------------------------------

@workflow("ticket.erase_subject_blacklist")
async def _erase_subject_blacklist(conn, ctx: WorkflowContext) -> LegOutcome:
    subject = int(ctx.params["subject_user_id"])
    rows = await store.erase_subject_blacklist_rows(conn, user_id=subject)
    return LegOutcome(step=StepResult(0, "erase_subject_blacklist", True),
                      before={}, after={"rows": rows})


# --- op table ------------------------------------------------------------------------

def _db_op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="ticket", lane=WorkflowLane.DOMAIN,
        authority_ref="staff",           # shipped perms_or_owner(manage_guild)
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


SET_LIMIT = _db_op("ticket.set_limit", "config",
                   "ticket.record_set_limit")
BLACKLIST_ADD = _db_op("ticket.blacklist_add", "blacklist",
                       "ticket.record_blacklist_add")
BLACKLIST_REMOVE = _db_op("ticket.blacklist_remove", "blacklist",
                          "ticket.record_blacklist_remove")

_OPS = (SET_LIMIT, BLACKLIST_ADD, BLACKLIST_REMOVE)

_REF_TABLE = (
    ("ticket.record_set_limit", _record_set_limit),
    ("ticket.record_blacklist_add", _record_blacklist_add),
    ("ticket.record_blacklist_remove", _record_blacklist_remove),
    ("ticket.erase_subject_blacklist", _erase_subject_blacklist),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):  # P2-resolution marker; the engine resolves via REGISTRY
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
    # the #141 doctrine: a manifest re-import re-fires decorators only for
    # freshly-imported modules — end with the idempotent leg-ref re-arm.
    ensure_ops_refs()


def ensure_ops_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
