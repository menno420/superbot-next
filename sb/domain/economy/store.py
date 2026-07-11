"""Economy CRUD (band 3) — asyncpg SQL behind the K3 seam.

Migration ``0012_economy.sql``. Store specs minted HERE (sole physical
authority — the band-1/2 pattern) and imported by the manifest. Every COIN
write is conn-required and called ONLY by the K7 economy/treasury op legs
(the shipped CRIT-9 sole-path discipline, now an AST-fenceable sole-writer);
reads are plain seam reads.

The two value-bearing stores are REVERSE_IMPORTABLE (S14): the ledger
re-inserts by ``mutation_id`` (``ledger_reinsert_sql``), the balance
aggregate copies absolute values back over the old ``xp.coins`` column
(``aggregate_upsert_sql`` — economy_balances is the RENAME extraction of
that column). Their importer bodies register at import so the
check_rollback_disposition both-directions fence sees the covered set.
"""

from __future__ import annotations

import uuid
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
from tools.importer.reverse import ledger_reinsert_sql, register_reverse_importer
from tools.importer.reverse.core import aggregate_upsert_sql

__all__ = [
    "ECONOMY_AUDIT_STORE",
    "ECONOMY_BALANCES_STORE",
    "ECONOMY_TRACK_STORE",
    "INVENTORY_STORE",
    "JOB_PROGRESS_STORE",
    "credit_coins",
    "ensure_and_get_economy",
    "ensure_tracking_row",
    "get_coins",
    "get_inventory",
    "get_job_times",
    "increment_job",
    "insert_economy_audit",
    "set_daily_claim",
    "set_last_worked",
    "try_debit_coins",
    "try_grant_unique_item",
]

