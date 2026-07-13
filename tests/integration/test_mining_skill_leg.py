"""WP-5 skill-spend leg — the error faces the write golden does not capture.

`goldens/mining/mining_skill_write.json` pins the success spend and
`mining_skill_bad_branch.json` the bad-branch refusal; this suite drives the
ported `skill_service.allocate` leg (`sb/domain/mining/ops.py::_record_skill`,
op `mining.skill`) through the real workflow engine on Postgres to pin the two
remaining refusal faces — the per-branch cap and the available-points budget —
plus the non-positive-amount guard, each asserted BYTE-IDENTICAL to the oracle
`services/skill_service.py::allocate` copy. The leg raises the refusal bare (no
mention); `skill_route` prefixes the invoker mention on the wire (the golden
pins that). Driven directly through the engine (no `!skill` command dispatch),
so no chat-XP award perturbs the `game_xp` budget the leg reads.

One `asyncio.run()` per body — see `conftest.py` on why (asyncpg pools bind to
their creating loop).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_781_000_000_001
UID = 900_000_781_000_000_101
NOW = 1_000_000


def _ctx(params: dict, *, uid: int = UID, gid: int = GID,
         request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(NOW, tz=dt.timezone.utc))


async def _seed_game_xp(xp: int) -> None:
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


async def _run_spend(argv: tuple[str, ...]):
    from sb.domain.mining import ops
    from sb.kernel.workflow import engine

    return await engine.run(ops.SKILL, _ctx({"argv": argv}))


# --- per-branch cap refusal (oracle allocate copy verbatim) -----------------------


async def _cap_body() -> None:
    # A LOT of game XP so the budget is generous — the CAP check must fire first.
    await _seed_game_xp(10_000)
    await _seed_branch("mining", 10)  # already at PER_BRANCH_CAP
    r = await _run_spend(("mining", "1"))
    assert r.outcome == "blocked", r.outcome
    assert r.user_message == (
        "**mining** caps at **10** points (you have 10 — room for 0)."
    ), repr(r.user_message)


def test_skill_spend_refuses_at_per_branch_cap(monkeypatch):
    async def _run():
        h = await boot_harness()
        try:
            await _cap_body()
        finally:
            await h.close()

    asyncio.run(_run())


# --- insufficient available points refusal (oracle allocate copy verbatim) --------


async def _no_points_body() -> None:
    # No game_xp row → level 0 → pool min(0, 20) − 0 = 0 available points.
    r = await _run_spend(("mining", "1"))
    assert r.outcome == "blocked", r.outcome
    assert r.user_message == (
        "You only have **0** skill points to spend — level up (play more) "
        "to earn more."
    ), repr(r.user_message)


def test_skill_spend_refuses_without_available_points(monkeypatch):
    async def _run():
        h = await boot_harness()
        try:
            await _no_points_body()
        finally:
            await h.close()

    asyncio.run(_run())


# --- non-positive amount guard (oracle allocate copy verbatim) --------------------


async def _bad_amount_body() -> None:
    r = await _run_spend(("mining", "0"))
    assert r.outcome == "blocked", r.outcome
    assert r.user_message == "Spend a positive number of points.", repr(
        r.user_message)


def test_skill_spend_refuses_non_positive_amount(monkeypatch):
    async def _run():
        h = await boot_harness()
        try:
            await _bad_amount_body()
        finally:
            await h.close()

    asyncio.run(_run())
