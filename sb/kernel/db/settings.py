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
from sb.spec.refs import EngineRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "BINDINGS_STORE",
    "SETTINGS_STORE",
    "delete_binding",
    "delete_setting",
    "get_binding",
    "get_bindings",
    "get_setting_rows",
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
    row = await fetchone(
        "SELECT resource_id FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND name = $3 AND slot = 0",
        (guild_id, subsystem, name), conn=conn)
    return None if row is None else int(row["resource_id"])


async def get_bindings(guild_id: int, subsystem: str, name: str,
                       conn: Any = None) -> tuple[int, ...]:
    """All slots of a multiplicity>1 binding, slot-ordered."""
    rows = await fetchall(
        "SELECT resource_id FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND name = $3 ORDER BY slot",
        (guild_id, subsystem, name), conn=conn)
    return tuple(int(r["resource_id"]) for r in rows)


async def fetchall_bindings(guild_id: int, conn: Any = None) -> list[dict]:
    """Every binding row for one guild (the A-15 export inventory read)."""
    return await fetchall(
        "SELECT subsystem, name, slot, kind, resource_id FROM subsystem_bindings "
        "WHERE guild_id = $1 ORDER BY subsystem, name, slot",
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
                         kind: str, resource_id: int, slot: int = 0) -> int | None:
    prior = await fetchone(
        "SELECT resource_id FROM subsystem_bindings "
        "WHERE guild_id = $1 AND subsystem = $2 AND name = $3 AND slot = $4",
        (guild_id, subsystem, name, slot), conn=conn)
    await execute(
        "INSERT INTO subsystem_bindings (guild_id, subsystem, name, slot, kind, resource_id) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "ON CONFLICT (guild_id, subsystem, name, slot) DO UPDATE SET "
        "kind = EXCLUDED.kind, resource_id = EXCLUDED.resource_id, updated_at = now()",
        (guild_id, subsystem, name, slot, kind, resource_id), conn=conn)
    return None if prior is None else int(prior["resource_id"])


async def delete_binding(conn: Any, *, guild_id: int, subsystem: str, name: str,
                         slot: int | None = None) -> int:
    """Delete one slot (or all slots when slot=None); returns rows removed."""
    if slot is None:
        rows = await fetchall(
            "DELETE FROM subsystem_bindings "
            "WHERE guild_id = $1 AND subsystem = $2 AND name = $3 RETURNING slot",
            (guild_id, subsystem, name), conn=conn)
    else:
        rows = await fetchall(
            "DELETE FROM subsystem_bindings "
            "WHERE guild_id = $1 AND subsystem = $2 AND name = $3 AND slot = $4 "
            "RETURNING slot",
            (guild_id, subsystem, name, slot), conn=conn)
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
