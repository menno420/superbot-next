# 2026-07-11 — farm/mining money-race fix (the F-001/F-002 class, PR #213's siblings)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · bug fix + regression tests (Q-0194)

## Scope

Close the farm and mining money-race sites — the same
unlocked-read → settle → credit defect class #213 (merge `f71d60b`)
fixed for the blackjack/rps checkpoint store — with red-then-green
regression tests on real Postgres FIRST, then sweep BOTH domains for
every same-class site plus a bounded check of the other economy-shaped
domains. Origin: the parked codex-cloud risk reviews #196/#206 named
farm/mining money races among their claims; per the claim file
(`control/claims/codex-risk-review-prs-196-206.md`) every claim was
verified end-to-end against shipped source before acting.

## Races confirmed and fixed (each reproduced RED live pre-fix)

All four sit inside K7 legs declaring `IdempotencyPosture.NATURAL_KEY`
— the posture whose "intrinsically once" contract puts the WHOLE
concurrency fence on the DB legs (the #213 root-cause analysis holds
verbatim here):

1. **`farm.collect` double-credit** (`sb/domain/farm/ops.py::
   _record_collect` over `sb/domain/farm/store.py::get_farm`) — plain
   SELECT: two concurrent collects both read `eggs > 0`, both
   `wager.credit_in_txn` the payout, both upsert `eggs=0`. Reproduced:
   both racers succeeded, balance +2× payout (a pure mint).
2. **`farm.buy_chicken` first-insert race** (fresh farmer, no
   `chicken_farm` row yet) — `FOR UPDATE` cannot fence a row that does
   not exist: both racers read the starter defaults, both debit
   `chicken_price(1)`, both upsert `chickens=2` — the user pays twice
   and one purchase vanishes (the count-reset flavor; the same stale
   write-back also lets a racing buy/upgrade restore pre-collect eggs
   over a committed `eggs=0`, a re-mint enabler). Reproduced: 2 hens
   where 3 were paid for.
3. **`mining.sell` double-payout** (`sb/domain/mining/ops.py::
   _record_sell` over `get_mining_inventory`) — plain SELECT plus
   `update_mining_item`'s `GREATEST(0, …)` decrement floor: both
   racers read `held=N`, the loser's decrement silently floors, BOTH
   credit `N × price`. Reproduced: balance +2× the stack's value.
4. **`mining.sell_all`** — the whole-inventory twin of (3).
   Reproduced identically.

## Fix (mirrors #213: locking reads; advisory lock where no row exists yet)

