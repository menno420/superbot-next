# 2026-07-13 — fishing: cast bait-consume race fence + secondary ledger notes

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · verify-and-fix lane: the suspected
  cast-vs-buy bait-slot lost update (third-party review lead), plus
  three triaged non-money races dispositioned as ledgered posture notes
  (no locking changes).

## Scope

1. VERIFY the lead against source: `begin_cast`
   (`sb/domain/fishing/service.py`, the `fishing.cast_open` handler)
   reads the active bait slot with a plain unlocked autocommit read and
   later writes back an ABSOLUTE `charges - 1` (or clears the row),
   while the buy/craft legs stack/replace the loadout behind
   `store.lock_bait_slot` in their own txn — a bait purchase committing
   inside the cast's read→write window loses its coin-bought charges
   (or the whole replaced pack, on the clear path).
2. If confirmed: the MINIMAL fence consistent with the surrounding
   store code — convert the cast's write-back to a single conditional
   relative decrement (`UPDATE … SET charges = charges - 1 WHERE …
   AND bait_key = $3 AND charges >= 1`, clearing the pack in the same
   statement at zero), NOT a new lock: the consume leg is not in a txn
   and the one-statement decrement closes the lost update without
   changing any user-visible byte.
3. Secondary (ledger notes only, no locking changes): `!use`
   double-settle (already noted in `_record_use_item`'s docstring —
   skip), `!cook` mint-from-one-stack (`sb/domain/mining/ops.py`
   `_record_cook`), cross-craft fish spend under per-kind advisory
   locks (`sb/domain/fishing/ops.py` `_record_craft_rod` /
   `_record_craft_bait` / `_record_craft_charm`).
4. Regression tests: deterministic cast-vs-buy interleave through the
   real `fishing.cast_open` handler (unit, fake stores — the
   band6 cast-wiring harness), plus real-Postgres semantics for the new
   `consume_bait_charge` including the true stale-read × locked-buy
   interleave (integration, skips without Postgres like every race
   test).

NOT this session: no golden/parity changes (no golden drives a
bait-loaded cast — `fishing_bait` is guard-only-capture), no
`check_money_race` edits, no locking on the three ledgered secondary
sites, no PR #392 contact.

## Guard recipe

If a future slice makes the cast consume transactional (e.g. folding it
into an audited op), take `store.lock_bait_slot` before the loadout
read like the buy/craft legs and retire `consume_bait_charge`'s
contention `None` branch — test target:
`tests/unit/band6/test_band6_fishing_cast_wiring.py::test_cast_open_consume_never_clobbers_a_concurrent_bait_buy`.

## 💡 Session idea

`check_money_race` only recognizes coin legs (`wager.debit_in_txn` /
credit), so a coin-PURCHASED consumable spent on a lockless game lane
(this bait slot; potentially any future consumable) is invisible to the
checker even though eating it destroys purchased value. A cheap
extension: let store modules declare "coin-funded tables" and have the
checker flag any unfenced absolute write-back to one — this class would
have been caught mechanically.

## ⟲ Previous-session review

Previous card (`2026-07-13-energy-slice-2.md`, PR #385): its
decide-and-flag list ("in-txn re-checks refuse raced writes the oracle
would dupe") is exactly the doctrine this session leaned on, and the
flip-playbook trap it wrote up saved this session a wrong turn on
refusal copy; one miss — it called the cook race "the port refuses"
for the in-txn re-check, but the cook leg's stack check still reads
pre-lock (no fence), which is precisely secondary item 2 here.
