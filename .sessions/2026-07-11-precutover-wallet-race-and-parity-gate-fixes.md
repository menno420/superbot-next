# 2026-07-11 — pre-cutover wallet-race + parity-gate fixes (F-001/F-002/F-003)

> **Status:** `complete`

- **📊 Model:** sonnet-5 · high · bug fix + regression tests

## Scope

Fix three source-confirmed pre-cutover bugs, each with a failing-then-passing
regression test:

- **F-001** — blackjack solo double-settle: two in-flight terminal actions
  (e.g. a double-clicked "stand") on the same `game_state` checkpoint row
  could both read the pre-mutation state and both settle.
- **F-002** — blackjack/rps PvP double-escrow: the same unlocked-checkpoint-
  load class, at the pending-challenge accept step.
- **F-003** — golden-parity gate false-green: `tools/run_golden_parity.py`'s
  `--gate` leg counted goldens on disk and replayed cases through two
  different code paths and never compared them, so a golden that silently
  failed reconstruction just shrank the replayed set instead of redding the
  required check.

Then sweep money/game domains for the same wallet-race class, then continue
the port toward cutover (highest-value pending subsystem — see the
follow-up PR: the treasury flip, kept SEPARATE from this fix PR per the
"fix PRs first, port progress after" split). (Actual session shape: the
sweep + an adversarial review pass surfaced two MORE real instances of the
F-001/F-002 class plus a couple of test-infrastructure gaps — all fixed
with the same red-then-green discipline. See "Sweep" and "Adversarial
review" below.)

## Root cause (F-001/F-002)

`sb/domain/games/store.py`'s `fetch_checkpoint`/`fetch_user_checkpoint` were
plain `SELECT`s. Every caller composes the read inside a K7 leg transaction
ahead of a mutate-then-settle sequence (`sb/domain/blackjack/ops.py`,
`sb/domain/rps/ops.py`), and every one of those ops declares
`IdempotencyPosture.NATURAL_KEY` — which mints **no** `once()`/dedup key
(`sb/kernel/workflow/engine.py` only mints one for `DURABLE_ONCE`) and takes
**no** `SINGLE_FLIGHT` lock. NATURAL_KEY's own contract ("intrinsically
once — ON CONFLICT / FOR UPDATE") puts the whole fence on the DB legs
themselves — but the checkpoint *load* wasn't holding up its half: two
concurrent op invocations could both read the identical pre-mutation row,
both compute a settle/escrow, and both commit before either's delete
landed. The settle-time guard (`store.lock_rows_for_settlement`, used by
`wager.settle_pvp_in_txn` etc.) already did this correctly — the gap was
specifically the *load* side.

Fix: add `FOR UPDATE` to both `fetch_checkpoint` and `fetch_user_checkpoint`.
The row lock holds for the life of the leg's transaction, so a second racer
either blocks-then-sees the first's committed state, or blocks-then-finds
the row already deleted (a clean "session expired" denial, never a second
settle). One shared fix in the band-6 store closes it for blackjack solo,
blackjack PvP, and rps PvP identically (verified live for all three —
see Evidence).

Also reconciled `sb/domain/games/wager.py`'s module docstring, which
claimed a "K7 once() fence... PLUS the FOR-UPDATE row-consumption guard" —
the once() fence never applied under NATURAL_KEY; only the row-consumption
guard (now on both ends, load AND settle) was ever real.

## Root cause (F-003)

`sb/adapters/parity/cases.py`'s `load_replay_cases` silently `continue`d
past any golden file whose `case_id` failed `reconstruct_case` (a click
step with a normalized session id, no `CURATED_CASES` override). A dropped
golden just vanished from the cases list — no count, no signal.
`tools/run_golden_parity.py --gate` then iterated only the *successfully
replayed* cases and never compared that count against `_golden_counts()`
(goldens on disk), so a silently-dropped golden in a `ported` subsystem
would report GREEN over fewer cases than actually exist.

Fix: `sb.adapters.parity.cases.load_replay_cases_with_report` now returns
`(cases, dropped)` — `dropped` is `{subsystem: count}`. `run_gate()` sums
replayed cases per subsystem and asserts it equals the golden count on disk
for every `ported` row; a mismatch reds the gate with the exact dropped
count. `run_report()` prints the same `dropped` map for visibility.

## Evidence

- **F-001/F-002**: `tests/integration/test_games_checkpoint_race.py` — real
  Postgres, real K7 engine (`sb.kernel.workflow.engine.run`), two genuinely
  concurrent transactions via `asyncio.gather` with a monkeypatched hold on
  whichever racer's locking read wins first (forces overlap regardless of
  asyncio scheduling order). Three tests: blackjack solo double-stand,
  blackjack PvP double-accept, rps PvP double-accept (the sweep). All three
  **reproduced the bug live pre-fix** (double credit / double escrow — e.g.
  the PvP test asserted `2 == 1` successes) and pass post-fix, run
  repeatedly with no flakes. A fast DB-free companion pin
  (`tests/unit/band6/test_band6_games_substrate.py`) asserts the SQL text
  itself carries `FOR UPDATE`, so an accidental revert reds even where no
  Postgres is available (`code-quality`'s required gate has no asyncpg).
- **F-003**: `tests/unit/parity_adapter/test_replay_adapter.py` +
  `tests/unit/parity_gate/test_check_parity_depth.py::TestGateDriver` — a
  synthetic unreconstructable golden proves `load_replay_cases_with_report`
  counts the drop; a monkeypatched `_replay_corpus` proves `run_gate()` reds
  on a replayed/golden-count mismatch. Both red pre-fix, green post-fix.
- **Full-corpus real run**: `tools/run_golden_parity.py --gate` against a
  real local Postgres 18 → `gate: GREEN — all 253 golden(s) across 37 ported
  subsystem(s) replay clean` (zero denominator mismatches — the F-003 fix
  doesn't false-red the currently-clean corpus). `tests/unit/` — 1436
  passed, 2 skipped. The full committed checker fleet + `manifest_compile.py`
  + `check_parity_depth.py` + `bootstrap.py check --strict` all green.
- **CI enforcement gap closed**: `tests/integration/` needs both the full
  runtime lock (asyncpg) and a live Postgres — `code-quality` (the required
  pytest gate) installs neither, so a real-DB concurrency test would never
  have run anywhere in CI. Added a `pytest tests/integration -q` step to
  the `golden-parity` gate job in both `.github/workflows/golden-parity.yml`
  and `.github/workflows/named-gates.yml` (the only jobs with both), so
  this class of regression is now actually enforced going forward, not just
  proven once by hand.

## Sweep (F-002's class, beyond blackjack)

`sb/domain/rps/ops.py`'s `_load_pending` calls the exact same
`store.fetch_checkpoint` at its PvP-accept step — same unlocked-load +
NATURAL_KEY shape, same bug, closed by the same store.py fix (confirmed
live: the rps race test reproduced the double-escrow pre-fix and passes
post-fix). `sb/domain/deathmatch/ops.py` has the identical unlocked-load
pattern at its challenge/duel-move steps but moves no money (no wager
calls at all) — not a wallet-race, left as-is.

Two MORE instances of the same class were found by a fan-out adversarial
review (3 independent reviewers over the diff, each finding adversarially
re-verified by 3 more agents before being trusted) and, since both were
confirmed reachable, fixed here rather than left for later:

- **The session_gc sweep vs. a live settle** (`sb/domain/games/service.py`
  session_gc_fire / recover_escrow → `sb/domain/games/ops.py`
  `_record_gc_sweep_row`) — the GC driver's `store.list_stale`/
  `list_active` scan is an UNLOCKED snapshot (F-001/F-002's `FOR UPDATE`
  fix never touches it), and the sweep leg credited the stale snapshot's
  bet UNCONDITIONALLY before deleting by id — a stranded row whose own
  player settled for real between the scan and the GC leg's turn got
  refunded on top of the player's own payout. Fix: delete-by-id FIRST (a
  bare `DELETE ... WHERE id=$1` already takes the row's lock for the life
  of its own txn — no new locking primitive needed), credit ONLY when the
  delete actually removed a row. Real-Postgres regression test rigged to a
  PUSH (not a win) specifically to avoid a same-user-economy-row deadlock
  between the two transactions that would otherwise mask the bug by
  aborting one side cleanly (documented in the test itself — this
  confounder cost real iteration time to diagnose).
- **`blackjack.record_solo_start`'s existence guard** — checks "already
  have a game running" via `fetch_user_checkpoint` (now `FOR UPDATE`
  locked), but the row it's checking doesn't exist yet when two concurrent
  `!blackjack` starts land in *different* channels for the same user —
  `FOR UPDATE` locks existing rows, it cannot fence an INSERT race against
  a row that isn't there yet (the unique constraint, `uq_game_state`,
  includes `channel_id`, so two concurrent starts in different channels
  can both pass the guard and both insert). Fix: a transaction-scoped
  advisory lock (`store.lock_new_checkpoint_slot`, `pg_advisory_xact_lock
  (hashtext(...))`, auto-released at commit/rollback) keyed on the SAME
  `(guild_id, user_id, subsystem)` triple the existence check uses,
  acquired before it — closes the invariant violation for the real,
  persisting-game case. (Narrower nuance recorded for the next reader:
  the *specific* "both land a natural blackjack and both get paid"
  framing isn't fully closable by any lock, since a natural resolves and
  returns without ever writing a row to protect — two independently
  dispatched, independently funds-checked commands each landing a natural
  isn't a double-settle of one action, just two lucky wins; the advisory
  lock fixes the actual invariant — no two persisted games — which is the
  meaningful, general-case bug.)

