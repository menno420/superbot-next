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
    "MINING_WORLD_STORE",
    "MINING_VAULT_STORE",
    "MINING_STRUCTURES_STORE",
    "get_structures",
    "set_structure_level",
    "lock_structure_build_slot",
    "lock_workshop_slot",
    "get_last_broken",
    "set_last_broken",
    "get_vault",
    "update_vault_item",
    "get_vault_level",
    "set_vault_level",
    "lock_vault_upgrade_slot",
    "get_depth",
    "set_depth",
    "record_depth",
    "get_max_depth",
    "get_equipped_title",
    "get_energy",
    "set_energy",
    "get_world_seed",
    "set_world_seed",
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
    "lock_skill_slot",
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


MINING_WORLD_STORE = register_store(StoreSpec(
    table="mining_world",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_world",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    # Per-guild world seed (guild_id-keyed config) — carries no member id,
    # so no subject-erasure body (the treasury/guild-config precedent).
    data_class=DataClass.NONE,
))


MINING_VAULT_STORE = register_store(StoreSpec(
    table="mining_vault",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_vault",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    # A per-player item-state store (TEXT user ids, mirrors mining_inventory);
    # the vault_level capacity tier rides mining_player_state (no new table).
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_vault"),
))


MINING_STRUCTURES_STORE = register_store(StoreSpec(
    table="mining_structures",
    sole_writer=EngineRef("mining.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="mining_structures",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    # Per-player built structure levels (BIGINT user ids — player-progression
    # identity, matching player_skills / game_xp, NOT mining_inventory's legacy
    # TEXT column). The Forge (gates gold/diamond gear crafting) + the Campfire
    # (gates cooking) are its two slice-4 rows; a fresh player has no row (all
    # structures level 0).
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("mining.erase_subject_structures"),
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


async def lock_skill_slot(conn: Any, *, user_id: int, guild_id: int) -> None:
    """Fence concurrent `!skill <branch>` spends for one (user, guild) against a
    read-then-settle over-allocation of the SHARED available-points budget (the
    #213/#217 doctrine; ``lock_vault_upgrade_slot`` precedent). ``allocate``
    reads the current allocation + the game-XP level to size the available pool
    (``min(level, SOFT_TOTAL_CAP) − total_spent``), checks ``n <= avail``, then
    upserts the branch's absolute point total — a read-then-settle over a
    cross-branch budget: two racing spends into DIFFERENT branches both read
    ``total_spent=0``, both pass the budget check, and both commit, so the pool
    is overspent (a same-branch race is a lost update, since ``set_skill_points``
    writes an absolute value). No coins move and the budget is spread across
    per-branch rows that may not exist yet, so FOR UPDATE alone can fence
    nothing. A transaction-scoped advisory lock keyed on the (guild, user) pair
    serializes two racing spends: the loser blocks here until the winner's txn
    commits, then re-reads the winner's committed allocation and its budget check
    is sized against the reduced pool. Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"mining:skill:{guild_id}:{user_id}",), conn=conn)


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


async def set_depth(conn: Any, *, user_id: int, guild_id: int,
                    depth: int) -> None:
    """Persist the player's *depth* band (upsert — one row per player).

    The shipped ``mining_player_state.set_depth`` write (the descend/ascend
    move); the target's ``updated_at`` is a BIGINT epoch (band convention),
    so — unlike the oracle's ``now()`` — it is left to its column default,
    never a TIMESTAMPTZ literal."""
    await execute(
        "INSERT INTO mining_player_state (user_id, guild_id, depth) "
        "VALUES ($1,$2,$3) ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET depth=$3",
        (str(user_id), guild_id, depth), conn=conn)


async def record_depth(conn: Any, *, user_id: int, guild_id: int,
                       depth: int) -> bool:
    """Raise ``max_depth`` to *depth* if it beats the record; True on a new
    record. Shipped ``mining_player_state.record_depth`` verbatim — one
    conditional upsert decides and writes together (no read-then-write
    race). A fresh row at depth >= 1 and a beaten record both return a row;
    an unbeaten record updates nothing and returns none."""
    row = await fetchone(
        "INSERT INTO mining_player_state (user_id, guild_id, max_depth) "
        "VALUES ($1,$2,GREATEST(0,$3)) ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET max_depth=$3 "
        "WHERE mining_player_state.max_depth < $3 "
        "RETURNING max_depth",
        (str(user_id), guild_id, depth), conn=conn)
    return row is not None


async def get_max_depth(user_id: int, guild_id: int, conn: Any = None) -> int:
    """The deepest band the player has ever reached (``max_depth``); 0 for a
    no-row player. Shipped ``mining_player_state.get_max_depth`` — a plain
    read feeding the titles depth-milestone earn-checks
    (``title_service.build_context``)."""
    row = await fetchone(
        "SELECT max_depth FROM mining_player_state WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return int(row["max_depth"]) if row and row["max_depth"] is not None else 0


async def get_equipped_title(user_id: int, guild_id: int,
                             conn: Any = None) -> str | None:
    """The player's stored equipped-title id, or None when none is set.
    Shipped ``mining_player_state.get_equipped_title`` — a plain read; the
    title-service gates the value on the live earn-check, so a no-row / NULL
    player renders the "— none —" byte (goldens/mining/sweep_titles). The
    equipped-title WRITE (the panel select) rides the deferred panel port
    (D-0043) — no golden drives it."""
    row = await fetchone(
        "SELECT equipped_title FROM mining_player_state WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return row["equipped_title"] if row and row["equipped_title"] else None


async def get_energy(user_id: int, guild_id: int,
                     conn: Any = None) -> tuple[int, int]:
    """``(energy, energy_updated_at)`` — the player's stored dig-energy fuel.

    Shipped ``mining_player_state.get_energy`` verbatim (oracle @ 87bbe1d):
    a missing row returns ``(0, 0)`` — ``sb.domain.mining.energy.settle``
    reads that as "0 energy as of the epoch", which regenerates to a full
    bar by now, so a fresh (or pre-energy) player always starts full
    without this layer knowing ``MAX_ENERGY`` (no constant duplicated
    outside the pure energy domain). A PLAIN read — energy is game pacing,
    never coins (the ``get_fishing_energy`` non-money posture; the shipped
    read carried no lock)."""
    row = await fetchone(
        "SELECT energy, energy_updated_at FROM mining_player_state "
        "WHERE user_id=$1 AND guild_id=$2", (str(user_id), guild_id),
        conn=conn)
    if row is None:
        return 0, 0
    return int(row["energy"]), int(row["energy_updated_at"])


async def set_energy(user_id: int, guild_id: int, energy: int,
                     updated_at: int, conn: Any = None) -> None:
    """Upsert the settled ``(energy, energy_updated_at)`` pair.

    Shipped ``mining_player_state.set_energy`` (oracle @ 87bbe1d) minus the
    oracle's ``updated_at=now()`` touch — the target's ``updated_at`` is a
    BIGINT epoch (band convention, the ``set_depth`` precedent), left to its
    column default. Plain non-audited upsert (the ``set_fishing_energy``
    non-money posture); with *conn* given it composes inside the caller's
    transaction (the slice-2 cook/use debit+restore legs, the slice-3 dig
    spend — callers own commit)."""
    await execute(
        "INSERT INTO mining_player_state "
        "(user_id, guild_id, energy, energy_updated_at) "
        "VALUES ($1,$2,$3,$4) ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET energy=$3, energy_updated_at=$4",
        (str(user_id), guild_id, energy, updated_at), conn=conn)


# --- mining_world (per-guild world seed; guild-keyed, no member data) ---------


async def get_world_seed(guild_id: int, conn: Any = None) -> int:
    """The guild's world seed — its stored override, or ``guild_id`` by
    default. Shipped ``get_world_seed`` verbatim: the default makes every
    guild a stable, shared, shareable world with no setup; only an explicit
    ``!mineworld <seed>`` ever writes a row (goldens/mining/sweep_mineworld
    pins the default-seed read)."""
    row = await fetchone(
        "SELECT seed FROM mining_world WHERE guild_id=$1", (guild_id,),
        conn=conn)
    return int(row["seed"]) if row else int(guild_id)


async def set_world_seed(conn: Any, *, guild_id: int, seed: int) -> None:
    """Persist a guild's world *seed* (upsert — the owner re-seed). Shipped
    ``set_world_seed`` verbatim."""
    await execute(
        "INSERT INTO mining_world (guild_id, seed) VALUES ($1,$2) "
        "ON CONFLICT (guild_id) DO UPDATE SET seed=$2, updated_at=now()",
        (guild_id, seed), conn=conn)


# --- mining_vault (per-player safe stash; TEXT user ids) + vault_level --------


async def get_vault(user_id: int, guild_id: int,
                    conn: Any = None) -> dict[str, int]:
    """The player's vault contents for a guild (quantity > 0 only). Shipped
    ``mining_vault.get_vault`` verbatim: zero-quantity rows (a fully-withdrawn
    item) are filtered out so callers see only what is actually stored."""
    rows = await fetchall(
        "SELECT item_name, quantity FROM mining_vault WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return {str(r["item_name"]): int(r["quantity"])
            for r in rows if int(r["quantity"]) > 0}


async def update_vault_item(conn: Any, *, user_id: int, guild_id: int,
                            item: str, delta: int) -> None:
    """Add or subtract *delta* of *item* in the vault (floor 0) — the shipped
    ``mining_vault.update_vault_item`` upsert, mirroring
    ``update_mining_item`` so a deposit/withdraw is a symmetric pair of clamped
    deltas (``-qty`` on one table, ``+qty`` on the other) inside ONE txn."""
    await execute(
        "INSERT INTO mining_vault (user_id, guild_id, item_name, quantity) "
        "VALUES ($1,$2,$3,GREATEST(0,$4)) "
        "ON CONFLICT (user_id, guild_id, item_name) DO UPDATE SET "
        "quantity = GREATEST(0, mining_vault.quantity + $4)",
        (str(user_id), guild_id, item, delta), conn=conn)


async def get_vault_level(user_id: int, guild_id: int,
                          conn: Any = None) -> int:
    """The player's vault capacity tier (0 by default) — shipped
    ``mining_player_state.get_vault_level``; a no-row player reads level 0
    (base capacity)."""
    row = await fetchone(
        "SELECT vault_level FROM mining_player_state WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return int(row["vault_level"]) if row and row["vault_level"] is not None \
        else 0


async def lock_vault_upgrade_slot(conn: Any, *, user_id: int,
                                  guild_id: int) -> None:
    """Fence concurrent `!vaultupgrade` attempts for one (user, guild) against
    a first-insert / read-then-settle double-charge (the #213/#217 doctrine;
    lock_new_checkpoint_slot precedent). ``vault_upgrade`` reads the current
    vault_level (to size the coin cost), debits, then bumps the level — a
    read-then-settle over a natural-key row that may not exist yet (a fresh
    player has no mining_player_state row), so FOR UPDATE alone can lock
    nothing. A transaction-scoped advisory lock keyed on the SAME (guild, user)
    pair serializes two racing upgrades: the loser blocks here until the
    winner's txn commits, then re-reads the winner's committed level and its
    debit is sized against the raised cost. Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"mining:vault_upgrade:{guild_id}:{user_id}",), conn=conn)


async def set_vault_level(conn: Any, *, user_id: int, guild_id: int,
                          level: int) -> None:
    """Persist the player's *vault_level* (upsert; clamped >= 0) — the shipped
    ``mining_player_state.set_vault_level`` write (the ``!vaultupgrade`` sink).
    The target's ``updated_at`` is a BIGINT epoch column default, never a
    TIMESTAMPTZ literal (the set_depth convention)."""
    await execute(
        "INSERT INTO mining_player_state (user_id, guild_id, vault_level) "
        "VALUES ($1,$2,GREATEST(0,$3)) ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET vault_level=GREATEST(0,$3)",
        (str(user_id), guild_id, level), conn=conn)


# --- mining_structures (per-player built levels; BIGINT user ids) + the
# last_broken_item quick-craft marker (mining_player_state, TEXT user ids) ------


async def get_structures(user_id: int, guild_id: int,
                         conn: Any = None) -> dict[str, int]:
    """``{structure: level}`` for the player's built structures (level > 0
    only). Shipped ``mining_structures.get_structures`` verbatim: an absent row
    reads level 0 (not built), so a fresh player reads ``{}`` — the forge panel
    renders the not-built card and the cook gate stays locked."""
    rows = await fetchall(
        "SELECT structure, level FROM mining_structures WHERE user_id=$1 AND "
        "guild_id=$2", (int(user_id), guild_id), conn=conn)
    return {str(r["structure"]): int(r["level"]) for r in rows
            if int(r["level"]) > 0}


async def set_structure_level(conn: Any, *, user_id: int, guild_id: int,
                              structure: str, level: int) -> None:
    """Persist a structure's built *level* (upsert; clamped >= 0) — the shipped
    ``mining_structures.set_structure_level`` write (the `!build` / 🔥 Build
    sink). The MINING row-bearing build rides the deferred structures BUILD
    system (slice 6); the FISHING structure panels' Build buttons (fishing
    slice 4) write through THIS seam via the audited
    ``fishing.build_structure`` op — mining_structures stays sole-writer
    here."""
    await execute(
        "INSERT INTO mining_structures (user_id, guild_id, structure, level) "
        "VALUES ($1,$2,$3,GREATEST(0,$4)) ON CONFLICT "
        "(user_id, guild_id, structure) DO UPDATE SET level=GREATEST(0,$4)",
        (int(user_id), guild_id, structure, level), conn=conn)


async def lock_structure_build_slot(conn: Any, *, user_id: int,
                                    guild_id: int) -> None:
    """Fence concurrent structure-build settles for one (user, guild)
    against a read-then-settle double-charge / double-level-raise (the
    #213/#217 doctrine; ``lock_vault_upgrade_slot`` precedent). A build
    reads the current structure level (to size the coin + material cost),
    debits, consumes materials, then bumps the level — a read-then-settle
    over natural-key rows that may not exist yet (a fresh player has no
    mining_structures row), so FOR UPDATE alone can lock nothing. A
    transaction-scoped advisory lock keyed on the (guild, user) pair
    serializes two racing builds: the loser blocks here until the
    winner's txn commits, then re-reads the winner's committed level and
    its debit is sized against the raised cost. One key for ALL
    structures per player (a player can't race two different builds into
    a double coin debit either). Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"mining:structure_build:{guild_id}:{user_id}",), conn=conn)


async def lock_workshop_slot(conn: Any, *, user_id: int,
                             guild_id: int) -> None:
    """Fence concurrent workshop settles (repair / quick-craft) for one
    (user, guild) against a read-then-settle double-charge / double-consume
    (the #213/#217 doctrine; ``lock_vault_upgrade_slot`` precedent). Repair
    reads the current gear-wear (to size the coin cost) then debits + clears
    the wear; quick-craft reads the pack (to size the material spend) then
    consumes + equips — each a read-then-settle over natural-key rows that may
    not exist yet (a fresh player has no wear / structure row), so FOR UPDATE
    alone can lock nothing. A transaction-scoped advisory lock keyed on the
    (guild, user) pair serializes two racing settles: the loser blocks here
    until the winner's txn commits, then re-reads the winner's committed state.
    Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"mining:workshop:{guild_id}:{user_id}",), conn=conn)


