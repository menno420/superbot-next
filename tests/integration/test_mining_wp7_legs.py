"""WP-7 craft / respec leg error faces — the refusals the write goldens do not
capture.

`goldens/mining/mining_craft_write.json` pins the success craft and
`mining_craft_no_recipe.json` the no-recipe refusal; `mining_respec_write.json`
pins the success respec and `mining_respec_insufficient.json` the
insufficient-funds refusal. This suite drives the two ported legs
(`sb/domain/mining/ops.py::_record_craft` / `_record_respec`, ops
`mining.craft` / `mining.respec`) through the real workflow engine on Postgres
to pin the remaining refusal faces — craft's forge-gate and insufficient-
materials, respec's no-allocation — each asserted BYTE-IDENTICAL to the oracle
`services/mining_workflow.py::craft` (`_forge_gate` / `_check_materials`) and
`services/skill_service.py::respec` copy.

The legs raise the refusal bare (no mention); `build_route` / `skill_respec_route`
prefix the invoker mention on the wire (the goldens pin that). Driven directly
through the engine (no command dispatch), so no chat-XP award perturbs the
`game_xp` the respec leg reads.

One `asyncio.run()` per body — see `conftest.py` on why (asyncpg pools bind to
their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_789_000_000_001
UID = 900_000_789_000_000_101
NOW = 1_000_000


def _ctx(params: dict, *, request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=UID, actor_type="user"), guild_id=GID,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


async def _seed_item(item: str, qty: int) -> None:
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await mining_store.update_mining_item(
            conn, user_id=UID, guild_id=GID, item=item, delta=qty)


async def _seed_branch(branch: str, points: int) -> None:
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await mining_store.set_skill_points(
            conn, user_id=UID, guild_id=GID, branch=branch, points=points)


# --- craft leg refusals ----------------------------------------------------------


async def _craft_forge_gate() -> None:
    from sb.domain.mining import ops
    from sb.kernel.workflow import engine

    # Own the gold-sword materials but have NO forge → the gold tier is gated.
    await _seed_item("gold", 2)
    await _seed_item("wood", 1)
    result = await engine.run(ops.CRAFT, _ctx({"argv": ("gold", "sword")}))
    assert result.outcome == "blocked"
    assert result.user_message == (
        "Crafting **gold sword** needs a **Forge I** 🔥 — build the Forge "
        "with `!forge` to unlock gold-tier gear."), repr(result.user_message)


async def _craft_insufficient_materials() -> None:
    from sb.domain.mining import ops
    from sb.kernel.workflow import engine

    # torch needs 2× wood; hold only 1 → the short-materials face.
    await _seed_item("wood", 1)
    result = await engine.run(ops.CRAFT, _ctx({"argv": ("torch",)}))
    assert result.outcome == "blocked"
    assert result.user_message == (
        "You don't have enough **wood** to craft **torch** "
        "(needs 2× wood)."), repr(result.user_message)


def test_craft_forge_gate(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _craft_forge_gate()
        finally:
            await harness.close()

    asyncio.run(_run())


def test_craft_insufficient_materials(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _craft_insufficient_materials()
        finally:
            await harness.close()

    asyncio.run(_run())


# --- respec leg refusals ---------------------------------------------------------


async def _respec_no_allocation() -> None:
    from sb.domain.mining import ops
    from sb.kernel.workflow import engine

    # No player_skills rows → nothing to refund; refused before any coin read.
    result = await engine.run(ops.RESPEC, _ctx({}))
    assert result.outcome == "blocked"
    assert result.user_message == (
        "You have no skill points allocated to refund."), repr(
        result.user_message)


def test_respec_no_allocation(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _respec_no_allocation()
        finally:
            await harness.close()

    asyncio.run(_run())


async def _respec_success_wipes_all_branches() -> None:
    """A funded respec zeroes EVERY allocated branch (not just one) — the
    all-branches wipe the single-branch write golden does not exercise."""
    from sb.domain.mining import ops
    from sb.domain.mining import store as mining_store
    from sb.kernel.db import pool as db
    from sb.kernel.workflow import engine

    await _seed_branch("mining", 2)
    await _seed_branch("combat", 1)
    async with db.transaction() as conn:
        await db.execute(
            "INSERT INTO economy_balances (user_id, guild_id, coins) "
            "VALUES ($1,$2,$3)", (UID, GID, 1000), conn=conn)
    result = await engine.run(ops.RESPEC, _ctx({}))
    assert result.outcome == "success", repr(result.user_message)
    alloc = await mining_store.get_skills(UID, GID)
    assert alloc == {}, f"every branch must be refunded to 0; got {alloc}"


def test_respec_wipes_all_branches(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _respec_success_wipes_all_branches()
        finally:
            await harness.close()

    asyncio.run(_run())
