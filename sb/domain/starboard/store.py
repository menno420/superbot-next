"""Starboard config CRUD (the `_unmapped` starboard-family re-home) —
asyncpg SQL behind the K3 seam; migration ``0033_starboard.sql`` (the
oracle's disbot/migrations/083_starboard.sql + 084_starboard_pr2.sql
``starboard_settings``/``starboard_ignore_channels`` pair, imported
NAME_STABLE). Sole-writer discipline: mutations happen only in the K7
starboard ops (sb/domain/starboard/ops.py).

The oracle's third table (``starboard_entries`` — one row per source
message that entered the board) is deliberately NOT minted: no golden
touches it; it lands with the reaction-listener slice (the trap-15b
"declare only what the slice fully carries" rule).

Shipped write shapes carried verbatim (disbot/utils/db/starboard.py):
``set_enabled``/``set_self_star`` are pure UPDATEs — a no-op over an
unconfigured guild (goldens/starboard/sweep_starboard_off +
sweep_starboard_selfstar pin exactly that empty delta); the ignore
remove is a bare DELETE (the #193 oracle-wins unconditional-ack class).

Rollback disposition (S14): both tables are guild CONFIG —
bears_value=False, NAME_STABLE, no reverse importers; neither keys on
member ids (DataClass.NONE, no erasure body).
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

__all__ = [
    "STARBOARD_IGNORE_STORE",
    "STARBOARD_SETTINGS_STORE",
    "add_ignore_channel",
    "ensure_refs",
    "get_settings_row",
    "list_ignore_channel_rows",
    "remove_ignore_channel",
    "set_enabled",
    "set_self_star",
    "upsert_settings",
]


def _store(table: str) -> StoreSpec:
    return register_store(StoreSpec(
        table=table,
        sole_writer=EngineRef("starboard.store"),
        retention="permanent",
        checkpoint_class=CheckpointClass.AGGREGATE,
        invariant_tag=table,
        forward_map_kind=ForwardMapKind.NAME_STABLE,
        reader_domains=("diagnostics",),
        bears_value=False,
        data_class=DataClass.NONE,
    ))


STARBOARD_SETTINGS_STORE = _store("starboard_settings")
STARBOARD_IGNORE_STORE = _store("starboard_ignore_channels")


@engine("starboard.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/starboard/store.py"


def ensure_refs() -> None:
    """Re-arm the sole-writer marker after a sanctioned clear_ref_table
    (the #141 doctrine — a manifest re-import re-fires decorators only for
    freshly-imported modules)."""
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("starboard.store")):
        _engine("starboard.store")(_store_marker)


# --- starboard_settings ------------------------------------------------------------

async def get_settings_row(guild_id: int, conn: Any = None) -> dict | None:
    """The shipped ``get_settings`` row read (None until configured)."""
    return await fetchone(
        "SELECT guild_id, channel_id, threshold, emoji, enabled, self_star "
        "FROM starboard_settings WHERE guild_id=$1", (guild_id,), conn=conn)


async def upsert_settings(conn: Any, *, guild_id: int, channel_id: int,
                          threshold: int, emoji: str,
                          self_star: bool) -> None:
    """The shipped ``set_settings`` upsert verbatim (disbot
    utils/db/starboard.py): one row per guild, ``enabled`` forced TRUE on
    every configure (the shipped configure re-enables)."""
    await execute(
        "INSERT INTO starboard_settings "
        "    (guild_id, channel_id, threshold, emoji, enabled, self_star) "
        "VALUES ($1, $2, $3, $4, TRUE, $5) "
        "ON CONFLICT (guild_id) DO UPDATE SET "
        "    channel_id = $2, threshold = $3, emoji = $4, enabled = TRUE, "
        "    self_star = $5",
        (guild_id, channel_id, threshold, emoji, self_star), conn=conn)


async def set_enabled(conn: Any, *, guild_id: int, enabled: bool) -> None:
    """The shipped on/off flip — a PURE UPDATE ("without touching
    channel/threshold/emoji"), a no-op over an unconfigured guild
    (goldens/starboard/sweep_starboard_off pins the empty delta)."""
    await execute(
        "UPDATE starboard_settings SET enabled=$2 WHERE guild_id=$1",
        (guild_id, enabled), conn=conn)


async def set_self_star(conn: Any, *, guild_id: int,
                        self_star: bool) -> None:
    """The shipped self-star toggle — a PURE UPDATE, a no-op over an
    unconfigured guild (goldens/starboard/sweep_starboard_selfstar pins
    the empty delta)."""
    await execute(
        "UPDATE starboard_settings SET self_star=$2 WHERE guild_id=$1",
        (guild_id, self_star), conn=conn)


# --- starboard_ignore_channels ------------------------------------------------------

async def add_ignore_channel(conn: Any, *, guild_id: int,
                             channel_id: int) -> None:
    """Add a channel to the guild's ignore list — the shipped idempotent
    insert (goldens/starboard/sweep_starboard_ignore pins the two-column
    row shape)."""
    await execute(
        "INSERT INTO starboard_ignore_channels (guild_id, channel_id) "
        "VALUES ($1, $2) ON CONFLICT (guild_id, channel_id) DO NOTHING",
        (guild_id, channel_id), conn=conn)


async def remove_ignore_channel(conn: Any, *, guild_id: int,
                                channel_id: int) -> bool:
    """Remove a channel from the ignore list (no-op if absent) — the
    shipped bare DELETE; the caller acks success UNCONDITIONALLY (the
    #193 unsetrole/ticketblacklist-remove oracle-wins precedent:
    goldens/starboard/sweep_starboard_unignore pins the ack over an
    empty table)."""
    rows = await fetchall(
        "DELETE FROM starboard_ignore_channels "
        "WHERE guild_id = $1 AND channel_id = $2 RETURNING guild_id",
        (guild_id, channel_id), conn=conn)
    return bool(rows)


async def list_ignore_channel_rows(guild_id: int, conn: Any = None) -> tuple[int, ...]:
    """The shipped ignore-list read (config panel's ignored-channels
    field + the listener gate that stays with the reaction slice)."""
    rows = await fetchall(
        "SELECT channel_id FROM starboard_ignore_channels "
        "WHERE guild_id=$1 ORDER BY channel_id", (guild_id,))
    return tuple(int(r["channel_id"]) for r in rows or ())
