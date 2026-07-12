"""settings + subsystem_bindings CRUD (band 1) — asyncpg SQL behind the K3
seam.

Migration: ``0009_settings.sql``. The two tables are the band-1 SETTINGS
subsystem's stores and ALSO ride its manifest `stores` facet
(sb/manifest/settings.py) — the store specs are minted HERE (sole physical
authority) and imported by the manifest, so `register_store` runs on either
import path.

Design-spec §4.1: there is NO public raw-KV API — the write helpers below
take an explicit txn `conn` and are called ONLY by the K7 scalar/binding
lane legs (sb/domain/settings/ops.py); the read side is exported as
installable ports (`make_settings_reader` / `make_binding_probe` for
sb.kernel.settings, `get_binding` for the binding lane's own reads).

Key model (compat item 5): the row key is the CANONICAL persisted key
string — the shipped `utils.settings_keys` vocabulary, verbatim. guild_id=0
is the global row (the S10 `COALESCE(guild_id,0)` precedent).
"""

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
    "BINDING_AUDIT_STORE",
    "BINDINGS_STORE",
    "SETTINGS_STORE",
    "delete_binding",
    "delete_setting",
    "get_binding",
    "get_bindings",
    "get_setting_rows",
    "insert_binding_audit",
    "make_binding_probe",
    "make_settings_reader",
    "upsert_binding",
    "upsert_setting",
]

