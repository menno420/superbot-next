"""Mining stores (band 6) — the shipped mining_inventory (TEXT user ids,
kept NAME_STABLE) + mining_player_state (depth). Deep-system tables
(equipment, wear, vault, structures, skills, grid, loadouts, titles,
energy) ride the deferred mining depth port (D-0043 successor list)."""

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
    "MINING_INVENTORY_STORE",
    "MINING_PLAYER_STATE_STORE",
    "get_depth",
    "get_mining_inventory",
    "mining_totals",
    "update_mining_item",
]

MINING_INVENTORY_STORE = register_store(StoreSpec(
    table="mining_inventory",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_inventory",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community", "inventory"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_inventory"),
))

MINING_PLAYER_STATE_STORE = register_store(StoreSpec(
    table="mining_player_state",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_player_state",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_state"),
))


@engine("mining.store")
def _store_marker() -> str:
    return "sb/domain/mining/store.py"


async def get_mining_inventory(user_id: int, guild_id: int,
                               conn: Any = None) -> dict[str, int]:
    rows = await fetchall(
        "SELECT item_name, quantity FROM mining_inventory WHERE "
        "user_id=$1 AND guild_id=$2 AND quantity > 0",
        (str(user_id), guild_id), conn=conn)
    return {str(r["item_name"]): int(r["quantity"]) for r in rows}


async def update_mining_item(conn: Any, *, user_id: int, guild_id: int,
                             item: str, delta: int) -> int:
    """Adjust an item count (floor 0) — the shipped upsert shape."""
    row = await fetchone(
        "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
        "quantity) VALUES ($1,$2,$3,GREATEST(0,$4)) "
        "ON CONFLICT (user_id, guild_id, item_name) DO UPDATE SET "
        "quantity = GREATEST(0, mining_inventory.quantity + $4) "
        "RETURNING quantity",
        (str(user_id), guild_id, item, delta), conn=conn)
    return int(row["quantity"]) if row else 0


async def get_depth(user_id: int, guild_id: int, conn: Any = None) -> int:
    row = await fetchone(
        "SELECT depth FROM mining_player_state WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return int(row["depth"]) if row else 0


async def mining_totals(guild_id: int, limit: int = 10,
                        conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, COALESCE(SUM(quantity), 0) AS total FROM "
        "mining_inventory WHERE guild_id=$1 GROUP BY user_id "
        "ORDER BY total DESC LIMIT $2", (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_inventory(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM mining_inventory WHERE user_id=$1",
                           (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_state(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM mining_player_state WHERE user_id=$1",
        (str(user_id),), conn=conn)
    return _rc(result)


def _rc(result: Any) -> int:
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("mining.store")):
        _engine("mining.store")(_store_marker)
