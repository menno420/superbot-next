"""platform_migration_checkpoints CRUD (diagnostic flip) — the shipped
generic logical-migration checkpoint table (old repo migration 026,
imported NAME_STABLE by migrations/0029). Operational bookkeeping only —
no member data (guild_id scopes the checkpoint; summary_json carries
binding/config KEY names, never user content), so DataClass.NONE with no
erasure body. Sole consumer today: the ``!platform backfill`` dry run
(goldens/diagnostic/sweep_platform_backfill pins the row bytes)."""

from __future__ import annotations

from typing import Any

from sb.kernel.db.pool import execute, fetchall
from sb.spec.refs import EngineRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "PLATFORM_MIGRATION_CHECKPOINTS_STORE",
    "insert_checkpoint",
    "list_checkpoints",
]

PLATFORM_MIGRATION_CHECKPOINTS_STORE = register_store(StoreSpec(
    table="platform_migration_checkpoints",
    sole_writer=EngineRef("diagnostic.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="platform_migration_checkpoints",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.NONE,
))


@engine("diagnostic.store")
def _store_marker() -> str:
    return "sb/domain/diagnostic/store.py"


def ensure_refs() -> None:
    from sb.spec.refs import EngineRef, engine as _engine, is_registered

    if not is_registered(EngineRef("diagnostic.store")):
        _engine("diagnostic.store")(_store_marker)


async def insert_checkpoint(conn: Any, *, name: str, guild_id: int,
                            status: str, summary_json: str) -> None:
    """One checkpoint row (started_at = the DB clock, completed_at NULL —
    the shipped dry-run shape; version defaults 1)."""
    await execute(
        "INSERT INTO platform_migration_checkpoints"
        " (name, guild_id, status, summary_json)"
        " VALUES ($1, $2, $3, $4::jsonb)",
        (name, guild_id, status, summary_json),
        conn=conn)


async def list_checkpoints(guild_id: int, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT id, name, guild_id, status, version, started_at,"
        " completed_at FROM platform_migration_checkpoints"
        " WHERE guild_id = $1 ORDER BY id",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]
