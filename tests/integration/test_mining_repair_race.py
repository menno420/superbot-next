"""Repair double-spend race regression — the advisory-lock guard on
`mining.repair` (`sb/domain/mining/ops.py::_record_repair`, fenced by
`sb/domain/mining/store.py::lock_workshop_slot`), proven on a real Postgres with
two genuinely concurrent transactions exactly like
`tests/integration/test_mining_vault_upgrade_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-3 (workshop fold-in): `repair` reads the
`mining_gear_wear` row to SIZE the coin cost, debits it, then clears the wear
row — a read-then-settle over the (guild, user, item) wear key. Two concurrent
repairs of ONE worn item both read the same `durability = 30`, both size the
same `cost = 7`, both `wager.debit_in_txn`, and both `clear_gear_wear` — the
player is charged 14 🪙 to repair ONE item once (the double-charge flavor of the
F-001/F-002 class).

The fix — a transaction-scoped advisory lock keyed on the (guild, user) pair
(`lock_workshop_slot`, `pg_advisory_xact_lock`), acquired BEFORE the wear read —
makes the second racer block until the first commits; once unblocked it re-reads
the now-cleared wear and refuses with the shipped "already at full durability"
copy. Exactly ONE debit, one repair.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from sb.spec.outcomes import BLOCKED, SUCCESS  # noqa: E402
from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_780_000_000_001
UID = 900_000_780_000_000_101
START_BALANCE = 500
WORN_DURABILITY = 30          # of pickaxe's 60 max → cost 7
EXPECTED_COST = 7
NOW = 1_000_000


def _ctx(params: dict, *, uid: int = UID, gid: int = GID,
         request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER its underlying read returns — holding that call's
    still-open transaction (and, post-fix, its advisory lock acquired just
    before) open long enough for a genuinely concurrent second racer to arrive
    and contend (the test_mining_vault_upgrade_race.py technique verbatim)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


async def _seed_worn_pickaxe() -> None:
    """A funded balance, an owned pickaxe (repair's ownership read), and a worn
    wear row so the single legitimate repair's success branch runs."""
    from sb.domain.economy import store as economy_store
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await economy_store.credit_coins(
            conn, user_id=UID, guild_id=GID, amount=START_BALANCE)
        await mining_store.update_mining_item(
            conn, user_id=UID, guild_id=GID, item="pickaxe", delta=1)
        await mining_store.set_gear_wear(
            conn, user_id=UID, guild_id=GID, item_name="pickaxe",
            durability=WORN_DURABILITY)


async def _balance() -> int:
    from sb.domain.economy import store as economy_store

    return await economy_store.get_coins(UID, GID)


# --- repair: concurrent repairs of one worn item serialize (no double-spend) ------


async def _repair_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    await _seed_worn_pickaxe()

    # Hold the FIRST repair's transaction (and its advisory lock, acquired in
    # lock_workshop_slot just before this read) open long enough for the second
    # racer to arrive and contend on the SAME (guild, user) lock.
    _hold_first_caller(monkeypatch, mining_store, "get_gear_wear",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.REPAIR, _ctx({"argv": ("pickaxe",)}, request_id="a")),
        engine.run(ops.REPAIR, _ctx({"argv": ("pickaxe",)}, request_id="b")),
    )

    # The invariant is SERIALIZATION: exactly one repair wins (debits + clears
    # the wear); the loser re-reads the cleared wear and refuses.
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes == [BLOCKED, SUCCESS], (
        f"repair must serialize: one success, one refusal; got {outcomes} — a "
        f"concurrent double-repair charged the player twice ({r1}, {r2})")

    final_balance = await _balance()
    assert final_balance == START_BALANCE - EXPECTED_COST, (
        f"one repair must debit exactly {EXPECTED_COST} 🪙; got "
        f"{START_BALANCE - final_balance} — a race double-charged the same "
        f"repair")

    # the wear row is cleared exactly once (the item is at full durability)
    assert "pickaxe" not in await mining_store.get_gear_wear(UID, GID)


def test_concurrent_repairs_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _repair_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
