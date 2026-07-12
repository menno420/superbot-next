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
    "MINING_EQUIPMENT_STORE",
    "MINING_GEAR_WEAR_STORE",
    "MINING_LOADOUT_STORE",
    "PLAYER_SKILLS_STORE",
    "get_depth",
    "get_mining_inventory",
    "mining_totals",
    "reset_player_inventory",
    "update_mining_item",
    "get_equipment",
    "equip_item",
    "unequip_slot",
    "get_gear_wear",
    "set_gear_wear",
    "clear_gear_wear",
    "save_loadout",
    "get_loadout",
    "list_loadouts",
    "delete_loadout",
    "get_skills",
    "set_skill_points",
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


MINING_EQUIPMENT_STORE = register_store(StoreSpec(
    table="mining_equipment",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_equipment",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_equipment"),
))

MINING_GEAR_WEAR_STORE = register_store(StoreSpec(
    table="mining_gear_wear",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_gear_wear",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_gear_wear"),
))

MINING_LOADOUT_STORE = register_store(StoreSpec(
    table="mining_loadout_presets",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_loadout_presets",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_loadouts"),
))

PLAYER_SKILLS_STORE = register_store(StoreSpec(
    table="player_skills",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="player_skills",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_skills"),
))


@engine("mining.store")
def _store_marker() -> str:
    return "sb/domain/mining/store.py"


# --- mining_equipment CRUD (TEXT user ids — matches mining_inventory) --------


