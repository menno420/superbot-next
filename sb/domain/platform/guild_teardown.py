"""Unified guild lifecycle teardown (band 5) — disbot/guild_lifecycle.py
compiled: the shipped 31-step hardcoded sequence becomes a REGISTRY of
named teardown hooks (each band registers its own; higher-level state
registers before lower-level), with the shipped per-step isolation (one
failing hook logs a warning and never aborts the rest).

Band 5 registers the hooks whose subsystems exist TODAY (governance
caches+rows in the shipped order, command-access cache+rows, the role
family, proof locks, xp/karma/economy/settings in-memory seams). Later
bands append via register_teardown at manifest import.

The composition root / live adapter calls ``teardown(guild_id)`` from
on_guild_remove.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger("sb.domain.platform.guild_teardown")

__all__ = [
    "register_teardown",
    "registered_teardowns",
    "reset_teardowns_for_tests",
    "teardown",
]

TeardownHook = Callable[[int], Any]

_HOOKS: list[tuple[str, TeardownHook]] = []


def register_teardown(name: str, hook: TeardownHook) -> None:
    """Idempotent by name: re-registration replaces (hot-reload-friendly)."""
    for i, (existing, _) in enumerate(_HOOKS):
        if existing == name:
            _HOOKS[i] = (name, hook)
            return
    _HOOKS.append((name, hook))


def registered_teardowns() -> tuple[str, ...]:
    return tuple(name for name, _ in _HOOKS)


def reset_teardowns_for_tests() -> None:
    _HOOKS.clear()
    _register_band5_hooks()


async def teardown(guild_id: int) -> dict[str, str]:
    """Purge ALL registered per-guild state. Safe on a never-initialised
    guild (hooks no-op on missing keys). Returns name -> 'ok'|'failed'."""
    logger.info("guild_teardown: beginning cleanup for guild=%d", guild_id)
    results: dict[str, str] = {}
    for name, hook in list(_HOOKS):
        try:
            out = hook(guild_id)
            if inspect.isawaitable(out):
                await out
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001 — per-step isolation (shipped)
            results[name] = "failed"
            logger.warning("guild_teardown: %s failed: %s", name, exc)
    logger.info("guild_teardown: complete for guild=%d", guild_id)
    return results


# --- the band-5 hook roster ------------------------------------------------------------

def _register_band5_hooks() -> None:
    # 13/14 (shipped order): capability overrides BEFORE the visibility
    # cache; then the governance DB rows (audit log preserved).
    async def _governance(guild_id: int) -> None:
        from sb.domain.governance.service import teardown_guild

        await teardown_guild(guild_id)

    register_teardown("governance", _governance)

    # 22: command-access policy — cache and DB rows drop together.
    async def _command_access(guild_id: int) -> None:
        from sb.domain.platform.command_access import delete_guild_rows

        await delete_guild_rows(guild_id)

    register_teardown("command_access", _command_access)

    # 23-30: the role family (menus/modes/grants/pickup/thresholds/
    # exemptions/reaction_roles).
    async def _roles(guild_id: int) -> None:
        from sb.domain.role.store import delete_guild_role_rows

        await delete_guild_role_rows(guild_id)

    register_teardown("role_family", _roles)

    # 31: proof-channel timed locks.
    async def _proof(guild_id: int) -> None:
        from sb.domain.proof_channel.store import delete_guild_locks

        await delete_guild_locks(guild_id)

    register_teardown("proof_channel_locks", _proof)


_register_band5_hooks()
