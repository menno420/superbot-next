"""prohibited_words + wordfilter_config CRUD (band 2) — migrations 0011 /
0053; the shipped shapes verbatim (utils/db/moderation.py word helpers +
the migration-097 strict-flag pair; the cleanup cog is the consumer).
Writes are K7-leg-only (conn required)."""

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
    "PROHIBITED_WORDS_STORE",
    "WORDFILTER_CONFIG_STORE",
    "add_word",
    "get_wordfilter_strict",
    "get_words",
    "remove_word",
    "set_wordfilter_strict",
]

PROHIBITED_WORDS_STORE = register_store(StoreSpec(
    table="prohibited_words",
    sole_writer=EngineRef("cleanup.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="prohibited_words",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("automod", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,      # guild config words, no member data
))


WORDFILTER_CONFIG_STORE = register_store(StoreSpec(
    table="wordfilter_config",
    sole_writer=EngineRef("cleanup.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="wordfilter_config",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("automod", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,      # per-guild bool flag, no member data
))


@engine("cleanup.store")
def _store_marker() -> str:
    return "sb/domain/cleanup/store.py"


async def add_word(conn: Any, *, guild_id: int, word: str) -> bool:
    result = await execute(
        "INSERT INTO prohibited_words (guild_id, word) VALUES ($1, $2) "
        "ON CONFLICT DO NOTHING", (guild_id, word.lower().strip()), conn=conn)
    return str(result).endswith("1")


async def remove_word(conn: Any, *, guild_id: int, word: str) -> bool:
    result = await execute(
        "DELETE FROM prohibited_words WHERE guild_id=$1 AND word=$2",
        (guild_id, word.lower().strip()), conn=conn)
    return str(result).endswith("1")


async def get_words(guild_id: int) -> list[str]:
    rows = await fetchall(
        "SELECT word FROM prohibited_words WHERE guild_id=$1 ORDER BY word",
        (guild_id,))
    return [r["word"] for r in rows]


async def get_wordfilter_strict(guild_id: int, conn: Any = None) -> bool:
    """True when obfuscation-resistant (anti-evasion) matching is enabled —
    the shipped read verbatim (utils/db/moderation.py get_wordfilter_strict:
    default False on no row, so a guild that never opts in behaves exactly
    as before)."""
    row = await fetchone(
        "SELECT strict FROM wordfilter_config WHERE guild_id=$1",
        (guild_id,), conn=conn)
    return bool(row["strict"]) if row else False


async def set_wordfilter_strict(conn: Any, *, guild_id: int,
                                strict: bool) -> None:
    """The shipped upsert verbatim (set_wordfilter_strict) — K7-leg-only."""
    await execute(
        "INSERT INTO wordfilter_config (guild_id, strict) VALUES ($1, $2) "
        "ON CONFLICT (guild_id) DO UPDATE SET strict=EXCLUDED.strict",
        (guild_id, strict), conn=conn)


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("cleanup.store")):
        _engine("cleanup.store")(_store_marker)
