"""Games substrate service (band 6) — the world-card read surface, the
stranded-escrow recovery sweep (session_gc), and the hub overview.

session_gc is the shipped ``services/game_state_cleanup.py`` GC re-homed
onto the K9 declared-task rail (the S6 A-8 consumer list named it): an
IN_MEMORY interval sweep that finds checkpoints past the 24 h TTL,
refunds any staked ``bet`` through the AUDITED K7 lane
(games.gc_sweep_row — credit + ledger row + precise per-row delete in ONE
txn), and deletes stale no-money rows the same way. Safer than shipped,
deliberately: a failing refund KEEPS its row for the next sweep (shipped
cleared it; the ledger must never lose a stranded stake silently —
deviation ledgered D-0042)."""

from __future__ import annotations

import logging

from sb.domain.games import store, xp as game_xp
from sb.spec.refs import HandlerRef, handler, is_registered

logger = logging.getLogger("sb.domain.games.service")

__all__ = [
    "recover_escrow",
    "session_gc_fire",
    "world_card_text",
]


async def world_card_text(user_id: int, guild_id: int) -> str:
    """The shipped world card (views/explore/world_card.py semantics,
    text-rendered): shared world level from SUM(game_xp) through the ONE
    curve + per-game standing lines."""
    level, total = await game_xp.shared_level(user_id, guild_id)
    rows = await store.game_xp_rows(user_id, guild_id)
    lines = [f"🌍 **World level {level}** — {total:,} game XP total"]
    if not rows:
        lines.append("No game XP yet — play any game to start your track.")
    for row in rows:
        emoji, label = game_xp.game_display(str(row["game"]))
        lines.append(f"{emoji} {label}: **{int(row['xp']):,}** XP")
    return "\n".join(lines)


async def _sweep_row(row: dict, *, reason: str) -> bool:
    """Refund-and-clear ONE stranded row through the audited lane."""
    from sb.kernel.scheduler.due_queue import SYSTEM_ACTOR
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext
    from sb.spec.refs import WorkflowRef

    ctx = WorkflowContext(
        actor=SYSTEM_ACTOR, guild_id=int(row["guild_id"]),
        request_id=f"games.gc:{row['id']}", confirmed=True,
        params={"row": row, "reason": reason})
    result = await engine.run(
        engine_spec_for("games.gc_sweep_row"), ctx)
    return getattr(result, "outcome", None) == "success"


def engine_spec_for(op_key: str):
    from sb.kernel.workflow.registry import REGISTRY
    from sb.spec.refs import WorkflowRef

    return REGISTRY.resolve(WorkflowRef(op_key))


async def session_gc_fire(ctx: object = None) -> dict:
    """The games:session_gc ManagedTaskSpec body — sweep checkpoints past
    the TTL; refund staked rows; failures keep their rows (retry next
    sweep). Returns counts for the fire record."""
    import datetime as dt

    now = int(dt.datetime.now(tz=dt.timezone.utc).timestamp())
    try:
        rows = await store.list_stale(now=now)
    except Exception as exc:  # noqa: BLE001 — DB-down sweep skips honestly
        logger.warning("session_gc sweep skipped: %s", exc)
        return {"swept": 0, "failed": 0, "skipped": True}
    swept = failed = 0
    for row in rows:
        try:
            ok = await _sweep_row(row, reason="games:gc_refund")
        except Exception:  # noqa: BLE001 — per-row isolation
            logger.warning("session_gc row %s failed", row.get("id"),
                           exc_info=True)
            ok = False
        swept += 1 if ok else 0
        failed += 0 if ok else 1
    if swept:
        logger.info("session_gc: swept %d stale checkpoint(s), %d failed",
                    swept, failed)
    return {"swept": swept, "failed": failed, "skipped": False}


async def recover_escrow(subsystem: str, *, guild_id: int | None = None,
                         reason: str) -> int:
    """Prompt refund of EVERY stranded row for *subsystem* (the shipped
    cog_load / on_guild_remove recovery, callable from the composition
    root at CUT-1) — same audited lane as the GC."""
    try:
        rows = await store.list_active(subsystem, guild_id=guild_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s escrow recovery skipped: %s", subsystem, exc)
        return 0
    refunded = 0
    for row in rows:
        try:
            if await _sweep_row(row, reason=reason):
                refunded += 1
        except Exception:  # noqa: BLE001
            logger.warning("%s escrow recovery row %s failed", subsystem,
                           row.get("id"), exc_info=True)
    return refunded


@handler("games.session_gc_fire")
async def _session_gc_handler(ctx: object) -> dict:
    return await session_gc_fire(ctx)


@handler("games.world_card_view")
async def _world_card_view(req: object) -> dict:
    actor = getattr(req, "actor", None)
    uid = int(getattr(actor, "user_id", 0) or 0)
    gid = int(getattr(req, "guild_id", 0) or 0)
    return {"text": await world_card_text(uid, gid)}


def ensure_service_refs() -> None:
    if not is_registered(HandlerRef("games.session_gc_fire")):
        handler("games.session_gc_fire")(_session_gc_handler)
    if not is_registered(HandlerRef("games.world_card_view")):
        handler("games.world_card_view")(_world_card_view)
