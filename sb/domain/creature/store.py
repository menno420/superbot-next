"""Creature stores (band 6) — collection log (the dex) + battle record,
shipped 077/082 shapes, NAME_STABLE, MEMBER_ID delete erasure."""

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
    "CREATURE_BATTLE_STORE",
    "CREATURE_COLLECTION_STORE",
    "get_battle_record",
    "get_collection",
    "record_battle_result",
    "record_catch",
    "top_battlers",
    "top_catchers",
]

CREATURE_COLLECTION_STORE = register_store(StoreSpec(
    table="creature_collection_log",
    sole_writer=EngineRef("creature.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="creature_collection_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("creature.erase_subject_collection"),
))

CREATURE_BATTLE_STORE = register_store(StoreSpec(
    table="creature_battle_record",
    sole_writer=EngineRef("creature.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="creature_battle_record",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("creature.erase_subject_battles"),
))


@engine("creature.store")
def _store_marker() -> str:
    return "sb/domain/creature/store.py"


async def record_catch(conn: Any, *, user_id: int, guild_id: int,
                       creature: str, now: int) -> None:
    await execute(
        "INSERT INTO creature_collection_log (user_id, guild_id, creature, "
        "count, first_caught, last_caught) VALUES ($1,$2,$3,1,$4,$4) "
        "ON CONFLICT (user_id, guild_id, creature) DO UPDATE SET "
        "count = creature_collection_log.count + 1, last_caught = $4",
        (user_id, guild_id, creature, now), conn=conn)


async def get_collection(user_id: int, guild_id: int,
                         conn: Any = None) -> dict[str, int]:
    rows = await fetchall(
        "SELECT creature, count FROM creature_collection_log WHERE "
        "user_id=$1 AND guild_id=$2", (user_id, guild_id), conn=conn)
    return {str(r["creature"]): int(r["count"]) for r in rows}


async def top_catchers(guild_id: int, limit: int = 10,
                       conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, COUNT(DISTINCT creature) AS species, "
        "COALESCE(SUM(count), 0) AS total FROM creature_collection_log "
        "WHERE guild_id=$1 GROUP BY user_id ORDER BY species DESC, "
        "total DESC LIMIT $2", (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def record_battle_result(conn: Any, *, user_id: int, guild_id: int,
                               won: bool, now: int) -> None:
    await execute(
        "INSERT INTO creature_battle_record (user_id, guild_id, wins, "
        "losses, last_battle) VALUES ($1,$2,$3,$4,$5) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "wins = creature_battle_record.wins + $3, "
        "losses = creature_battle_record.losses + $4, last_battle = $5",
        (user_id, guild_id, 1 if won else 0, 0 if won else 1, now),
        conn=conn)


async def get_battle_record(user_id: int, guild_id: int,
                            conn: Any = None) -> tuple[int, int]:
    row = await fetchone(
        "SELECT wins, losses FROM creature_battle_record WHERE user_id=$1 "
        "AND guild_id=$2", (user_id, guild_id), conn=conn)
    return (int(row["wins"]), int(row["losses"])) if row else (0, 0)


async def top_battlers(guild_id: int, limit: int = 10,
                       conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, wins, losses FROM creature_battle_record WHERE "
        "guild_id=$1 ORDER BY wins DESC, losses ASC LIMIT $2",
        (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_collection(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM creature_collection_log WHERE user_id=$1",
        (user_id,), conn=conn)
    return _rc(result)


async def erase_subject_battles(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM creature_battle_record WHERE user_id=$1",
        (user_id,), conn=conn)
    return _rc(result)


def _rc(result: Any) -> int:
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("creature.store")):
        _engine("creature.store")(_store_marker)
