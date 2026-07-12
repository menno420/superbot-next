# 2026-07-12 — money-race lint (tools/check_money_race.py, the F-001/F-002 class guard)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · static checker + CI wiring (Q-0194)

## Scope

Build the structural guard the last two session cards asked for
(`check_natural_key_fencing` idea, TWICE-evidenced: games at #213
`f71d60b`, farm/mining at #217 `ed8eed34`): a DB-free static lint that
flags the money-race defect class at review time — (A) an unlocked read
(plain SELECT, no `FOR UPDATE` / `pg_advisory_xact_lock` fence earlier
in the txn scope) followed by a money mutation
(`wager.credit_in_txn`/`debit_in_txn`/economy balance writes), and
(B) a natural-key `INSERT … ON CONFLICT … DO UPDATE` writing
caller-computed state with no preceding locking read / advisory fence.
Scope `sb/domain`, wired into CI, proven red-then-green against the
verbatim pre-#217 shapes.

## Delivered

- `tools/check_money_race.py` — AST/regex over Python source + SQL
  string literals; import-aware store-seam resolution (`store.get_farm`
  resolves to the sibling store module's SQL), name-fixpoint money and
  fence propagation (a local helper that credits makes its caller
  money-bearing; `_load_pending` inherits `fetch_checkpoint`'s FOR
  UPDATE), branch-aware ordering (reads on a raise/return-terminated
  branch — the error-copy `get_coins` pattern — cannot leak into the
  settle path). Two site ledgers, both stale-row-guarded: `ALLOWLIST`
  (verified-safe, justification per row) and `KNOWN_RISKS` (real
  class members, loud on every run, never called safe).
- `tests/unit/invariants/test_check_money_race.py` — the pre-#217
  farm.collect / farm.buy_chicken / mining.sell shapes as RED fixtures
  (must flag; the mining fixture proves transitive money via the local
  `_sell_rows` helper), the post-#217 fixed shapes as GREEN fixtures
  (must pass), upsert atomicity classification pins, and the real-tree
  baseline pin (every HEAD finding dispositioned, no stale rows).
- CI: `check_money_race` joins the committed checker fleet loop in
  `ci.yml` and the `architecture` named gate in `named-gates.yml`
  (sibling-invocation shape, no new required check).

## Baseline verification (every flagged site walked against source)

Raw findings at HEAD: 4. Dispositions:

- ALLOW `sb/domain/games/wager.py::debit_floor_in_txn` (A) — the
  get_coins read only sizes the retry for `try_debit_coins`, a
  one-statement conditional decide-and-write that detects the race
  itself (None return handled).
- ALLOW `sb/domain/games/wager.py::escrow_pvp_in_txn` (B, 2 call
  sites) — every caller fences first: both PvP accept legs load the
  pending challenge via `_load_pending` → `fetch_checkpoint`
  (unconditional FOR UPDATE, the #213 fix) before escrowing.
- KNOWN-RISK `sb/domain/games/wager.py::enter_tournament_in_txn` (B) —
  judged a REAL class member, NOT whitelisted: the entry-fee debit +
  natural-key entry-row upsert has no advisory slot lock and no
  existence check; two concurrent same-user entries (rps
  `register_player`'s duplicate guard is in-memory and yields at
  awaits) both debit and collapse into ONE entry row — one fee
  vanishes. Fix shape: `lock_new_checkpoint_slot` + existence check
  (the #213 solo_start precedent). Ledgered loud-on-every-run; fixing
  it without deleting the ledger row reds the checker.

## Evidence

- Red proof: with the money seed neutered, the pre-#217 fixtures
  produce ZERO findings and the RED tests fail; armed, they produce
  A+B on farm collect/buy and A (transitive) on mining sell.
- `tests/` full suite green locally (1487 passed / 11 skipped, deps
  present); full committed checker fleet + manifest_compile green
  including the new checker.

## 💡 Session idea

The KNOWN_RISKS lane doubles as a machine-readable bug ledger: a
follow-up slice should fix `enter_tournament_in_txn` (advisory slot
lock + existence check under the lock, semantics decision: refuse or
no-op a duplicate entry — shipped intent is refuse, per the in-memory
"You're already registered" guard) with a real-Postgres race test, and
delete the ledger row in the same PR — the stale-row guard enforces
exactly that coupling.

## ⟲ Previous-session review

The #217 card's "Session idea" section is what made this slice
mechanical — it named the tool, the evidence trail (twice-shipped
class), and the detection predicate (NATURAL_KEY leg without FOR
UPDATE / advisory / conditional write). What it under-specified: the
disposition policy for sites the new checker would flag that are
SAFE-by-shape (conditional one-statement writes, fence-in-caller) vs
real residue — this session had to invent the two-ledger split
(ALLOWLIST vs KNOWN_RISKS) mid-slice when the tournament-entry site
turned out to be a live class member that must not be blessed as safe.
Next checker-building slice should decide the not-green-not-safe lane
up front.