- `sb/domain/farm/store.py::get_farm` grew `for_update: bool = False`:
  when set it takes `pg_advisory_xact_lock(hashtext('farm:slot:…'))`
  keyed on the SAME (guild, user) pair the `set_farm` upsert conflicts
  on (the `lock_new_checkpoint_slot` precedent — fences the no-row
  first-insert race), THEN reads `… FOR UPDATE` (the existing-row
  fence + a fence against the erasure lane's DELETE). Refuses loudly
  (`ValueError`) without a conn — a locking read outside the leg's
  transaction fences nothing.
- All three farm money legs (`_record_collect`, `_record_buy_chicken`,
  `_record_upgrade_coop`) now pass `for_update=True`.
- `sb/domain/mining/store.py::get_mining_inventory` grew the same
  flag: `… ORDER BY item_name FOR UPDATE` (deterministic lock order —
  no deadlock between two concurrent multi-row sell_alls). No advisory
  lock needed on this lane: selling requires `held > 0`, so the rows
  exist and the row locks fence. Same no-conn refusal.
- `_record_sell` and `_record_sell_all` pass `for_update=True`.
- Display/roll paths (panels, leaderboards, mine/harvest/explore loot
  reads) stay unlocked plain reads — no contention added.

## Evidence

- `tests/integration/test_farm_mining_money_race.py` — real Postgres,
  real K7 engine, two genuinely concurrent transactions
  (`asyncio.gather` + the #213 hold-the-first-caller technique so the
  overlap is scheduling-order-independent). Four tests: farm collect,
  farm first-buy (advisory-lock half specifically — no row exists),
  mining sell, mining sell_all. All four reproduced their race RED at
  HEAD `977bb27` (assertions like `2 == 1` successes / doubled net
  balance) and pass post-fix; 3 consecutive full runs, zero flakes.
- Fast DB-free SQL pins in
  `tests/unit/band6/test_band6_games_substrate.py` (the #213 companion
  pattern): locked reads carry `FOR UPDATE` (+ the advisory lock for
  farm, + `ORDER BY item_name` for mining), plain reads stay unlocked,
  and both stores refuse `for_update=True` without a conn — an
  accidental revert reds even where no Postgres is available.
- Full ladder at the branch head, local real Postgres 16:
  `tests/unit` 1473 passed / 2 skipped; `tests/integration` 9 passed
  (the 5 pre-existing #213 races stay green); gate GREEN — all 266
  goldens across 39 ported subsystems replay clean; report 302/467
  green, 467/467 replayable — byte-identical to the HEAD baseline
  measured the same way (stash-diffed): this fix moves ZERO goldens.
- Checker fleet green: manifest_compile, check_namespace,
  check_escape_hatches, check_schema_growth, check_amendments,
  check_symbol_shadowing, check_no_skip, check_config_usage,
  check_metric_cardinality, check_egress, check_sim_gate,
  check_parity_depth (50 subsystems / 39 ported / 467 goldens),
  `bootstrap.py check --strict`.

## Sweep (named exactly, per the task)

Every read-then-write lane in BOTH domains walked end-to-end:

- **farm**: `_record_collect` / `_record_buy_chicken` /
  `_record_upgrade_coop` — all three FIXED (above). `top_farmers`,
  `panels.py` reads, `erase_subject_farm` — display/atomic, CLEAN.
- **mining**: `_record_sell` / `_record_sell_all` — FIXED.
  `_record_mine` / `_record_harvest` / `_record_explore` — unlocked
  reads feed only the loot RNG and XP award; writes are atomic
  `ON CONFLICT` delta upserts; no money moves from a read value —
  CLEAN. `_record_buy` — conditional `try_debit_coins` (one-statement
  decide-and-write) then atomic upsert — CLEAN. `get_depth` /
  `mining_totals` — display/XP lanes — CLEAN.
- **Bounded check of the other economy-shaped domains**:
  - `fishing` (`_record_cast`) — no credit/debit at all; dex + item
    writes are atomic upserts; the `record_catch` prior-best pre-read
    can only misreport the "new personal best" flourish under a race,
    never money — CLEAN (cosmetic nuance ledgered here, not chased).
  - `treasury` — `try_debit_coins` / `try_debit_treasury` are
    conditional single-statement writes, `credit_treasury` is an
    atomic upsert — CLEAN (the #214 flip's shape held).
  - `creature` — no money movement (counts via atomic upserts) — CLEAN.
  - `casino` — display/evaluation only (no store writes, no wager
    calls) — CLEAN.
  - `inventory` — read-only composition over other stores — CLEAN.
  - `economy` daily/work lanes — already `SELECT … FOR UPDATE`
    (`get_or_create_economy_row`) — CLEAN.
  - `games`/`blackjack`/`rps` — fixed by #213; its 5 integration race
    tests re-run green here.
  - `deathmatch` — same unlocked-load shape but moves no money (#213's
    sweep finding stands) — left as-is.

## Goldens (classify-or-fix, ORDER 009 disposition)

farm 0/1, mining 0/2, fishing 0/2 report rows are red at HEAD and red
at the branch head with IDENTICAL counts (302/467 both sides, measured
stash-diffed on the same DB): pre-existing pending-row corpus reds
(`pending` rows in parity/parity.yml — the standing red-until-ported
report class, flag-13 disposition), not movement from this fix. Zero
goldens changed classification.

## 💡 Session idea

The `tools/check_natural_key_fencing.py` idea from the #213 session
card is now TWICE-evidenced: farm/mining shipped the same
NATURAL_KEY-op-without-a-locking-read gap #213 closed for games, and
a structural grep (every DB leg reachable from a NATURAL_KEY op must
carry `FOR UPDATE`, `pg_advisory_xact_lock`, or a conditional
one-statement write) would have caught both at review time. Worth
building before the next economy domain ports (four_twenty, casino
play lanes, the mining deep systems).

## ⟲ Previous-session review

The #213 session card (`.sessions/2026-07-11-precutover-wallet-race-
and-parity-gate-fixes.md`) is the best prior-session artifact this
lane has produced: its root-cause section named the defect CLASS (not
just the instance), which made this session's sweep mechanical — grep
the posture, walk the legs, rig the race. What it left on the table:
its own sweep stopped at the games checkpoint store's callers and
never walked the OTHER `NATURAL_KEY` economy domains (farm/mining were
already in-tree, same bug, same day) — the class-level lesson is that
a defect-class fix should end with a repo-wide posture sweep, not a
caller sweep. This session did that sweep; the fencing checker idea
above is how the next one gets it for free.
