"""XP CRUD (band 4) — asyncpg SQL behind the K3 seam. Migration
``0014_xp.sql``.

The shipped ``xp`` table carried a ``coins`` column; band 3 EXTRACTED it
into ``economy_balances`` (RENAME bijection, D-0031). This store is the
COMPLEMENT of that split: table name stays ``xp``, columns are the
progression set only (xp/level/messages/last_xp) — forward_map_kind=
RENAME (bijective column subset of the shipped table), and the S14
reverse importer copies absolute (xp, level, messages) values back over
the old ``xp`` rows (the same physical table band 3's balances importer
targets, different columns). ``xp.reset`` row deletions inside a rollback
window are DECLARED LOSS (a deleted row has no absolute value to copy
back) — recorded in the M1 loss manifest by the driver.

INV-G: writes are conn-required and called ONLY by the K7 xp op legs
(sole-writer discipline, the CRIT-9 analog for progression).
"""

from __future__ import annotations

from typing import Any

from sb.domain.xp.levels import level_progress
from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef, engine
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
    "XP_STORE",
    "add_xp",
    "all_xp_ordered",
    "delete_xp",
    "get_guild_xp_totals",
    "get_xp",
    "set_imported_xp",
    "top_xp",
]

XP_STORE = register_store(StoreSpec(
    table="xp",
    sole_writer=EngineRef("xp.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="xp",
    forward_map_kind=ForwardMapKind.RENAME,
    reader_domains=("economy", "community", "diagnostics"),
    bears_value=True,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("xp.erase_subject_xp"),
))


@engine("xp.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/xp/store.py"


# --- reads ---------------------------------------------------------------------------

async def get_xp(user_id: int, guild_id: int, conn: Any = None) -> dict:
    """The row or the shipped all-zeros synthesised dict (get_xp verbatim;
    ``messages == 0`` distinguishes the sentinel from any real row)."""
    row = await fetchone(
        "SELECT user_id, guild_id, xp, level, messages, last_xp "
        "FROM xp WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return dict(row) if row else {"user_id": user_id, "guild_id": guild_id,
                                  "xp": 0, "level": 0, "messages": 0,
                                  "last_xp": 0}


async def top_xp(guild_id: int, limit: int = 10,
                 conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, xp, level FROM xp WHERE guild_id=$1 "
        "ORDER BY xp DESC LIMIT $2", (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def all_xp_ordered(guild_id: int, conn: Any = None) -> list[dict]:
    """Full ordering for member_rank (shipped provider scan shape)."""
    rows = await fetchall(
        "SELECT user_id, xp, level FROM xp WHERE guild_id=$1 "
        "ORDER BY xp DESC", (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def get_guild_xp_totals(guild_id: int, conn: Any = None) -> int:
    """Guild-wide XP sum (the spotlight overview; the shipped twin summed
    coins too — coins now live in economy_balances, band 3)."""
    row = await fetchone(
        "SELECT COALESCE(SUM(xp), 0)::bigint AS total_xp "
        "FROM xp WHERE guild_id=$1", (guild_id,), conn=conn)
    return int(row["total_xp"]) if row else 0


# --- writes (K7 legs only — conn REQUIRED) --------------------------------------------

async def add_xp(conn: Any, *, user_id: int, guild_id: int, amount: int,
                 now: int) -> tuple[int, int, bool]:
    """Atomic XP increment — shipped upsert + monotonic level advance
    verbatim (level only ever raises; the conditional UPDATE closes the
    concurrent-award regression race)."""
    row = await fetchone(
        "INSERT INTO xp (user_id, guild_id, xp, level, messages, last_xp) "
        "VALUES ($1, $2, $3, 0, 1, $4) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "    xp       = xp.xp + $3, "
        "    messages = xp.messages + 1, "
        "    last_xp  = $4 "
        "RETURNING xp, level",
        (user_id, guild_id, amount, now), conn=conn)
    new_xp = int(row["xp"])
    old_level = int(row["level"])
    new_level, _, _ = level_progress(new_xp)
    leveled_up = new_level > old_level
    if leveled_up:
        await execute(
            "UPDATE xp SET level=$3 "
            "WHERE user_id=$1 AND guild_id=$2 AND level < $3",
            (user_id, guild_id, new_level), conn=conn)
    return new_xp, new_level, leveled_up


async def set_imported_xp(conn: Any, *, user_id: int, guild_id: int,
                          xp: int, level: int,
                          now: int) -> tuple[int, int, bool]:
    """Raise-only absolute set for bot-to-bot migration (shipped verbatim:
    GREATEST merge, level follows the larger total, idempotent re-runs;
    messages stays 0 on insert — an imported member has not messaged)."""
    row = await fetchone(
        "WITH prev AS ("
        "    SELECT xp AS old_xp FROM xp WHERE user_id=$1 AND guild_id=$2"
        ") "
        "INSERT INTO xp (user_id, guild_id, xp, level, messages, last_xp) "
        "VALUES ($1, $2, $3, $4, 0, $5) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "    xp    = GREATEST(xp.xp, EXCLUDED.xp), "
        "    level = CASE WHEN EXCLUDED.xp > xp.xp "
        "                 THEN EXCLUDED.level ELSE xp.level END "
        "RETURNING xp AS new_xp, level AS new_level, "
        "          COALESCE((SELECT old_xp FROM prev), -1) AS old_xp",
        (user_id, guild_id, xp, level, now), conn=conn)
    new_xp = int(row["new_xp"])
    new_level = int(row["new_level"])
    old_xp = int(row["old_xp"])
    return new_xp, new_level, new_xp > old_xp


async def delete_xp(conn: Any, *, user_id: int, guild_id: int) -> int:
    """Remove the row entirely (xp.reset's leg; shipped delete_xp)."""
    rows = await fetchall(
        "DELETE FROM xp WHERE user_id=$1 AND guild_id=$2 RETURNING user_id",
        (user_id, guild_id), conn=conn)
    return len(rows)


# --- privacy erasure row helper -------------------------------------------------------

async def erase_subject_xp(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM xp WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


# --- S14 reverse importer (aggregate tier) --------------------------------------------

async def _reverse_import_xp(store, *, old_conn, new_conn, flip_ts) -> int:
    """AGGREGATE tier: copy absolute (xp, level, messages) back over the
    old ``xp`` rows (the RENAME inverse — same physical table band 3's
    balances importer writes ``coins`` into). Rows touched since the flip
    move (``last_xp`` is the unix-epoch touch stamp); post-flip resets
    (deleted rows) are DECLARED LOSS in the M1 manifest."""
    flip_epoch = int(flip_ts.timestamp())
    rows = await new_conn.fetch(
        "SELECT user_id, guild_id, xp, level, messages FROM xp "
        "WHERE last_xp >= $1", flip_epoch)
    sql = aggregate_upsert_sql("xp", ("user_id", "guild_id"),
                               ("xp", "level", "messages"))
    for row in rows:
        await old_conn.execute(sql, row["user_id"], row["guild_id"],
                               row["xp"], row["level"], row["messages"])
    return len(rows)


def _register_importers() -> None:
    try:
        register_reverse_importer("xp", _reverse_import_xp)
    except ValueError:
        pass  # already registered in this process — idempotent re-arm


_register_importers()


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("xp.store")):
        _engine("xp.store")(_store_marker)
    _register_importers()
