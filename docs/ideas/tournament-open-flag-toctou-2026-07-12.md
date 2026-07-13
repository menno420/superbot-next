---
state: captured
origin: lab
shipped_pr: null
shipped_repo: menno420/superbot-next
merged_date: null
outcome: accepted-posture
---

# The tournament-OPEN `active_tournament` check-and-set is non-atomic — accepted boot-sweep-recovery posture (2026-07-12)

> **Status:** `ideas`
>
> **State:** captured (re-ledgered by the cross-game reverse-guard +
> atomicity follow-up to the #277 money-path review). This is NOT a bug
> to fix in-repo: it is the parity-faithful port of the oracle's own
> non-atomic open guard, and its worst case is recovered by the boot
> sweep. Recorded so the narrow TOCTOU window is not silently rediscovered
> and "fixed" into a divergence from the oracle.

**One line:** the shared `active_tournament` flag's OPEN guard
(`get_active` read → refuse) is a non-atomic check-and-set with a narrow
TOCTOU window between the read and the later `set_active` write; the
oracle (menno420/superbot) ships the exact same non-atomic guard and
recovers via a boot sweep, so the faithful posture is to MATCH it — the
window is low-severity and self-heals, not to invent atomicity the oracle
lacks.

## What IS atomic (not this row)

Two adjacent races on this flag are already fenced and must not be
conflated with the open window:

- **The entry (register_player) race** — fenced by a transaction-scoped
  advisory lock: `sb/domain/games/wager.py::enter_tournament_in_txn`
  takes `store.lock_new_checkpoint_slot(conn, guild, user, subsystem)`
  then does an existence check BEFORE the fee debit (the #223 / #221
  F-001/F-002 fix, the #213 `solo_start` precedent). Regression:
  `tests/integration/test_tournament_entry_race.py`.
- **The settle (champion payout) race** — fenced by construction: the
  `clear_active` row-DELETE runs FIRST as the check-and-set and its
  affected-row count IS the settle-once token
  (`sb/domain/rps/ops.py::_record_tournament_payout` and the blackjack
  twin `sb/domain/blackjack/ops.py`: `cleared = await clear_active(...);
  if not cleared: return paid=False` before `payout_tournament_in_txn`).
  Two racing champion resolutions serialize on the row lock; the loser
  deletes zero rows and pays nothing (#130 review). Regressions:
  `test_rps_champion_payout_fires_exactly_once` /
  `test_blackjack_champion_payout_fires_exactly_once` in
  `tests/unit/band6/test_band6_blackjack_tournament.py`.

## The non-atomic window (the OPEN guard)

The tournament-OPEN guard is a plain read-then-refuse with NO fence:

1. RPS: `sb/domain/rps/handlers.py::register_route` reads
   `existing = await get_active(gid)` and refuses when
   `existing and existing != "rps"`, then (on pass) runs
   `rps.tournament_open` → `sb/domain/rps/ops.py::_record_tournament_open`
   → `tournament_flag.set_active(conn, gid, "rps")`.
2. Blackjack: `sb/domain/blackjack/handlers.py::tournament_open_route`
   reads `existing = await get_active(gid)` and refuses when
   `existing and existing != "blackjack"`, then (on pass) runs
   `blackjack.tournament_open` → `set_active(conn, gid, "blackjack")`.

The window: `get_active`
(`sb/domain/games/tournament_flag.py::get_active`) is a bare `SELECT`
issued on its OWN pooled connection (`conn=None`, autocommit), NOT inside
the open workflow's transaction, and it takes no row/advisory lock.
Between that read and the later `set_active` UPSERT (`INSERT … ON CONFLICT
DO UPDATE`), nothing holds the shared row. Two DIFFERENT-game opens in one
guild that interleave across an `await` (both handlers await the read, so
the single event loop can schedule them between read and write) can each
read `None`, both pass their guard, and both `set_active` — the second
UPSERT clobbers the first game's flag value. Because `get_active` reads on
a separate autocommit connection it cannot even see an as-yet-uncommitted
`set_active` from the racing txn, which widens the window versus a
same-txn read.

Downstream effect if it fires: the two live tournaments share ONE flag
row; whichever settles first `clear_active`-deletes it and pays, and the
second settle finds `clear_active()==0` and pays its champion nothing,
stranding that pot's escrow rows. (This is the same money shape #277's
guard closes for the common case; the residue here is only the sub-tick
double-open race the guard's non-atomicity leaves open.)

## Why low-severity (and why we do NOT harden it)

- **Recoverable, not lost.** The stranded escrow rows are refunded at the
  next boot escrow sweep (`rps_tournament_entry` /
  `blackjack_tournament` join `ESCROW_RECOVERY_SUBSYSTEMS`;
  `sb/app/main.py`'s `recover_escrow` at boot), and the stale flag is
  reset by the boot flag sweep. No coins are minted or permanently
  destroyed — settlement is delayed to the next restart.
- **Narrow.** It requires two DIFFERENT games' opens in the SAME guild to
  interleave within the event loop's read→write await gap. Same-game
  double-open is caught earlier by the in-memory registration guards
  (`state.registration_active` / `state_or_none`).
- **Parity — the oracle is identical.** The oracle's open guard is the
  same non-atomic read/refuse, verified verbatim at
  menno420/superbot@97d281e5:

  ```python
  # disbot/cogs/rps_tournament_cog.py
  existing = await tournament_state_service.get_active(ctx.guild.id)
  if existing:
      await ctx.send(
          f"A **{existing}** tournament is already active in this server.")
      return
  ```

  and its recovery is a boot sweep, also verbatim:

  ```python
  # disbot/cogs/rps_tournament/_helpers.py
  async def clear_stale_tournament_flag(bot):
      """Reset ACTIVE_TOURNAMENT for any guild where it was left as 'rps'.
      Called once at cog_load to recover from a crash that left the [flag]."""
  # spawned at cog_load: tasks.spawn("rps:clear_stale_flag", ...)
  ```

  The oracle never fenced the open path; its posture is exactly
  read/refuse + boot-sweep recovery. Adding an advisory lock here would be
  inventing atomicity the oracle lacks — a divergence, not a fix.

## Decision

**MATCH the oracle: document the accepted boot-sweep-recovery posture; do
NOT add a fence.** The open guard stays a non-atomic read/refuse (both
games); recovery stays the boot escrow + flag sweep. This ledger row and
the note in `sb/domain/games/tournament_flag.py`'s module docstring
re-record the window, its low severity, and the oracle citation so the
narrowness is not mistaken for an omission.

If a future product decision wants opens to be strictly serialized (a
divergence from the oracle), the clean in-repo shape already exists — a
transaction-scoped `lock_new_checkpoint_slot`-style advisory lock keyed on
`(guild, "tournament-open")` taken inside BOTH openers' workflow txns
before the `get_active` re-check, mirroring the entry-race fence. That is
an OWNER-DECISION (it changes the oracle-faithful posture), flagged here
rather than taken unilaterally.
