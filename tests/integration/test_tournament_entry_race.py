"""Tournament double-entry money race — real-Postgres regression for the
#221 KNOWN_RISKS ledger row (F-001/F-002 class, the #217 buy_chicken
first-insert shape).

Pre-fix, `sb/domain/games/wager.py::enter_tournament_in_txn` debited the
entry fee and upserted the natural-key entry row with NO advisory slot
lock and NO existence check. The reachable surface is rps
`sb/domain/rps/tournament.py::register_player` (Join button + ✅ reaction
sign-up): its "You're already registered." guard is IN-MEMORY
(`state.players`) and the roster append happens only AFTER the K7 op
commits, so two concurrent sign-ups by the SAME user both pass the guard,
both debit the fee, and both upserts collapse into ONE entry row
(`uq_game_state` natural key) — one fee vanishes: it is not in the
settlement pot (`payout_tournament_in_txn` sums row stakes, not debits)
and no abort/GC path ever refunds it.

The fix mirrors #213's solo_start precedent: a transaction-scoped
advisory lock (`store.lock_new_checkpoint_slot`, keyed on the SAME
(guild, user, subsystem) triple) + an existence check under the lock,
BEFORE the debit — the racer that loses the lock blocks until the
winner's transaction commits, then SEES the committed entry row and is
refused with the oracle's duplicate-refusal copy
(disbot/views/rps/registration.py: "You're already registered!") having
debited nothing.

Test mechanics follow `test_games_checkpoint_race.py`: the REAL K7 engine
over a REAL Postgres pool, two genuinely concurrent transactions
(`asyncio.gather`), a monkeypatched hold on the first racer to reach the
wager primitive so the two transactions overlap regardless of asyncio
scheduling order, and the whole body under ONE `asyncio.run()` (asyncpg
pools bind to the loop that created them — see conftest.py).
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

pytest.importorskip("asyncpg")

from tests.integration.conftest import boot_harness  # noqa: E402

GID = 700_000_556_000_000_001
P1 = 900_000_556_000_000_101
START_BALANCE = 500
FEE = 25

#: the oracle's duplicate-refusal copy (disbot/views/rps/registration.py /
#: disbot/utils/tournaments.py — "You're already registered!").
ORACLE_DUPLICATE_COPY = "You're already registered!"


def _hold_first_caller(monkeypatch, module, attr_name: str, *,
                       seconds: float):
    """Wrap `module.<attr_name>` so the FIRST call to reach it sleeps for
    *seconds* AFTER the underlying call returns — holding that racer's
    still-open K7 transaction (and every lock it took) open long enough
    for the second racer's transaction to arrive and genuinely overlap."""
    real = getattr(module, attr_name)
    state = {"n": 0}

    async def _wrapped(*args, **kwargs):
        state["n"] += 1
        first = state["n"] == 1
        result = await real(*args, **kwargs)
        if first:
            await asyncio.sleep(seconds)
        return result

    monkeypatch.setattr(module, attr_name, _wrapped)


async def _seed_balance(user_id: int, amount: int) -> None:
    from sb.domain.economy import store as economy_store
    from sb.kernel.db import pool as db

    async with db.transaction() as conn:
        await economy_store.credit_coins(
            conn, user_id=user_id, guild_id=GID, amount=amount)


async def _balance(user_id: int) -> int:
    from sb.domain.economy import store as economy_store

    return await economy_store.get_coins(user_id, GID)


async def _double_entry_race(monkeypatch) -> None:
    from sb.domain.games import wager
    from sb.domain.rps import ops as rps_ops
    from sb.domain.rps import tournament
    from sb.kernel.db.pool import fetchone

    tournament.reset_tournaments_for_tests()
    try:
        await _seed_balance(P1, START_BALANCE)
        state = tournament.get_state(GID)
        state.entry_fee = FEE
        state.registration_active = True
        state.registration_opened_mono = time.monotonic()

        # Hold the first racer's leg open AFTER its wager primitive
        # returns: pre-fix the second racer's debit merely queues on the
        # economy row lock, then double-debits once the first commits;
        # post-fix the second racer blocks on the advisory slot lock,
        # then finds the committed entry row and refuses without
        # debiting.
        _hold_first_caller(monkeypatch, wager, "enter_tournament_in_txn",
                           seconds=0.4)

        (ok1, detail1), (ok2, detail2) = await asyncio.gather(
            tournament.register_player(GID, P1, display_name="racer"),
            tournament.register_player(GID, P1, display_name="racer"),
        )

        # exactly ONE fee debited — the ledgered bug: both racers debit,
        # the upserts collapse into one row, one fee vanishes.
        final_balance = await _balance(P1)
        assert final_balance == START_BALANCE - FEE, (
            f"expected exactly one entry fee (-{FEE}); got a net change "
            f"of {final_balance - START_BALANCE} — one fee vanished "
            f"(outcomes: {(ok1, detail1)!r} / {(ok2, detail2)!r})")

        results = sorted([(ok1, detail1), (ok2, detail2)])
        # exactly ONE registration succeeds …
        assert [ok for ok, _ in results] == [False, True], (
            f"expected exactly one success, got {(ok1, detail1)!r} and "
            f"{(ok2, detail2)!r} — a race double-registered")
        # … and the loser gets the oracle's duplicate-refusal copy.
        assert results[0][1] == ORACLE_DUPLICATE_COPY, (
            f"second attempt copy drifted: {results[0][1]!r}")

        # exactly ONE audited fee row on the economy ledger.
        row = await fetchone(
            "SELECT count(*) AS n FROM economy_audit_log "
            "WHERE guild_id=$1 AND user_id=$2 AND reason=$3",
            (GID, P1, "rps:entry_fee"))
        assert int(row["n"]) == 1, (
            f"expected exactly one rps:entry_fee ledger row, got "
            f"{row['n']} — the fee was debited more than once")

        # exactly ONE entry row backs the pot.
        row = await fetchone(
            "SELECT count(*) AS n FROM game_state "
            "WHERE guild_id=$1 AND user_id=$2 AND subsystem=$3",
            (GID, P1, rps_ops.TOURNAMENT_SUBSYSTEM))
        assert int(row["n"]) == 1, f"expected one entry row, got {row['n']}"

        # the in-memory roster holds the player exactly once.
        assert state.players == [P1], (
            f"roster drifted: {state.players!r}")
    finally:
        tournament.reset_tournaments_for_tests()


def test_concurrent_tournament_entries_debit_exactly_one_fee(monkeypatch):
    async def _run():
        harness = await boot_harness()
        try:
            await _double_entry_race(monkeypatch)
        finally:
            await harness.close()

    asyncio.run(_run())