Also caught and fixed in the same review pass (test-infrastructure, not
wallet-race, but real): `tests/integration/conftest.py`'s
`pytest.importorskip("asyncpg")` crashed with a raw traceback (not a clean
skip) under the EXACT invocation the new CI steps use
(`pytest tests/integration -q`, naming the directory directly) — pytest
loads a directly-targeted conftest.py through an "initial conftest" path
that doesn't catch the `Skipped` exception `importorskip` raises; only
collection via a parent directory (`pytest tests/`, `code-quality`'s real
invocation) catches it. Reproduced directly both ways. Fixed: a plain
guarded import + an in-function `pytest.skip()` call (always caught).
Same pass also fixed a resource leak — `boot_harness()` didn't close the
harness if `reset_database()` raised after a successful `Harness.start()`,
leaking the pool and every process-global test seam; now wrapped so a
failure after boot always closes what it opened.

One more F-003-adjacent gap, found and fixed the same way: two golden
FILES sharing a `case_id` (not a `CURATED_CASES` collision — a genuine
golden-vs-golden duplicate) were silently absorbed by
`load_replay_cases_with_report`'s dedup with no `dropped` signal at all —
reproduced directly (two files, one id → 1 case, `dropped == {}`, though
only 1 of 2 files was ever exercised). Fixed: a collision against an
EARLIER GOLDEN FILE now counts as a drop; a collision against a
`CURATED_CASES` id stays expected (that's the intended, by-design typed
override, not a drop).

