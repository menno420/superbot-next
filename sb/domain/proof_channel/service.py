"""Proof-channel prize sessions (band 5) — cogs/proof_channel_cog.py
compiled: lock-for-winner / unlock / timed locks with the bug-#8 durable
deadline rows. Channel permission mutations ride the installable
ChannelPermActions port (the RC-21-sibling pattern, fail-loud default);
the timed auto-unlock is the ``proof:lock_reconcile`` sweep (K9 pattern
— the shipped per-lock asyncio timers + on_ready reconcile collapse into
ONE minute-granularity lane, D-0041).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol

from sb.domain.proof_channel import store

logger = logging.getLogger("sb.domain.proof_channel")

__all__ = [
    "ChannelPermActions",
    "active_channel_actions",
    "bound_proof_channel",
    "install_channel_actions",
    "reconcile_due_locks",
    "reset_proof_ports_for_tests",
]


class ChannelPermActions(Protocol):
    """Adapter-implemented channel-permission mutations."""

    async def lock_channel_for_winner(self, guild_id: int, channel_id: int,
                                      winner_id: int) -> None: ...
    async def unlock_channel(self, guild_id: int, channel_id: int) -> None: ...


class _NoActions:
    async def _refuse(self, *_a, **_k) -> None:
        raise RuntimeError(
            "ChannelPermActions not installed — the composition root must "
            "install the discord adapter's implementation "
            "(sb.domain.proof_channel.service.install_channel_actions)")

    lock_channel_for_winner = unlock_channel = _refuse


_actions: ChannelPermActions = _NoActions()


def install_channel_actions(actions: ChannelPermActions) -> None:
    global _actions
    _actions = actions


def active_channel_actions() -> ChannelPermActions:
    return _actions


def reset_proof_ports_for_tests() -> None:
    global _actions
    _actions = _NoActions()


async def bound_proof_channel(guild_id: int) -> int | None:
    """The proof_channel binding (Q-0064 pattern; the name-based '#proof'
    fallback is the live adapter's compatibility read)."""
    try:
        from sb.kernel.db.settings import get_binding

        return await get_binding(guild_id, "proof_channel", "proof_channel")
    except Exception:  # noqa: BLE001 — unbound
        return None


def _utcnow() -> datetime:
    """The lane clock — reads through ``time.time()`` (identical to
    ``datetime.now`` live) so the ONE wall-clock seam the parity harness
    pins covers the lock/reconcile lane too: LOCK_TIMED stamps
    ``unlock_at`` from the leg's ``ctx.clock()``; the sweep's due-read
    must ride the SAME seam or the deadline never matches under a pinned
    clock (the band-4 karma two-clocks bug, D-0061)."""
    import time

    return datetime.fromtimestamp(time.time(), tz=timezone.utc)


async def reconcile_due_locks(now: datetime | None = None) -> int:
    """The proof:lock_reconcile fire: unlock every lock whose deadline
    passed (survives restarts — bug #8), dropping the row through the
    audited K7 unlock lane. Without the channel-actions port every row
    is kept (honest wait)."""
    from sb.domain.proof_channel.ops import RECORD_UNLOCK
    from sb.kernel.scheduler.due_queue import SYSTEM_ACTOR
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext

    now = now or _utcnow()
    due = await store.list_due_locks(now)
    resolved = 0
    for row in due:
        gid, cid = int(row["guild_id"]), int(row["channel_id"])
        try:
            await _actions.unlock_channel(gid, cid)
        except RuntimeError:
            logger.warning("proof: channel actions port not installed; "
                           "reconcile deferred")
            return resolved
        except Exception as exc:  # noqa: BLE001 — retry next sweep
            logger.warning("proof: unlock failed for guild=%s channel=%s: %s",
                           gid, cid, exc)
            continue
        ctx = WorkflowContext(
            actor=SYSTEM_ACTOR, guild_id=gid,
            request_id=f"proofunlock:{gid}:{cid}:{int(now.timestamp())}",
            confirmed=True,
            params={"channel_id": cid, "reason": "timed unlock"},
            clock=lambda: _utcnow())
        await engine.run(RECORD_UNLOCK, ctx)
        resolved += 1
    return resolved
