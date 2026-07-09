"""Governance CRUD (band 5) — asyncpg SQL behind the K3 seam; migration
``0016_governance.sql``. Sole-writer discipline: every mutation of these
five tables happens in the K7 governance ops (sb/domain/governance/ops.py)
or the audited service paths that call them.

Rollback disposition (S14): governance rows are guild CONFIG, not value —
bears_value=False, NAME_STABLE, DECLARED_LOSS on rollback (the band-1
settings precedent, Q3-B: post-flip governance edits are lost on reverse
import; no reverse importer may be registered). governance_audit_log
carries actor ids => MEMBER_ID with a tombstone erasure body (rows stay,
actor scrubs — the mod_logs precedent).
"""

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
    "CAPABILITY_OVERRIDES_STORE",
    "CLEANUP_POLICIES_STORE",
    "GOVERNANCE_AUDIT_STORE",
    "GOVERNANCE_TEMPLATES_STORE",
    "SUBSYSTEM_VISIBILITY_STORE",
    "delete_guild_governance_rows",
    "delete_visibility_row",
    "ensure_refs",
    "fetch_capability_overrides",
    "fetch_visibility_for_chain",
    "get_all_cleanup_for_guild",
    "get_all_visibility_for_guild",
    "get_cleanup_policy",
    "get_visibility_override",
    "guild_has_role_overrides",
    "insert_governance_audit",
    "insert_template",
    "load_template_row",
    "remove_cleanup_policy",
    "tombstone_subject_governance_audit",
    "upsert_capability_override",
    "upsert_cleanup_policy",
    "upsert_visibility",
]

SUBSYSTEM_VISIBILITY_STORE = register_store(StoreSpec(
    table="subsystem_visibility",
    sole_writer=EngineRef("governance.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="subsystem_visibility",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics", "help"),
    bears_value=False,
    data_class=DataClass.NONE,
))