Port progress (the treasury subsystem, `pending → ported`) ships as a
SEPARATE follow-up PR from the same session — kept apart from this PR so
the urgent fixes aren't gated behind the port's own review/CI surface; see
its own session log for that evidence.

## Adversarial review (ultracode workflow)

Ran a 3-dimension fan-out review (locking-correctness / F-003-gate-logic /
test-soundness-and-conventions) over the staged diff before shipping, each
finding adversarially re-verified by 3 independent agents (majority-vote
refute). 6 findings surfaced; verify agents CONFIRMED 2 as real bugs not
yet closed by the diff (the GC sweep race, the solo_start channel race)
and REFUTED 3 as already-fixed once they read the current (fixed) source
(the GC sweep finding's 3 verifiers all independently confirmed the fix
— strong evidence the fix is correct, not just self-reported). All 6
findings were investigated by hand regardless of verdict; every
CONFIRMED-real one is fixed above with its own red-then-green test. The
one `nit`-severity finding (a mildly tautological wrapper-consistency
test) was reviewed and left as-is — harmless, low value to chase further.

## 💡 Session idea

The `IdempotencyPosture.NATURAL_KEY` enum member's own docstring
("intrinsically once — ON CONFLICT / FOR UPDATE") is a *contract* every op
declaring that posture is implicitly relying on, but nothing enforces it —
`compile.py`'s fences check the posture is *declared* correctly (e.g.
`session_transition` ⇒ NATURAL_KEY), never that the DB legs *behind* a
NATURAL_KEY op actually take a locking read or an `ON CONFLICT` upsert.
F-001/F-002 was exactly this gap: a NATURAL_KEY op whose load leg forgot
the lock half of its own contract. A cheap structural guard — grep every
DB leg reachable from a NATURAL_KEY op for at least one `FOR UPDATE` or
`ON CONFLICT` in its SQL — would catch a *new* instance of this bug class
at review time instead of needing a live-race regression test to prove it
each time. Worth a `tools/check_natural_key_fencing.py` if another
subsystem hits the same class during the port.

## ⟲ Previous-session review

This checkout is a shallow clone (`--depth 1` — a single squashed root
commit), so there's no git history to walk back to the literal prior
session's log file; the closest honest substitute is the HEAD commit
itself (`ab1e9162`, PR #203, "xp-admin family (4) re-homed
_unmapped→xp"). What it did well: a real, verified gate number in the
commit message (253/253) rather than a vague "tests pass" claim, and it
named the exact traps it hit (CAPTURE_WORLD_CHANNELS leak, trap 17/20) —
that specificity is what let this session trust `gate: GREEN` from a cold
build without re-deriving it. What it didn't carry forward: nothing in
that commit (or reachable from this shallow checkout) flagged that
`run_golden_parity.py --gate`'s denominator was unchecked — a latent gap
that predates this session by a long way and had nothing to do with the
xp-admin port specifically. One concrete workflow improvement: a shallow
clone silently forecloses "read the previous session's actual log" as a
review mechanism — worth noting in `docs/AGENT_ORIENTATION.md` (or the
`add_repo` clone step) that a session wanting real prior-session context
should `git fetch --unshallow` before writing its "previous-session
review" section, not just its `git blame`/bisect use case.
