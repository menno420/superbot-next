"""Structure-build money-race regression — the advisory-lock guard on
`mining.build` (`sb/domain/mining/ops.py::_record_build`, fenced by
`sb/domain/mining/store.py::lock_structure_slot`), proven on a real Postgres
with two genuinely concurrent transactions exactly like
`tests/integration/test_mining_vault_upgrade_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-6: the WP-6 structure-build write golden
pins the single-actor `!forge` -> 🔥 Build write, but a golden cannot express a
two-txn RACE. `build_structure` reads the built level to SIZE the coin +
material cost, debits the coins, consumes the materials, then bumps the level —
a read-then-settle over a natural-key `mining_structures` row that DOES NOT
EXIST YET for a fresh player, so `FOR UPDATE` alone can lock nothing. Pre-fix
shape (no advisory lock): two concurrent first builds both read level 0, both
size the Forge-I cost (3000 🪙 + 25× iron + 15× stone), and both upsert
`level = 1` (the write is absolute — `GREATEST(0, 1)`), so the player pays
2× 3000 = 6000 🪙 but gets ONE level, and the second level the second debit paid
for silently vanishes (the double-charge flavor of the F-001/F-002 class).

The fix — a transaction-scoped advisory lock keyed on the same (guild, user)
pair the upsert conflicts on (`pg_advisory_xact_lock`, `lock_vault_upgrade_slot`
precedent), acquired BEFORE the level read (`lock_structure_slot`) — makes the
second racer block until the first's transaction commits; once unblocked it
re-reads the committed `level = 1`, its cost is sized against the raised
`build_cost(FORGE, 1)` = Forge-II (8000 🪙 + 20× gold + 10× iron), and it
correctly lands `level = 2`. Two legitimate builds → forge level 2, priced at
the escalating 3000 + 8000 schedule, every coin buying a real level.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_780_000_000_001
UID = 900_000_780_000_000_101
# enough coins + materials for BOTH forge levels (Forge I: 3000 + iron25/stone15;
# Forge II: 8000 + gold20/iron10) so two SERIALIZED builds both legitimately land.
START_BALANCE = 11_000
SEED_MATERIALS = {"iron": 35, "stone": 15, "gold": 20}
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


async def _seed_materials(user_id: int, materials: dict[str, int]) -> None:
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        for item, qty in materials.items():
            await mining_store.update_mining_item(
                conn, user_id=user_id, guild_id=GID, item=item, delta=qty)


async def _balance(user_id: int) -> int:
    from sb.domain.economy import store as economy_store

    return await economy_store.get_coins(user_id, GID)


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER its underlying read returns — holding that call's
    still-open transaction (and, post-fix, its advisory lock acquired just
    before in lock_structure_slot) open long enough for a genuinely concurrent
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


# --- build: concurrent first builds serialize (no-row-yet race) -------------------


async def _build_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.domain.mining import structures
    from sb.kernel.workflow import engine

    await _seed_balance(UID, START_BALANCE)
    await _seed_materials(UID, SEED_MATERIALS)

    # Hold the FIRST build's transaction (and its advisory lock, acquired in
    # lock_structure_slot just before this read) open long enough for the second
    # racer to arrive and contend on the SAME (guild, user) lock.
    _hold_first_caller(monkeypatch, mining_store, "get_structures", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.BUILD, _ctx({"structure": "forge"}, request_id="a")),
        engine.run(ops.BUILD, _ctx({"structure": "forge"}, request_id="b")),
    )
    # both builds are legitimate — the invariant is that they SERIALIZE: every
    # coin debited buys a real level (no lost level, no double charge for one).
    assert sorted([r1.outcome, r2.outcome]) == ["success", "success"], (
        r1, r2)

    built = await mining_store.get_structures(UID, GID)
    level = built.get(structures.FORGE, 0)
    expected_cost = (structures.build_cost(structures.FORGE, 0).coins
                     + structures.build_cost(structures.FORGE, 1).coins)
    final_balance = await _balance(UID)
    assert level == 2, (
        f"two successful builds must yield forge level 2; got {level} — a "
        f"concurrent first-insert race swallowed a level")
    assert final_balance == START_BALANCE - expected_cost, (
        f"expected -{expected_cost} for two serialized builds (3000 + 8000); "
        f"got {final_balance - START_BALANCE} — a race double-charged the same "
        f"level")


def test_concurrent_structure_builds_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _build_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
