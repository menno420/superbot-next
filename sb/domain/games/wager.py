"""The game wager primitives (band 6) — the audited money boundary for
wagered games, ported from the shipped ``services/game_wager_workflow.py``
(P0-1 escrow-at-accept / debit-with-the-row / settle-once).

Shape change, deliberately: the shipped service OWNED its transactions;
here every primitive is a **conn-threaded helper composed inside the
calling game's K7 leg** — the op owns the ONE txn, the engine owns
audit/idempotency, and ``economy.balance_changed`` emits post-commit via
the op's EventEmitSpec payload builders (conditional emission, D-0036).
Money legs write the economy ledger through the band-3 sole-writer store
(the treasury precedent), so every escrow/settle/refund is a first-class
ledger row with the shipped reason tags.

Idempotency is double-guarded exactly like shipped: the K7 once() fence
on the op PLUS the FOR-UPDATE row-consumption guard (a settle that finds
its escrow rows already gone pays nothing — a replay can never
double-pay).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.domain.economy import service as economy_service
from sb.domain.economy import store as economy_store
from sb.domain.games import store

__all__ = [
    "EscrowResult",
    "STAKE_KEY",
    "SettleResult",
    "credit_in_txn",
    "debit_floor_in_txn",
    "debit_in_txn",
    "enter_tournament_in_txn",
    "escrow_pvp_in_txn",
    "payout_tournament_in_txn",
    "refund_pvp_in_txn",
    "settle_pvp_in_txn",
]

#: Payload key under which each escrow / entry row records the staked
#: amount. Shared with the session_gc refund sweep — keep it ``bet``.
STAKE_KEY = "bet"


@dataclass(frozen=True)
class EscrowResult:
    escrowed: bool
    stake: int
    #: (user_id, delta, new_balance) triples for the op's emit builders.
    balance_changes: tuple[tuple[int, int, int], ...] = ()


@dataclass(frozen=True)
class SettleResult:
    paid: bool
    amount: int
    new_winner_balance: int | None = None
    balance_changes: tuple[tuple[int, int, int], ...] = ()


async def _debit(conn, *, guild_id: int, user_id: int, amount: int,
                 reason: str, actor_id: int) -> int:
    """Hard debit with ledger row; raises InsufficientFundsError (rolling
    the caller's txn back) when the wallet is short — the shipped
    escrow-abort semantics."""
    balance = await economy_store.try_debit_coins(
        conn, user_id=user_id, guild_id=guild_id, amount=amount)
    if balance is None:
        held = await economy_store.get_coins(user_id, guild_id, conn=conn)
        raise economy_service.InsufficientFundsError(
            f"❌ You only have **{held}** 🪙.")
    await economy_store.insert_economy_audit(
        conn, guild_id=guild_id, user_id=user_id, actor_id=actor_id,
        delta=-amount, new_balance=balance, reason=reason)
    return balance


async def debit_floor_in_txn(conn, *, guild_id: int, user_id: int,
                             amount: int, reason: str,
                             actor_id: int) -> tuple[int, int]:
    """Overdraft-tolerant debit (the shipped ``add_coins(GREATEST(0,…))``
    loss semantics): take *amount*, flooring at zero, with the ledger row
    recording the ACTUAL delta. Returns (actual_delta, new_balance)."""
    if amount <= 0:
        held = await economy_store.get_coins(user_id, guild_id, conn=conn)
        return 0, held
    balance = await economy_store.try_debit_coins(
        conn, user_id=user_id, guild_id=guild_id, amount=amount)
    if balance is not None:
        actual = -amount
    else:
        held = await economy_store.get_coins(user_id, guild_id, conn=conn)
        if held <= 0:
            return 0, held
        balance = await economy_store.try_debit_coins(
            conn, user_id=user_id, guild_id=guild_id, amount=held)
        if balance is None:                 # raced to zero — nothing to take
            return 0, await economy_store.get_coins(user_id, guild_id,
                                                    conn=conn)
        actual = -held
    await economy_store.insert_economy_audit(
        conn, guild_id=guild_id, user_id=user_id, actor_id=actor_id,
        delta=actual, new_balance=balance, reason=reason)
    return actual, balance


async def _credit(conn, *, guild_id: int, user_id: int, amount: int,
                  reason: str, actor_id: int) -> int:
    balance = await economy_store.credit_coins(
        conn, user_id=user_id, guild_id=guild_id, amount=amount)
    await economy_store.insert_economy_audit(
        conn, guild_id=guild_id, user_id=user_id, actor_id=actor_id,
        delta=amount, new_balance=balance, reason=reason)
    return balance


#: public names — the game legs compose these inside their own txns.
credit_in_txn = _credit
debit_in_txn = _debit


async def escrow_pvp_in_txn(conn, *, guild_id: int, channel_id: int,
                            subsystem: str, version: int, p1_id: int,
                            p2_id: int, stake: int, reason: str,
                            now: int, extra_state: dict | None = None,
                            ) -> EscrowResult:
    """D1 escrow-at-accept: debit BOTH stakes and write one escrow row per
    player in the caller's txn. Raises InsufficientFundsError (rolling
    both legs back) if either player is short. stake<=0 = free play."""
    if stake <= 0:
        return EscrowResult(escrowed=False, stake=0)
    bal1 = await _debit(conn, guild_id=guild_id, user_id=p1_id,
                        amount=stake, reason=reason, actor_id=p1_id)
    bal2 = await _debit(conn, guild_id=guild_id, user_id=p2_id,
                        amount=stake, reason=reason, actor_id=p2_id)
    base = dict(extra_state or {})
    await store.upsert_checkpoint(
        conn, guild_id=guild_id, user_id=p1_id, channel_id=channel_id,
        subsystem=subsystem, state={**base, STAKE_KEY: stake, "peer": p2_id},
        version=version, now=now)
    await store.upsert_checkpoint(
        conn, guild_id=guild_id, user_id=p2_id, channel_id=channel_id,
        subsystem=subsystem, state={**base, STAKE_KEY: stake, "peer": p1_id},
        version=version, now=now)
    return EscrowResult(escrowed=True, stake=stake, balance_changes=(
        (p1_id, -stake, bal1), (p2_id, -stake, bal2)))


def _row_stake(row: dict) -> int:
    stake = (row.get("state") or {}).get(STAKE_KEY)
    return stake if isinstance(stake, int) and stake > 0 else 0


def _sum_stakes(rows: list[dict]) -> int:
    return sum(_row_stake(r) for r in rows)


async def _delete_rows(conn, guild_id: int, channel_id: int | None,
                       subsystem: str, rows: list[dict]) -> None:
    for row in rows:
        await store.delete_checkpoint(
            conn, guild_id=guild_id, user_id=row["user_id"],
            channel_id=(channel_id if channel_id is not None
                        else row["channel_id"]),
            subsystem=subsystem)


async def settle_pvp_in_txn(conn, *, guild_id: int, channel_id: int,
                            subsystem: str, p1_id: int, p2_id: int,
                            winner_id: int, reason: str) -> SettleResult:
    """Pay the escrowed pot to the winner and consume the escrow rows —
    idempotent by row consumption (a replay finds them gone: paid=False)."""
    rows = await store.lock_rows_for_settlement(
        conn, guild_id=guild_id, subsystem=subsystem,
        channel_id=channel_id, user_ids=[p1_id, p2_id])
    pot = _sum_stakes(rows)
    if pot <= 0:
        return SettleResult(paid=False, amount=0)
    balance = await _credit(conn, guild_id=guild_id, user_id=winner_id,
                            amount=pot, reason=reason, actor_id=winner_id)
    await _delete_rows(conn, guild_id, channel_id, subsystem, rows)
    return SettleResult(paid=True, amount=pot, new_winner_balance=balance,
                        balance_changes=((winner_id, pot, balance),))


async def refund_pvp_in_txn(conn, *, guild_id: int, channel_id: int,
                            subsystem: str, p1_id: int, p2_id: int,
                            reason: str) -> SettleResult:
    """Return each player's own stake (tie / both-forfeit / abort) —
    idempotent by the same row-consumption guard."""
    rows = await store.lock_rows_for_settlement(
        conn, guild_id=guild_id, subsystem=subsystem,
        channel_id=channel_id, user_ids=[p1_id, p2_id])
    if _sum_stakes(rows) <= 0:
        return SettleResult(paid=False, amount=0)
    total = 0
    changes: list[tuple[int, int, int]] = []
    for row in rows:
        stake = _row_stake(row)
        if stake <= 0:
            continue
        uid = int(row["user_id"])
        balance = await _credit(conn, guild_id=guild_id, user_id=uid,
                                amount=stake, reason=reason, actor_id=uid)
        total += stake
        changes.append((uid, stake, balance))
    await _delete_rows(conn, guild_id, channel_id, subsystem, rows)
    return SettleResult(paid=total > 0, amount=total,
                        balance_changes=tuple(changes))


async def enter_tournament_in_txn(conn, *, guild_id: int, user_id: int,
                                  channel_id: int, subsystem: str,
                                  version: int, fee: int, reason: str,
                                  now: int,
                                  extra_state: dict | None = None) -> int:
    """Debit the entry fee and write the recovery row in the caller's txn
    (closing the shipped lost-fee window). Returns the new balance;
    fee<=0 = free entry (no debit, no row)."""
    if fee <= 0:
        return await economy_store.get_coins(user_id, guild_id, conn=conn)
    state = {STAKE_KEY: fee}
    if extra_state:
        state.update(extra_state)
    balance = await _debit(conn, guild_id=guild_id, user_id=user_id,
                           amount=fee, reason=reason, actor_id=user_id)
    await store.upsert_checkpoint(
        conn, guild_id=guild_id, user_id=user_id, channel_id=channel_id,
        subsystem=subsystem, state=state, version=version, now=now)
    return balance


async def payout_tournament_in_txn(conn, *, guild_id: int, subsystem: str,
                                   winner_id: int | None, reason: str,
                                   free_reward: int = 0,
                                   free_reason: str | None = None,
                                   ) -> SettleResult:
    """Pay the winner the SUMMED escrowed pot (the truth, never fee×N) and
    release every entry row atomically; idempotent by row consumption.
    free_reward covers the no-entry-fee consolation case (single-call by
    construction — no recovery path pays rewards)."""
    rows = await store.lock_rows_for_settlement(
        conn, guild_id=guild_id, subsystem=subsystem)
    pot = _sum_stakes(rows)
    if rows:
        await _delete_rows(conn, guild_id, None, subsystem, rows)
        if winner_id is None or pot <= 0:
            return SettleResult(paid=False, amount=0)
        paid_reason, amount = reason, pot
    elif winner_id is not None and free_reward > 0:
        paid_reason, amount = free_reason or reason, free_reward
    else:
        return SettleResult(paid=False, amount=0)
    balance = await _credit(conn, guild_id=guild_id, user_id=winner_id,
                            amount=amount, reason=paid_reason,
                            actor_id=winner_id)
    return SettleResult(paid=True, amount=amount, new_winner_balance=balance,
                        balance_changes=((winner_id, amount, balance),))