# The money aggregate — shipped home was ONE COLUMN (`xp.coins`); the rebuild
# extracts it to its own table => forward_map_kind=RENAME (pure bijection),
# bears_value=True => REVERSE_IMPORTABLE (aggregate absolute-value upsert).
ECONOMY_BALANCES_STORE = register_store(StoreSpec(
    table="economy_balances",
    sole_writer=EngineRef("economy.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="economy_balances",
    forward_map_kind=ForwardMapKind.RENAME,
    reader_domains=("diagnostics", "games", "xp", "community"),  # band 4:
    # the coins rank provider + spotlight totals read the aggregate
    bears_value=True,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("economy.erase_subject_balances"),
))

# The money ledger — the hottest audit table; imports NAME_STABLE at CUT-2
# (band contract), LEDGER tier reverse import by mutation_id.
ECONOMY_AUDIT_STORE = register_store(StoreSpec(
    table="economy_audit_log",
    sole_writer=EngineRef("economy.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="economy_audit_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "treasury"),
    bears_value=True,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("economy.tombstone_subject_audit"),
))

# Daily/work tracking (streak anchors) — game state, not money (Q3-B posture).
ECONOMY_TRACK_STORE = register_store(StoreSpec(
    table="economy",
    sole_writer=EngineRef("economy.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="economy",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("economy.erase_subject_track"),
))

JOB_PROGRESS_STORE = register_store(StoreSpec(
    table="job_progress",
    sole_writer=EngineRef("economy.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="job_progress",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("economy.erase_subject_jobs"),
))

# Item ownership — game state; the MONEY trail of every purchase lives in
# economy_audit_log (REVERSE_IMPORTABLE), so rollback loss here is declared
# and recoverable-by-ledger (D-0031 rationale).
INVENTORY_STORE = register_store(StoreSpec(
    table="inventory",
    sole_writer=EngineRef("economy.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="inventory",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("economy.erase_subject_inventory"),
))


@engine("economy.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/economy/store.py"


# --- coin primitives (K7 legs only — conn REQUIRED on writes) ----------------------

async def get_coins(user_id: int, guild_id: int, conn: Any = None) -> int:
    row = await fetchone(
        "SELECT coins FROM economy_balances WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return int(row["coins"]) if row else 0


async def credit_coins(conn: Any, *, user_id: int, guild_id: int,
                       amount: int) -> int:
    """Add *amount* and return the new balance (GREATEST floor, shipped)."""
    row = await fetchone(
        "INSERT INTO economy_balances (user_id, guild_id, coins) "
        "VALUES ($1, $2, GREATEST(0, $3)) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "coins = GREATEST(0, economy_balances.coins + $3) RETURNING coins",
        (user_id, guild_id, amount), conn=conn)
    return int(row["coins"]) if row else 0


async def try_debit_coins(conn: Any, *, user_id: int, guild_id: int,
                          amount: int) -> int | None:
    """Conditionally subtract; ``None`` when unaffordable — the shipped
    one-statement decide-and-write (no read-then-write race)."""
    row = await fetchone(
        "UPDATE economy_balances SET coins = economy_balances.coins - $3 "
        "WHERE user_id=$1 AND guild_id=$2 AND coins >= $3 RETURNING coins",
        (user_id, guild_id, amount), conn=conn)
    return int(row["coins"]) if row else None


async def insert_economy_audit(conn: Any, *, guild_id: int, user_id: int,
                               actor_id: int | None, delta: int,
                               new_balance: int, reason: str) -> str:
    """Append one ledger row; returns the minted movement ``mutation_id``
    (the S14 ledger-reinsert conflict key)."""
    movement_id = str(uuid.uuid4())
    await execute(
        "INSERT INTO economy_audit_log "
        "(mutation_id, guild_id, user_id, actor_id, delta, new_balance, reason) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        (movement_id, guild_id, user_id, actor_id, delta, new_balance, reason),
        conn=conn)
    return movement_id


# --- daily/work tracking ------------------------------------------------------------

async def ensure_and_get_economy(conn: Any, *, user_id: int,
                                 guild_id: int) -> dict:
    """Ensure the tracking row exists, then return it (shipped name: the
    write is in the name). Inside a K7 txn the SELECT takes a row lock so
    concurrent claims serialize (NATURAL_KEY posture)."""
    await execute(
        "INSERT INTO economy (user_id, guild_id) VALUES ($1, $2) "
        "ON CONFLICT DO NOTHING", (user_id, guild_id), conn=conn)
    row = await fetchone(
        "SELECT * FROM economy WHERE user_id=$1 AND guild_id=$2 FOR UPDATE",
        (user_id, guild_id), conn=conn)
    return dict(row) if row else {"user_id": user_id, "guild_id": guild_id,
                                  "last_daily": 0, "daily_streak": 0,
                                  "daily_count": 0, "last_worked": 0}


async def ensure_tracking_row(user_id: int, guild_id: int) -> dict:
    """The shipped ``ensure_and_get_economy`` READ SURFACE (utils/db/
    economy.py): NOT a pure read — the name says so — a missing row is
    INSERTed (column defaults) before the SELECT, exactly what the old
    bot's hub/work opens did outside any transaction (the goldens pin the
    zero-row db_delta on !economymenu / /economy / !work). No lock, no
    txn: the K7 legs keep their own in-txn ``ensure_and_get_economy``."""
    await execute(
        "INSERT INTO economy (user_id, guild_id) VALUES ($1, $2) "
        "ON CONFLICT DO NOTHING", (user_id, guild_id))
    return await read_economy(user_id, guild_id)


async def read_economy(user_id: int, guild_id: int) -> dict:
    """Plain read (no lock, no insert) for panels/handlers."""
    row = await fetchone(
        "SELECT * FROM economy WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id))
    return dict(row) if row else {"user_id": user_id, "guild_id": guild_id,
                                  "last_daily": 0, "daily_streak": 0,
                                  "daily_count": 0, "last_worked": 0}


async def set_daily_claim(conn: Any, *, user_id: int, guild_id: int,
                          last_daily: int, daily_streak: int,
                          daily_count: int) -> None:
    await execute(
        "UPDATE economy SET last_daily=$1, daily_streak=$2, daily_count=$3 "
        "WHERE user_id=$4 AND guild_id=$5",
        (last_daily, daily_streak, daily_count, user_id, guild_id), conn=conn)


async def set_last_worked(conn: Any, *, user_id: int, guild_id: int,
                          ts: int) -> None:
    await execute(
        "UPDATE economy SET last_worked=$1 WHERE user_id=$2 AND guild_id=$3",
        (ts, user_id, guild_id), conn=conn)


# --- job progress -------------------------------------------------------------------

async def get_job_times(user_id: int, guild_id: int, job_name: str,
                        conn: Any = None) -> int:
    row = await fetchone(
        "SELECT times_worked FROM job_progress "
        "WHERE user_id=$1 AND guild_id=$2 AND job_name=$3",
        (user_id, guild_id, job_name), conn=conn)
    return int(row["times_worked"]) if row else 0


async def increment_job(conn: Any, *, user_id: int, guild_id: int,
                        job_name: str) -> int:
    row = await fetchone(
        "INSERT INTO job_progress (user_id, guild_id, job_name, times_worked) "
        "VALUES ($1, $2, $3, 1) "
        "ON CONFLICT (user_id, guild_id, job_name) "
        "DO UPDATE SET times_worked = job_progress.times_worked + 1 "
        "RETURNING times_worked",
        (user_id, guild_id, job_name), conn=conn)
    return int(row["times_worked"]) if row else 1


# --- inventory ----------------------------------------------------------------------

async def get_inventory(user_id: int, guild_id: int,
                        conn: Any = None) -> dict[str, int]:
    rows = await fetchall(
        "SELECT item_name, quantity FROM inventory "
        "WHERE user_id=$1 AND guild_id=$2", (user_id, guild_id), conn=conn)
    return {r["item_name"]: int(r["quantity"]) for r in rows}


async def try_grant_unique_item(conn: Any, *, user_id: int, guild_id: int,
                                item_name: str) -> bool:
    """Grant one unit iff not already owned — the shipped one-statement
    conditional upsert that closed the double-click double-charge race."""
    row = await fetchone(
        "INSERT INTO inventory (user_id, guild_id, item_name, quantity) "
        "VALUES ($1, $2, $3, 1) "
        "ON CONFLICT (user_id, guild_id, item_name) "
        "DO UPDATE SET quantity = inventory.quantity + 1 "
        "  WHERE inventory.quantity <= 0 "
        "RETURNING item_name",
        (user_id, guild_id, item_name), conn=conn)
    return row is not None


async def has_item(user_id: int, guild_id: int, item_name: str,
                   conn: Any = None) -> bool:
    row = await fetchone(
        "SELECT quantity FROM inventory "
        "WHERE user_id=$1 AND guild_id=$2 AND item_name=$3",
        (user_id, guild_id, item_name), conn=conn)
    return bool(row and int(row["quantity"]) > 0)


# --- ledger aggregation reads (economy_flow_service.py verbatim SQL) ----------------

async def economy_flow_by_reason(guild_id: int, *, since=None,
                                 conn: Any = None) -> list[tuple[str, int, int]]:
    """Per-reason (reason, net_delta, movement_count) over the ledger."""
    where = "WHERE guild_id=$1" + ("" if since is None else " AND occurred_at >= $2")
    params = (guild_id,) if since is None else (guild_id, since)
    rows = await fetchall(
        "SELECT COALESCE(reason, '(unspecified)') AS reason, "
        "SUM(delta)::bigint AS net, COUNT(*)::bigint AS n "
        f"FROM economy_audit_log {where} "
        "GROUP BY COALESCE(reason, '(unspecified)') ORDER BY net DESC",
        params, conn=conn)
    return [(r["reason"], int(r["net"]), int(r["n"])) for r in rows]


# --- privacy erasure row helpers (the store-declared refs' bodies call these) -------

async def erase_subject_balances(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM economy_balances WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


async def tombstone_subject_audit(conn: Any, *, user_id: int) -> int:
    """Ledger tombstone: rows stay (the money trail must add up), subject
    ids go to 0 — the mod_logs precedent."""
    tagged = await fetchall(
        "UPDATE economy_audit_log SET user_id = 0 "
        "WHERE user_id = $1 RETURNING id", (user_id,), conn=conn)
    await execute(
        "UPDATE economy_audit_log SET actor_id = 0 WHERE actor_id = $1",
        (user_id,), conn=conn)
    return len(tagged)


async def erase_subject_track(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM economy WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


async def erase_subject_jobs(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM job_progress WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


async def erase_subject_inventory(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM inventory WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


# --- S14 reverse importers (the REVERSE_IMPORTABLE coverage bodies) -----------------

_AUDIT_COLUMNS = ("mutation_id", "guild_id", "user_id", "actor_id", "delta",
                  "new_balance", "reason", "occurred_at")


async def _reverse_import_audit(store, *, old_conn, new_conn, flip_ts) -> int:
    """LEDGER tier: re-insert every post-flip ledger row into the OLD DB by
    mutation_id (idempotent — ON CONFLICT DO NOTHING). The CUT-2 alias map
    adds the mutation_id column+unique index to the old table before any
    rollback window opens (rollback-playbook re-bind note)."""
    rows = await new_conn.fetch(
        "SELECT mutation_id, guild_id, user_id, actor_id, delta, new_balance, "
        "reason, occurred_at FROM economy_audit_log WHERE occurred_at >= $1",
        flip_ts)
    sql = ledger_reinsert_sql("economy_audit_log", _AUDIT_COLUMNS)
    for row in rows:
        await old_conn.execute(sql, *[row[c] for c in _AUDIT_COLUMNS])
    return len(rows)


async def _reverse_import_balances(store, *, old_conn, new_conn,
                                   flip_ts) -> int:
    """AGGREGATE tier: copy the NEW absolute balance over the frozen OLD
    `xp.coins` value (the RENAME inverse), upsert-by-natural-key — never
    per-mutation deltas. Only balances touched since the flip move."""
    rows = await new_conn.fetch(
        "SELECT DISTINCT b.user_id, b.guild_id, b.coins "
        "FROM economy_balances b JOIN economy_audit_log a "
        "ON a.user_id = b.user_id AND a.guild_id = b.guild_id "
        "WHERE a.occurred_at >= $1", flip_ts)
    sql = aggregate_upsert_sql("xp", ("user_id", "guild_id"), ("coins",))
    for row in rows:
        await old_conn.execute(sql, row["user_id"], row["guild_id"], row["coins"])
    return len(rows)


def _register_importers() -> None:
    try:
        register_reverse_importer("economy_audit_log", _reverse_import_audit)
        register_reverse_importer("economy_balances", _reverse_import_balances)
    except ValueError:
        pass  # already registered in this process — idempotent re-arm


_register_importers()


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("economy.store")):
        _engine("economy.store")(_store_marker)
    _register_importers()
