"""ai_channel_policy / ai_category_policy / ai_role_policy CRUD (band 7,
the policy-mutation slice) — the shipped migration 039 override shapes
(NAME_STABLE; migrations/0028_ai_policy.sql). Rows carry the mutating
operator's id (``updated_by``) → MEMBER_ID; erasure = detach editorship
(NULL the column), the ai_answer_presets authorship precedent.

The shipped per-guild policy GENERATION (ai_guild_policy.generation —
bumped on every scoped write, ORACLE utils/db/ai.bump_generation) rides a
``guild_settings`` KV row here (the ai_review_channel precedent): the
shipped counter's runtime job was resolver-cache invalidation, which the
KV port does not carry (reads are per-message); the counter survives for
the shipped ``(generation N)`` ack byte and the minted-defaults
"configured" semantics (D-0070)."""

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
    "AI_CATEGORY_POLICY_STORE",
    "AI_CHANNEL_POLICY_STORE",
    "AI_POLICY_GENERATION_KEY",
    "AI_ROLE_POLICY_STORE",
    "bump_generation",
    "detach_policy_editor",
    "ensure_policy_store_refs",
    "get_generation",
    "list_category_policies",
    "list_channel_policies",
    "list_role_policies",
    "load_overlays",
    "upsert_category_policy",
    "upsert_channel_policy",
    "upsert_role_policy",
]


def _policy_store_spec(table: str) -> StoreSpec:
    return StoreSpec(
        table=table,
        sole_writer=EngineRef("ai.policy_store"),
        retention="permanent",
        checkpoint_class=CheckpointClass.AGGREGATE,
        invariant_tag=table,
        forward_map_kind=ForwardMapKind.NAME_STABLE,
        reader_domains=("diagnostics",),
        bears_value=False,
        data_class=DataClass.MEMBER_ID,          # updated_by (operator id)
        erasure_ref=WorkflowRef("ai.scrub_policy_editor"),
    )


AI_CHANNEL_POLICY_STORE = register_store(_policy_store_spec("ai_channel_policy"))
AI_CATEGORY_POLICY_STORE = register_store(_policy_store_spec("ai_category_policy"))
AI_ROLE_POLICY_STORE = register_store(_policy_store_spec("ai_role_policy"))


@engine("ai.policy_store")
def _store_marker() -> str:
    return "sb/domain/ai/policy_store.py"


#: the per-guild policy generation counter's guild_settings key (the shipped
#: ai_guild_policy.generation twin — see the module docstring).
AI_POLICY_GENERATION_KEY = "ai_policy_generation"


# --- writes (op legs only — the K7 sole-writer lane) ---------------------------------


async def upsert_channel_policy(conn: Any, *, guild_id: int, channel_id: int,
                                mode: str, min_level: int | None,
                                cooldown_seconds: int | None,
                                updated_by: int | None) -> dict | None:
    """Upsert one channel override; returns the PRIOR row (or None).

    ``instruction_profile_id`` is never in the conflict SET — the shipped
    PR-C-pre UNCHANGED sentinel posture for the column this UI does not
    own (profile binding belongs to the Behavior slice)."""
    prior = await fetchone(
        "SELECT mode, min_level, cooldown_seconds, instruction_profile_id "
        "FROM ai_channel_policy WHERE guild_id=$1 AND channel_id=$2",
        (guild_id, channel_id), conn=conn)
    await execute(
        "INSERT INTO ai_channel_policy (guild_id, channel_id, mode, "
        "min_level, cooldown_seconds, instruction_profile_id, updated_at, "
        "updated_by) VALUES ($1,$2,$3,$4,$5,NULL,NOW(),$6) "
        "ON CONFLICT (guild_id, channel_id) DO UPDATE SET "
        "mode=EXCLUDED.mode, min_level=EXCLUDED.min_level, "
        "cooldown_seconds=EXCLUDED.cooldown_seconds, updated_at=NOW(), "
        "updated_by=EXCLUDED.updated_by",
        (guild_id, channel_id, mode, min_level, cooldown_seconds,
         updated_by), conn=conn)
    return dict(prior) if prior else None


async def upsert_category_policy(conn: Any, *, guild_id: int,
                                 category_id: int, mode: str,
                                 min_level: int | None,
                                 cooldown_seconds: int | None,
                                 updated_by: int | None) -> dict | None:
    prior = await fetchone(
        "SELECT mode, min_level, cooldown_seconds, instruction_profile_id "
        "FROM ai_category_policy WHERE guild_id=$1 AND category_id=$2",
        (guild_id, category_id), conn=conn)
    await execute(
        "INSERT INTO ai_category_policy (guild_id, category_id, mode, "
        "min_level, cooldown_seconds, instruction_profile_id, updated_at, "
        "updated_by) VALUES ($1,$2,$3,$4,$5,NULL,NOW(),$6) "
        "ON CONFLICT (guild_id, category_id) DO UPDATE SET "
        "mode=EXCLUDED.mode, min_level=EXCLUDED.min_level, "
        "cooldown_seconds=EXCLUDED.cooldown_seconds, updated_at=NOW(), "
        "updated_by=EXCLUDED.updated_by",
        (guild_id, category_id, mode, min_level, cooldown_seconds,
         updated_by), conn=conn)
    return dict(prior) if prior else None