# NAME_STABLE: the shipped KV `settings` table imports verbatim (§4.5 rule 5
# — key strings stay the canonical persisted vocabulary). bears_value=False
# => rollback class DECLARED_LOSS by posture (Q3-B): config is re-enterable,
# never money/audit-bearing; no reverse importer is registered.
SETTINGS_STORE = register_store(StoreSpec(
    table="settings",
    sole_writer=EngineRef("settings.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="settings",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "help", "setup"),
    bears_value=False,
    data_class=DataClass.NONE,   # guild config values; no member data
))

# RENAME: binding rows arrive from legacy KV pointer keys through each
# BindingSpec's `legacy_settings_key_aliases` map (decision 3 — the alias
# map is manifest data, so the forward import is generated, not hand-known).
# Physical shape: the SHIPPED oracle 022 columns (binding_name / target_id /
# status / version / last_updated_at / last_validated_at — migration 0038;
# goldens/economy/sweep_setlogchannel pins the row bytes).
BINDINGS_STORE = register_store(StoreSpec(
    table="subsystem_bindings",
    sole_writer=EngineRef("settings.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="subsystem_bindings",
    forward_map_kind=ForwardMapKind.RENAME,
    reader_domains=("diagnostics", "help", "setup"),
    bears_value=False,
    data_class=DataClass.NONE,   # channel/role/category pointers
))

# The shipped append-only bind/clear audit trail (oracle migration 022's
# `binding_audit_log`, migration 0038 here — preserved on guild leave by
# design, the oracle guild_lifecycle retention posture). Rows key on the
# acting operator's id (pseudonymous, S11 class 12) — erasure = TOMBSTONE
# (scrub actor column in place, keep the forensic skeleton); the body lands
# with the erasure band, the ref is DECLARED now (the kernel
# audit_log/event_outbox precedent).
BINDING_AUDIT_STORE = register_store(StoreSpec(
    table="binding_audit_log",
    sole_writer=EngineRef("settings.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.LEDGER,
    invariant_tag="binding_audit_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics",),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("settings.tombstone_binding_audit"),
))


# --- reads (the installable ports) ------------------------------------------------

async def get_setting_rows(guild_id: int, keys: tuple[str, ...] = (),
                           conn: Any = None) -> dict[str, str]:
    """All explicit rows for one guild (0 = global), optionally filtered."""
    if keys:
        rows = await fetchall(
            "SELECT key, value FROM settings WHERE guild_id = $1 AND key = ANY($2)",
            (guild_id, list(keys)), conn=conn)
    else:
        rows = await fetchall(
            "SELECT key, value FROM settings WHERE guild_id = $1", (guild_id,), conn=conn)
    return {r["key"]: r["value"] for r in rows}


def make_settings_reader():
    """The sb.kernel.settings reader port: (guild_id|None, declaration key)
    -> stored value | UNSET. Translates the declaration key to the
    persisted vocabulary via sb.kernel.settings.persisted_key."""
    from sb.kernel import settings as ksettings

    async def _reader(guild_id: int | None, decl_key: str) -> object:
        subsystem, _, name = decl_key.partition(".")
        key = ksettings.persisted_key(subsystem, name)
        row = await fetchone(
            "SELECT value FROM settings WHERE guild_id = $1 AND key = $2",
            (0 if guild_id is None else int(guild_id), key))
        if row is None:
            return ksettings.UNSET
        return row["value"]

    return _reader


async def get_binding(guild_id: int, subsystem: str, name: str,
                      conn: Any = None) -> int | None:
    """The bound pointer (None = unbound/unresolved) — binding-first reads
    resolve only 'bound' rows (the shipped arbitration posture)."""
    row = await fetchone(
        "SELECT target_id FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND binding_name = $3 "
        "AND status = 'bound'",
        (guild_id, subsystem, name), conn=conn)
    if row is None or row["target_id"] is None:
        return None
    return int(row["target_id"])


async def get_bindings(guild_id: int, subsystem: str, name: str,
                       conn: Any = None) -> tuple[int, ...]:
    """The binding's bound targets as a tuple (0 or 1 — the oracle 022
    shape keys one row per (guild, subsystem, binding_name); the 0009
    slot-multiplicity lane was a port invention, migration 0038)."""
    target = await get_binding(guild_id, subsystem, name, conn=conn)
    return () if target is None else (target,)


async def fetchall_bindings(guild_id: int, conn: Any = None) -> list[dict]:
    """Every binding row for one guild (the A-15 export inventory read)."""
    return await fetchall(
        "SELECT subsystem, binding_name, kind, target_id, status "
        "FROM subsystem_bindings "
        "WHERE guild_id = $1 ORDER BY subsystem, binding_name",
        (guild_id,), conn=conn)


def make_binding_probe():
    """The sb.kernel.settings ON_WHEN_BOUND probe: bound-for-guild?"""

    async def _probe(guild_id: int, binding_name: str) -> bool:
        subsystem, _, name = binding_name.partition(".")
        if not name:
            return False
        return await get_binding(guild_id, subsystem, name) is not None

    return _probe


# --- writes (K7 leg helpers ONLY — always conn-threaded, §4.1) ---------------------

async def upsert_setting(conn: Any, *, guild_id: int, key: str, value: str) -> str | None:
    """Upsert one explicit row; returns the PRIOR value (None = was unset)."""
    prior = await fetchone(
        "SELECT value FROM settings WHERE guild_id = $1 AND key = $2",
        (guild_id, key), conn=conn)
    await execute(
        "INSERT INTO settings (guild_id, key, value) VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value, "
        "updated_at = now()",
        (guild_id, key, value), conn=conn)
    return None if prior is None else prior["value"]


async def delete_setting(conn: Any, *, guild_id: int, key: str) -> str | None:
    prior = await fetchone(
        "SELECT value FROM settings WHERE guild_id = $1 AND key = $2",
        (guild_id, key), conn=conn)
    await execute("DELETE FROM settings WHERE guild_id = $1 AND key = $2",
                  (guild_id, key), conn=conn)
    return None if prior is None else prior["value"]


async def upsert_binding(conn: Any, *, guild_id: int, subsystem: str, name: str,
                         kind: str, resource_id: int) -> dict | None:
    """Upsert one binding row to 'bound' (the shipped set_binding write —
    version bumps on re-bind, both stamps refresh). Returns the PRIOR
    row's {target_id, status} (None = the binding had no row — the
    shipped 'unresolved' vocabulary for absent)."""
    prior = await fetchone(
        "SELECT target_id, status FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND binding_name = $3",
        (guild_id, subsystem, name), conn=conn)
    await execute(
        "INSERT INTO subsystem_bindings (guild_id, subsystem, binding_name, "
        "kind, target_id, status, last_updated_at, last_validated_at, version) "
        "VALUES ($1, $2, $3, $4, $5, 'bound', now(), now(), 1) "
        "ON CONFLICT (guild_id, subsystem, binding_name) DO UPDATE SET "
        "kind = EXCLUDED.kind, target_id = EXCLUDED.target_id, "
        "status = 'bound', last_updated_at = now(), last_validated_at = now(), "
        "version = subsystem_bindings.version + 1",
        (guild_id, subsystem, name, kind, resource_id), conn=conn)
    if prior is None:
        return None
    return {"target_id": (None if prior["target_id"] is None
                          else int(prior["target_id"])),
            "status": str(prior["status"])}


async def delete_binding(conn: Any, *, guild_id: int, subsystem: str,
                         name: str) -> dict | None:
    """Delete one binding row; returns the removed row's
    {target_id, status} (None = no row existed)."""
    row = await fetchone(
        "DELETE FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND binding_name = $3 "
        "RETURNING target_id, status",
        (guild_id, subsystem, name), conn=conn)
    if row is None:
        return None
    return {"target_id": (None if row["target_id"] is None
                          else int(row["target_id"])),
            "status": str(row["status"])}


async def insert_binding_audit(conn: Any, *, mutation_id: str, guild_id: int,
                               subsystem: str, binding_name: str,
                               actor_type: str, actor_id: int, action: str,
                               old_target_id: int | None,
                               new_target_id: int | None,
                               old_status: str | None,
                               new_status: str | None) -> None:
    """Append one binding_audit_log row (the shipped
    utils/db/bindings.py audit insert — IN the same txn as the binding
    write, AFTER it; the pipeline's write-then-audit ordering)."""
    await execute(
        "INSERT INTO binding_audit_log "
        "(mutation_id, guild_id, subsystem, binding_name, actor_type, "
        "actor_id, action, old_target_id, new_target_id, old_status, "
        "new_status) "
        "VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
        (mutation_id, guild_id, subsystem, binding_name, actor_type,
         actor_id, action, old_target_id, new_target_id, old_status,
         new_status), conn=conn)


async def tombstone_binding_audit_actor(conn: Any, *, user_id: int) -> int:
    """Privacy erasure (S11 class 12, the TOMBSTONE posture): scrub the
    subject's actor identity in place — actor_id is NOT NULL, so the
    tombstone value is 0 (never a row delete; the forensic skeleton and
    the binding trail stay). Returns rows scrubbed."""
    rows = await fetchall(
        "UPDATE binding_audit_log SET actor_id = 0 "
        "WHERE actor_id = $1 RETURNING id",
        (user_id,), conn=conn)
    return len(rows)


@engine("settings.store")
class _SettingsStoreEngine:
    """The sole-writer marker (INV-style): every write to `settings` /
    `subsystem_bindings` goes through this module's conn-threaded helpers,
    invoked only by the K7 lane legs (sb/domain/settings/ops.py)."""


def ensure_refs() -> None:
    """Idempotent re-arm (the clear_ref_table test seam wipes import-time
    registrations; see the manifest ENSURE_REFS hook)."""
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("settings.store")):
        engine("settings.store")(_SettingsStoreEngine)
