"""ai_channel_policy / ai_category_policy / ai_role_policy CRUD (band 7,
the policy-mutation slice) — the shipped migration 039 override shapes
(NAME_STABLE; migrations/0028_ai_policy.sql) — plus the
ai_instruction_profile preset-catalog reads (band 7, the behavior-preset
slice — D-0071; migrations/0030_ai_instruction_profile.sql seeds the
seven shipped system presets and no runtime lane writes the table). Rows
carry the mutating operator's id (``updated_by`` / ``created_by``) →
MEMBER_ID; erasure = detach editorship (NULL the column), the
ai_answer_presets authorship precedent.

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
    "AI_INSTRUCTION_PROFILE_STORE",
    "AI_ORCHESTRATION_PROFILE_KEY",
    "AI_POLICY_GENERATION_KEY",
    "AI_ROLE_POLICY_STORE",
    "UNCHANGED",
    "bump_generation",
    "detach_policy_editor",
    "ensure_policy_store_refs",
    "get_generation",
    "get_guild_orchestration_profile",
    "get_preset_profile",
    "list_category_policies",
    "list_channel_policies",
    "list_preset_profiles",
    "list_role_policies",
    "load_orchestration_overlays",
    "load_overlays",
    "read_guild_orchestration_profile",
    "set_guild_orchestration_profile",
    "upsert_category_orchestration",
    "upsert_category_policy",
    "upsert_channel_orchestration",
    "upsert_channel_policy",
    "upsert_role_policy",
]


class _Unchanged:
    """The shipped ai_policy_mutation UNCHANGED sentinel (PR-C-pre): a
    column the caller does not own is neither set on insert (NULL) nor
    touched on conflict."""

    def __repr__(self) -> str:  # pragma: no cover — debug aid
        return "UNCHANGED"


UNCHANGED = _Unchanged()


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

#: the shipped instruction-profile CATALOG (band 7, the behavior-preset
#: slice — D-0071): migration 0030 seeds the seven system presets and no
#: runtime lane writes the table (guild-authored profiles are the oracle
#: ai_instruction_mutation surface, unported); ``created_by`` exists in
#: the shipped shape (NULL on every seed row) so the store rides the same
#: MEMBER_ID erasure lane as the override tables.
AI_INSTRUCTION_PROFILE_STORE = register_store(
    _policy_store_spec("ai_instruction_profile"))


@engine("ai.policy_store")
def _store_marker() -> str:
    return "sb/domain/ai/policy_store.py"


#: the per-guild policy generation counter's guild_settings key (the shipped
#: ai_guild_policy.generation twin — see the module docstring).
AI_POLICY_GENERATION_KEY = "ai_policy_generation"

#: the guild-default tool-orchestration profile's guild_settings key — the
#: shipped ``ai_guild_policy.orchestration_profile`` column's KV twin (the
#: orchestration-mutation slice; the ai_policy_generation precedent —
#: D-0025 keeps the guild policy row a settings-plane port). Empty string
#: = cleared (the shipped NULL).
AI_ORCHESTRATION_PROFILE_KEY = "ai_orchestration_profile"


# --- writes (op legs only — the K7 sole-writer lane) ---------------------------------


async def _upsert_scoped_policy(conn: Any, *, table: str, id_col: str,
                                guild_id: int, target_id: int, mode: str,
                                min_level, cooldown_seconds,
                                instruction_profile_id,
                                updated_by: int | None) -> dict | None:
    """Upsert one channel/category override; returns the PRIOR row (or
    None). The three optional columns carry the shipped UNCHANGED
    sentinel semantics (ai_policy_mutation PR-C-pre): an UNCHANGED column
    is neither set on insert (stays NULL) nor touched on conflict — the
    modal lane always passes min_level/cooldown explicitly (blank =
    None = clear), the behavior-preset lane passes instruction_profile_id
    and leaves min_level/cooldown UNCHANGED ('Existing min_level /
    cooldown overrides for that scope are preserved', the shipped picker
    copy)."""
    prior = await fetchone(
        f"SELECT mode, min_level, cooldown_seconds, instruction_profile_id "  # noqa: S608
        f"FROM {table} WHERE guild_id=$1 AND {id_col}=$2",
        (guild_id, target_id), conn=conn)
    dynamic = [(col, val) for col, val in (
        ("min_level", min_level),
        ("cooldown_seconds", cooldown_seconds),
        ("instruction_profile_id", instruction_profile_id),
    ) if not isinstance(val, _Unchanged)]
    cols = ["guild_id", id_col, "mode",
            *[col for col, _ in dynamic], "updated_at", "updated_by"]
    params: list = [guild_id, target_id, mode,
                    *[val for _, val in dynamic], updated_by]
    placeholders, n = [], 0
    for col in cols:
        if col == "updated_at":
            placeholders.append("NOW()")
        else:
            n += 1
            placeholders.append(f"${n}")
    sets = ["mode=EXCLUDED.mode",
            *[f"{col}=EXCLUDED.{col}" for col, _ in dynamic],
            "updated_at=NOW()", "updated_by=EXCLUDED.updated_by"]
    await execute(
        f"INSERT INTO {table} ({', '.join(cols)}) "  # noqa: S608
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT (guild_id, {id_col}) DO UPDATE SET {', '.join(sets)}",
        tuple(params), conn=conn)
    return dict(prior) if prior else None


async def upsert_channel_policy(conn: Any, *, guild_id: int, channel_id: int,
                                mode: str,
                                min_level: int | None | _Unchanged = UNCHANGED,
                                cooldown_seconds: int | None | _Unchanged = UNCHANGED,
                                instruction_profile_id: int | None | _Unchanged = UNCHANGED,
                                updated_by: int | None) -> dict | None:
    return await _upsert_scoped_policy(
        conn, table="ai_channel_policy", id_col="channel_id",
        guild_id=guild_id, target_id=channel_id, mode=mode,
        min_level=min_level, cooldown_seconds=cooldown_seconds,
        instruction_profile_id=instruction_profile_id,
        updated_by=updated_by)


async def upsert_category_policy(conn: Any, *, guild_id: int,
                                 category_id: int, mode: str,
                                 min_level: int | None | _Unchanged = UNCHANGED,
                                 cooldown_seconds: int | None | _Unchanged = UNCHANGED,
                                 instruction_profile_id: int | None | _Unchanged = UNCHANGED,
                                 updated_by: int | None) -> dict | None:
    return await _upsert_scoped_policy(
        conn, table="ai_category_policy", id_col="category_id",
        guild_id=guild_id, target_id=category_id, mode=mode,
        min_level=min_level, cooldown_seconds=cooldown_seconds,
        instruction_profile_id=instruction_profile_id,
        updated_by=updated_by)


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


async def _upsert_scoped_orchestration(conn: Any, *, table: str, id_col: str,
                                       guild_id: int, target_id: int,
                                       orchestration_profile: str | None,
                                       updated_by: int | None) -> dict | None:
    """The shipped COLUMN-ONLY orchestration setter (ORACLE utils/db/ai.py
    set_channel_orchestration_profile / set_category_orchestration_profile
    — migration 062): a fresh row is minted with ``mode='inherit'`` and a
    conflicting row's mode/min_level/cooldown/instruction_profile_id are
    NEVER touched — only ``orchestration_profile`` (+ the audit stamps)
    move. NULL clears the override (inherit the next layer). Returns the
    PRIOR row (or None)."""
    prior = await fetchone(
        f"SELECT orchestration_profile "  # noqa: S608
        f"FROM {table} WHERE guild_id=$1 AND {id_col}=$2",
        (guild_id, target_id), conn=conn)
    await execute(
        f"INSERT INTO {table} (guild_id, {id_col}, mode, "  # noqa: S608
        f"orchestration_profile, updated_at, updated_by) "
        f"VALUES ($1, $2, 'inherit', $3, NOW(), $4) "
        f"ON CONFLICT (guild_id, {id_col}) DO UPDATE SET "
        f"orchestration_profile=EXCLUDED.orchestration_profile, "
        f"updated_at=NOW(), updated_by=EXCLUDED.updated_by",
        (guild_id, target_id, orchestration_profile, updated_by), conn=conn)
    return dict(prior) if prior else None


async def upsert_channel_orchestration(conn: Any, *, guild_id: int,
                                       channel_id: int,
                                       orchestration_profile: str | None,
                                       updated_by: int | None) -> dict | None:
    return await _upsert_scoped_orchestration(
        conn, table="ai_channel_policy", id_col="channel_id",
        guild_id=guild_id, target_id=channel_id,
        orchestration_profile=orchestration_profile, updated_by=updated_by)


async def upsert_category_orchestration(conn: Any, *, guild_id: int,
                                        category_id: int,
                                        orchestration_profile: str | None,
                                        updated_by: int | None) -> dict | None:
    return await _upsert_scoped_orchestration(
        conn, table="ai_category_policy", id_col="category_id",
        guild_id=guild_id, target_id=category_id,
        orchestration_profile=orchestration_profile, updated_by=updated_by)


async def set_guild_orchestration_profile(conn: Any, *, guild_id: int,
                                          profile_key: str | None) -> str | None:
    """The shipped ai_guild_policy.orchestration_profile write's KV twin
    (see AI_ORCHESTRATION_PROFILE_KEY): clear (None) stores the empty
    string — the read side NULLIFs it back. Returns the PRIOR key (or
    None)."""
    prior = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id=$1 AND key=$2",
        (guild_id, AI_ORCHESTRATION_PROFILE_KEY), conn=conn)
    await execute(
        "INSERT INTO guild_settings (guild_id, key, value) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value=EXCLUDED.value",
        (guild_id, AI_ORCHESTRATION_PROFILE_KEY, profile_key or ""),
        conn=conn)
    if prior is None:
        return None
    return str(prior["value"]) or None


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


async def list_preset_profiles(conn: Any = None) -> list[dict]:
    """The shipped ai_db.list_preset_profiles: built-in presets, sorted
    alphabetically — all rows with ``is_preset = TRUE`` (the migration
    0030 seed, oracle 044)."""
    rows = await fetchall(
        "SELECT id, guild_id, name, body, scope, feature_key, is_preset "
        "FROM ai_instruction_profile WHERE is_preset ORDER BY name",
        (), conn=conn)
    return [dict(r) for r in rows]


async def get_preset_profile(preset_id: int,
                             conn: Any = None) -> dict | None:
    """One preset row by id — None when absent OR not flagged is_preset
    (the shipped describe_preset 'rejects rows missing is_preset = True'
    posture lives on this read)."""
    row = await fetchone(
        "SELECT id, guild_id, name, body, scope, feature_key, is_preset "
        "FROM ai_instruction_profile WHERE id=$1 AND is_preset",
        (preset_id,), conn=conn)
    return dict(row) if row else None


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


async def read_guild_orchestration_profile(
        guild_id: int, conn: Any = None) -> tuple[bool, str | None]:
    """(row_present, key) — the KV twin keeps a distinction the shipped
    single NULL column could not: a PRESENT row with the empty-string
    marker is an EXPLICIT clear (reads as key=None), an ABSENT row means
    the slice never wrote here (callers may fall back to the band-1
    approximation). The codex #187 P2: without the distinction an
    explicit guild clear resurrected the band-1 fallback."""
    row = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id=$1 AND key=$2",
        (guild_id, AI_ORCHESTRATION_PROFILE_KEY), conn=conn)
    if row is None:
        return False, None
    return True, (str(row["value"]) or None)


async def get_guild_orchestration_profile(guild_id: int,
                                          conn: Any = None) -> str | None:
    """The guild-default orchestration key, or None while unset/cleared
    (the shipped NULL column)."""
    return (await read_guild_orchestration_profile(guild_id, conn=conn))[1]


async def load_orchestration_overlays(guild_id: int) -> tuple[
        dict[int, str], dict[int, str]]:
    """(channel, category) maps of the NON-NULL orchestration_profile
    overrides — the shape the K10 profile-key reader consumes (most-
    specific-wins happens in sb/kernel/ai/orchestration.py)."""
    channel_rows = await fetchall(
        "SELECT channel_id, orchestration_profile FROM ai_channel_policy "
        "WHERE guild_id=$1 AND orchestration_profile IS NOT NULL "
        "ORDER BY channel_id", (guild_id,))
    category_rows = await fetchall(
        "SELECT category_id, orchestration_profile FROM ai_category_policy "
        "WHERE guild_id=$1 AND orchestration_profile IS NOT NULL "
        "ORDER BY category_id", (guild_id,))
    return ({int(r["channel_id"]): str(r["orchestration_profile"])
             for r in channel_rows},
            {int(r["category_id"]): str(r["orchestration_profile"])
             for r in category_rows})


# --- erasure -------------------------------------------------------------------------


async def detach_policy_editor(conn: Any, *, user_id: int) -> int:
    """NULL the subject's editorship stamps across the three override
    tables (the preset-authorship detach precedent — the rows themselves
    are guild config, not the subject's data)."""
    touched = 0
    for table, column in (("ai_channel_policy", "updated_by"),
                          ("ai_category_policy", "updated_by"),
                          ("ai_role_policy", "updated_by"),
                          ("ai_instruction_profile", "created_by")):
        result = await execute(
            f"UPDATE {table} SET {column}=NULL WHERE {column}=$1",  # noqa: S608
            (user_id,), conn=conn)
        digits = "".join(ch for ch in str(result) if ch.isdigit())
        touched += int(digits or 0)
    return touched


def ensure_policy_store_refs() -> None:
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("ai.policy_store")):
        engine("ai.policy_store")(_store_marker)
