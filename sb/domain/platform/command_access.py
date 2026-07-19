"""Command-access policy (band 5) — the DB truth behind the K8 admission
resolver (core/runtime/command_access.py's storage half; the DECISION
logic already lives in sb/kernel/authority/channel_access.py since S9).

Fills the K8 waiting port: install_access_policy_reader gets the real
per-guild CommandAccessSnapshot read (band-5 obligation — the resolver
has been running on the mode=None safe default since S9). Mutations are
K7 lanes (set_mode / set_channels); a per-guild TTL cache mirrors the
shipped typed-accessor read path with post-commit write-through.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sb.kernel.authority.channel_access import AccessMode, CommandAccessSnapshot
from sb.kernel.db.pool import execute, fetchall, fetchone
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
from sb.spec.refs import EngineRef, WorkflowRef, engine, workflow
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

logger = logging.getLogger("sb.domain.platform.command_access")

__all__ = [
    "COMMAND_ACCESS_CHANNELS_STORE",
    "COMMAND_ACCESS_CHANNEL_ROLES_STORE",
    "COMMAND_ACCESS_POLICY_STORE",
    "ensure_refs",
    "forget_guild",
    "install_access_reader",
    "read_policy_snapshot",
    "register_ops",
    "reset_access_cache_for_tests",
]

COMMAND_ACCESS_POLICY_STORE = register_store(StoreSpec(
    table="guild_command_access_policy",
    sole_writer=EngineRef("platform.command_access_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="guild_command_access_policy",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))

COMMAND_ACCESS_CHANNELS_STORE = register_store(StoreSpec(
    table="guild_command_access_channels",
    sole_writer=EngineRef("platform.command_access_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="guild_command_access_channels",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))

COMMAND_ACCESS_CHANNEL_ROLES_STORE = register_store(StoreSpec(
    table="guild_command_access_channel_roles",
    sole_writer=EngineRef("platform.command_access_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="guild_command_access_channel_roles",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))


@engine("platform.command_access_store")
def _store_marker() -> str:
    return "sb/domain/platform/command_access.py"


# --- reads + the TTL cache (shipped typed-accessor semantics) ----------------------

_CACHE: dict[int, tuple[float, CommandAccessSnapshot]] = {}
_CACHE_TTL = 60.0


async def _fetch_snapshot(guild_id: int,
                          conn: Any = None) -> CommandAccessSnapshot:
    row = await fetchone(
        "SELECT mode FROM guild_command_access_policy WHERE guild_id=$1",
        (guild_id,), conn=conn)
    if row is None:
        return CommandAccessSnapshot()   # mode=None => safe default (allow)
    channels = await fetchall(
        "SELECT channel_id FROM guild_command_access_channels "
        "WHERE guild_id=$1", (guild_id,), conn=conn)
    role_rows = await fetchall(
        "SELECT channel_id, role_id FROM "
        "guild_command_access_channel_roles WHERE guild_id=$1",
        (guild_id,), conn=conn)
    role_sets: dict[int, set[int]] = {}
    for r in role_rows:
        role_sets.setdefault(int(r["channel_id"]), set()).add(int(r["role_id"]))
    return CommandAccessSnapshot(
        mode=str(row["mode"]),
        allowed_channels=frozenset(int(c["channel_id"]) for c in channels),
        channel_role_sets={cid: frozenset(rs) for cid, rs in role_sets.items()})


async def read_policy_snapshot(guild_id: int) -> CommandAccessSnapshot:
    """The cached per-guild policy read (the K8 reader body)."""
    entry = _CACHE.get(guild_id)
    if entry is not None and time.monotonic() - entry[0] < _CACHE_TTL:
        return entry[1]
    snapshot = await _fetch_snapshot(guild_id)
    _CACHE[guild_id] = (time.monotonic(), snapshot)
    return snapshot


def forget_guild(guild_id: int) -> None:
    """Paired cache+DB forget rides guild teardown (the shipped
    command_access.forget_guild contract: they never diverge)."""
    _CACHE.pop(guild_id, None)


def reset_access_cache_for_tests() -> None:
    _CACHE.clear()


async def delete_guild_rows(guild_id: int, conn: Any = None) -> None:
    await execute("DELETE FROM guild_command_access_policy WHERE guild_id=$1",
                  (guild_id,), conn=conn)   # channels CASCADE
    forget_guild(guild_id)


def install_access_reader() -> None:
    """Fill K8's install_access_policy_reader with the real DB read."""
    from sb.kernel.interaction.resolve import install_access_policy_reader

    async def _reader(guild_id: int) -> CommandAccessSnapshot | None:
        snapshot = await read_policy_snapshot(guild_id)
        return snapshot if snapshot.mode is not None else None

    install_access_policy_reader(_reader)


