"""Boot-gate LEG C — remote parity (frozen L0 spec 01 §3.3-§3.4): snapshot
command paths vs the Discord remote tree. NON-FATAL: divergence is a gated
snapshot→Discord sync (`REMOTE_LAG`), never a refused boot. Lifts the
shipped `command_tree_sync._remote_paths` + `SyncOutcome` verbatim
(duck-typed — no discord import; option types 1/2 are the subcommand kinds).
Direction is ALWAYS snapshot→Discord.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from sb.app.boot_gate import snapshot_command_paths

logger = logging.getLogger("sb.app.tree_sync")

__all__ = ["SyncOutcome", "sync_remote"]

_SUBCOMMAND_TYPE_VALUES = {1, 2}   # subcommand, subcommand_group


def _remote_paths(commands: Iterable[object], prefix: str = "") -> set[str]:
    """Qualified paths for the REMOTE tree (shipped verbatim, duck-typed)."""
    out: set[str] = set()
    for cmd in commands:
        path = f"{prefix}{cmd.name}"
        out.add(path)
        subs = [
            opt for opt in (getattr(cmd, "options", None) or [])
            if getattr(getattr(opt, "type", None), "value", getattr(opt, "type", None))
            in _SUBCOMMAND_TYPE_VALUES
        ]
        out |= _remote_paths(subs, prefix=f"{path} ")
    return out


@dataclass(frozen=True)
class SyncOutcome:
    """What the auto-sync did, for logging + tests (it never raises) —
    shipped shape verbatim."""

    synced: bool
    reason: str  # disabled | fetch_failed | unchanged | sync_failed | synced
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


async def sync_remote(bot: object, committed: dict, *, enabled: bool) -> SyncOutcome:
    """Leg C: compare the SNAPSHOT's slash paths against Discord's and sync
    snapshot→Discord iff they differ. Never raises (REMOTE_LAG is non-fatal)."""
    if not enabled:
        logger.debug("leg C: disabled via AUTO_SYNC_COMMANDS")
        return SyncOutcome(False, "disabled")

    tree = getattr(bot, "tree", None)
    try:
        local = snapshot_command_paths(committed)
        remote = _remote_paths(await tree.fetch_commands())
    except Exception:  # noqa: BLE001 — non-fatal by contract
        logger.warning("leg C: fetch/compare failed (non-fatal)", exc_info=True)
        return SyncOutcome(False, "fetch_failed")

    if local == remote:
        logger.info("leg C: command tree in sync (%d commands)", len(local))
        return SyncOutcome(False, "unchanged")

    added = tuple(sorted(local - remote))
    removed = tuple(sorted(remote - local))
    try:
        synced = await tree.sync()
    except Exception as exc:  # noqa: BLE001 — HTTP failure is non-fatal
        logger.warning("leg C: tree.sync() failed (non-fatal): %s", exc)
        return SyncOutcome(False, "sync_failed", added, removed)

    logger.info("leg C: REMOTE_LAG resolved (+%d/-%d) — synced %d commands",
                len(added), len(removed), len(synced))
    return SyncOutcome(True, "synced", added, removed)
