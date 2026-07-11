"""ai_review_log + ai_answer_presets CRUD (band 7) — the shipped
migrations 100/102 shapes (NAME_STABLE). Both stores carry member ids
and redacted member-authored text → MEMBER_PII; erasure = delete review
rows for the subject, detach preset authorship."""

from __future__ import annotations

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
    "AI_ANSWER_PRESETS_STORE",
    "AI_REVIEW_CHANNEL_KEY",
    "AI_REVIEW_LOG_STORE",
    "count_unreviewed",
    "erase_subject",
    "export_entries",
    "get_entry",
    "get_preset",
    "get_review_channel_value",
    "insert_entry",
    "list_presets",
    "lookup_preset",
    "mark_reviewed",
    "query_entries",
    "remove_preset",
    "upsert_preset",
]

AI_REVIEW_LOG_STORE = register_store(StoreSpec(
    table="ai_review_log",
    sole_writer=EngineRef("ai.store"),
    retention="90d",
    checkpoint_class=CheckpointClass.SESSION,
    invariant_tag="ai_review_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_PII,
    erasure_ref=WorkflowRef("ai.scrub_review_subject"),
))

AI_ANSWER_PRESETS_STORE = register_store(StoreSpec(
    table="ai_answer_presets",
    sole_writer=EngineRef("ai.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="ai_answer_presets",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("ai.scrub_review_subject"),
))


@engine("ai.store")
def _store_marker() -> str:
    return "sb/domain/ai/store.py"


# --- review log ---------------------------------------------------------------------


async def insert_entry(conn: Any, *, guild_id: int, channel_id: int,
                       user_id: int, kind: str, reason_code: str | None,
                       task: str | None, route: str | None,
                       question: str | None, answer: str | None,
                       correction: str | None = None,
                       corrected_by: int | None = None,
                       message_id: int | None = None,
                       reply_message_id: int | None = None,
                       provider: str | None = None,
                       model: str | None = None) -> int:
    row = await fetchone(
        "INSERT INTO ai_review_log (guild_id, channel_id, user_id, "
        "message_id, reply_message_id, kind, reason_code, task, route, "
        "question, answer, correction, corrected_by, provider, model, "
        "expires_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,"
        "$14,$15, NOW() + INTERVAL '90 days') RETURNING id",
        (guild_id, channel_id, user_id, message_id, reply_message_id,
         kind, reason_code, task, route, question, answer, correction,
         corrected_by, provider, model), conn=conn)
    return int(row["id"])


async def query_entries(guild_id: int, *, kind: str | None = None,
                        unreviewed_only: bool = False, limit: int = 10,
                        conn: Any = None) -> list[dict]:
    """Recent entries, newest first (shipped utils/db/ai_review.py
    query_review_entries: ORDER BY created_at DESC)."""
    clauses = ["guild_id=$1"]
    params: list[Any] = [guild_id]
    if kind:
        params.append(kind)
        clauses.append(f"kind=${len(params)}")
    if unreviewed_only:
        clauses.append("reviewed=FALSE")
    params.append(max(1, min(int(limit), 100)))
    rows = await fetchall(
        f"SELECT * FROM ai_review_log WHERE {' AND '.join(clauses)} "  # noqa: S608
        f"ORDER BY created_at DESC LIMIT ${len(params)}",
        tuple(params), conn=conn)
    return [dict(r) for r in rows]


async def export_entries(guild_id: int, *, kind: str | None = None,
                         include_reviewed: bool = True, limit: int = 1000,
                         conn: Any = None) -> list[dict]:
    """The operator-export read (shipped export_review_entries verbatim):
    triage-relevant columns only, oldest-first so the dump reads
    chronologically; ``id`` included so entries stay resolvable."""
    clauses = ["guild_id=$1"]
    params: list[Any] = [guild_id]
    if kind:
        params.append(kind)
        clauses.append(f"kind=${len(params)}")
    if not include_reviewed:
        clauses.append("reviewed=FALSE")
    params.append(max(1, min(int(limit), 5000)))
    rows = await fetchall(
        "SELECT id, created_at, kind, reason_code, task, route, question, "
        "answer, correction, provider, model, reviewed FROM ai_review_log "
        f"WHERE {' AND '.join(clauses)} "  # noqa: S608
        f"ORDER BY created_at ASC LIMIT ${len(params)}",
        tuple(params), conn=conn)
    return [dict(r) for r in rows]


async def get_entry(guild_id: int, entry_id: int,
                    conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT * FROM ai_review_log WHERE guild_id=$1 AND id=$2",
        (guild_id, entry_id), conn=conn)
    return dict(row) if row else None


async def mark_reviewed(conn: Any, *, guild_id: int, entry_id: int) -> bool:
    result = await execute(
        "UPDATE ai_review_log SET reviewed=TRUE "
        "WHERE guild_id=$1 AND id=$2",
        (guild_id, entry_id), conn=conn)
    return "1" in str(result)


async def count_unreviewed(guild_id: int, *, kind: str | None = None,
                           conn: Any = None) -> int:
    """Unreviewed count, optionally by kind (the shipped per-kind reads
    behind the bare ``!aireview`` status embed)."""
    if kind:
        row = await fetchone(
            "SELECT COUNT(*) AS n FROM ai_review_log "
            "WHERE guild_id=$1 AND reviewed=FALSE AND kind=$2",
            (guild_id, kind), conn=conn)
    else:
        row = await fetchone(
            "SELECT COUNT(*) AS n FROM ai_review_log "
            "WHERE guild_id=$1 AND reviewed=FALSE",
            (guild_id,), conn=conn)
    return int(row["n"]) if row else 0


# --- presets --------------------------------------------------------------------------


async def upsert_preset(conn: Any, *, guild_id: int, question_key: str,
                        question: str, answer: str, task: str | None,
                        source: str | None, created_by: int | None) -> int:
    row = await fetchone(
        "INSERT INTO ai_answer_presets (guild_id, question_key, question, "
        "answer, task, source, created_by) VALUES ($1,$2,$3,$4,$5,$6,$7) "
        "ON CONFLICT (guild_id, question_key) DO UPDATE SET "
        "answer=EXCLUDED.answer, question=EXCLUDED.question, "
        "task=EXCLUDED.task, source=EXCLUDED.source, enabled=TRUE, "
        "updated_at=NOW() RETURNING id",
        (guild_id, question_key, question, answer, task, source,
         created_by), conn=conn)
    return int(row["id"])


async def remove_preset(conn: Any, *, guild_id: int,
                        preset_id: int) -> bool:
    """Delete one preset BY ID (the shipped ``!aireview preset remove
    <id>`` semantics — utils/db/ai_presets.delete)."""
    result = await execute(
        "DELETE FROM ai_answer_presets WHERE guild_id=$1 AND id=$2",
        (guild_id, preset_id), conn=conn)
    return "1" in str(result)


async def get_preset(guild_id: int, preset_id: int,
                     conn: Any = None) -> dict | None:
    """One full preset row by id (shipped get_by_id), or None."""
    row = await fetchone(
        "SELECT * FROM ai_answer_presets WHERE guild_id=$1 AND id=$2",
        (guild_id, preset_id), conn=conn)
    return dict(row) if row else None


async def lookup_preset(guild_id: int, question_key: str,
                        conn: Any = None) -> str | None:
    row = await fetchone(
        "SELECT answer FROM ai_answer_presets "
        "WHERE guild_id=$1 AND question_key=$2 AND enabled=TRUE",
        (guild_id, question_key), conn=conn)
    return str(row["answer"]) if row else None


async def list_presets(guild_id: int, *, limit: int = 20,
                       conn: Any = None) -> list[dict]:
    """A guild's presets, newest first, DISABLED ROWS INCLUDED (the
    shipped list_for_guild — the ``!aireview preset list`` embed marks
    disabled rows instead of hiding them)."""
    rows = await fetchall(
        "SELECT id, question_key, question, answer, task, source, enabled, "
        "created_by, created_at, updated_at FROM ai_answer_presets "
        "WHERE guild_id=$1 ORDER BY created_at DESC LIMIT $2",
        (guild_id, max(1, min(int(limit), 100))), conn=conn)
    return [dict(r) for r in rows]


# --- review-channel pointer (shipped legacy-KV read) ------------------------------------

#: the shipped utils/settings_keys/ai.py AI_REVIEW_CHANNEL key string,
#: verbatim (sb/domain/settings/keys.py carries the vocabulary).
AI_REVIEW_CHANNEL_KEY = "ai_review_channel"


async def get_review_channel_value(guild_id: int,
                                   conn: Any = None) -> str | None:
    """READ-ONLY over the shipped legacy-KV ``guild_settings`` table — the
    review-feed channel pointer the shipped ``resolve_settings_channel``
    read (goldens/ai/sweep_aireview_off pins the row's write home; the
    write is the audited ``ai.set_review_channel`` op leg, the
    btd6.set_announce_channel precedent)."""
    row = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id=$1 AND key=$2",
        (guild_id, AI_REVIEW_CHANNEL_KEY), conn=conn)
    return None if row is None else str(row["value"])


# --- erasure ---------------------------------------------------------------------------


async def erase_subject(conn: Any, *, user_id: int) -> int:
    """Delete the subject's review rows (asker or corrector — the rows
    carry their redacted text) and detach preset authorship."""
    touched = 0
    result = await execute(
        "DELETE FROM ai_review_log WHERE user_id=$1 OR corrected_by=$1",
        (user_id,), conn=conn)
    digits = "".join(ch for ch in str(result) if ch.isdigit())
    touched += int(digits or 0)
    result = await execute(
        "UPDATE ai_answer_presets SET created_by=NULL WHERE created_by=$1",
        (user_id,), conn=conn)
    digits = "".join(ch for ch in str(result) if ch.isdigit())
    touched += int(digits or 0)
    return touched


def ensure_refs() -> None:
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("ai.store")):
        engine("ai.store")(_store_marker)
