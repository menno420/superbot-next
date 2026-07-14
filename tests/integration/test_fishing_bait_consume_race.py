"""Fishing cast-vs-buy bait-slot race — the read-then-settle lost update
on a COIN-PURCHASED slot (the #213/#217 class, fenced here without a
lock because the consume leg is a single statement outside any txn).

Pre-fix shape, reproduced red before the store fix landed:
``begin_cast`` (`sb/domain/fishing/service.py`, `fishing.cast_open`)
read the active bait with a plain unlocked autocommit read and later
wrote back the ABSOLUTE ``bait_charges - 1`` via ``set_active_bait`` (or
``clear_active_bait`` on the last charge). The buy/craft legs stack or
replace the loadout behind ``store.lock_bait_slot`` inside their own K7
txn — so a purchase committing between the cast's read and its
write-back was clobbered: a stacked buy lost its coin-bought charges
(3 read + 10 bought → 2 written), and a replacing buy lost the whole
fresh pack to the clear.

The fix (`sb/domain/fishing/store.py::consume_bait_charge`) makes the
consume ONE conditional relative decrement (``charges = charges - 1``
keyed on the rolled-with ``bait_key``, ``charges >= 1``, the last charge
clearing the pack in-statement), so the committed count — not the stale
snapshot — is what settles. This file proves the REAL SQL semantics and
the true interleave against the REAL locked buy leg; the handler-level
interleave (through `fishing.cast_open` itself) is pinned by
`tests/unit/band6/test_band6_fishing_cast_wiring.py::
test_cast_open_consume_never_clobbers_a_concurrent_bait_buy`.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_777_000_000_002
UID = 900_000_777_000_000_102
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


# --- the real SQL contract of the conditional consume ------------------------------


async def _consume_semantics() -> None:
    from sb.domain.fishing import store as fs

    # relative decrement on a matching loadout
    await fs.set_active_bait(UID, GID, "worm", 3)
    assert await fs.consume_bait_charge(UID, GID, "worm") == 2
    assert await fs.get_active_bait(UID, GID) == ("worm", 2)

    # the last charge clears the pack IN-STATEMENT (the exact
    # clear_active_bait end state — never a 0-charge keyed row)
    await fs.set_active_bait(UID, GID, "worm", 1)
    assert await fs.consume_bait_charge(UID, GID, "worm") == 0
    assert await fs.get_active_bait(UID, GID) == ("", 0)

    # a swapped loadout misses the key condition — None, row untouched
    await fs.set_active_bait(UID, GID, "grub", 5)
    assert await fs.consume_bait_charge(UID, GID, "worm") is None
    assert await fs.get_active_bait(UID, GID) == ("grub", 5)

    # an emptied/absent loadout — None (the "no bait" posture)
    await fs.clear_active_bait(UID, GID)
    assert await fs.consume_bait_charge(UID, GID, "grub") is None
    assert await fs.consume_bait_charge(UID + 1, GID, "worm") is None


def test_consume_bait_charge_sql_semantics():
    async def _run():
        harness = await boot_harness()
        try:
            await _consume_semantics()
        finally:
            await harness.close()

    asyncio.run(_run())


# --- the cast-vs-buy interleave against the REAL locked buy leg --------------------
#
# The cast's consume is not transactional, so the interleave is expressed
# deterministically as the exact sequence the raced schedule produces:
# the cast's unlocked read → the buy's whole fenced txn commits → the
# cast's consume. No sleeps needed — the lost update was never about
# blocking, it was the stale ABSOLUTE write-back.


async def _cast_read_buy_commit_consume() -> None:
    from sb.domain.fishing import bait as bait_mod
    from sb.domain.fishing import ops
    from sb.domain.fishing import store as fs
    from sb.kernel.workflow import engine

    worm = bait_mod.bait_by_key("worm")
    assert worm is not None
    await _seed_balance(UID, START_BALANCE)
    await fs.set_active_bait(UID, GID, "worm", 3)

    # 1. the cast's unlocked read (begin_cast's snapshot)
    bait_key, bait_charges = await fs.get_active_bait(UID, GID)
    assert (bait_key, bait_charges) == ("worm", 3)

    # 2. the concurrent BUY: the real fishing.buy_bait op — debit +
    #    stack behind lock_bait_slot in ONE txn — commits in the window
    result = await engine.run(
        ops.BUY_BAIT, _ctx({"bait_key": "worm"}, request_id="buy"))
    assert result.outcome == "success", result
    assert await fs.get_active_bait(UID, GID) == (
        "worm", 3 + worm.charges)

    # 3. the cast's consume settles against the COMMITTED count — the
    #    pre-fix absolute write-back (bait_charges - 1 = 2) ate the
    #    purchase's coin-bought charges here
    remaining = await fs.consume_bait_charge(UID, GID, bait_key)
    assert remaining == 3 + worm.charges - 1, (
        f"expected the purchase to survive the cast's consume "
        f"({3 + worm.charges - 1} left); got {remaining!r} — the "
        f"write-back clobbered a committed buy")
    assert await fs.get_active_bait(UID, GID) == (
        "worm", 3 + worm.charges - 1)


def test_cast_consume_survives_a_buy_committing_in_the_window():
    async def _run():
        harness = await boot_harness()
        try:
            await _cast_read_buy_commit_consume()
        finally:
            await harness.close()

    asyncio.run(_run())
