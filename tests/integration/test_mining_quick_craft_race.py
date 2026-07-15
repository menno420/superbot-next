"""Quick-craft double-craft / item-dup race regression — the advisory-lock
guard on `mining.quick_craft` (`sb/domain/mining/ops.py::_record_quick_craft`,
fenced by `sb/domain/mining/store.py::lock_workshop_slot`), proven on a real
Postgres with two genuinely concurrent transactions exactly like
`tests/integration/test_mining_vault_upgrade_race.py` (PR #213/#217 pattern).

The money-reviewer follow-up to WP-3, and the PRIORITY of this slice: unlike
`repair` / `vault_upgrade`, `quick_craft` moves MATERIALS, not coins, so
`tools/check_money_race.py` does NOT cover it at all — the advisory lock is its
ONLY guard against a duplication exploit. `quick_craft` reads the
`last_broken_item` marker + the recipe materials, consumes the materials, mints
the crafted item into `mining_inventory`, auto-equips it, then clears the
marker — a read-then-settle over the per-player `mining_player_state` row.

Pre-fix shape (no advisory lock): two concurrent quick-crafts of ONE broken
item (with only enough material for ONE craft) both read `last_broken = torch`,
both pass the material check (each sees the pre-consume `wood = 2`), both
consume the wood (flooring at 0), and both mint a `torch` — the player ends with
TWO torches from ONE broken item and ONE recipe's worth of wood: a straight
item-duplication out of thin materials (the F-001/F-002 count-reset class,
here minting an ITEM rather than coins).

The fix — a transaction-scoped advisory lock keyed on the (guild, user) pair
(`lock_workshop_slot`, `pg_advisory_xact_lock`), acquired BEFORE the
`last_broken` read — makes the second racer block until the first commits; once
unblocked it re-reads the now-cleared marker and refuses with the shipped
"Nothing has broken recently" copy. Exactly ONE craft, ONE torch, no dup.

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

GID = 700_000_779_000_000_001
UID = 900_000_779_000_000_101
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
    and contend, regardless of asyncio scheduling order (the
    test_mining_vault_upgrade_race.py technique verbatim)."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


async def _seed_broken_torch() -> None:
    """One broken torch marker + exactly ONE recipe's worth of wood
    (torch = {wood: 2}) — enough for a single legitimate quick-craft."""
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await mining_store.set_last_broken(
            conn, user_id=UID, guild_id=GID, item="torch")
        await mining_store.update_mining_item(
            conn, user_id=UID, guild_id=GID, item="wood", delta=2)


async def _torch_count() -> int:
    from sb.domain.mining import store as mining_store

    inv = await mining_store.get_mining_inventory(UID, GID)
    return inv.get("torch", 0)


# --- quick_craft: concurrent crafts of one broken item serialize (no item-dup) ---


async def _quick_craft_race(monkeypatch) -> None:
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.workflow import engine

    await _seed_broken_torch()

    # Hold the FIRST quick-craft's transaction open at the MATERIAL read (the
    # step that sizes the spend), so a genuinely concurrent second racer reaches
    # the SAME material read and passes its own recipe check BEFORE either racer
    # consumes — the exact window the item-dup exploits. Post-fix, the first
    # caller already holds the (guild, user) advisory lock (acquired in
    # lock_workshop_slot before the last_broken read), so the second racer
    # blocks at the lock and never reaches this read until the winner commits.
    # (Holding the earlier last_broken read would NOT expose the dup: READ
    # COMMITTED lets the loser's later material re-read see the winner's
    # committed consumption and refuse on its own — the lock must be what
    # serializes, not the isolation level.)
    _hold_first_caller(monkeypatch, mining_store, "get_mining_inventory",
                       seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.QUICK_CRAFT, _ctx({}, request_id="a")),
        engine.run(ops.QUICK_CRAFT, _ctx({}, request_id="b")),
    )

    # The invariant is SERIALIZATION: the lock lets exactly one craft win; the
    # loser re-reads the cleared marker and refuses (no second craft, no dup).
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes == [BLOCKED, SUCCESS], (
        f"quick_craft must serialize: one success, one refusal; got {outcomes} "
        f"— a concurrent double-craft minted the item twice ({r1}, {r2})")

    torches = await _torch_count()
    assert torches == 1, (
        f"one broken torch + one recipe's wood must yield exactly ONE crafted "
        f"torch; got {torches} — the race duplicated the item")

    # the marker is cleared and the wood is spent exactly once
    assert await mining_store.get_last_broken(UID, GID) is None
    inv = await mining_store.get_mining_inventory(UID, GID)
    assert inv.get("wood", 0) == 0, inv


def test_concurrent_quick_crafts_serialize(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _quick_craft_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