# --- K7 lanes ----------------------------------------------------------------------

_VALID_MODES = tuple(m.value for m in AccessMode)


@workflow("platform.record_set_access_mode")
async def _record_set_access_mode(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    gid = int(ctx.guild_id or 0)
    mode = str(ctx.params.get("mode", "") or "")
    if mode not in _VALID_MODES:
        # copy-only form: the sentence renders bare (D-0060/D-0061 posture)
        raise ValidatorError(
            "", f"Mode must be one of: {', '.join(_VALID_MODES)}.")
    actor = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    prior = await fetchone(
        "SELECT mode FROM guild_command_access_policy WHERE guild_id=$1",
        (gid,), conn=conn)
    await execute(
        "INSERT INTO guild_command_access_policy (guild_id, mode, updated_by) "
        "VALUES ($1, $2, $3) ON CONFLICT (guild_id) DO UPDATE SET "
        "mode = EXCLUDED.mode, updated_by = EXCLUDED.updated_by, "
        "updated_at = NOW()", (gid, mode, actor or None), conn=conn)
    return LegOutcome(
        step=StepResult(gid, "set_access_mode", True),
        before={"mode": prior["mode"] if prior else None},
        after={"mode": mode})


@workflow("platform.record_set_access_channels")
async def _record_set_access_channels(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    gid = int(ctx.guild_id or 0)
    channels = tuple(int(c) for c in (ctx.params.get("channel_ids") or ()))
    if not channels and not ctx.params.get("allow_empty", False):
        # copy-only form: the sentence renders bare (D-0060/D-0061 posture)
        raise ValidatorError(
            "", "Give at least one channel id (or allow_empty).")
    actor = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    row = await fetchone(
        "SELECT mode FROM guild_command_access_policy WHERE guild_id=$1",
        (gid,), conn=conn)
    if row is None:
        # a channel allowlist implies SELECTED_CHANNELS (shipped panel flow)
        await execute(
            "INSERT INTO guild_command_access_policy (guild_id, mode, "
            "updated_by) VALUES ($1, 'selected_channels', $2)",
            (gid, actor or None), conn=conn)
    await execute(
        "DELETE FROM guild_command_access_channels WHERE guild_id=$1",
        (gid,), conn=conn)
    for cid in channels:
        await execute(
            "INSERT INTO guild_command_access_channels (guild_id, channel_id, "
            "created_by) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            (gid, cid, actor or None), conn=conn)
    return LegOutcome(
        step=StepResult(gid, "set_access_channels", True),
        before={}, after={"channels": list(channels)})


@workflow("platform.record_set_channel_roles")
async def _record_set_channel_roles(conn, ctx: WorkflowContext) -> LegOutcome:
    from sb.kernel.interaction.errors import ValidatorError

    gid = int(ctx.guild_id or 0)
    channel_id = int(ctx.params.get("channel_id", 0) or 0)
    if not channel_id:
        # copy-only form: the sentence renders bare (D-0060/D-0061 posture)
        raise ValidatorError("", "Give a channel id.")
    role_ids = tuple(int(r) for r in (ctx.params.get("role_ids") or ()))
    if not role_ids and not ctx.params.get("allow_empty", False):
        # copy-only form: the sentence renders bare (D-0060/D-0061 posture)
        raise ValidatorError(
            "", "Give at least one role id (or allow_empty to clear).")
    actor = int(getattr(getattr(ctx, "actor", None), "user_id", 0) or 0)
    row = await fetchone(
        "SELECT mode FROM guild_command_access_policy WHERE guild_id=$1",
        (gid,), conn=conn)
    if row is None:
        # a role-set constraint implies a policy row exists; a role-set is
        # usable under ANY mode, so seed the same ALL_CHANNELS-equivalent
        # default the resolver treats as allow (mode is stored, not None).
        await execute(
            "INSERT INTO guild_command_access_policy (guild_id, mode, "
            "updated_by) VALUES ($1, 'all_channels', $2)",
            (gid, actor or None), conn=conn)
    # atomic per-(guild, channel) replace: clear then re-INSERT this
    # channel's role set (leaves other channels' rows untouched).
    await execute(
        "DELETE FROM guild_command_access_channel_roles "
        "WHERE guild_id=$1 AND channel_id=$2", (gid, channel_id), conn=conn)
    for rid in role_ids:
        await execute(
            "INSERT INTO guild_command_access_channel_roles (guild_id, "
            "channel_id, role_id, created_by) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT DO NOTHING", (gid, channel_id, rid, actor or None),
            conn=conn)
    return LegOutcome(
        step=StepResult(gid, "set_channel_roles", True),
        before={}, after={"channel_id": channel_id,
                          "role_ids": list(role_ids)})


def _op(op_key: str, verb: str, ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="platform", lane=WorkflowLane.DOMAIN,
        authority_ref="administrator",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(ref), "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb, emits=())


SET_ACCESS_MODE = _op("platform.set_access_mode", "command_access_mode_set",
                      "platform.record_set_access_mode")
SET_ACCESS_CHANNELS = _op("platform.set_access_channels",
                          "command_access_channels_set",
                          "platform.record_set_access_channels")
SET_CHANNEL_ROLES = _op("platform.set_channel_roles",
                        "command_access_channel_roles_set",
                        "platform.record_set_channel_roles")

_OPS = (SET_ACCESS_MODE, SET_ACCESS_CHANNELS, SET_CHANNEL_ROLES)

_REF_TABLE = (
    ("platform.record_set_access_mode", _record_set_access_mode),
    ("platform.record_set_access_channels", _record_set_access_channels),
    ("platform.record_set_channel_roles", _record_set_channel_roles),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.kernel.workflow import engine as _engine

        return await _engine.run(op, ctx)
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


async def set_access_mode(ctx, *, mode: str) -> object:
    from sb.kernel.workflow import engine as _engine

    ctx.params["mode"] = mode
    result = await _engine.run(SET_ACCESS_MODE, ctx)
    if getattr(result, "outcome", None) == "success":
        forget_guild(int(ctx.guild_id or 0))
    return result


async def set_access_channels(ctx, *, channel_ids: tuple[int, ...],
                              allow_empty: bool = False) -> object:
    from sb.kernel.workflow import engine as _engine

    ctx.params.update({"channel_ids": tuple(channel_ids),
                       "allow_empty": allow_empty})
    result = await _engine.run(SET_ACCESS_CHANNELS, ctx)
    if getattr(result, "outcome", None) == "success":
        forget_guild(int(ctx.guild_id or 0))
    return result


async def set_channel_roles(ctx, *, channel_id: int,
                            role_ids: tuple[int, ...],
                            allow_empty: bool = False) -> object:
    from sb.kernel.workflow import engine as _engine

    ctx.params.update({"channel_id": int(channel_id),
                       "role_ids": tuple(role_ids),
                       "allow_empty": allow_empty})
    result = await _engine.run(SET_CHANNEL_ROLES, ctx)
    if getattr(result, "outcome", None) == "success":
        forget_guild(int(ctx.guild_id or 0))
    return result


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine_dec
    from sb.spec.refs import workflow as _workflow

    if not is_registered(EngineRef("platform.command_access_store")):
        _engine_dec("platform.command_access_store")(_store_marker)
    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
