"""The draft DB primitive (K9/S10 — frozen L0 spec 06 §3.2). asyncpg SQL
only. Append-by-``op_seq`` — NO slot upsert (the L-7 collapse fix).

- ``load_draft`` / ``select_expired`` are READ-ONLY — the OPEN/PREVIEWED →
  EXPIRED write is owned by the janitor lane, never lazily at load.
- ``update_status(expect=…)`` is a CONDITIONAL compare-and-set;
  ``reap_stuck_applying`` is a strictly-conditional CAS sweep (only a STALE
  ``APPLYING`` row moves to ``PARTIAL`` — the per-op heartbeat keeps a live
  apply fresh).
- ``list_open_drafts`` keys ``owner_actor_id`` with IS NOT DISTINCT FROM
  (NULL-safe — system rows store NULL).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import CheckpointClass, DataClass, ForwardMapKind, StoreSpec, register_store
from sb.spec.draft import (
    Draft,
    DraftOperation,
    DraftStatus,
    OwnerScope,
    Producer,
    VerificationContext,
)

__all__ = [
    "append_operation",
    "delete_draft",
    "delete_operation",
    "insert_draft",
    "list_open_drafts",
    "load_draft",
    "reap_stuck_applying",
    "select_expired",
    "update_status",
]

_OPEN_STATUSES = (DraftStatus.OPEN.value, DraftStatus.PREVIEWED.value,
                  DraftStatus.APPLYING.value)

# S11 class 12: drafts key owner_actor_id + staged payloads may carry member
# data — a MEMBER_ID store. Erasure = discard the subject's drafts; body
# lands with the draft-surface band, ref DECLARED now. SELF-MANAGED expiry
# (the janitor lane), so AGGREGATE / no recovery reader.
DRAFTS_STORE = register_store(StoreSpec(
    table="sb_drafts",
    sole_writer=EngineRef("sb.kernel.db.draft"),
    retention="expires_at",   # per-draft TTL; janitor writes EXPIRED
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="draft_staging",
    forward_map_kind=ForwardMapKind.NEW_ONLY,  # fresh-chain kernel table (S14)
    reader_domains=(),
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("kernel.draft.discard_subject_drafts"),
))


def _row_to_draft(row: Mapping[str, Any],
                  op_rows: list[Mapping[str, Any]]) -> Draft:
    verification = None
    vj = row["verification_json"]
    if vj:
        data = json.loads(vj) if isinstance(vj, str) else dict(vj)
        verification = VerificationContext(
            test_mode=bool(data.get("test_mode")),
            debug_channel_id=data.get("debug_channel_id"),
            sign_off_store_ref=data.get("sign_off_store_ref"))
    ops = []
    for op in op_rows:
        payload = op["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        ops.append(DraftOperation(
            op_seq=op["op_seq"], op_kind=op["op_kind"], subsystem=op["subsystem"],
            authority_ref=op["authority_ref"], payload=payload or {},
            label=op["label"], dedup_token=op["dedup_token"]))
    return Draft(
        draft_id=str(row["draft_id"]), producer=Producer(row["producer"]),
        owner_scope=OwnerScope(guild_id=row["owner_guild_id"],
                               actor_id=row["owner_actor_id"]),
        status=DraftStatus(row["status"]), operations=tuple(ops),
        created_at=row["created_at"], updated_at=row["updated_at"],
        expires_at=row["expires_at"],
        accept_authority_ref=row["accept_authority_ref"],
        correlation_id=str(row["correlation_id"]), verification=verification)


async def insert_draft(draft: Draft, *, conn) -> None:
    verification_json = None
    if draft.verification is not None:
        verification_json = json.dumps({
            "test_mode": draft.verification.test_mode,
            "debug_channel_id": draft.verification.debug_channel_id,
            "sign_off_store_ref": draft.verification.sign_off_store_ref})
    await execute(
        "INSERT INTO sb_drafts (draft_id, producer, owner_guild_id,"
        " owner_actor_id, status, accept_authority_ref, correlation_id,"
        " verification_json, created_at, updated_at, expires_at)"
        " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)",
        (draft.draft_id, draft.producer.value, draft.owner_scope.guild_id,
         draft.owner_scope.actor_id, draft.status.value,
         draft.accept_authority_ref, draft.correlation_id, verification_json,
         draft.created_at, draft.updated_at, draft.expires_at), conn=conn)


async def append_operation(draft_id: str, op: DraftOperation, *, conn) -> int:
    """op_seq = COALESCE(MAX,0)+1 — APPEND, never upsert."""
    row = await fetchone(
        "INSERT INTO sb_draft_operations (draft_id, op_seq, op_kind, subsystem,"
        " authority_ref, payload_json, label, dedup_token)"
        " SELECT $1, COALESCE(MAX(op_seq),0)+1, $2, $3, $4, $5, $6, $7"
        " FROM sb_draft_operations WHERE draft_id=$1"
        " RETURNING op_seq",
        (draft_id, op.op_kind, op.subsystem, op.authority_ref,
         json.dumps(dict(op.payload)), op.label, op.dedup_token), conn=conn)
    await execute("UPDATE sb_drafts SET updated_at=now() WHERE draft_id=$1",
                  (draft_id,), conn=conn)
    return int(row["op_seq"]) if row else 0


async def delete_operation(draft_id: str, op_seq: int, *, conn) -> int:
    tag = await execute(
        "DELETE FROM sb_draft_operations WHERE draft_id=$1 AND op_seq=$2",
        (draft_id, op_seq), conn=conn)
    await execute("UPDATE sb_drafts SET updated_at=now() WHERE draft_id=$1",
                  (draft_id,), conn=conn)
    try:
        return int(str(tag).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def load_draft(draft_id: str, *, conn=None) -> Draft | None:
    """READ-ONLY; joins ops ordered by op_seq — NEVER mutates status."""
    row = await fetchone("SELECT * FROM sb_drafts WHERE draft_id=$1",
                         (draft_id,), conn=conn)
    if row is None:
        return None
    ops = await fetchall(
        "SELECT * FROM sb_draft_operations WHERE draft_id=$1 ORDER BY op_seq",
        (draft_id,), conn=conn)
    return _row_to_draft(row, ops)


async def list_open_drafts(scope: OwnerScope, *, conn=None) -> tuple[Draft, ...]:
    rows = await fetchall(
        "SELECT * FROM sb_drafts WHERE owner_guild_id = $1"
        " AND owner_actor_id IS NOT DISTINCT FROM $2"
        " AND status = ANY($3::text[]) ORDER BY created_at",
        (scope.guild_id, scope.actor_id, list(_OPEN_STATUSES)), conn=conn)
    drafts = []
    for row in rows:
        ops = await fetchall(
            "SELECT * FROM sb_draft_operations WHERE draft_id=$1 ORDER BY op_seq",
            (str(row["draft_id"]),), conn=conn)
        drafts.append(_row_to_draft(row, ops))
    return tuple(drafts)


async def update_status(draft_id: str, status: DraftStatus, *, conn,
                        expect: DraftStatus | None = None) -> bool:
    """expect=None ⇒ unconditional overwrite; expect given ⇒ CONDITIONAL
    compare-and-set (returns whether the row transitioned)."""
    if expect is None:
        tag = await execute(
            "UPDATE sb_drafts SET status=$2, updated_at=now() WHERE draft_id=$1",
            (draft_id, status.value), conn=conn)
    else:
        tag = await execute(
            "UPDATE sb_drafts SET status=$2, updated_at=now()"
            " WHERE draft_id=$1 AND status=$3",
            (draft_id, status.value, expect.value), conn=conn)
    try:
        return int(str(tag).rsplit(" ", 1)[-1]) == 1
    except (ValueError, AttributeError):
        return False


async def reap_stuck_applying(now: datetime, ttl_s: int, *, conn) -> tuple[str, ...]:
    """ONE conditional-CAS statement — only a STALE APPLYING row (no per-op
    heartbeat for the whole TTL) flips to PARTIAL."""
    # $1::timestamptz pins the parameter's type for the subtraction: without
    # the cast Postgres resolves `$1 - make_interval(...)` through the
    # PREFERRED datetime type (interval - interval → interval) and prepare
    # fails with `timestamptz < interval` (caught by the CUT-1 live boot —
    # the unit fakes never prepared the statement against a real server).
    rows = await fetchall(
        "UPDATE sb_drafts SET status='partial', updated_at=$1"
        " WHERE status='applying'"
        " AND updated_at < $1::timestamptz - make_interval(secs => $2)"
        " RETURNING draft_id", (now, float(ttl_s)), conn=conn)
    return tuple(str(r["draft_id"]) for r in rows)


async def delete_draft(draft_id: str, *, conn) -> int:
    tag = await execute("DELETE FROM sb_drafts WHERE draft_id=$1",
                        (draft_id,), conn=conn)
    try:
        return int(str(tag).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def select_expired(now: datetime, *, conn=None) -> tuple[str, ...]:
    """READ: draft_ids past expires_at, non-terminal (the janitor writes)."""
    rows = await fetchall(
        "SELECT draft_id FROM sb_drafts WHERE expires_at IS NOT NULL"
        " AND expires_at < $1 AND status = ANY($2::text[])",
        (now, list(_OPEN_STATUSES)), conn=conn)
    return tuple(str(r["draft_id"]) for r in rows)
