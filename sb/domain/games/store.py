"""GAMES substrate stores (band 6) — the game_state checkpoint table and the
cross-game game_xp progression track.

Migration ``0019_games.sql`` (shipped migrations 015/018 + 065, NAME_STABLE).

`game_state` is SESSION-class: restart-lossy BY DESIGN (rollback_class
derives COLLAPSE — the S14 short-circuit). It carries NO independent money
truth: escrow/entry rows record the staked amount under the ``bet`` payload
key, but every coin that enters or leaves a wallet is written on the economy
ledger by the owning K7 leg — recovery refunds re-run THROUGH the ledger, so
bears_value=False is honest (the pot is reconstructible from
economy_audit_log's ``*:escrow`` / ``*:entry_fee`` reason rows).

`game_xp` mirrors the xp-band posture: NAME_STABLE AGGREGATE,
bears_value=True ⇒ REVERSE_IMPORTABLE (absolute-value upsert keyed
(user_id, guild_id, game)); MEMBER_ID with a delete-rows erasure body.
"""

from __future__ import annotations

import json
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
from tools.importer.reverse import register_reverse_importer
from tools.importer.reverse.core import aggregate_upsert_sql

__all__ = [
    "GAME_STATE_STORE",
    "GAME_STATE_TTL_HOURS",
    "GAME_XP_STORE",
    "add_game_xp",
    "delete_checkpoint",
    "delete_checkpoint_by_id",
    "erase_subject_game_state",
    "erase_subject_game_xp",
    "fetch_checkpoint",
    "game_xp_rows",
    "list_active",
    "list_stale",
    "lock_rows_for_settlement",
    "top_game_xp",
    "total_game_xp",
    "upsert_checkpoint",
]

GAME_STATE_STORE = register_store(StoreSpec(
    table="game_state",
    sole_writer=EngineRef("games.store"),
    retention="24h GC (session_gc sweep)",
    checkpoint_class=CheckpointClass.SESSION,
    invariant_tag="game_state",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("games.discard_subject_sessions"),
))