async def get_equipment(user_id: int, guild_id: int,
                        conn: Any = None) -> dict[str, str]:
    """``{slot: item_name}`` for the user's equipped gear in a guild."""
    rows = await fetchall(
        "SELECT slot, item_name FROM mining_equipment WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return {str(r["slot"]): str(r["item_name"]) for r in rows}


async def equip_item(conn: Any, *, user_id: int, guild_id: int, slot: str,
                     item_name: str) -> None:
    """Equip *item_name* into *slot* (upsert — one item per slot)."""
    await execute(
        "INSERT INTO mining_equipment (user_id, guild_id, slot, item_name) "
        "VALUES ($1,$2,$3,$4) ON CONFLICT (user_id, guild_id, slot) "
        "DO UPDATE SET item_name=$4, equipped_at=now()",
        (str(user_id), guild_id, slot, item_name), conn=conn)


async def unequip_slot(conn: Any, *, user_id: int, guild_id: int,
                       slot: str) -> None:
    """Clear *slot* for the user in a guild."""
    await execute(
        "DELETE FROM mining_equipment WHERE user_id=$1 AND guild_id=$2 AND "
        "slot=$3", (str(user_id), guild_id, slot), conn=conn)


# --- mining_gear_wear CRUD (keyed by NAME; row absent = full durability) -----


async def get_gear_wear(user_id: int, guild_id: int,
                        conn: Any = None) -> dict[str, int]:
    """``{item_name: remaining}`` for the user's worn gear (rows that exist)."""
    rows = await fetchall(
        "SELECT item_name, durability FROM mining_gear_wear WHERE user_id=$1 "
        "AND guild_id=$2", (str(user_id), guild_id), conn=conn)
    return {str(r["item_name"]): int(r["durability"]) for r in rows}


async def set_gear_wear(conn: Any, *, user_id: int, guild_id: int,
                        item_name: str, durability: int) -> None:
    """Set the remaining durability of *item_name* (upsert)."""
    await execute(
        "INSERT INTO mining_gear_wear (user_id, guild_id, item_name, "
        "durability) VALUES ($1,$2,$3,$4) ON CONFLICT "
        "(user_id, guild_id, item_name) DO UPDATE SET durability=$4, "
        "updated_at=now()",
        (str(user_id), guild_id, item_name, durability), conn=conn)


async def clear_gear_wear(conn: Any, *, user_id: int, guild_id: int,
                          item_name: str) -> None:
    """Delete the wear row for *item_name* (break/repair → full durability)."""
    await execute(
        "DELETE FROM mining_gear_wear WHERE user_id=$1 AND guild_id=$2 AND "
        "item_name=$3", (str(user_id), guild_id, item_name), conn=conn)


# --- mining_loadout_presets CRUD (a preset = the rows sharing a name) --------


async def save_loadout(conn: Any, *, user_id: int, guild_id: int, name: str,
                       slots: dict[str, str]) -> None:
    """Replace the preset *name* with *slots* (``{slot: item_name}``).

    DELETE-then-INSERT per slot: any previously-saved slot not present in
    *slots* is dropped, so saving an empty mapping clears the preset.
    """
    await execute(
        "DELETE FROM mining_loadout_presets WHERE user_id=$1 AND guild_id=$2 "
        "AND name=$3", (str(user_id), guild_id, name), conn=conn)
    for slot, item_name in slots.items():
        await execute(
            "INSERT INTO mining_loadout_presets (user_id, guild_id, name, "
            "slot, item_name) VALUES ($1,$2,$3,$4,$5)",
            (str(user_id), guild_id, name, slot, item_name), conn=conn)


async def get_loadout(user_id: int, guild_id: int, name: str,
                      conn: Any = None) -> dict[str, str]:
    """``{slot: item_name}`` for the saved preset *name* (``{}`` if none)."""
    rows = await fetchall(
        "SELECT slot, item_name FROM mining_loadout_presets WHERE user_id=$1 "
        "AND guild_id=$2 AND name=$3", (str(user_id), guild_id, name),
        conn=conn)
    return {str(r["slot"]): str(r["item_name"]) for r in rows}


async def list_loadouts(user_id: int, guild_id: int,
                        conn: Any = None) -> list[str]:
    """The player's saved preset names, alphabetically."""
    rows = await fetchall(
        "SELECT DISTINCT name FROM mining_loadout_presets WHERE user_id=$1 "
        "AND guild_id=$2 ORDER BY name", (str(user_id), guild_id), conn=conn)
    return [str(r["name"]) for r in rows]


async def delete_loadout(conn: Any, *, user_id: int, guild_id: int,
                         name: str) -> int:
    """Delete the preset *name*; return the number of slot rows removed."""
    rows = await fetchall(
        "DELETE FROM mining_loadout_presets WHERE user_id=$1 AND guild_id=$2 "
        "AND name=$3 RETURNING slot", (str(user_id), guild_id, name),
        conn=conn)
    return len(rows)


# --- player_skills CRUD (BIGINT user ids — derives from the game-XP level) ---


async def get_skills(user_id: int, guild_id: int,
                     conn: Any = None) -> dict[str, int]:
    """``{branch: points}`` for spent branches (zero-point branches filtered)."""
    rows = await fetchall(
        "SELECT branch, points FROM player_skills WHERE user_id=$1 AND "
        "guild_id=$2", (int(user_id), guild_id), conn=conn)
    return {str(r["branch"]): int(r["points"]) for r in rows
            if int(r["points"]) > 0}


async def set_skill_points(conn: Any, *, user_id: int, guild_id: int,
                           branch: str, points: int) -> None:
    """Set the *absolute* allocated points for *branch* (clamped ``>= 0``)."""
    await execute(
        "INSERT INTO player_skills (user_id, guild_id, branch, points) "
        "VALUES ($1,$2,$3,GREATEST(0,$4)) ON CONFLICT "
        "(user_id, guild_id, branch) DO UPDATE SET points=GREATEST(0,$4)",
        (int(user_id), guild_id, branch, points), conn=conn)


async def get_mining_inventory(user_id: int, guild_id: int,
                               conn: Any = None, *,
                               for_update: bool = False) -> dict[str, int]:
    """The user's held items (quantity > 0 only).

    ``for_update=True`` (the F-001/F-002 fix's mining sibling, PR #213
    class): the sell/sell_all K7 legs compose this read inside their own
    txn ahead of a decrement → ``wager.credit_in_txn`` sequence under
    ``IdempotencyPosture.NATURAL_KEY``, and ``update_mining_item``'s
    decrement floors at zero (``GREATEST(0, …)``) — so with a plain
    SELECT, two concurrent sells both read ``held=N``, both pass the
    holdings check, the loser's decrement silently floors instead of
    failing, and BOTH credit ``N × price``: a double payout for one
    inventory. The row locks hold until the leg's txn commits, so the
    second racer blocks here and then re-reads the committed (emptied)
    stack — a clean denial, never a second credit. ``ORDER BY item_name``
    keeps multi-row lock acquisition deterministic (no deadlock between
    two concurrent sell_alls). Selling requires ``held > 0`` (the rows
    exist), so no advisory no-row fence is needed on this lane.

    Money-bearing legs MUST pass ``for_update=True`` (and a conn); plain
    reads (loot rolls, panels, totals) stay unlocked."""
    if for_update and conn is None:
        raise ValueError("for_update=True requires the caller's leg conn "
                         "— a locking read outside a transaction fences "
                         "nothing")
    rows = await fetchall(
        "SELECT item_name, quantity FROM mining_inventory WHERE "
        "user_id=$1 AND guild_id=$2 AND quantity > 0"
        + (" ORDER BY item_name FOR UPDATE" if for_update else ""),
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


async def reset_player_inventory(conn: Any, *, user_id: int,
                                 guild_id: int) -> int:
    """Guild-scoped admin wipe of one member's pack — the shipped
    `!reset_inventory` write (\"reset a user's inventory in THIS guild\",
    mining_cog.py PR M3). Additive to the #217 lanes: a single atomic
    DELETE inside the caller's leg txn — no read-check-write sequence, so
    no FOR UPDATE / advisory fence is needed (the sell/sell_all locking
    contract in ``get_mining_inventory`` is untouched)."""
    result = await execute(
        "DELETE FROM mining_inventory WHERE user_id=$1 AND guild_id=$2",
        (str(user_id), guild_id), conn=conn)
    return _rc(result)


async def erase_subject_inventory(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM mining_inventory WHERE user_id=$1",
                           (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_state(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM mining_player_state WHERE user_id=$1",
        (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_equipment(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM mining_equipment WHERE user_id=$1",
                           (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_gear_wear(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM mining_gear_wear WHERE user_id=$1",
                           (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_loadouts(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM mining_loadout_presets WHERE user_id=$1",
        (str(user_id),), conn=conn)
    return _rc(result)


async def erase_subject_skills(conn: Any, *, user_id: int) -> int:
    # player_skills.user_id is BIGINT (derives from the game-XP level).
    result = await execute("DELETE FROM player_skills WHERE user_id=$1",
                           (int(user_id),), conn=conn)
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
