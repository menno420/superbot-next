"""Vault-upgrade money-race regression — the advisory-lock guard on
`mining.vault_upgrade` (`sb/domain/mining/ops.py::_record_vault_upgrade`,
fenced by `sb/domain/mining/store.py::lock_vault_upgrade_slot`), proven on
a real Postgres with two genuinely concurrent transactions exactly like
`tests/integration/test_farm_mining_money_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-2: the WP-2 vault write goldens pin the
single-actor `!vaultupgrade` write, but a golden cannot express a two-txn
RACE. `!vaultupgrade` reads `vault_level` to SIZE the coin cost, debits, then
bumps the level — a read-then-settle over a natural-key `mining_player_state`
row that DOES NOT EXIST YET for a fresh player, so `FOR UPDATE` alone can lock
nothing. Pre-fix shape (no advisory lock): two concurrent first upgrades both
read level 0, both `wager.debit_in_txn` `vault_upgrade_cost(0)` = 2000 🪙, and
both upsert `vault_level = 1` — the player pays 4000 🪙 but gets ONE tier, and
the second tier the second debit paid for silently vanishes (the count-reset /
double-charge flavor of the F-001/F-002 class).

The fix — a transaction-scoped advisory lock keyed on the same (guild, user)
pair the upsert conflicts on (`pg_advisory_xact_lock`,
`lock_new_checkpoint_slot` precedent), acquired BEFORE the level read — makes
the second racer block until the first's transaction commits; once unblocked it
re-reads the committed `vault_level = 1`, its cost is sized against the raised
`vault_upgrade_cost(1)` = 3500 🪙, and it correctly lands `vault_level = 2`.
Two legitimate upgrades → level 2, priced at the escalating 2000 + 3500
schedule, every coin buying a real tier.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_778_000_000_001
UID = 900_000_778_000_000_101
START_BALANCE = 20_000
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
    still-open transaction (and, post-fix, its advisory lock acquired just
    before) open long enough for a genuinely concurrent second racer to arrive
    and contend, regardless of asyncio scheduling order (the
    test_farm_mining_money_race.py technique verbatim)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


# --- vault_upgrade: concurrent first upgrades serialize (no-row-yet race) ---------


async def _vault_upgrade_race(monkeypatch) -> None:
    from sb.domain.mining import capacity, ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)

    # Hold the FIRST upgrade's transaction (and its advisory lock, acquired in
    # lock_vault_upgrade_slot just before this read) open long enough for the
    # second racer to arrive and contend on the SAME (guild, user) lock.
    _hold_first_caller(monkeypatch, mining_store, "get_vault_level",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.VAULT_UPGRADE, _ctx({}, request_id="a")),
        engine.run(ops.VAULT_UPGRADE, _ctx({}, request_id="b")),
    )
    # both upgrades are legitimate — the invariant is that they SERIALIZE:
    # every coin debited buys a real tier (no lost tier, no double charge for
    # one tier).
    assert sorted([r1.outcome, r2.outcome]) == ["success", "success"], (
        r1, r2)

    level = await mining_store.get_vault_level(UID, GID)
    expected_cost = (capacity.vault_upgrade_cost(0)
                     + capacity.vault_upgrade_cost(1))
    final_balance = await _balance(UID)
    assert level == 2, (
        f"two successful upgrades must yield vault_level 2; got {level} — a "
        f"concurrent first-insert race swallowed a tier")
    assert final_balance == START_BALANCE - expected_cost, (
        f"expected -{expected_cost} for two serialized upgrades "
        f"(2000 + 3500); got {final_balance - START_BALANCE} — a race "
        f"double-charged the same tier")


def test_concurrent_vault_upgrades_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _vault_upgrade_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
