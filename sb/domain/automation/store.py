"""automation_rules CRUD — asyncpg SQL behind the K3 seam; migration
``0055_automation_rules.sql`` (oracle utils/db/automation.py @ f969b95,
the insert path this write seam consumes). Sole-writer discipline:
mutations happen only in the K7 ``automation.add_rule`` op
(sb/domain/automation/ops.py).

Rollback disposition (S14): guild CONFIG — bears_value=False,
NAME_STABLE, DECLARED_LOSS. ``created_by`` is a member id ⇒ MEMBER_ID
with a tombstone erasure body (scrub the creator pointer, keep the rule
row — the routing-policy/governance-audit posture).
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
    "AUTOMATION_RULES_STORE",
    "ensure_refs",
    "get_rule_by_name",
    "insert_rule",
    "list_rules_for_guild",
    "tombstone_rule_creator",
]

AUTOMATION_RULES_STORE = register_store(StoreSpec(
    table="automation_rules",
    sole_writer=EngineRef("automation.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="automation_rules",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("automation.tombstone_rule_creator"),
))


@engine("automation.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/automation/store.py"


def _decode(value: Any) -> dict:
    """JSONB round-trip tolerance (oracle utils/db/automation._decode)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes)):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


async def insert_rule(conn: Any, *, guild_id: int, name: str,
                      trigger_kind: str, action_kind: str,
                      trigger_config: dict | None = None,
                      action_config: dict | None = None,
                      schedule: str | None = None, timezone: str = "UTC",
                      created_by: int | None = None) -> int:
    """Insert a new DISABLED rule; returns the new row's ``id`` (oracle
    utils/db/automation.insert_rule, verbatim column set — ``enabled``
    rides the DDL's DEFAULT FALSE, never this INSERT)."""
    row = await fetchone(
        "INSERT INTO automation_rules (guild_id, name, trigger_kind, "
        "trigger_config, action_kind, action_config, schedule, timezone, "
        "created_by) VALUES ($1, $2, $3, $4::JSONB, $5, $6::JSONB, $7, $8, "
        "$9) RETURNING id",
        (guild_id, name, trigger_kind, json.dumps(trigger_config or {}),
         action_kind, json.dumps(action_config or {}), schedule, timezone,
         created_by), conn=conn)
    if row is None:
        raise RuntimeError("automation.insert_rule: RETURNING returned no row.")
    return int(row["id"])


async def get_rule_by_name(guild_id: int, name: str,
                           conn: Any = None) -> dict | None:
    row = await fetchone(
        "SELECT id, guild_id, name, enabled, trigger_kind, trigger_config, "
        "action_kind, action_config, schedule, timezone, created_by "
        "FROM automation_rules WHERE guild_id=$1 AND name=$2",
        (guild_id, name), conn=conn)
    if row is None:
        return None
    out = dict(row)
    out["trigger_config"] = _decode(out.get("trigger_config"))
    out["action_config"] = _decode(out.get("action_config"))
    return out


async def list_rules_for_guild(guild_id: int, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT id, guild_id, name, enabled, trigger_kind, trigger_config, "
        "action_kind, action_config, schedule, timezone, created_by, "
        "created_at, updated_at FROM automation_rules WHERE guild_id=$1 "
        "ORDER BY name", (guild_id,), conn=conn)
    out: list[dict] = []
    for row in rows:
        rec = dict(row)
        rec["trigger_config"] = _decode(rec.get("trigger_config"))
        rec["action_config"] = _decode(rec.get("action_config"))
        out.append(rec)
    return out


async def tombstone_rule_creator(conn: Any, *, user_id: int) -> int:
    """S11 class-12 TOMBSTONE: scrub the subject's ``created_by`` pointer
    in place, keep the rule rows (guild config, not the subject's trail)."""
    result = await execute(
        "UPDATE automation_rules SET created_by=NULL WHERE created_by=$1",
        (user_id,), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, TypeError):
        return 0


def ensure_refs() -> None:
    """Re-arm the sole-writer marker after a sanctioned clear_ref_table
    (the #141 doctrine)."""
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("automation.store")):
        _engine("automation.store")(_store_marker)