async def lock_structure_slot(conn: Any, *, user_id: int,
                              guild_id: int) -> None:
    """Fence concurrent structure BUILD settles (🔥 Build / 🏠 Build) for one
    (user, guild) against a read-then-settle double-charge / skipped-level (the
    #213/#217 doctrine; ``lock_vault_upgrade_slot`` precedent). ``build_structure``
    reads the current built level (to size the coin + material cost) then debits +
    consumes + raises the level — a read-then-settle over a natural-key row that
    may not exist yet (a fresh player has no ``mining_structures`` row), so FOR
    UPDATE alone can lock nothing. Two racing builds both read level L, both pass
    the affordability check, and both debit + bump, so the player is
    double-charged for one net level (or a level is skipped). A
    transaction-scoped advisory lock keyed on the (guild, user) pair serializes
    two racing builds: the loser blocks here until the winner's txn commits, then
    re-reads the winner's committed level and its cost/affordability check is
    sized against the raised level. Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"mining:structure:{guild_id}:{user_id}",), conn=conn)


async def get_last_broken(user_id: int, guild_id: int,
                          conn: Any = None) -> str | None:
    """The name of the last gear item that broke for the player (the
    quick-craft target), or ``None`` if nothing has broken. Shipped
    ``mining_player_state.get_last_broken``: reads the ``last_broken_item``
    column (NULL for a fresh player → the "Nothing has broken recently" read
    goldens/mining/sweep_quickcraft.json pins)."""
    row = await fetchone(
        "SELECT last_broken_item FROM mining_player_state WHERE user_id=$1 AND "
        "guild_id=$2", (str(user_id), guild_id), conn=conn)
    return str(row["last_broken_item"]) if row and \
        row["last_broken_item"] is not None else None


async def set_last_broken(conn: Any, *, user_id: int, guild_id: int,
                          item: str | None) -> None:
    """Set (or clear, with ``None``) the quick-craft marker — the shipped
    ``mining_player_state.set_last_broken`` write. A wear tick that breaks an
    item sets it; a successful quick-craft clears it. Upsert keyed on the
    per-player row (TEXT user ids, matching mining_player_state)."""
    await execute(
        "INSERT INTO mining_player_state (user_id, guild_id, last_broken_item) "
        "VALUES ($1,$2,$3) ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET last_broken_item=$3",
        (str(user_id), guild_id, item), conn=conn)


async def erase_subject_structures(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM mining_structures WHERE user_id=$1", (int(user_id),),
        conn=conn)
    return _rc(result)


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


async def erase_subject_vault(conn: Any, *, user_id: int) -> int:
    # vault_level lives on mining_player_state (cleared by erase_subject_state).
    result = await execute("DELETE FROM mining_vault WHERE user_id=$1",
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
