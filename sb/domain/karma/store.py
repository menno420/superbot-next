"""Karma CRUD (band 4) — asyncpg SQL behind the K3 seam. Migration
``0015_karma.sql``. INV-K: writes are conn-required and called ONLY by
the K7 ``karma.give`` leg (sole-writer discipline).

Both stores are REVERSE_IMPORTABLE (S14): the aggregate copies absolute
(karma_points, received_count, given_count) values back over the old
``karma`` rows (NAME_STABLE shape); the audit log re-inserts by the
ADDITIVE ``mutation_id`` (the economy_audit_log precedent — the CUT-2
alias map adds the column old-side before any rollback window).
"""

from __future__ import annotations

import uuid
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
from tools.importer.reverse import ledger_reinsert_sql, register_reverse_importer
from tools.importer.reverse.core import aggregate_upsert_sql

__all__ = [
    "KARMA_AUDIT_STORE",
    "KARMA_STORE",
    "credit_karma",
    "get_karma",
    "grants_given_since",
    "increment_given",
    "insert_karma_audit",
    "karma_rank",
    "recent_grant_count",
    "top_karma",
]

KARMA_STORE = register_store(StoreSpec(
    table="karma",
    sole_writer=EngineRef("karma.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="karma",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("community", "diagnostics"),
    bears_value=True,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("karma.erase_subject_karma"),
))

# reason is granter free text => MEMBER_PII; erasure = tombstone (rows
# stay so the anti-abuse + INV-K trail keeps adding up; ids -> 0, reason
# scrubbed — the mod_logs/economy_audit precedent).
KARMA_AUDIT_STORE = register_store(StoreSpec(
    table="karma_audit_log",
    sole_writer=EngineRef("karma.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="karma_audit_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("community", "diagnostics"),
    bears_value=True,
    data_class=DataClass.MEMBER_PII,
    erasure_ref=WorkflowRef("karma.tombstone_subject_audit"),
))


@engine("karma.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/karma/store.py"


# --- reads ---------------------------------------------------------------------------

async def get_karma(user_id: int, guild_id: int, conn: Any = None) -> dict:
    """The row or the shipped all-zeros synthesised dict."""
    row = await fetchone(
        "SELECT karma_points, received_count, given_count, last_received "
        "FROM karma WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    if row is None:
        return {"karma_points": 0, "received_count": 0, "given_count": 0,
                "last_received": None}
    return dict(row)


async def top_karma(guild_id: int, limit: int = 10,
                    conn: Any = None) -> list[dict]:
    """Ranked board — oldest last_received breaks ties (shipped)."""
    rows = await fetchall(
        "SELECT user_id, karma_points FROM karma "
        "WHERE guild_id=$1 AND karma_points > 0 "
        "ORDER BY karma_points DESC, last_received ASC "
        "LIMIT $2", (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def karma_rank(user_id: int, guild_id: int,
                     conn: Any = None) -> int | None:
    row = await fetchone(
        "SELECT rank FROM ("
        "    SELECT user_id,"
        "           ROW_NUMBER() OVER ("
        "               ORDER BY karma_points DESC, last_received ASC"
        "           ) AS rank"
        "    FROM karma"
        "    WHERE guild_id=$1 AND karma_points > 0"
        ") ranked WHERE user_id=$2",
        (guild_id, user_id), conn=conn)
    return int(row["rank"]) if row else None


# --- anti-abuse reads (over the audit log; shipped verbatim) ---------------------------

async def recent_grant_count(guild_id: int, from_user: int, to_user: int,
                             since: datetime, conn: Any = None) -> int:
    row = await fetchone(
        "SELECT COUNT(*)::bigint AS n FROM karma_audit_log "
        "WHERE guild_id=$1 AND from_user=$2 AND to_user=$3 "
        "AND occurred_at >= $4",
        (guild_id, from_user, to_user, since), conn=conn)
    return int(row["n"]) if row else 0


async def grants_given_since(guild_id: int, from_user: int, since: datetime,
                             conn: Any = None) -> int:
    row = await fetchone(
        "SELECT COUNT(*)::bigint AS n FROM karma_audit_log "
        "WHERE guild_id=$1 AND from_user=$2 AND occurred_at >= $3",
        (guild_id, from_user, since), conn=conn)
    return int(row["n"]) if row else 0


# --- write primitives (K7 leg only — conn REQUIRED) ------------------------------------

async def credit_karma(conn: Any, *, to_user: int, guild_id: int,
                       amount: int) -> int:
    """Upsert + RETURNING; GREATEST(0, …) floors the total (shipped)."""
    row = await fetchone(
        "INSERT INTO karma "
        "    (user_id, guild_id, karma_points, received_count, last_received) "
        "VALUES ($1, $2, GREATEST(0, $3), 1, NOW()) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "    karma_points   = GREATEST(0, karma.karma_points + $3), "
        "    received_count = karma.received_count + 1, "
        "    last_received  = NOW() "
        "RETURNING karma_points",
        (to_user, guild_id, amount), conn=conn)
    return int(row["karma_points"]) if row else 0


async def increment_given(conn: Any, *, from_user: int,
                          guild_id: int) -> None:
    await execute(
        "INSERT INTO karma (user_id, guild_id, given_count) "
        "VALUES ($1, $2, 1) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "    given_count = karma.given_count + 1",
        (from_user, guild_id), conn=conn)


async def insert_karma_audit(conn: Any, *, guild_id: int, from_user: int,
                             to_user: int, delta: int, source: str,
                             reason: str | None) -> str:
    """Append one immutable row; returns the minted ``mutation_id`` (the
    S14 ledger-reinsert conflict key)."""
    movement_id = str(uuid.uuid4())
    await execute(
        "INSERT INTO karma_audit_log "
        "    (mutation_id, guild_id, from_user, to_user, delta, source, reason) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        (movement_id, guild_id, from_user, to_user, delta, source, reason),
        conn=conn)
    return movement_id


# --- privacy erasure row helpers --------------------------------------------------------

async def erase_subject_karma(conn: Any, *, user_id: int) -> int:
    rows = await fetchall(
        "DELETE FROM karma WHERE user_id=$1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)


async def tombstone_subject_audit(conn: Any, *, user_id: int) -> int:
    """Rows stay (the anti-abuse/INV-K trail must keep adding up);
    subject ids -> 0 and free-text reasons scrub (MEMBER_PII)."""
    tagged = await fetchall(
        "UPDATE karma_audit_log SET to_user = 0, reason = NULL "
        "WHERE to_user = $1 RETURNING id", (user_id,), conn=conn)
    await execute(
        "UPDATE karma_audit_log SET from_user = 0, reason = NULL "
        "WHERE from_user = $1", (user_id,), conn=conn)
    return len(tagged)


# --- S14 reverse importers ---------------------------------------------------------------

_AUDIT_COLUMNS = ("mutation_id", "guild_id", "from_user", "to_user", "delta",
                  "source", "reason", "occurred_at")


async def _reverse_import_audit(store, *, old_conn, new_conn, flip_ts) -> int:
    rows = await new_conn.fetch(
        "SELECT mutation_id, guild_id, from_user, to_user, delta, source, "
        "reason, occurred_at FROM karma_audit_log WHERE occurred_at >= $1",
        flip_ts)
    sql = ledger_reinsert_sql("karma_audit_log", _AUDIT_COLUMNS)
    for row in rows:
        await old_conn.execute(sql, *[row[c] for c in _AUDIT_COLUMNS])
    return len(rows)


async def _reverse_import_karma(store, *, old_conn, new_conn,
                                flip_ts) -> int:
    """AGGREGATE tier: absolute-value upsert by natural key; rows touched
    since the flip move (join with the post-flip audit rows)."""
    rows = await new_conn.fetch(
        "SELECT DISTINCT k.user_id, k.guild_id, k.karma_points, "
        "k.received_count, k.given_count "
        "FROM karma k JOIN karma_audit_log a "
        "ON k.guild_id = a.guild_id "
        "AND (k.user_id = a.to_user OR k.user_id = a.from_user) "
        "WHERE a.occurred_at >= $1", flip_ts)
    sql = aggregate_upsert_sql(
        "karma", ("user_id", "guild_id"),
        ("karma_points", "received_count", "given_count"))
    for row in rows:
        await old_conn.execute(sql, row["user_id"], row["guild_id"],
                               row["karma_points"], row["received_count"],
                               row["given_count"])
    return len(rows)


def _register_importers() -> None:
    try:
        register_reverse_importer("karma_audit_log", _reverse_import_audit)
        register_reverse_importer("karma", _reverse_import_karma)
    except ValueError:
        pass  # already registered in this process — idempotent re-arm


_register_importers()


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("karma.store")):
        _engine("karma.store")(_store_marker)
    _register_importers()
