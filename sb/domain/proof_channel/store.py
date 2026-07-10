"""Proof-channel lock CRUD (band 5) — the bug-#8 restart-recovery rows
(shipped migration 104 → 0018). Sole writer: the K7 proof lanes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = ["PROOF_LOCKS_STORE", "ensure_refs"]

PROOF_LOCKS_STORE = register_store(StoreSpec(
    table="proof_channel_locks",
    sole_writer=EngineRef("proof_channel.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.SESSION,
    invariant_tag="proof_channel_locks",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("proof_channel.erase_subject_locks"),
))


@engine("proof_channel.store")
def _store_marker() -> str:
    return "sb/domain/proof_channel/store.py"


async def upsert_lock(conn: Any, *, guild_id: int, channel_id: int,
                      winner_id: int, unlock_at: datetime) -> None:
    await execute(
        "INSERT INTO proof_channel_locks (guild_id, channel_id, winner_id, "
        "unlock_at) VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (guild_id, channel_id) DO UPDATE SET "
        "winner_id = EXCLUDED.winner_id, unlock_at = EXCLUDED.unlock_at",
        (guild_id, channel_id, winner_id, unlock_at), conn=conn)


async def insert_lock_if_absent(conn: Any, *, guild_id: int, channel_id: int,
                                winner_id: int, unlock_at: datetime) -> bool:
    """Compensation-only insert (codex 4673572674): restore a deleted
    deadline row ONLY while the slot is still empty. end_access commits its
    delete before the unlock EFFECT runs, so a concurrent grant_access can
    land a NEWER row before the compensator fires — an upsert here would
    clobber that grant with the stale stash (lost update). ON CONFLICT DO
    NOTHING lets the newer row win. Returns True iff the row was restored."""
    rows = await fetchall(
        "INSERT INTO proof_channel_locks (guild_id, channel_id, winner_id, "
        "unlock_at) VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (guild_id, channel_id) DO NOTHING RETURNING winner_id",
        (guild_id, channel_id, winner_id, unlock_at), conn=conn)
    return bool(rows)


async def get_lock(guild_id: int, channel_id: int,
                   conn: Any = None) -> dict | None:
    return await fetchone(
        "SELECT winner_id, unlock_at FROM proof_channel_locks "
        "WHERE guild_id=$1 AND channel_id=$2",
        (guild_id, channel_id), conn=conn)


async def list_due_locks(now: datetime, conn: Any = None) -> list[dict]:
    return await fetchall(
        "SELECT guild_id, channel_id, winner_id, unlock_at "
        "FROM proof_channel_locks WHERE unlock_at <= $1 ORDER BY unlock_at",
        (now,), conn=conn)


async def delete_lock(conn: Any, *, guild_id: int, channel_id: int) -> bool:
    rows = await fetchall(
        "DELETE FROM proof_channel_locks WHERE guild_id=$1 AND channel_id=$2 "
        "RETURNING winner_id", (guild_id, channel_id), conn=conn)
    return bool(rows)


async def erase_subject_locks(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM proof_channel_locks WHERE winner_id=$1 "
        "RETURNING guild_id", (user_id,), conn=conn)
    return len(rows)


async def delete_guild_locks(guild_id: int, conn: Any = None) -> None:
    await execute("DELETE FROM proof_channel_locks WHERE guild_id=$1",
                  (guild_id,), conn=conn)


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("proof_channel.store")):
        _engine("proof_channel.store")(_store_marker)
