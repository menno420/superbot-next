"""fishing_catch_log CRUD (band 6) — the dex/trophy record, shipped
075/095 shape, NAME_STABLE, MEMBER_ID delete erasure."""

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
    "FISHING_CATCH_LOG_STORE",
    "get_catch_log",
    "record_catch",
    "top_fishers",
    "top_trophies",
]

FISHING_CATCH_LOG_STORE = register_store(StoreSpec(
    table="fishing_catch_log",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_catch_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_catch_log"),
))


@engine("fishing.store")
def _store_marker() -> str:
    return "sb/domain/fishing/store.py"


async def record_catch(conn: Any, *, user_id: int, guild_id: int,
                       species: str, weight: float,
                       now: int) -> float | None:
    """Upsert the dex row (count+1, best_weight max). Returns the PRIOR
    best weight (None on a first catch) — the personal-best signal."""
    prior = await fetchone(
        "SELECT best_weight FROM fishing_catch_log WHERE user_id=$1 AND "
        "guild_id=$2 AND species=$3", (user_id, guild_id, species),
        conn=conn)
    await execute(
        "INSERT INTO fishing_catch_log (user_id, guild_id, species, count, "
        "best_weight, total_value, first_caught, last_caught) "
        "VALUES ($1,$2,$3,1,$4,0,$5,$5) "
        "ON CONFLICT (user_id, guild_id, species) DO UPDATE SET "
        "count = fishing_catch_log.count + 1, "
        "best_weight = GREATEST(fishing_catch_log.best_weight, $4), "
        "last_caught = $5",
        (user_id, guild_id, species, weight, now), conn=conn)
    return float(prior["best_weight"]) if prior else None


async def get_catch_log(user_id: int, guild_id: int,
                        conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT species, count, best_weight FROM fishing_catch_log WHERE "
        "user_id=$1 AND guild_id=$2 ORDER BY count DESC",
        (user_id, guild_id), conn=conn)
    return [dict(r) for r in rows]


async def top_fishers(guild_id: int, known_species: list[str],
                      limit: int = 10, conn: Any = None) -> list[dict]:
    """Catalog-scoped totals (a superseded catalog never inflates)."""
    rows = await fetchall(
        "SELECT user_id, COALESCE(SUM(count), 0) AS total FROM "
        "fishing_catch_log WHERE guild_id=$1 AND species = ANY($2) "
        "GROUP BY user_id ORDER BY total DESC LIMIT $3",
        (guild_id, known_species, limit), conn=conn)
    return [dict(r) for r in rows]


async def top_trophies(guild_id: int, known_species: list[str],
                       limit: int = 10, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, species, best_weight FROM fishing_catch_log "
        "WHERE guild_id=$1 AND species = ANY($2) AND best_weight > 0 "
        "ORDER BY best_weight DESC LIMIT $3",
        (guild_id, known_species, limit), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_catch_log(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_catch_log WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("fishing.store")):
        _engine("fishing.store")(_store_marker)
