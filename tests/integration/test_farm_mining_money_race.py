"""Farm/mining money-race regression — the F-001/F-002 defect class
(unlocked read → settle → credit under `IdempotencyPosture.NATURAL_KEY`)
at the farm and mining K7 legs, proven on a real Postgres with two
genuinely concurrent transactions exactly like
`tests/integration/test_games_checkpoint_race.py` (PR #213's pattern).

Pre-fix shapes, each reproduced red before the store fix landed:

- `farm.collect` (`sb/domain/farm/ops.py::_record_collect`): `get_farm`
  was a plain SELECT — two concurrent collects both read `eggs > 0`,
  both `wager.credit_in_txn` the payout, and both upsert `eggs=0`; the
  second credit is a pure mint (the house pays the same eggs twice).
- `farm.buy_chicken` for a FRESH farmer (no `chicken_farm` row yet):
  `FOR UPDATE` alone cannot fence this — there is no row to lock — so
  two concurrent first buys both read the starter defaults, both debit
  `chicken_price(1)`, and both upsert `chickens=2`: the user pays twice
  and one purchase silently vanishes (the count-reset flavor of the same
  class). Closed by a transaction-scoped advisory lock
  (`pg_advisory_xact_lock`, `sb/domain/games/store.py`'s
  `lock_new_checkpoint_slot` precedent) keyed on the same
  (guild, user) pair the upsert conflicts on.
- `mining.sell` / `mining.sell_all`
  (`sb/domain/mining/ops.py::_record_sell/_record_sell_all`):
  `get_mining_inventory` was a plain SELECT and `update_mining_item`'s
  decrement floors at zero (`GREATEST(0, …)`) — two concurrent sells
  both read `held=N`, both pass the balance check, the second decrement
  silently floors instead of failing, and BOTH credit `N × price`: a
  double payout for one inventory.

The fix (`sb/domain/farm/store.py::get_farm` /
`sb/domain/mining/store.py::get_mining_inventory`, `for_update=True` at
every money-bearing leg) makes the second racer's load block on the
first's still-open transaction; once unblocked it sees the committed
post-mutation state (empty coop / empty inventory) and is cleanly
denied, never paid.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_777_000_000_001
UID = 900_000_777_000_000_101
START_BALANCE = 500
NOW = 1_000_000


def _ctx(params: dict, *, uid: int = UID, gid: int = GID,
         request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


async def _seed_balance(user_id: int, amount: int) -> None:
    from sb.domain.economy import store as economy_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await economy_store.credit_coins(
            conn, user_id=user_id, guild_id=GID, amount=amount)


async def _balance(user_id: int) -> int:
    from sb.domain.economy import store as economy_store

    return await economy_store.get_coins(user_id, GID)


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER its underlying read returns — holding that call's
    still-open K7 transaction (and, post-fix, its row/advisory lock) open
    long enough for a genuinely concurrent second racer to arrive and
    contend, regardless of asyncio scheduling order (the
    test_games_checkpoint_race.py technique verbatim)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


# --- farm.collect: concurrent collects credit exactly once ------------------------


async def _farm_collect_race(monkeypatch) -> None:
    from sb.domain.farm import core, ops
    from sb.domain.farm import store as farm_store
    from sb.kernel.db import pool as db
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)
    # a settled coop with 10 eggs banked as of the ops' fixed clock — the
    # leg's own settle() adds zero accrual (elapsed = 0), so the payout is
    # exactly collect_value(10).
    eggs = 10
    async with db.transaction() as conn:
        await farm_store.set_farm(conn, user_id=UID, guild_id=GID,
                                  chickens=2, eggs=eggs, now=NOW,
                                  coop_level=0)
    payout = core.collect_value(eggs)

    _hold_first_caller(monkeypatch, farm_store, "get_farm", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.COLLECT, _ctx({}, request_id="a")),
        engine.run(ops.COLLECT, _ctx({}, request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    # exactly one collect pays; the racer that loses the lock re-reads the
    # committed eggs=0 row and is denied ("the coop is empty"), never paid.
    assert outcomes.count("success") == 1, (r1, r2)

    final_balance = await _balance(UID)
    assert final_balance == START_BALANCE + payout, (
        f"expected exactly one collect (+{payout}); got a net change of "
        f"{final_balance - START_BALANCE} — a race double-credited the "
        f"same eggs")


def test_concurrent_farm_collect_credits_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _farm_collect_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- farm.buy_chicken: concurrent FIRST buys serialize (no-row-yet race) ----------
#
# FOR UPDATE cannot fence this shape — a fresh farmer has no chicken_farm
# row to lock, so both racers read the starter defaults (1 hen). Pre-fix
# both debit chicken_price(1) and both upsert chickens=2: the user pays
# twice for one hen. Post-fix (the advisory lock keyed on the upsert's
# own (guild, user) conflict key) the second buy blocks, then correctly
# sees the first's committed row: two buys → three hens, priced at the
# escalating chicken_price(1) + chicken_price(2) schedule.


async def _farm_first_buy_race(monkeypatch) -> None:
    from sb.domain.farm import core, ops
    from sb.domain.farm import store as farm_store
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)

    _hold_first_caller(monkeypatch, farm_store, "get_farm", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.BUY_CHICKEN, _ctx({}, request_id="a")),
        engine.run(ops.BUY_CHICKEN, _ctx({}, request_id="b")),
    )
    # both purchases are legitimate — the invariant is that they SERIALIZE:
    # every coin debited buys a real hen (no count reset, no double charge
    # for one bird).
    assert sorted([r1.outcome, r2.outcome]) == ["success", "success"], (
        r1, r2)

    chickens, _, _, _ = await farm_store.get_farm(UID, GID)
    expected_cost = core.chicken_price(1) + core.chicken_price(2)
    final_balance = await _balance(UID)
    assert chickens == 3, (
        f"two successful buys must yield 3 hens (starter + 2); got "
        f"{chickens} — a concurrent first-insert race swallowed a "
        f"purchase")
    assert final_balance == START_BALANCE - expected_cost, (
        f"expected -{expected_cost} for two serialized buys; got "
        f"{final_balance - START_BALANCE}")


def test_concurrent_first_chicken_buys_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _farm_first_buy_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- mining.sell: concurrent sells of the same stack credit exactly once ----------


async def _mining_sell_race(monkeypatch) -> None:
    from sb.domain.mining import market, ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)
    qty = 5
    price = market.sell_price("iron")
    assert price is not None
    async with db.transaction() as conn:
        await mining_store.update_mining_item(conn, user_id=UID,
                                              guild_id=GID, item="iron",
                                              delta=qty)

    _hold_first_caller(monkeypatch, mining_store, "get_mining_inventory",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.SELL, _ctx({"item": "iron", "qty": qty},
                                  request_id="a")),
        engine.run(ops.SELL, _ctx({"item": "iron", "qty": qty},
                                  request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    # exactly one sale pays; the loser re-reads the committed empty stack
    # and is denied — the GREATEST(0, …) decrement floor can no longer
    # silently absorb a second sale of the same ore.
    assert outcomes.count("success") == 1, (r1, r2)

    final_balance = await _balance(UID)
    assert final_balance == START_BALANCE + qty * price, (
        f"expected exactly one sale (+{qty * price}); got a net change of "
        f"{final_balance - START_BALANCE} — a race sold the same stack "
        f"twice")
    held = await mining_store.get_mining_inventory(UID, GID)
    assert held.get("iron", 0) == 0


def test_concurrent_mining_sell_credits_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _mining_sell_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- mining.sell_all: the whole-inventory twin of the same race -------------------


async def _mining_sell_all_race(monkeypatch) -> None:
    from sb.domain.mining import market, ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)
    qty = 4
    price = market.sell_price("gold")
    assert price is not None
    async with db.transaction() as conn:
        await mining_store.update_mining_item(conn, user_id=UID,
                                              guild_id=GID, item="gold",
                                              delta=qty)

    _hold_first_caller(monkeypatch, mining_store, "get_mining_inventory",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.SELL_ALL, _ctx({}, request_id="a")),
        engine.run(ops.SELL_ALL, _ctx({}, request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    # the loser's re-read finds nothing sellable and is denied.
    assert outcomes.count("success") == 1, (r1, r2)

    final_balance = await _balance(UID)
    assert final_balance == START_BALANCE + qty * price, (
        f"expected exactly one sell-all (+{qty * price}); got a net change "
        f"of {final_balance - START_BALANCE} — a race sold the same "
        f"inventory twice")


def test_concurrent_mining_sell_all_credits_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _mining_sell_all_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
