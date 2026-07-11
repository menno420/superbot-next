"""F-001/F-002 regression — real-Postgres concurrency races over the games
checkpoint store (`sb/domain/games/store.py`).

Pre-fix, `fetch_checkpoint`/`fetch_user_checkpoint` were plain SELECTs: two
in-flight terminal actions on the SAME checkpoint row (a double-clicked
solo "stand", a double-clicked PvP "accept") could both read the identical
pre-mutation state inside their own K7 leg transaction and both settle —
blackjack solo double-pays a win, PvP double-escrows both stakes. The fix
(this repo's `sb/domain/games/store.py`) adds `FOR UPDATE` to both loads,
so the SECOND racer's SELECT blocks on the FIRST's still-open transaction
and, once unblocked, finds the row already consumed (a clean "expired"
denial, never a second settle).

These tests drive the REAL K7 engine (`sb.kernel.workflow.engine.run`)
against a REAL Postgres connection pool with two genuinely concurrent
transactions (`asyncio.gather`), not the in-memory FakeGamesStore band6
fixtures use — those fakes replace `fetch_checkpoint`/`fetch_user_checkpoint`
outright and so cannot exercise the SQL-level fix at all (verified: the
band6 fakes hold no lock semantics). A monkeypatched hold on whichever
racer's load wins the DB row lock first forces the two transactions to
genuinely overlap regardless of asyncio scheduling order, so the assertion
is not scheduling-order-dependent.

Every test drives its whole body through ONE `asyncio.run()` call — see
`conftest.py`'s note on why (asyncpg pools bind to the event loop that
created them).
"""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_555_000_000_001
P1 = 900_000_555_000_000_101   # solo player / PvP challenger
P2 = 900_000_555_000_000_102   # PvP acceptor
CH = 800_000_555_000_000_001
START_BALANCE = 500
BET = 10


def _ctx(params: dict, *, uid: int, gid: int = GID, request_id: str = "r1"):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id=request_id, confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000,
                                                 tz=dt.timezone.utc))


class RiggedStandDeck(random.Random):
    """Deals the solo player 9+9=18 vs a dealer that draws to a 17 stand
    (2+3, hits 6, 6) — a clean, non-natural player win worth `BET` coins,
    so a double-settle shows up as a doubled credit, not a masked push."""

    POP_ORDER = ("9 ♠", "9 ♥", "2 ♠", "3 ♥", "6 ♠", "6 ♥")

    def shuffle(self, seq):
        rest = [c for c in seq if c not in self.POP_ORDER]
        seq[:] = rest + list(reversed(self.POP_ORDER))


class NoShuffle(random.Random):
    """Deck stays in construction order — pops come from the tail (K ♣ …),
    dealing both PvP players K ♣ + K ♦ = 20 (non-natural, match stays open
    for the escrow race to be observed before any settle)."""

    def shuffle(self, seq):
        return None


async def _seed_balance(user_id: int, amount: int) -> None:
    from sb.domain.economy import store as economy_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await economy_store.credit_coins(
            conn, user_id=user_id, guild_id=GID, amount=amount)


async def _balance(user_id: int) -> int:
    from sb.domain.economy import store as economy_store

    return await economy_store.get_coins(user_id, GID)


