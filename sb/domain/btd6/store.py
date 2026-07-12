"""btd6_strategies CRUD (band 7) — the shipped strategy-memory store
(migration 041 shape, NAME_STABLE) focused to the ported flow: guild
submissions, review transitions, published rows, and the submitter
identity-erasure body (``present → anonymized``) — plus the
``btd6_data_blobs`` deterministic-data blob store (oracle migration 054,
NAME_STABLE): the ``!btd6 ops seed-data`` terminal's write target
(upsert-by-name, sha256 over the canonical JSON — the shipped
``utils/db/btd6_data.upsert_blob`` bytes).

Shipped ``btd6_strategy_audit`` side table FOLDS into the K7 central
audit lane (one-write discipline — every transition runs through an
audited op; D-0046). The live ``btd6_facts`` / source-registry /
ingestion stores ride the named ingestion successor port."""

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

__all__ = [
    "BTD6_DATA_BLOBS_STORE",
    "BTD6_STRATEGIES_STORE",
    "anonymize_submitter",
    "count_data_blobs",
    "get_data_blob_row",
    "get_strategy",
    "insert_strategy",
    "list_strategies",
    "set_review",
    "upsert_data_blob",
]

_MAX_LIMIT = 25

BTD6_STRATEGIES_STORE = register_store(StoreSpec(
    table="btd6_strategies",
    sole_writer=EngineRef("btd6.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="btd6_strategies",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "ai"),
    bears_value=False,
    data_class=DataClass.MEMBER_PII,
    erasure_ref=WorkflowRef("btd6.scrub_strategy_submitter"),
))


#: The shipped static reference blob store (oracle migration 054 —
#: "A static reference blob store for the BTD6 fixtures + per-entity
#: stats tree"). Sole runtime writer: the audited ``btd6.seed_data`` op
#: (the `!btd6 ops seed-data` / `!btd6ops seed-data` admin terminals).
#: NO serving reader in this build: the dataset lane reads the committed
#: files directly (the capture world's file backend — goldens/btd6 pin
#: the `local:` data-source label); the postgres-serving provider is the
#: D-0046 ingestion successor's call.
BTD6_DATA_BLOBS_STORE = register_store(StoreSpec(
    table="btd6_data_blobs",
    sole_writer=EngineRef("btd6.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="btd6_data_blobs",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.NONE,      # versioned game fixtures, no member data
))


@engine("btd6.store")
def _store_marker() -> str:
    return "sb/domain/btd6/store.py"


def _clamp(limit: int) -> int:
    return max(1, min(int(limit), _MAX_LIMIT))


async def insert_strategy(conn: Any, *, guild_id: int, title: str,
                          summary: str, map_name: str | None,
                          mode: str | None, hero: str | None,
                          submitted_by: int,
                          submitter_display: str | None) -> int:
    row = await fetchone(
        "INSERT INTO btd6_strategies (origin_guild_id, current_guild_id, "
        "visibility, approval_status, title, summary, map, mode, hero, "
        "submitted_by, submitter_display_snapshot) "
        "VALUES ($1, $1, 'guild', 'pending', $2, $3, $4, $5, $6, $7, $8) "
        "RETURNING id",
        (guild_id, title, summary, map_name, mode, hero,
         submitted_by, submitter_display), conn=conn)
    return int(row["id"])


async def get_strategy(strategy_id: int, conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT * FROM btd6_strategies WHERE id=$1",
        (strategy_id,), conn=conn)
    return dict(row) if row else None


async def list_strategies(*, guild_id: int | None = None,
                          visibility: str | None = None,
                          approval_status: str | None = None,
                          submitted_by: int | None = None,
                          limit: int = 10,
                          conn: Any = None) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []
    if guild_id is not None:
        params.append(guild_id)
        clauses.append(f"current_guild_id=${len(params)}")
    if visibility is not None:
        params.append(visibility)
        clauses.append(f"visibility=${len(params)}")
    if approval_status is not None:
        params.append(approval_status)
        clauses.append(f"approval_status=${len(params)}")
    if submitted_by is not None:
        params.append(submitted_by)
        clauses.append(f"submitted_by=${len(params)}")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(_clamp(limit))
    rows = await fetchall(
        f"SELECT * FROM btd6_strategies {where} "  # noqa: S608 — clauses built above
        f"ORDER BY id DESC LIMIT ${len(params)}",
        tuple(params), conn=conn)
    return [dict(r) for r in rows]


async def set_review(conn: Any, *, strategy_id: int, approval_status: str,
                     approved_by: str | None, approved_by_id: int | None,
                     review_notes: dict | None = None) -> bool:
    result = await execute(
        "UPDATE btd6_strategies SET approval_status=$2, approved_by=$3, "
        "approved_by_id=$4, origin_metadata=origin_metadata || $5::jsonb, "
        "updated_at=NOW(), version=version+1 WHERE id=$1",
        (strategy_id, approval_status, approved_by, approved_by_id,
         json.dumps({"review": review_notes} if review_notes else {})),
        conn=conn)
    return "1" in str(result)


async def anonymize_submitter(conn: Any, *, user_id: int) -> int:
    """The MEMBER_PII erasure body: identity detached, row retained
    (shipped ``submitter_identity_state`` transition)."""
    result = await execute(
        "UPDATE btd6_strategies SET submitted_by=NULL, "
        "submitter_display_snapshot=NULL, "
        "submitter_identity_state='anonymized', updated_at=NOW() "
        "WHERE submitted_by=$1",
        (user_id,), conn=conn)
    digits = "".join(ch for ch in str(result) if ch.isdigit())
    return int(digits or 0)


async def upsert_data_blob(conn: Any, *, name: str, body: Any,
                           sha256: str | None = None) -> None:
    """Insert or update one blob (shipped ``utils/db/btd6_data.upsert_blob``
    — ``body`` is a JSON-serialisable object; the conflict key is the name)."""
    await execute(
        "INSERT INTO btd6_data_blobs (name, body, sha256, updated_at) "
        "VALUES ($1, $2::jsonb, $3, NOW()) "
        "ON CONFLICT (name) DO UPDATE "
        "SET body = EXCLUDED.body, sha256 = EXCLUDED.sha256, "
        "updated_at = NOW()",
        (name, json.dumps(body), sha256), conn=conn)


async def count_data_blobs(conn: Any = None) -> int:
    row = await fetchone(
        "SELECT COUNT(*) AS n FROM btd6_data_blobs", (), conn=conn)
    return int(row["n"]) if row is not None else 0


async def get_data_blob_row(name: str, conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT name, body, sha256 FROM btd6_data_blobs WHERE name=$1",
        (name,), conn=conn)
    return dict(row) if row else None


def ensure_refs() -> None:
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("btd6.store")):
        engine("btd6.store")(_store_marker)
