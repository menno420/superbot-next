"""WP-7 money/material-race regressions — the advisory-lock guards on the two
ported read-then-settle legs `mining.respec` and `mining.craft`, proven on a
real Postgres with two genuinely concurrent transactions exactly like
`tests/integration/test_mining_skill_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-7: the WP-7 write goldens pin the
single-actor respec / craft mutations, but a golden cannot express a two-txn
RACE.

- **respec** (`sb/domain/mining/ops.py::_record_respec`, fenced by
  `store.lock_skill_slot`): reads the player's `player_skills` allocation to
  decide there IS something to refund, then debits a level-scaled coin fee and
  zeroes every branch. Two concurrent respecs by a player funded for TWO fees
  both read a non-empty allocation, both debit, and both wipe — the player is
  charged TWICE for a SINGLE logical refund (the coin-row lock in
  `wager.debit_in_txn` cannot help: each debit is affordable on its own). The
  advisory lock keyed on (guild, user), acquired BEFORE the allocation read,
  makes the loser block until the winner commits; it then re-reads an EMPTY
  allocation and is refused ("no skill points allocated to refund") — exactly
  one fee is charged.

- **craft** (`sb/domain/mining/ops.py::_record_craft`, fenced by
  `store.lock_workshop_slot`): reads the pack to check it holds every material,
  then consumes the materials and adds `+1` product. Two concurrent crafts of
  the same recipe by a player holding materials for exactly ONE both read a
  sufficient pack, both pass the material check, and both add the product — TWO
  products from ONE set of materials (`update_mining_item` floors at 0, so the
  over-consume is silently swallowed while both products land). The advisory
  lock makes the loser re-read the reduced pack and be refused
  ("not enough <material>") — exactly one product is crafted.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py` on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_787_000_000_001
UID = 900_000_787_000_000_101
# level_progress(100) = level 1 → respec_cost = 200 + 50*1 = 250 🪙.
SEED_XP = 100
NOW = 1_000_000


def _ctx(params: dict, *, request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=UID, actor_type="user"), guild_id=GID,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER its underlying read returns — holding that call's still-open
    transaction (and, post-fix, its advisory lock acquired just before) open
    long enough for a genuinely concurrent second racer to arrive and contend on
    the SAME (guild, user) lock (the test_mining_skill_race.py technique)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


async def _seed_xp(xp: int) -> None:
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await db.execute(
            "INSERT INTO game_xp (user_id, guild_id, game, xp) "
            "VALUES ($1,$2,'mining',$3)", (UID, GID, xp), conn=conn)


async def _seed_branch(branch: str, points: int) -> None:
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await mining_store.set_skill_points(
            conn, user_id=UID, guild_id=GID, branch=branch, points=points)


async def _seed_coins(coins: int) -> None:
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await db.execute(
            "INSERT INTO economy_balances (user_id, guild_id, coins) "
            "VALUES ($1,$2,$3)", (UID, GID, coins), conn=conn)


async def _seed_item(item: str, qty: int) -> None:
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await mining_store.update_mining_item(
            conn, user_id=UID, guild_id=GID, item=item, delta=qty)


async def _coins() -> int:
    from sb.domain.economy.store import get_coins

    return await get_coins(UID, GID)


# --- respec: two concurrent respecs charge exactly one fee -----------------------


async def _respec_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    await _seed_xp(SEED_XP)
    await _seed_branch("mining", 2)
    await _seed_coins(500)  # funds TWO 250 🪙 respecs — the double-charge window

    # Hold the FIRST respec's transaction (and its lock_skill_slot advisory lock,
    # acquired just before this read) open long enough for the second racer to
    # arrive and contend on the SAME (guild, user) lock.
    _hold_first_caller(monkeypatch, mining_store, "get_skills", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.RESPEC, _ctx({}, request_id="a")),
        engine.run(ops.RESPEC, _ctx({}, request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes == ["blocked", "success"], (
        f"two concurrent respecs must serialize — one refunds, the other is "
        f"refused (empty allocation); got {outcomes} "
        f"({r1.user_message!r} / {r2.user_message!r}) — a race double-charged "
        f"the respec fee")
    # exactly ONE 250 🪙 fee charged: 500 − 250 = 250 (not 0, which would be a
    # double-charge).
    remaining = await _coins()
    assert remaining == 250, (
        f"exactly one 250 🪙 respec fee may be charged; got balance "
        f"{remaining} — a concurrent race charged the fee twice")


def test_concurrent_respecs_charge_one_fee(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _respec_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- craft: two concurrent crafts consume one material set → one product ---------


async def _craft_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    # torch recipe = {wood: 2}; seed exactly one craft's worth.
    await _seed_item("wood", 2)

    # Hold the FIRST craft's transaction (and its lock_workshop_slot advisory
    # lock) open long enough for the second racer to contend.
    _hold_first_caller(monkeypatch, mining_store, "get_mining_inventory",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.CRAFT, _ctx({"argv": ("torch",)}, request_id="a")),
        engine.run(ops.CRAFT, _ctx({"argv": ("torch",)}, request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes == ["blocked", "success"], (
        f"two concurrent crafts of the same recipe must serialize — one crafts, "
        f"the other is refused (not enough material); got {outcomes} "
        f"({r1.user_message!r} / {r2.user_message!r}) — a race double-consumed "
        f"one material set")
    inventory = await mining_store.get_mining_inventory(UID, GID)
    # exactly ONE torch from the single 2-wood material set (a race would land
    # TWO products), and the wood fully consumed.
    assert inventory.get("torch", 0) == 1, (
        f"exactly one torch may be crafted from one 2-wood set; got "
        f"{inventory.get('torch', 0)} — a concurrent race crafted two products "
        f"from one material set")
    assert inventory.get("wood", 0) == 0, (
        f"the single 2-wood set must be fully consumed; got "
        f"{inventory.get('wood', 0)} wood remaining")


def test_concurrent_crafts_consume_one_material_set(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _craft_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