GAME_XP_STORE = register_store(StoreSpec(
    table="game_xp",
    sole_writer=EngineRef("games.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="game_xp",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=True,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("games.erase_subject_game_xp"),
))

#: shipped GC horizon — checkpoints older than this are stranded (crash
#: mid-game) and get swept + bet-refunded by the session_gc task.
GAME_STATE_TTL_HOURS = 24


@engine("games.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/games/store.py"


# --- game_state checkpoint CRUD (shipped game_state_service semantics) ------------


def _decode(raw: Any) -> dict:
    if isinstance(raw, str):
        return json.loads(raw)
    return dict(raw or {})


async def upsert_checkpoint(conn: Any, *, guild_id: int, user_id: int,
                            channel_id: int, subsystem: str, state: dict,
                            version: int, now: int) -> None:
    """Atomic upsert — the latest checkpoint wins (shipped verbatim).
    ALWAYS conn-threaded: every write composes inside its owning K7 leg
    (the P0-1 escrow lesson made structural)."""
    await execute(
        "INSERT INTO game_state (guild_id, user_id, channel_id, subsystem, "
        "state, version, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$7) "
        "ON CONFLICT ON CONSTRAINT uq_game_state DO UPDATE SET "
        "state=$5, version=$6, updated_at=$7",
        (guild_id, user_id, channel_id, subsystem, json.dumps(state),
         version, now), conn=conn)


async def fetch_checkpoint(guild_id: int, user_id: int, channel_id: int,
                           subsystem: str, conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT state, version FROM game_state WHERE guild_id=$1 AND "
        "user_id=$2 AND channel_id=$3 AND subsystem=$4",
        (guild_id, user_id, channel_id, subsystem), conn=conn)
    if row is None:
        return None
    return _decode(row["state"])


async def delete_checkpoint(conn: Any, *, guild_id: int, user_id: int,
                            channel_id: int, subsystem: str) -> int:
    result = await execute(
        "DELETE FROM game_state WHERE guild_id=$1 AND user_id=$2 AND "
        "channel_id=$3 AND subsystem=$4",
        (guild_id, user_id, channel_id, subsystem), conn=conn)
    return _rowcount(result)


async def delete_checkpoint_by_id(conn: Any, *, row_id: int) -> int:
    """Precise per-row delete for the GC (the natural key may have been
    reused by a brand-new game — shipped clear_by_id semantics)."""
    result = await execute("DELETE FROM game_state WHERE id=$1",
                           (row_id,), conn=conn)
    return _rowcount(result)


async def lock_rows_for_settlement(conn: Any, *, guild_id: int,
                                   subsystem: str,
                                   channel_id: int | None = None,
                                   user_ids: list[int] | None = None,
                                   ) -> list[dict]:
    """FOR UPDATE lock on the escrow rows about to be settled — the
    row-consumption idempotency guard (shipped verbatim): the first settle
    holds + deletes them; a replay finds them gone and is a no-op."""
    sql = ("SELECT id, guild_id, user_id, channel_id, state FROM game_state "
           "WHERE guild_id=$1 AND subsystem=$2")
    params: list[Any] = [guild_id, subsystem]
    if channel_id is not None:
        params.append(channel_id)
        sql += f" AND channel_id=${len(params)}"
    if user_ids:
        params.append(user_ids)
        sql += f" AND user_id = ANY(${len(params)})"
    sql += " FOR UPDATE"
    rows = await fetchall(sql, tuple(params), conn=conn)
    return [dict(r, state=_decode(r["state"])) for r in rows]


async def list_active(subsystem: str, *, guild_id: int | None = None,
                      conn: Any = None) -> list[dict]:
    sql = ("SELECT id, guild_id, user_id, channel_id, state, version, "
           "updated_at FROM game_state WHERE subsystem=$1")
    params: list[Any] = [subsystem]
    if guild_id is not None:
        params.append(guild_id)
        sql += " AND guild_id=$2"
    rows = await fetchall(sql, tuple(params), conn=conn)
    return [dict(r, state=_decode(r["state"])) for r in rows]


async def list_stale(*, now: int, cutoff_hours: int = GAME_STATE_TTL_HOURS,
                     conn: Any = None) -> list[dict]:
    """Every checkpoint older than *cutoff_hours* — crash-stranded games
    the session_gc sweep refunds (via the ``bet`` convention) and clears."""
    cutoff = now - cutoff_hours * 3600
    rows = await fetchall(
        "SELECT id, guild_id, user_id, channel_id, subsystem, state "
        "FROM game_state WHERE updated_at < $1", (cutoff,), conn=conn)
    return [dict(r, state=_decode(r["state"])) for r in rows]


def _rowcount(result: Any) -> int:
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


# --- game_xp (shipped game_xp_service write shape) ---------------------------------


async def add_game_xp(conn: Any, *, user_id: int, guild_id: int, game: str,
                      amount: int, day: str, day_xp_add: int,
                      now: int) -> int:
    """Add *amount* xp under *game*; the per-day counter resets when *day*
    rolls over (read-compute-write inside the caller's txn — the shipped
    acceptable-slack contract). Returns the new per-game xp total."""
    row = await fetchone(
        "INSERT INTO game_xp (user_id, guild_id, game, xp, day, day_xp, "
        "updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7) "
        "ON CONFLICT (user_id, guild_id, game) DO UPDATE SET "
        "xp = game_xp.xp + $4, "
        "day_xp = CASE WHEN game_xp.day = $5 THEN game_xp.day_xp + $6 "
        "ELSE $6 END, day = $5, updated_at = $7 "
        "RETURNING xp",
        (user_id, guild_id, game, amount, day, day_xp_add, now), conn=conn)
    return int(row["xp"]) if row else 0


async def game_xp_rows(user_id: int, guild_id: int,
                       conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT game, xp, day, day_xp FROM game_xp WHERE user_id=$1 AND "
        "guild_id=$2 ORDER BY xp DESC", (user_id, guild_id), conn=conn)
    return [dict(r) for r in rows]


async def day_xp_for(user_id: int, guild_id: int, game: str, day: str,
                     conn: Any = None) -> int:
    row = await fetchone(
        "SELECT day, day_xp FROM game_xp WHERE user_id=$1 AND guild_id=$2 "
        "AND game=$3", (user_id, guild_id, game), conn=conn)
    if row is None or row["day"] != day:
        return 0
    return int(row["day_xp"])


async def total_game_xp(user_id: int, guild_id: int,
                        conn: Any = None) -> int:
    row = await fetchone(
        "SELECT COALESCE(SUM(xp), 0) AS total FROM game_xp WHERE "
        "user_id=$1 AND guild_id=$2", (user_id, guild_id), conn=conn)
    return int(row["total"]) if row else 0


async def top_game_xp(guild_id: int, *, game: str | None = None,
                      limit: int = 10, conn: Any = None) -> list[dict]:
    """Leaderboard read: per-game rows, or SUM(xp) totals when game=None."""
    if game is None:
        rows = await fetchall(
            "SELECT user_id, SUM(xp) AS xp FROM game_xp WHERE guild_id=$1 "
            "GROUP BY user_id ORDER BY xp DESC LIMIT $2",
            (guild_id, limit), conn=conn)
    else:
        rows = await fetchall(
            "SELECT user_id, xp FROM game_xp WHERE guild_id=$1 AND game=$2 "
            "ORDER BY xp DESC LIMIT $3", (guild_id, game, limit), conn=conn)
    return [dict(r) for r in rows]


# --- erasure bodies (MEMBER_ID) ------------------------------------------------------


async def erase_subject_game_state(conn: Any, *, user_id: int) -> int:
    """Delete the subject's checkpoints. Any still-escrowed stake is
    forfeited-by-erasure — the money trail lives on the economy ledger and
    is tombstoned by the economy erasure body (D-0042)."""
    result = await execute("DELETE FROM game_state WHERE user_id=$1",
                           (user_id,), conn=conn)
    return _rowcount(result)


async def erase_subject_game_xp(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM game_xp WHERE user_id=$1",
                           (user_id,), conn=conn)
    return _rowcount(result)


# --- S14 reverse importer (AGGREGATE tier, game_xp) ---------------------------------


async def _reverse_import_game_xp(store, *, old_conn, new_conn,
                                  flip_ts) -> int:
    """Copy post-flip NEW absolute per-game xp back over the frozen OLD
    rows, upsert by (user_id, guild_id, game) — never deltas."""
    flip_epoch = int(flip_ts.timestamp())
    rows = await new_conn.fetch(
        "SELECT user_id, guild_id, game, xp, updated_at FROM game_xp "
        "WHERE updated_at >= $1", flip_epoch)
    sql = aggregate_upsert_sql("game_xp", ("user_id", "guild_id", "game"),
                               ("xp", "updated_at"))
    for row in rows:
        await old_conn.execute(sql, row["user_id"], row["guild_id"],
                               row["game"], row["xp"], row["updated_at"])
    return len(rows)


def _register_importers() -> None:
    try:
        register_reverse_importer("game_xp", _reverse_import_game_xp)
    except ValueError:
        pass  # already registered in this process — idempotent re-arm


_register_importers()


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("games.store")):
        _engine("games.store")(_store_marker)
    _register_importers()