def _hold_first_caller(monkeypatch, module, attr_name: str, *, seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it (regardless
    of which racing ctx that turns out to be) sleeps for *seconds* AFTER
    its underlying (locking) read returns — holding that call's still-open
    K7 transaction, and therefore its row lock, open long enough for a
    genuinely concurrent second racer's identical locking read to arrive
    and contend on the SAME row."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        result = await real(*args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


# --- F-001: blackjack solo double-settle -----------------------------------------


async def _solo_race(monkeypatch) -> None:
    from sb.domain.blackjack import ops
    from sb.kernel.workflow import engine

    ops.set_rng_for_tests(RiggedStandDeck())
    try:
        await _seed_balance(P1, START_BALANCE)
        start_result = await engine.run(
            ops.SOLO_START, _ctx({"bet": BET, "channel_id": CH}, uid=P1))
        assert start_result.outcome == "success", start_result
        assert await _balance(P1) == START_BALANCE   # no debit at deal

        _hold_first_caller(monkeypatch, ops, "_load_solo", seconds=0.4)

        r1, r2 = await asyncio.gather(
            engine.run(ops.SOLO_STAND, _ctx({}, uid=P1, request_id="a")),
            engine.run(ops.SOLO_STAND, _ctx({}, uid=P1, request_id="b")),
        )
        outcomes = sorted([r1.outcome, r2.outcome])
        # exactly one settle succeeds; the racer that loses the row lock
        # finds the checkpoint already consumed and is denied, never paid.
        assert outcomes.count("success") == 1, (r1, r2)

        final_balance = await _balance(P1)
        # a win pays +BET (delta-only settle, no stake was ever debited at
        # deal) — SINGLE settle means +BET once, never +2*BET.
        assert final_balance == START_BALANCE + BET, (
            f"expected exactly one settle (+{BET}); got a net change of "
            f"{final_balance - START_BALANCE} — a race double-paid")
    finally:
        ops.set_rng_for_tests(None)


def test_concurrent_solo_stand_settles_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _solo_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- F-002: blackjack PvP double-escrow -------------------------------------------


async def _pvp_accept_race(monkeypatch) -> None:
    from sb.domain.blackjack import ops
    from sb.kernel.workflow import engine

    ops.set_rng_for_tests(NoShuffle())
    try:
        await _seed_balance(P1, START_BALANCE)
        await _seed_balance(P2, START_BALANCE)

        challenge = await engine.run(
            ops.PVP_CHALLENGE,
            _ctx({"target_id": P2, "bet": BET, "channel_id": CH}, uid=P1))
        assert challenge.outcome == "success", challenge
        session_id = challenge.after["pvp_challenge"]["session_id"]

        _hold_first_caller(monkeypatch, ops, "_load_pending", seconds=0.4)

        r1, r2 = await asyncio.gather(
            engine.run(ops.PVP_ACCEPT,
                      _ctx({"session_id": session_id}, uid=P2,
                           request_id="a")),
            engine.run(ops.PVP_ACCEPT,
                      _ctx({"session_id": session_id}, uid=P2,
                           request_id="b")),
        )
        outcomes = sorted([r1.outcome, r2.outcome])
        assert outcomes.count("success") == 1, (r1, r2)

        # single escrow: each player debited BET exactly once, never twice.
        assert await _balance(P1) == START_BALANCE - BET, (
            "challenger was escrowed more than once — a race double-escrowed")
        assert await _balance(P2) == START_BALANCE - BET, (
            "acceptor was escrowed more than once — a race double-escrowed")
    finally:
        ops.set_rng_for_tests(None)


def test_concurrent_pvp_accept_escrows_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _pvp_accept_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- sweep: the SAME wallet-race class in rps (unlocked checkpoint load +
# NATURAL_KEY posture) — rps/ops.py's `_load_pending` calls the exact same
# `store.fetch_checkpoint`, so the store.py fix covers it for free; this
# confirms that generalization holds under a real race rather than taking
# it on faith. ------------------------------------------------------------


async def _rps_accept_race(monkeypatch) -> None:
    from sb.domain.rps import ops
    from sb.kernel.workflow import engine

    await _seed_balance(P1, START_BALANCE)
    await _seed_balance(P2, START_BALANCE)

    challenge = await engine.run(
        ops.PVP_CHALLENGE,
        _ctx({"target_id": P2, "bet": BET, "channel_id": CH}, uid=P1))
    assert challenge.outcome == "success", challenge
    session_id = challenge.after["pvp_challenge"]["session_id"]

    _hold_first_caller(monkeypatch, ops, "_load_pending", seconds=0.4)

    r1, r2 = await asyncio.gather(
        engine.run(ops.PVP_ACCEPT,
                  _ctx({"session_id": session_id}, uid=P2, request_id="a")),
        engine.run(ops.PVP_ACCEPT,
                  _ctx({"session_id": session_id}, uid=P2, request_id="b")),
    )
    outcomes = sorted([r1.outcome, r2.outcome])
    assert outcomes.count("success") == 1, (r1, r2)

    assert await _balance(P1) == START_BALANCE - BET, (
        "rps challenger was escrowed more than once")
    assert await _balance(P2) == START_BALANCE - BET, (
        "rps acceptor was escrowed more than once")


def test_rps_concurrent_pvp_accept_escrows_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _rps_accept_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- adversarial-review finding: session_gc sweep vs. a live settle --------------
#
# The GC sweep (`sb/domain/games/service.py` session_gc_fire /
# recover_escrow) scans stranded rows via `store.list_stale`/`list_active`
# — an UNLOCKED snapshot, unlike the checkpoint loads F-001/F-002 fixed —
# then fires `games.gc_sweep_row` per row from that stale snapshot. If the
# row's own player settles for real between the scan and the GC leg's turn,
# an unguarded GC leg would credit the STALE bet on top of the player's own
# already-paid settle — a double-pay this store.py fix alone does not
# close, because the GC path never calls fetch_checkpoint/
# fetch_user_checkpoint at all. Fixed in `sb/domain/games/ops.py`'s
# `_record_gc_sweep_row`: delete-by-id FIRST (itself race-safe — a bare
# `DELETE ... WHERE id=$1` takes the row's lock for the life of its own
# txn), credit ONLY if that delete actually removed a row.
#
# The race is rigged to a PUSH (dealt 20 vs 20 — NoShuffle, delta=0), not a
# win: a win would have the player's OWN settle credit the SAME user's
# economy_balances row that GC's stale refund also credits, and forcing
# the player's FOR-UPDATE lock to be held first would then deadlock the
# two transactions against EACH OTHER (game_state lock held by the player
# vs. an uncommitted economy_balances write held by GC) — Postgres's
# deadlock detector aborts one side, which happens to also yield a clean
# "exactly one credit" result and would mask the bug entirely. A push's
# own settle takes no economy write (a bare read), so only GC's refund
# ever touches the wallet — isolating the exact defect: GC must pay
# NOTHING when the row it scanned was already properly consumed by a
# real (zero-sum) settle.


async def _gc_sweep_vs_live_settle_race(monkeypatch) -> None:
    from sb.domain.blackjack import ops
    from sb.domain.games import ops as games_ops
    from sb.domain.games import store as games_store
    from sb.kernel.workflow import engine
    from sb.kernel.workflow.context import WorkflowContext

    ops.set_rng_for_tests(NoShuffle())
    try:
        await _seed_balance(P1, START_BALANCE)
        start_result = await engine.run(
            ops.SOLO_START, _ctx({"bet": BET, "channel_id": CH}, uid=P1))
        assert start_result.outcome == "success", start_result

        # the GC driver's own scan shape (store.list_stale/list_active): an
        # UNLOCKED read of the row, taken BEFORE the player's real move.
        stale_row = await games_store.fetch_user_checkpoint(
            GID, P1, ops.SOLO_SUBSYSTEM)
        assert stale_row is not None

        # Force the exact failure window deterministically (a natural race
        # is timing-luck: whichever op reaches the row FIRST always "wins"
        # cleanly, which never exercises the bug — the phantom refund only
        # happens when the player's FOR-UPDATE lock is held FIRST and GC's
        # leg starts, and credits, WHILE that lock is still held). Signal
        # the instant the player's locking read succeeds, hold that
        # transaction open, and only THEN let the GC leg start.
        player_has_lock = asyncio.Event()
        real_load_solo = ops._load_solo

        async def _load_solo_signal_then_hold(conn, ctx):
            result = await real_load_solo(conn, ctx)
            player_has_lock.set()
            await asyncio.sleep(0.4)
            return result

        monkeypatch.setattr(ops, "_load_solo", _load_solo_signal_then_hold)

        gc_ctx = WorkflowContext(
            actor=SimpleNamespace(user_id=0, actor_type="system"),
            guild_id=GID, request_id=f"games.gc:{stale_row['id']}",
            confirmed=True,
            params={"row": stale_row, "reason": "games:gc_refund"})

        async def _gc_after_player_holds_the_lock():
            await player_has_lock.wait()
            return await engine.run(games_ops.GC_SWEEP_ROW, gc_ctx)

        player_result, gc_result = await asyncio.gather(
            engine.run(ops.SOLO_STAND, _ctx({}, uid=P1, request_id="a")),
            _gc_after_player_holds_the_lock(),
        )

        # the player's own settle is a push (delta=0, no economy write) —
        # the ONLY money that could move is GC's refund, and it must NOT
        # fire: the row it scanned was already properly resolved for free
        # by the player's own settle by the time GC's leg reaches it.
        assert player_result.outcome == "success", player_result
        final_balance = await _balance(P1)
        assert final_balance == START_BALANCE, (
            f"expected NO payout (a push settles for zero); got a net "
            f"change of {final_balance - START_BALANCE} — GC paid a "
            f"phantom refund for a row the player's own settle already "
            f"consumed for free")
    finally:
        ops.set_rng_for_tests(None)


def test_gc_sweep_and_live_settle_pay_exactly_once(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _gc_sweep_vs_live_settle_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())


# --- adversarial-review finding: concurrent solo_start in different channels ----
#
# `_record_solo_start`'s "already have a game running" guard is keyed on
# (guild, user, subsystem) — WITHOUT channel_id — but the row it may insert
# is ADDITIONALLY keyed on channel_id (the uq_game_state constraint). FOR
# UPDATE (F-001) only locks rows that already exist, so it cannot serialize
# two concurrent starts that both see "no row yet": two `!blackjack`
# invocations for the SAME user in two DIFFERENT channels both pass the
# guard, and — pre-fix — could both persist a checkpoint, violating the
# one-active-game invariant the guard exists to enforce (which itself
# enables further inconsistent play: independent hit/stand/double decisions
# on what the game model assumes is a single game). Fixed with a
# transaction-scoped advisory lock (`store.lock_new_checkpoint_slot`) keyed
# on the SAME (guild, user, subsystem) triple the existence check uses,
# acquired before it — the second racer blocks until the first's
# transaction resolves, and then correctly finds the first's row.


async def _concurrent_solo_start_different_channels_race(monkeypatch) -> None:
    from sb.domain.blackjack import ops
    from sb.domain.games import store as games_store
    from sb.kernel.workflow import engine

    ops.set_rng_for_tests(RiggedStandDeck())   # non-natural (18 vs 17) deal
    try:
        await _seed_balance(P1, START_BALANCE)

        _hold_first_caller(monkeypatch, games_store, "lock_new_checkpoint_slot",
                           seconds=0.4)

        r1, r2 = await asyncio.gather(
            engine.run(ops.SOLO_START,
                      _ctx({"bet": BET, "channel_id": CH}, uid=P1,
                           request_id="a")),
            engine.run(ops.SOLO_START,
                      _ctx({"bet": BET, "channel_id": CH + 1}, uid=P1,
                           request_id="b")),
        )
        outcomes = sorted([r1.outcome, r2.outcome])
        # exactly one start succeeds — the one-active-game invariant holds
        # even when the two starts target different channels.
        assert outcomes.count("success") == 1, (r1, r2)

        row = await games_store.fetch_user_checkpoint(GID, P1,
                                                       ops.SOLO_SUBSYSTEM)
        assert row is not None, "the successful start must have persisted"
    finally:
        ops.set_rng_for_tests(None)


def test_concurrent_solo_start_different_channels_starts_at_most_one_game(
        monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _concurrent_solo_start_different_channels_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