async def upsert_role_policy(conn: Any, *, guild_id: int, role_id: int,
                             decision: str, min_level_override: int | None,
                             bypass_cooldown: bool,
                             updated_by: int | None) -> dict | None:
    prior = await fetchone(
        "SELECT decision, min_level_override, bypass_cooldown "
        "FROM ai_role_policy WHERE guild_id=$1 AND role_id=$2",
        (guild_id, role_id), conn=conn)
    await execute(
        "INSERT INTO ai_role_policy (guild_id, role_id, decision, "
        "min_level_override, bypass_cooldown, created_at, updated_at, "
        "updated_by) VALUES ($1,$2,$3,$4,$5,NOW(),NOW(),$6) "
        "ON CONFLICT (guild_id, role_id) DO UPDATE SET "
        "decision=EXCLUDED.decision, "
        "min_level_override=EXCLUDED.min_level_override, "
        "bypass_cooldown=EXCLUDED.bypass_cooldown, updated_at=NOW(), "
        "updated_by=EXCLUDED.updated_by",
        (guild_id, role_id, decision, min_level_override, bypass_cooldown,
         updated_by), conn=conn)
    return dict(prior) if prior else None


async def bump_generation(conn: Any, *, guild_id: int) -> int:
    """The shipped bump_generation twin over the guild_settings KV row:
    first scoped write mints the counter at 1 (ORACLE's INSERT … VALUES 1),
    every later write increments — same monotone contract."""
    row = await fetchone(
        "INSERT INTO guild_settings (guild_id, key, value) "
        "VALUES ($1, $2, '1') "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = "
        "(COALESCE(NULLIF(guild_settings.value, ''), '0')::bigint + 1)::text "
        "RETURNING value",
        (guild_id, AI_POLICY_GENERATION_KEY), conn=conn)
    return int(row["value"]) if row else 0


# --- reads ---------------------------------------------------------------------------


async def get_generation(guild_id: int, conn: Any = None) -> int | None:
    """The counter, or None while no scoped write ever landed (the shipped
    "no ai_guild_policy row" state)."""
    row = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id=$1 AND key=$2",
        (guild_id, AI_POLICY_GENERATION_KEY), conn=conn)
    if row is None:
        return None
    try:
        return int(str(row["value"]) or 0)
    except ValueError:
        return 0


async def list_channel_policies(guild_id: int,
                                conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT guild_id, channel_id, mode, min_level, cooldown_seconds, "
        "instruction_profile_id, updated_at, updated_by "
        "FROM ai_channel_policy WHERE guild_id=$1 ORDER BY channel_id",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def list_category_policies(guild_id: int,
                                 conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT guild_id, category_id, mode, min_level, cooldown_seconds, "
        "instruction_profile_id, updated_at, updated_by "
        "FROM ai_category_policy WHERE guild_id=$1 ORDER BY category_id",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def list_role_policies(guild_id: int, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT guild_id, role_id, decision, min_level_override, "
        "bypass_cooldown, created_at, updated_at, updated_by "
        "FROM ai_role_policy WHERE guild_id=$1 ORDER BY role_id",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def load_overlays(guild_id: int) -> tuple[
        dict[int, dict], dict[int, dict], dict[int, dict]]:
    """(channel, category, role) maps in the PolicyBundle row shapes the
    K10 resolver consumes (sb/kernel/ai/policy.py PolicyBundle)."""
    channel = {int(r["channel_id"]): {
        "mode": r["mode"], "min_level": r["min_level"],
        "cooldown_seconds": r["cooldown_seconds"],
        "instruction_profile_id": r["instruction_profile_id"]}
        for r in await list_channel_policies(guild_id)}
    category = {int(r["category_id"]): {
        "mode": r["mode"], "min_level": r["min_level"],
        "cooldown_seconds": r["cooldown_seconds"],
        "instruction_profile_id": r["instruction_profile_id"]}
        for r in await list_category_policies(guild_id)}
    role = {int(r["role_id"]): {
        "decision": r["decision"],
        "min_level_override": r["min_level_override"],
        "bypass_cooldown": r["bypass_cooldown"]}
        for r in await list_role_policies(guild_id)}
    return channel, category, role


# --- erasure -------------------------------------------------------------------------


async def detach_policy_editor(conn: Any, *, user_id: int) -> int:
    """NULL the subject's editorship stamps across the three override
    tables (the preset-authorship detach precedent — the rows themselves
    are guild config, not the subject's data)."""
    touched = 0
    for table in ("ai_channel_policy", "ai_category_policy",
                  "ai_role_policy"):
        result = await execute(
            f"UPDATE {table} SET updated_by=NULL WHERE updated_by=$1",  # noqa: S608
            (user_id,), conn=conn)
        digits = "".join(ch for ch in str(result) if ch.isdigit())
        touched += int(digits or 0)
    return touched


def ensure_policy_store_refs() -> None:
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("ai.policy_store")):
        engine("ai.policy_store")(_store_marker)
