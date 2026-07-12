"""Settings service (band 1) — the typed READ side + guild config snapshot.

Ports the shipped `services/settings_resolution.py` semantics onto the K7
resolve seam: `SettingResolution` (value + provenance + default + valid +
raw + diagnostics) is the shipped frozen result shape, verbatim fields; the
source chain is now the kernel tri-state (`per-guild explicit → global
explicit → activation/default terminus`, design-spec §4.1) instead of the
legacy `guild_config` TTL cache + raw KV read. Coercion + validation (falls
back to `default`, `valid=False`) are ported behavior.

Also here:
  * `export_guild_config` — the A-15 one-inventory snapshot: a
    manifest-driven read of per-guild explicit setting rows + binding rows
    (design-spec §4.1/§4.5). The restore half is a spec-06 draft-lane
    consumer (Producer IMPORT_REPAIR) — successor work, see D-0025.
  * `install_platform_state_store` — the S15 latch persistence
    (sb.kernel.platform_governance.install_state_store): latch tokens live
    as `platform.*` rows in the `settings` table (kernel-internal state,
    not declared SettingSpecs — deviation ledgered in D-0025).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from sb.kernel import settings as ksettings
from sb.kernel.db import settings as db_settings

logger = logging.getLogger("sb.domain.settings.service")

__all__ = [
    "SettingResolution",
    "export_guild_config",
    "install_platform_state_store",
    "install_read_ports",
    "resolve_setting",
    "coerce_value",
]

Provenance = Literal["default", "explicit", "global", "activation"]


@dataclass(frozen=True)
class SettingResolution:
    """Shipped shape (services/settings_resolution.py), re-based on the
    tri-state chain: provenance gains `explicit|global|activation` in place
    of the legacy `legacy_kv|global_kv` (the KV table IS the explicit
    store now — same rows, new names)."""

    subsystem: str
    name: str
    value: Any
    provenance: Provenance
    default: Any
    valid: bool = True
    raw: str | None = None
    diagnostics: tuple[str, ...] = ()


_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def coerce_value(spec: object, raw: str) -> tuple[Any, bool, tuple[str, ...]]:
    """Coerce a stored string to the spec's declared type (ported semantics:
    failure -> (default, False, diagnostics))."""
    diagnostics: list[str] = []
    token = str(getattr(spec, "value_type", "str"))
    default = getattr(spec, "default", None)
    try:
        if token == "bool":
            lowered = raw.strip().lower()
            if lowered in _TRUE_TOKENS:
                return True, True, ()
            if lowered in _FALSE_TOKENS:
                return False, True, ()
            raise ValueError(f"not a bool token: {raw!r}")
        if token == "int":
            value: Any = int(raw.strip())
        elif token == "float":
            value = float(raw.strip())
        elif token == "str":
            value = raw
        else:  # list variants — stored as JSON (G-2)
            import json
            value = json.loads(raw)
            if not isinstance(value, list):
                raise ValueError("list-typed setting row is not a JSON list")
        bounds = getattr(spec, "bounds", None)
        if bounds and token in ("int", "float") and len(bounds) == 2:
            lo, hi = bounds
            if not (lo <= value <= hi):
                raise ValueError(f"{value!r} outside bounds {bounds!r}")
        allowed = getattr(spec, "allowed_values", ()) or ()
        if allowed and value not in allowed:
            raise ValueError(f"{value!r} not in allowed_values")
        return value, True, ()
    except (ValueError, TypeError) as exc:
        diagnostics.append(f"coercion_failed: {exc}")
        return default, False, tuple(diagnostics)


async def resolve_setting(guild_id: int, subsystem: str, name: str,
                          spec: object | None = None) -> SettingResolution:
    """Single-key typed resolution over THE kernel read seam."""
    decl_map = {d.name: d for d in ksettings.iter_declarations(subsystem)}
    decl = decl_map.get(name)
    if decl is None:
        raise LookupError(f"setting {subsystem}.{name} is not declared")
    value = await ksettings.resolve(guild_id, subsystem, name)
    # Distinguish provenance by re-reading the explicit chain (cheap; the
    # kernel seam stays the single source of resolution truth).
    key = f"{subsystem}.{name}"
    per_guild = await ksettings._reader(guild_id, key)  # noqa: SLF001 — sibling module
    if per_guild is not ksettings.UNSET:
        provenance: Provenance = "explicit"
        raw = str(per_guild)
    else:
        global_row = await ksettings._reader(None, key)  # noqa: SLF001
        if global_row is not ksettings.UNSET:
            provenance = "global"
            raw = str(global_row)
        else:
            provenance = "activation" if decl.activation is not None else "default"
            raw = None
    if raw is not None and spec is not None:
        value, valid, diagnostics = coerce_value(spec, raw)
        return SettingResolution(subsystem, name, value, provenance,
                                 getattr(spec, "default", decl.default),
                                 valid, raw, diagnostics)
    return SettingResolution(subsystem, name, value, provenance, decl.default,
                             True, raw)


def install_read_ports() -> None:
    """Wire the kernel settings seam to the real DB store (composition
    root; design-spec §4.1 — the store read is a private installable port)."""
    ksettings.install_settings_reader(db_settings.make_settings_reader())
    ksettings.install_binding_probe(db_settings.make_binding_probe())


# --- A-15: the guild config snapshot (export half) -------------------------------

async def export_guild_config(guild_id: int) -> dict:
    """Manifest-driven snapshot of one guild's EXPLICIT config: setting rows
    keyed by the persisted vocabulary + binding rows. The one-inventory rule
    (A-15): restore, the CUT-2 importer, and this export walk the same
    declared-store inventory."""
    declared_keys = tuple(sorted(
        ksettings.persisted_key(d.subsystem, d.name)
        for d in ksettings.iter_declarations()))
    rows = await db_settings.get_setting_rows(guild_id, declared_keys)
    bindings = await db_settings.fetchall_bindings(guild_id)
    return {
        "schema": 1,
        "guild_id": guild_id,
        "settings": {k: rows[k] for k in sorted(rows)},
        "bindings": [
            # keys track the oracle-shape columns (migration 0038):
            # binding_name/target_id/status — the pre-0038 name/slot/
            # resource_id keys were the invented-schema twins.
            {"subsystem": b["subsystem"], "name": b["binding_name"],
             "kind": b["kind"], "target_id": b["target_id"],
             "status": b["status"]}
            for b in bindings
        ],
    }


# --- S15: the platform-governance latch store -------------------------------------

# platform_governance's ports are SYNC (read(key) -> str|None; write(key,
# value)) — a write-through in-memory view over `platform.*` rows in the
# `settings` table (guild_id=0), warmed at boot by load_platform_state()
# and persisted fire-and-forget on write (latches are once-per-state-change
# markers; a lost in-flight persist re-fires the notice, never corrupts).
_platform_state: dict[str, str] = {}


async def load_platform_state() -> int:
    """Boot warm-up: read every `platform.*` row into the sync view.
    Composition-root obligation (call before gateway serve)."""
    rows = await db_settings.get_setting_rows(0)
    _platform_state.clear()
    _platform_state.update(
        {k: v for k, v in rows.items() if k.startswith("platform.")})
    return len(_platform_state)


def _state_read(key: str) -> str | None:
    return _platform_state.get(key)


def _state_write(key: str, value: str) -> None:
    """Sync port write: update the in-memory view NOW, persist through the
    K7 lane fire-and-forget (ORDER 004 item 4 — the raw upsert bypassed the
    sole-writer/audit lane; `settings.platform_latch` is its audited home).
    A failed persist stays best-effort BY DESIGN: latches are once-per-
    state-change markers — a lost write re-fires the notice at the next
    boot warm-up, never corrupts (spec 14 §2.B)."""
    import uuid

    _platform_state[key] = value

    async def _persist() -> None:
        try:
            from sb.domain.settings.ops import PLATFORM_LATCH
            from sb.kernel.interaction.request import ActorRef
            from sb.kernel.workflow import engine
            from sb.kernel.workflow.context import WorkflowContext
            from sb.spec.outcomes import SUCCESS

            result = await engine.run(PLATFORM_LATCH, WorkflowContext(
                actor=ActorRef(user_id=None, is_guild_operator=False,
                               is_bot_owner=False, is_dm=False,
                               actor_type="system", member_tier=None),
                guild_id=0,
                request_id=f"platform-latch-{uuid.uuid4().hex}",
                params={"key": key, "value": value}))
            if result.outcome != SUCCESS:
                logger.warning("platform latch persist %s for %s: %s",
                               result.outcome, key, result.user_message)
        except Exception:  # noqa: BLE001 — latch persist is best-effort
            logger.warning("platform latch persist failed for %s", key,
                           exc_info=True)

    try:
        import asyncio

        asyncio.get_running_loop().create_task(_persist())
    except RuntimeError:
        logger.debug("no running loop; platform latch %s persists at next boot warm-up", key)


def install_platform_state_store() -> None:
    from sb.kernel import platform_governance

    platform_governance.install_state_store(_state_read, _state_write)
