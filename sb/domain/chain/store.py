"""chain_channels CRUD (band 6) — the shipped one-row-per-channel shape
(``utils/db/games/chain.py`` / inlined baseline DDL), NAME_STABLE.
Channel-scoped game config + the running chain_count — no member data
lives here (the configured word is operator content), so the store is
DataClass.NONE (config + a non-personal counter) with no erasure body."""

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
    "CHAIN_CHANNELS_STORE",
    "delete_chain_channel",
    "get_all_chain_channels",
    "get_chain_channel",
    "increment_chain_count",
    "set_chain_channel",
    "set_chain_limit",
]

CHAIN_CHANNELS_STORE = register_store(StoreSpec(
    table="chain_channels",
    sole_writer=EngineRef("chain.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="chain_channels",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.NONE,
))


@engine("chain.store")
def _store_marker() -> str:
    return "sb/domain/chain/store.py"


async def get_chain_channel(channel_id: int,
                            conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT channel_id, guild_id, word, word_limit, chain_count "
        "FROM chain_channels WHERE channel_id=$1",
        (channel_id,), conn=conn)
    return dict(row) if row else None


async def get_all_chain_channels(guild_id: int,
                                 conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT channel_id, word, word_limit, chain_count "
        "FROM chain_channels WHERE guild_id=$1 ORDER BY channel_id",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def set_chain_channel(conn: Any, *, channel_id: int,
                            guild_id: int, word: str,
                            limit: int = 0) -> None:
    await execute(
        "INSERT INTO chain_channels (channel_id, guild_id, word, "
        "word_limit) VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (channel_id) DO UPDATE SET guild_id=$2, word=$3, "
        "word_limit=$4",
        (channel_id, guild_id, word, limit), conn=conn)


async def set_chain_limit(conn: Any, *, channel_id: int,
                          limit: int) -> None:
    await execute(
        "UPDATE chain_channels SET word_limit=$2 WHERE channel_id=$1",
        (channel_id, limit), conn=conn)


async def delete_chain_channel(conn: Any, *, channel_id: int) -> None:
    await execute(
        "DELETE FROM chain_channels WHERE channel_id=$1",
        (channel_id,), conn=conn)


async def increment_chain_count(conn: Any, *, channel_id: int) -> int:
    row = await fetchone(
        "UPDATE chain_channels SET chain_count=chain_count+1 "
        "WHERE channel_id=$1 RETURNING chain_count",
        (channel_id,), conn=conn)
    return int(row["chain_count"]) if row else 0


def ensure_refs() -> None:
    from sb.spec.refs import engine as _engine, is_registered

    if not is_registered(EngineRef("chain.store")):
        _engine("chain.store")(_store_marker)
