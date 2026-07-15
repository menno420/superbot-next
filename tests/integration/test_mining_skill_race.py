"""Skill-spend over-allocation race regression — the advisory-lock guard on
`mining.skill` (`sb/domain/mining/ops.py::_record_skill`, fenced by
`sb/domain/mining/store.py::lock_skill_slot`), proven on a real Postgres with
two genuinely concurrent transactions exactly like
`tests/integration/test_mining_vault_upgrade_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-5: the WP-5 skill write golden pins the
single-actor `!skill <branch>` spend, but a golden cannot express a two-txn
RACE. The ported `skill_service.allocate` reads the player's allocation AND the
game-XP level to size the SHARED available-points budget
(`min(level, SOFT_TOTAL_CAP) − total_spent`), checks `n <= avail`, then upserts
the branch's ABSOLUTE point total — a read-then-settle over a cross-branch budget
spread across per-branch `player_skills` rows that may not exist yet, so
`FOR UPDATE` alone can lock nothing. No coins move, so `check_money_race` does
NOT cover it; the advisory lock is its ONLY guard.

Pre-fix shape (no advisory lock): a level-1 player has exactly 1 available point.
Two concurrent spends into DIFFERENT branches (mining / combat) both read
`total_spent = 0`, both pass `1 <= avail(=1)`, and both upsert their branch to 1
— the player spends 2 points from a 1-point budget (the pool is overspent; a
same-branch race is instead a lost update, since the write is absolute).

The fix — a transaction-scoped advisory lock keyed on the (guild, user) pair,
acquired BEFORE the allocation/level read (`lock_skill_slot`,
`lock_vault_upgrade_slot` precedent) — makes the second racer block until the
first's transaction commits; once unblocked it re-reads `total_spent = 1`, its
available budget is now 0, and its spend is correctly REFUSED. Exactly one spend
lands; the shared budget is never overspent.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_779_000_000_001
UID = 900_000_779_000_000_101
# level_progress(100) = level 1 → available pool min(1, 20) − 0 = 1 point.
SEED_XP = 100
NOW = 1_000_000


def _ctx(params: dict, *, uid: int = UID, gid: int = GID,
         request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


async def _seed_xp(user_id: int, xp: int) -> None:
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await db.execute(
            "INSERT INTO game_xp (user_id, guild_id, game, xp) "
            "VALUES ($1,$2,'mining',$3)", (user_id, GID, xp), conn=conn)


async def _total_spent(user_id: int) -> int:
    from sb.domain.mining import skills
    from sb.domain.mining import store as mining_store

    alloc = await mining_store.get_skills(user_id, GID)
    return skills.total_spent(alloc)


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER its underlying read returns — holding that call's
    still-open transaction (and, post-fix, its advisory lock acquired just
    before in lock_skill_slot) open long enough for a genuinely concurrent
    second racer to arrive and contend, regardless of asyncio scheduling order
    (the test_mining_vault_upgrade_race.py technique verbatim)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


# --- skill spend: concurrent cross-branch spends serialize (shared budget) --------


async def _skill_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    await _seed_xp(UID, SEED_XP)

    # Hold the FIRST spend's transaction (and its advisory lock, acquired in
    # lock_skill_slot just before this read) open long enough for the second
    # racer to arrive and contend on the SAME (guild, user) lock.
    _hold_first_caller(monkeypatch, mining_store, "get_skills", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.SKILL, _ctx({"argv": ("mining",)}, request_id="a")),
        engine.run(ops.SKILL, _ctx({"argv": ("combat",)}, request_id="b")),
    )
    # the invariant: the two spends SERIALIZE over the 1-point shared budget —
    # exactly ONE lands, the other is refused (no over-allocation).
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes == ["blocked", "success"], (
        f"one spend must win and the other be refused; got {outcomes} "
        f"({r1.user_message!r} / {r2.user_message!r}) — a race overspent the "
        f"shared skill-point budget")

    spent = await _total_spent(UID)
    assert spent == 1, (
        f"a level-1 player has 1 available point, so exactly 1 may be spent; "
        f"got total_spent={spent} — a concurrent cross-branch race overspent "
        f"the shared budget")


def test_concurrent_skill_spends_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _skill_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
