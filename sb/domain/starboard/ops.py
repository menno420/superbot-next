"""The starboard config mutation lanes (the `_unmapped` starboard-family
re-home; NEW subsystem birth) — every starboard-family DB write as a K7
CompoundOpSpec: the `!starboard #channel [threshold]` configure upsert,
the `off`/`selfstar` pure-UPDATE flips and the `ignore`/`unignore` pair
(the oracle's audited ``starboard_service`` direct lane:
disbot/services/starboard_service.py ``configure`` / ``disable`` /
``set_self_star`` / ``add_ignore_channel`` / ``remove_ignore_channel``).

Audit verbs carry the oracle's own ``mutation_type`` vocabulary verbatim
(``configure_starboard`` / ``disable_starboard`` /
``set_starboard_self_star`` / ``add_starboard_ignore_channel`` /
``remove_starboard_ignore_channel`` — the shipped ``_emit`` fields; the
bus event surface is kernel-owned and disposition-dropped at replay-diff,
so the verb lives here for the audit_log spine's honesty, not for byte
parity). The shipped ``disable``/``set_self_star`` audit UNCONDITIONALLY
— even when the pure UPDATE matched no row (goldens/starboard/
sweep_starboard_off + sweep_starboard_selfstar pin the ack + zero domain
delta over the unconfigured capture guild); the legs mirror that shape.

Authority: the shipped commands were ``perms_or_owner(manage_guild=True)``
— tier "staff" (TIER_DISCORD_PERMISSION: staff = manage_guild, verbatim).
"""

from __future__ import annotations

from sb.domain.starboard import store
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


# --- DB legs ---------------------------------------------------------------------

@workflow("starboard.record_configure")
async def _record_configure(conn, ctx: WorkflowContext) -> LegOutcome:
    """``configure(guild_id, channel_id, threshold, emoji, actor_id)`` —
    the shipped upsert verbatim: threshold clamped ``max(1, n)``, the
    existing ``self_star`` policy PRESERVED ("re-pointing the channel or
    changing the threshold must not silently reset the self-star
    toggle"), ``enabled`` forced TRUE. The write-bearing argful invocation
    exists in no imported golden (D-0069 — the sweep drove `!starboard`
    bare); shape carried from the oracle service reconstruction."""
    gid = int(ctx.guild_id or 0)
    channel_id = int(ctx.params.get("channel_id", 0) or 0)
    threshold = max(1, int(ctx.params.get("threshold", 3) or 3))
    emoji = str(ctx.params.get("emoji", "⭐") or "⭐")
    prior = await store.get_settings_row(gid, conn=conn)
    self_star = bool(prior["self_star"]) if prior else False
    await store.upsert_settings(conn, guild_id=gid, channel_id=channel_id,
                                threshold=threshold, emoji=emoji,
                                self_star=self_star)
    ctx.params["_stored_threshold"] = threshold
    return LegOutcome(
        step=StepResult(gid, "configure", True),
        before={"channel_id": (prior or {}).get("channel_id"),
                "threshold": (prior or {}).get("threshold")},
        after={"channel_id": channel_id, "threshold": threshold,
               "emoji": emoji})


@workflow("starboard.record_disable")
async def _record_disable(conn, ctx: WorkflowContext) -> LegOutcome:
    """``disable(guild_id, actor_id)`` — the shipped ``set_enabled(gid,
    False)`` PURE UPDATE (a no-op over an unconfigured guild) + the
    unconditional audit (goldens/starboard/sweep_starboard_off pins the
    ack + the empty domain delta)."""
    gid = int(ctx.guild_id or 0)
    await store.set_enabled(conn, guild_id=gid, enabled=False)
    return LegOutcome(step=StepResult(gid, "disable", True),
                      before=None, after="disabled")


@workflow("starboard.record_self_star")
async def _record_self_star(conn, ctx: WorkflowContext) -> LegOutcome:
    """``set_self_star(guild_id, self_star, actor_id)`` — the shipped
    PURE UPDATE (a no-op over an unconfigured guild) + the unconditional
    audit (goldens/starboard/sweep_starboard_selfstar pins the ack + the
    empty domain delta; the oracle's new_value shape ``self_star={bool}``
    carried on the rollup)."""
    gid = int(ctx.guild_id or 0)
    self_star = bool(ctx.params.get("self_star", False))
    await store.set_self_star(conn, guild_id=gid, self_star=self_star)
    return LegOutcome(step=StepResult(gid, "self_star", True),
                      before=None, after=f"self_star={self_star}")


@workflow("starboard.record_ignore_add")
async def _record_ignore_add(conn, ctx: WorkflowContext) -> LegOutcome:
    """``add_ignore_channel(guild_id, channel_id, actor_id)`` — the
    shipped idempotent insert (goldens/starboard/sweep_starboard_ignore
    pins the {guild_id, channel_id} row + the oracle's
    ``channel={id}`` audit rollup shape)."""
    gid = int(ctx.guild_id or 0)
    channel_id = int(ctx.params.get("channel_id", 0) or 0)
    await store.add_ignore_channel(conn, guild_id=gid,
                                   channel_id=channel_id)
    return LegOutcome(step=StepResult(gid, "ignore_add", True),
                      before=None, after=f"channel={channel_id}")


@workflow("starboard.record_ignore_remove")
async def _record_ignore_remove(conn, ctx: WorkflowContext) -> LegOutcome:
    """``remove_ignore_channel(guild_id, channel_id, actor_id)`` — the
    shipped bare DELETE (no-op if absent); the ack is UNCONDITIONAL (the
    #193 oracle-wins class — goldens/starboard/sweep_starboard_unignore
    pins the success copy over an empty table)."""
    gid = int(ctx.guild_id or 0)
    channel_id = int(ctx.params.get("channel_id", 0) or 0)
    removed = await store.remove_ignore_channel(conn, guild_id=gid,
                                                channel_id=channel_id)
    return LegOutcome(step=StepResult(gid, "ignore_remove", True),
                      before={"present": removed},
                      after=f"channel={channel_id}")


# --- op table ------------------------------------------------------------------------

def _db_op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="starboard", lane=WorkflowLane.DOMAIN,
        authority_ref="staff",           # shipped perms_or_owner(manage_guild)
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


CONFIGURE = _db_op("starboard.configure", "configure_starboard",
                   "starboard.record_configure")
DISABLE = _db_op("starboard.disable", "disable_starboard",
                 "starboard.record_disable")
SET_SELF_STAR = _db_op("starboard.set_self_star", "set_starboard_self_star",
                       "starboard.record_self_star")
IGNORE_ADD = _db_op("starboard.ignore_add", "add_starboard_ignore_channel",
                    "starboard.record_ignore_add")
IGNORE_REMOVE = _db_op("starboard.ignore_remove",
                       "remove_starboard_ignore_channel",
                       "starboard.record_ignore_remove")

_OPS = (CONFIGURE, DISABLE, SET_SELF_STAR, IGNORE_ADD, IGNORE_REMOVE)

_REF_TABLE = (
    ("starboard.record_configure", _record_configure),
    ("starboard.record_disable", _record_disable),
    ("starboard.record_self_star", _record_self_star),
    ("starboard.record_ignore_add", _record_ignore_add),
    ("starboard.record_ignore_remove", _record_ignore_remove),
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
