"""ai_decision_audit CRUD (K10) — asyncpg SQL behind the K3 seam.

Migration: ``0008_ai_decision_audit.sql``. AI_DECISION_AUDIT_STORE follows
the kernel-store convention (module StoreSpec constant + migration — not a
manifest facet until a kernel manifest exists).
"""

from __future__ import annotations

import json
from typing import Any

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = ["AI_DECISION_AUDIT_STORE", "delete_subject_rows", "insert_decision", "query_decisions"]

AI_DECISION_AUDIT_STORE = register_store(StoreSpec(
    table="ai_decision_audit",
    sole_writer=EngineRef("sb.kernel.ai"),
    retention="operational",  # diagnostics trail, prunable (owner retention call)
    checkpoint_class=CheckpointClass.LEDGER,  # append-only decision ledger
    invariant_tag="ai_decision_audit",
    forward_map_kind=ForwardMapKind.NEW_ONLY,  # fresh-chain kernel table (S14)
    reader_domains=("diagnostics",),
    bears_value=False,
    # S11 class 12: rows key on actor ids (pseudonymous), no message bodies.
    # Erasure = hard delete of the subject's rows (no value skeleton to
    # preserve — unlike audit_log this ledger is diagnostic, not forensic).
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("kernel.ai.scrub_decision_audit"),
))


async def insert_decision(
    *,
    guild_id: int,
    channel_id: int,
    category_id: int | None,
    user_id: int,
    message_id: int | None,
    task: str | None,
    route: str | None,
    decision: str,
    reason_code: str,
    policy_snapshot_hash: str | None,
    instruction_profile_ids: list[int] | None,
    provider: str | None,
    model: str | None,
    conn: Any = None,
) -> int:
    """Insert one row; returns the new id."""
    row = await fetchone(
        """
        INSERT INTO ai_decision_audit (
            guild_id, channel_id, category_id, user_id, message_id,
            task, route, decision, reason_code, policy_snapshot_hash,
            instruction_profile_ids, provider, model)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        RETURNING id
        """,
        (
            guild_id,
            channel_id,
            category_id,
            user_id,
            message_id,
            task,
            route,
            decision,
            reason_code,
            policy_snapshot_hash,
            json.dumps(instruction_profile_ids) if instruction_profile_ids else None,
            provider,
            model,
        ),
        conn=conn,
    )
    return int(row["id"])


async def query_decisions(
    guild_id: int,
    *,
    channel_id: int | None = None,
    user_id: int | None = None,
    decision: str | None = None,
    limit: int = 50,
    conn: Any = None,
) -> list[dict[str, Any]]:
    """Newest-first decision rows for the operator diagnostics view."""
    clauses = ["guild_id = $1"]
    args: list[Any] = [guild_id]
    if channel_id is not None:
        args.append(channel_id)
        clauses.append(f"channel_id = ${len(args)}")
    if user_id is not None:
        args.append(user_id)
        clauses.append(f"user_id = ${len(args)}")
    if decision is not None:
        args.append(decision)
        clauses.append(f"decision = ${len(args)}")
    args.append(max(1, min(int(limit), 500)))
    rows = await fetchall(
        f"""
        SELECT * FROM ai_decision_audit
        WHERE {' AND '.join(clauses)}
        ORDER BY occurred_at DESC
        LIMIT ${len(args)}
        """,  # noqa: S608 — clauses are built from constants above
        tuple(args),
        conn=conn,
    )
    return [dict(r) for r in rows]


async def delete_subject_rows(guild_id: int | None, user_id: int, *, conn: Any = None) -> int:
    """Erasure leg (kernel.ai.scrub_decision_audit body): hard-delete the
    subject's rows; guild_id=None sweeps cross-guild (account-level A-15)."""
    if guild_id is None:
        result = await execute(
            "DELETE FROM ai_decision_audit WHERE user_id = $1",
            (user_id,),
            conn=conn,
        )
    else:
        result = await execute(
            "DELETE FROM ai_decision_audit WHERE guild_id = $1 AND user_id = $2",
            (guild_id, user_id),
            conn=conn,
        )
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return 0
