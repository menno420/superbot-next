"""Governance in-process cache (band 5) — disbot/governance/cache.py
verbatim: version-stamped, tier-keyed, thread-id-isolated (RC-2 /
ISSUE-016), role-fingerprinted only for guilds with role-scoped
overrides (Phase 3.1 cache-explosion guard).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

__all__ = [
    "forget_guild",
    "invalidate_guild_cache",
    "register_failed_subsystems",
    "reset_cache_for_tests",
]

_CACHE: dict[tuple, tuple[float, Any]] = {}
_CACHE_VERSION: dict[int, int] = {}
_CACHE_LOCK = asyncio.Lock()
_CACHE_TTL = 60.0
_CACHE_CLEANUP_THRESHOLD = 50_000

# Guilds with at least one role-scoped visibility override in DB.
_guild_has_role_overrides: dict[int, bool] = {}

# Subsystems whose registration failed at boot — treated INTERNAL.
_FAILED_SUBSYSTEMS: set[str] = set()


def _cache_ver(guild_id: int) -> int:
    return _CACHE_VERSION.get(guild_id, 0)


def _cache_key(
    guild_id: int,
    channel_id: int | None,
    tier: str,
    role_ids: frozenset[int] = frozenset(),
    *,
    thread_id: int | None = None,
) -> tuple:
    if _guild_has_role_overrides.get(guild_id, False) and role_ids:
        role_fingerprint = hash(role_ids)
        return (guild_id, _cache_ver(guild_id), channel_id, thread_id,
                tier, role_fingerprint)
    return (guild_id, _cache_ver(guild_id), channel_id, thread_id, tier)


def _cache_get(key: tuple) -> Any:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.monotonic() - ts > _CACHE_TTL:
        return None
    return value


def _cache_set(key: tuple, value: Any) -> None:
    _CACHE[key] = (time.monotonic(), value)
    if len(_CACHE) > _CACHE_CLEANUP_THRESHOLD:
        cutoff = time.monotonic() - _CACHE_TTL
        stale = [k for k, (ts, _) in _CACHE.items() if ts < cutoff]
        for k in stale:
            _CACHE.pop(k, None)


def invalidate_guild_cache(guild_id: int) -> None:
    """Increment version counter — old keys become unreachable (O(1))."""
    _CACHE_VERSION[guild_id] = _cache_ver(guild_id) + 1


def forget_guild(guild_id: int) -> None:
    """Remove visibility cache state (guild teardown; capability override
    state lives in execution.py and is cleared separately — the shipped
    layering rule: cache must not import execution)."""
    _CACHE_VERSION.pop(guild_id, None)
    _guild_has_role_overrides.pop(guild_id, None)


def register_failed_subsystems(subsystems: set[str]) -> None:
    """Mark subsystems whose registration failed as INTERNAL (invisible)."""
    _FAILED_SUBSYSTEMS.update(subsystems)


def diagnostics_snapshot() -> dict[str, object]:
    """Snapshot of governance cache state (the shipped !platform caches
    provider — band-1 diagnostic reads it)."""
    return {
        "size": len(_CACHE),
        "guilds_versioned": len(_CACHE_VERSION),
        "guilds_with_role_overrides": sum(_guild_has_role_overrides.values()),
        "failed_subsystems": sorted(_FAILED_SUBSYSTEMS),
    }


def reset_cache_for_tests() -> None:
    _CACHE.clear()
    _CACHE_VERSION.clear()
    _guild_has_role_overrides.clear()
    _FAILED_SUBSYSTEMS.clear()
