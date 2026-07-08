"""guild_treasury CRUD (band 3) — the per-guild server-owned coin pool.

Migration ``0013_treasury.sql`` (shipped migration 092 shape, NAME_STABLE).
Plain CRUD only; the audited contribute/disburse policy is the K7 lane
(sb/domain/treasury/ops.py) and the per-user coin legs route through the
economy sole-writer store — mirrored from the shipped
services/treasury_service.py layering.

bears_value=True (a coin pool) ⇒ REVERSE_IMPORTABLE: the aggregate
absolute-value importer copies post-flip balances back over the frozen OLD
rows by guild_id. DataClass.NONE — the pool row carries no member ids (the
attribution trail is the economy ledger's treasury:* rows).
"""

from __future__ import annotations

from typing import Any

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)
from tools.importer.reverse import register_reverse_importer
from tools.importer.reverse.core import aggregate_upsert_sql

__all__ = [
    "GUILD_TREASURY_STORE",
    "credit_treasury",
    "get_treasury",
    "try_debit_treasury",
]

GUILD_TREASURY_STORE = register_store(StoreSpec(
    table="guild_treasury",
    sole_writer=EngineRef("treasury.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="guild_treasury",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "economy"),
    bears_value=True,
    data_class=DataClass.NONE,
))


@engine("treasury.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/treasury/store.py"


async def get_treasury(guild_id: int, conn: Any = None) -> int:
    """The guild's stored pool balance (0 when no row exists yet)."""
    row = await fetchone(
        "SELECT balance FROM guild_treasury WHERE guild_id=$1",
        (guild_id,), conn=conn)
    return int(row["balance"]) if row else 0


async def credit_treasury(conn: Any, *, guild_id: int, amount: int,
                          updated_at: int) -> int:
    """Add *amount* and return the new pool balance in one statement
    (GREATEST floor upsert — a fresh guild's first contribution creates
    the row; shipped verbatim)."""
    row = await fetchone(
        "INSERT INTO guild_treasury (guild_id, balance, updated_at) "
        "VALUES ($1, GREATEST(0, $2), $3) "
        "ON CONFLICT (guild_id) DO UPDATE SET "
        "balance = GREATEST(0, guild_treasury.balance + $2), "
        "updated_at = $3 RETURNING balance",
        (guild_id, amount, updated_at), conn=conn)
    return int(row["balance"]) if row else 0


async def try_debit_treasury(conn: Any, *, guild_id: int, amount: int,
                             updated_at: int) -> int | None:
    """Conditionally subtract; ``None`` when underfunded — the shipped
    one-statement decide-and-write (never overdraws, no read race)."""
    row = await fetchone(
        "UPDATE guild_treasury "
        "SET balance = guild_treasury.balance - $2, updated_at = $3 "
        "WHERE guild_id=$1 AND balance >= $2 RETURNING balance",
        (guild_id, amount, updated_at), conn=conn)
    return int(row["balance"]) if row else None


# --- S14 reverse importer (AGGREGATE tier) -----------------------------------------

async def _reverse_import_treasury(store, *, old_conn, new_conn,
                                   flip_ts) -> int:
    """Copy post-flip NEW absolute pool balances over the frozen OLD rows,
    upsert-by-guild_id — never per-movement deltas."""
    flip_epoch = int(flip_ts.timestamp())
    rows = await new_conn.fetch(
        "SELECT guild_id, balance, updated_at FROM guild_treasury "
        "WHERE updated_at >= $1", flip_epoch)
    sql = aggregate_upsert_sql("guild_treasury", ("guild_id",),
                               ("balance", "updated_at"))
    for row in rows:
        await old_conn.execute(sql, row["guild_id"], row["balance"],
                               row["updated_at"])
    return len(rows)


def _register_importers() -> None:
    try:
        register_reverse_importer("guild_treasury", _reverse_import_treasury)
    except ValueError:
        pass  # already registered in this process — idempotent re-arm


_register_importers()


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("treasury.store")):
        _engine("treasury.store")(_store_marker)
    _register_importers()
