"""prohibited_words CRUD (band 2) — migration 0011; the shipped shape
verbatim (utils/db/moderation.py word helpers; the cleanup cog is the
consumer). Writes are K7-leg-only (conn required)."""

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

__all__ = ["PROHIBITED_WORDS_STORE", "add_word", "get_words", "remove_word"]

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


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("cleanup.store")):
        _engine("cleanup.store")(_store_marker)
