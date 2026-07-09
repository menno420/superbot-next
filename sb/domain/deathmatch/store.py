"""deathmatch_stats CRUD (band 6) — the shipped shape, NAME_STABLE:
atomic two-side W/L update (the shipped one-txn invariant becomes the
K7 leg's conn), guild-scoped rows. PvP results only — bot duels never
write here (the shipped PR-6 anti-farming rule)."""

from __future__ import annotations

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

__all__ = [
    "DEATHMATCH_STATS_STORE",
    "erase_subject_stats",
    "get_stats",
    "leaderboard",
    "record_result",
]

DEATHMATCH_STATS_STORE = register_store(StoreSpec(
    table="deathmatch_stats",
    sole_writer=EngineRef("deathmatch.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="deathmatch_stats",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("deathmatch.erase_subject_stats"),
))


@engine("deathmatch.store")
def _store_marker() -> str:
    return "sb/domain/deathmatch/store.py"


async def get_stats(user_id: int, guild_id: int,
                    conn: Any = None) -> dict:
    row = await fetchone(
        "SELECT wins, losses FROM deathmatch_stats "
        "WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return dict(row) if row else {"wins": 0, "losses": 0}


async def record_result(conn: Any, *, winner_id: int, loser_id: int,
                        guild_id: int) -> None:
    """Atomic two-side update — both statements on the leg's conn."""
    await execute(
        "INSERT INTO deathmatch_stats (user_id, guild_id, wins) "
        "VALUES ($1, $2, 1) ON CONFLICT (user_id, guild_id) DO UPDATE "
        "SET wins=deathmatch_stats.wins+1",
        (winner_id, guild_id), conn=conn)
    await execute(
        "INSERT INTO deathmatch_stats (user_id, guild_id, losses) "
        "VALUES ($1, $2, 1) ON CONFLICT (user_id, guild_id) DO UPDATE "
        "SET losses=deathmatch_stats.losses+1",
        (loser_id, guild_id), conn=conn)


async def leaderboard(guild_id: int, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, wins, losses FROM deathmatch_stats "
        "WHERE guild_id=$1 ORDER BY wins DESC LIMIT 15",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_stats(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM deathmatch_stats WHERE user_id=$1",
        (user_id,), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import engine as _engine, is_registered

    if not is_registered(EngineRef("deathmatch.store")):
        _engine("deathmatch.store")(_store_marker)