CLEANUP_POLICIES_STORE = register_store(StoreSpec(
    table="cleanup_policies",
    sole_writer=EngineRef("governance.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="cleanup_policies",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("interaction", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))

GOVERNANCE_AUDIT_STORE = register_store(StoreSpec(
    table="governance_audit_log",
    sole_writer=EngineRef("governance.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="governance_audit_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("governance.tombstone_subject_audit"),
))

CAPABILITY_OVERRIDES_STORE = register_store(StoreSpec(
    table="capability_execution_overrides",
    sole_writer=EngineRef("governance.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="capability_execution_overrides",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("authority", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,
))

GOVERNANCE_TEMPLATES_STORE = register_store(StoreSpec(
    table="governance_templates",
    sole_writer=EngineRef("governance.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="governance_templates",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.NONE,
))


@engine("governance.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/governance/store.py"


# --- visibility reads ---------------------------------------------------------

async def fetch_visibility_for_chain(
    guild_id: int, chain: list[tuple[str, int]], conn: Any = None,
) -> dict[tuple[str, int], dict[str, bool | None]]:
    """All visibility rows for the scope chain in ONE query (shipped
    _fetch_all_visibility)."""
    if not chain:
        return {}
    scope_types = [s for s, _ in chain]
    scope_ids = [i for _, i in chain]
    rows = await fetchall(
        "SELECT scope_type, scope_id, subsystem, enabled "
        "FROM subsystem_visibility WHERE guild_id=$1 "
        "AND scope_type = ANY($2::text[]) AND scope_id = ANY($3::bigint[])",
        (guild_id, scope_types, scope_ids), conn=conn)
    result: dict[tuple[str, int], dict[str, bool | None]] = {
        (s, i): {} for s, i in chain}
    for row in rows:
        key = (row["scope_type"], row["scope_id"])
        if key in result:
            result[key][row["subsystem"]] = row["enabled"]
    return result


async def get_visibility_override(
    guild_id: int, scope_type: str, scope_id: int, subsystem: str,
    conn: Any = None,
) -> bool | None:
    row = await fetchone(
        "SELECT enabled FROM subsystem_visibility WHERE guild_id=$1 "
        "AND scope_type=$2 AND scope_id=$3 AND subsystem=$4",
        (guild_id, scope_type, scope_id, subsystem), conn=conn)
    return None if row is None else row["enabled"]


async def get_all_visibility_for_guild(
    guild_id: int, conn: Any = None,
) -> list[dict]:
    return await fetchall(
        "SELECT scope_type, scope_id, subsystem, enabled "
        "FROM subsystem_visibility WHERE guild_id=$1",
        (guild_id,), conn=conn)


async def guild_has_role_overrides(guild_id: int, conn: Any = None) -> bool:
    row = await fetchone(
        "SELECT 1 AS x FROM subsystem_visibility "
        "WHERE guild_id=$1 AND scope_type='role' LIMIT 1",
        (guild_id,), conn=conn)
    return row is not None


# --- visibility / cleanup writes (K7-leg only) ---------------------------------

async def upsert_visibility(
    conn: Any, *, guild_id: int, scope_type: str, scope_id: int,
    subsystem: str, enabled: bool | None,
) -> None:
    await execute(
        "INSERT INTO subsystem_visibility "
        "(guild_id, scope_type, scope_id, subsystem, enabled) "
        "VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (guild_id, scope_type, scope_id, subsystem) "
        "DO UPDATE SET enabled = EXCLUDED.enabled",
        (guild_id, scope_type, scope_id, subsystem, enabled), conn=conn)


async def delete_visibility_row(
    conn: Any, *, guild_id: int, scope_type: str, scope_id: int,
    subsystem: str,
) -> None:
    await execute(
        "DELETE FROM subsystem_visibility WHERE guild_id=$1 "
        "AND scope_type=$2 AND scope_id=$3 AND subsystem=$4",
        (guild_id, scope_type, scope_id, subsystem), conn=conn)


async def get_cleanup_policy(
    guild_id: int, scope_type: str, scope_id: int, conn: Any = None,
) -> dict | None:
    return await fetchone(
        "SELECT delete_invalid_commands, delete_failed_commands, "
        "delete_after_seconds FROM cleanup_policies "
        "WHERE guild_id=$1 AND scope_type=$2 AND scope_id=$3",
        (guild_id, scope_type, scope_id), conn=conn)


async def get_all_cleanup_for_guild(
    guild_id: int, conn: Any = None,
) -> list[dict]:
    return await fetchall(
        "SELECT scope_type, scope_id, delete_invalid_commands, "
        "delete_failed_commands, delete_after_seconds "
        "FROM cleanup_policies WHERE guild_id=$1",
        (guild_id,), conn=conn)


async def upsert_cleanup_policy(
    conn: Any, *, guild_id: int, scope_type: str, scope_id: int,
    delete_invalid_commands: bool, delete_failed_commands: bool,
    delete_after_seconds: int,
) -> None:
    await execute(
        "INSERT INTO cleanup_policies (guild_id, scope_type, scope_id, "
        "delete_invalid_commands, delete_failed_commands, delete_after_seconds) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "ON CONFLICT (guild_id, scope_type, scope_id) DO UPDATE SET "
        "delete_invalid_commands = EXCLUDED.delete_invalid_commands, "
        "delete_failed_commands  = EXCLUDED.delete_failed_commands, "
        "delete_after_seconds    = EXCLUDED.delete_after_seconds",
        (guild_id, scope_type, scope_id, delete_invalid_commands,
         delete_failed_commands, delete_after_seconds), conn=conn)


async def remove_cleanup_policy(
    conn: Any, *, guild_id: int, scope_type: str, scope_id: int,
) -> bool:
    """DELETE by literal scope key; True when a row was removed (the
    shipped audited-no-op contract)."""
    rows = await fetchall(
        "DELETE FROM cleanup_policies WHERE guild_id=$1 AND scope_type=$2 "
        "AND scope_id=$3 RETURNING guild_id",
        (guild_id, scope_type, scope_id), conn=conn)
    return bool(rows)


# --- governance audit ----------------------------------------------------------

async def insert_governance_audit(
    conn: Any, *, guild_id: int, actor_id: int, action: str,
    scope_type: str | None, scope_id: int | None, subsystem: str | None,
    old_value: dict | None, new_value: dict | None,
) -> None:
    await execute(
        "INSERT INTO governance_audit_log (guild_id, actor_id, action, "
        "scope_type, scope_id, subsystem, old_value, new_value) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        (guild_id, actor_id, action, scope_type, scope_id, subsystem,
         json.dumps(old_value) if old_value is not None else None,
         json.dumps(new_value) if new_value is not None else None),
        conn=conn)


async def recent_governance_audit(
    guild_id: int, limit: int = 20, conn: Any = None,
) -> list[dict]:
    return await fetchall(
        "SELECT occurred_at, actor_id, action, scope_type, scope_id, "
        "subsystem, old_value, new_value FROM governance_audit_log "
        "WHERE guild_id=$1 ORDER BY occurred_at DESC LIMIT $2",
        (guild_id, limit), conn=conn)


async def tombstone_subject_governance_audit(
    conn: Any, *, user_id: int,
) -> int:
    """Erasure body: rows stay (the governance trail), actor scrubs to 0."""
    rows = await fetchall(
        "UPDATE governance_audit_log SET actor_id = 0 "
        "WHERE actor_id = $1 RETURNING id", (user_id,), conn=conn)
    return len(rows)


# --- capability overrides -------------------------------------------------------

async def fetch_capability_overrides(
    guild_id: int, conn: Any = None,
) -> dict[str, bool]:
    rows = await fetchall(
        "SELECT capability, allowed FROM capability_execution_overrides "
        "WHERE guild_id = $1", (guild_id,), conn=conn)
    return {row["capability"]: row["allowed"] for row in rows}


async def upsert_capability_override(
    conn: Any, *, guild_id: int, capability: str, allowed: bool | None,
) -> None:
    """allowed=None clears the override row."""
    if allowed is None:
        await execute(
            "DELETE FROM capability_execution_overrides "
            "WHERE guild_id=$1 AND capability=$2",
            (guild_id, capability), conn=conn)
        return
    await execute(
        "INSERT INTO capability_execution_overrides "
        "(guild_id, capability, allowed) VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, capability) "
        "DO UPDATE SET allowed = EXCLUDED.allowed",
        (guild_id, capability, allowed), conn=conn)


# --- templates -------------------------------------------------------------------

async def insert_template(
    conn: Any, *, name: str, description: str,
    created_by_guild_id: int | None, payload: dict,
) -> int:
    row = await fetchone(
        "INSERT INTO governance_templates "
        "(name, description, created_by_guild_id, payload) "
        "VALUES ($1, $2, $3, $4::jsonb) RETURNING template_id",
        (name, description, created_by_guild_id, json.dumps(payload)),
        conn=conn)
    return int(row["template_id"])


async def load_template_row(
    template_id: int, conn: Any = None,
) -> dict | None:
    return await fetchone(
        "SELECT payload FROM governance_templates WHERE template_id = $1",
        (template_id,), conn=conn)


# --- guild teardown --------------------------------------------------------------

async def delete_guild_governance_rows(guild_id: int, conn: Any = None) -> None:
    """Guild-leave teardown: overrides + cleanup + capability rows drop;
    governance_audit_log is PRESERVED (the shipped retention posture —
    the trail survives re-invitation)."""
    await execute("DELETE FROM subsystem_visibility WHERE guild_id=$1",
                  (guild_id,), conn=conn)
    await execute("DELETE FROM cleanup_policies WHERE guild_id=$1",
                  (guild_id,), conn=conn)
    await execute(
        "DELETE FROM capability_execution_overrides WHERE guild_id=$1",
        (guild_id,), conn=conn)


def ensure_refs() -> None:
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("governance.store")):
        _engine("governance.store")(_store_marker)
