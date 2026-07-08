"""mod_logs + warnings CRUD (band 2) — asyncpg SQL behind the K3 seam.

Migration ``0010_moderation.sql``. Store specs minted HERE (sole physical
authority, the band-1 settings-store pattern) and imported by the manifest.

Write helpers take an explicit txn ``conn`` and are called ONLY by the K7
moderation-op legs (sb/domain/moderation/ops.py). Reads are plain seam reads.
"""

from __future__ import annotations

import datetime as _dt
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
    "MOD_LOGS_STORE",
    "WARNINGS_STORE",
    "add_warning",
    "clear_warnings",
    "get_mod_logs",
    "get_warnings",
    "log_mod_action",
    "tombstone_subject_rows",
]

#: shipped display token, verbatim (services/moderation_service.py:93)
DEFAULT_REASON = "No reason provided"

# NAME_STABLE: the shipped moderation history imports verbatim at CUT-2 (the
# operator spine's audit-adjacent table — row shapes are the compat surface).
# bears_value=False (history, not balances) => DECLARED_LOSS rollback posture
# (Q3-B pattern); MEMBER_ID => erasure ref REQUIRED (tombstone: the row stays,
# the subject ids go — history counts must survive erasure honestly).
MOD_LOGS_STORE = register_store(StoreSpec(
    table="mod_logs",
    sole_writer=EngineRef("moderation.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="mod_logs",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "logging"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("moderation.tombstone_subject"),
))

WARNINGS_STORE = register_store(StoreSpec(
    table="warnings",
    sole_writer=EngineRef("moderation.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="warnings",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("moderation.clear_subject_warnings"),
))


@engine("moderation.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/moderation/store.py"


# --- writes (K7 legs only — conn REQUIRED) -----------------------------------

async def log_mod_action(conn: Any, *, guild_id: int, action: str,
                         target_id: int, moderator_id: int,
                         reason: str = DEFAULT_REASON,
                         at: _dt.datetime | None = None) -> None:
    ts = at or _dt.datetime.now(tz=_dt.timezone.utc)
    await execute(
        "INSERT INTO mod_logs (timestamp, guild_id, action, target_id, "
        "moderator_id, reason) VALUES ($1, $2, $3, $4, $5, $6)",
        (ts, guild_id, action, target_id, moderator_id, reason), conn=conn)


async def add_warning(conn: Any, *, user_id: int, guild_id: int) -> int:
    row = await fetchone(
        "INSERT INTO warnings (user_id, guild_id, count) VALUES ($1, $2, 1) "
        "ON CONFLICT (user_id, guild_id) "
        "DO UPDATE SET count = warnings.count + 1 RETURNING count",
        (user_id, guild_id), conn=conn)
    return int(row["count"]) if row else 1


async def clear_warnings(conn: Any, *, user_id: int, guild_id: int) -> None:
    await execute("DELETE FROM warnings WHERE user_id=$1 AND guild_id=$2",
                  (user_id, guild_id), conn=conn)


async def tombstone_subject_rows(conn: Any, *, user_id: int) -> int:
    """Privacy erasure body: keep the history rows, drop the subject id
    (tombstone id 0 — counts and actions stay auditable)."""
    tagged = await fetchall(
        "UPDATE mod_logs SET target_id = 0, reason = '<erased>' "
        "WHERE target_id = $1 RETURNING id", (user_id,), conn=conn)
    await execute("UPDATE mod_logs SET moderator_id = 0 WHERE moderator_id = $1",
                  (user_id,), conn=conn)
    return len(tagged)


# --- reads --------------------------------------------------------------------

async def get_warnings(user_id: int, guild_id: int, conn: Any = None) -> int:
    row = await fetchone(
        "SELECT count FROM warnings WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return int(row["count"]) if row else 0


async def get_mod_logs(target_id: int, guild_id: int,
                       limit: int = 10) -> list[dict]:
    return await fetchall(
        "SELECT action, timestamp, moderator_id, reason FROM mod_logs "
        "WHERE target_id=$1 AND guild_id=$2 ORDER BY id DESC LIMIT $3",
        (target_id, guild_id, limit))


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("moderation.store")):
        _engine("moderation.store")(_store_marker)
