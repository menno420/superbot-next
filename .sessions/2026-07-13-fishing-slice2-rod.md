# 2026-07-13 — fishing depth slice 2 port: rod / rodrecipes / craftrod (rod ladder)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · feature build

## Scope

The faithful port of fishing depth slice 2 — the rod ladder rung of the
fishing gear port (D-0043 named successor scope; lane claim
`control/claims/fishing-port-remaining.md`, built directly atop slice 1 =
PR #313 / `3bd42d3`). Three shipped commands move from honest D-0043
pending terminals to real surfaces: `!rod` · `!rodrecipes` · `!craftrod`.

Planned shape (the #313 slice recipe):

- **Domain** (`sb/domain/fishing/rods.py`, NEW): the shipped
  `utils/fishing/rods.py` ported verbatim — the five-rung ROD_LADDER
  (Bare 🎣 0 / Bronze 🥉 250 / Silver 🥈 750 / Gold 🥇 2000 / Diamond 💎
  5000, five knobs each), ROD_RECIPES (1:10≤6 · 2:16≤12 · 3:26≤18 ·
  4:40≤21), `rod_for_tier`/`next_rod`/`rod_recipe`/`rod_recipe_text`.
- **Domain** (`sb/domain/fishing/crafting.py`, NEW): the shared
  fish-spend planner (`_eligible_fish`/`eligible_fish_total`/
  `_plan_fish_spend` — smallest-first, ties by name) from
  `services/fishing_workflow.py`.
- **Store + migration**: `fishing_rod` (per-(user, guild) owned rod tier;
  no row reads as 0 — the shipped migration-087 shape) as a MEMBER_ID
  registered store with the `fishing.erase_subject_rod` delete-erasure
  body; migration `0049_fishing_rod.sql` (+ checksums).
- **Handlers**: `fishing.rod_shop` (the rod-shop panel — ladder embed +
  ⬆️ Upgrade / 🎣 Craft from fish / 📋 Recipes buttons),
  `fishing.rodrecipes_view` (the recipe browser + live progress),
  `fishing.craftrod_route` (the fish→rod craft: guards as pure reads, the
  write as an audited one-leg one-txn op), `fishing.rod_upgrade_route`
  (buy_rod — the audited coin debit leg, #217 locking-read pattern,
  balance event after commit). The three keys leave `PENDING`; their
  `*_pending` refs pruned from the composition-parity burn-down.
- **Parity**: the 3 `_unmapped` sweeps (sweep_rod / sweep_rodrecipes /
  sweep_craftrod) re-homed into the gated `fishing` row (#193 law: `git
  mv` + the one sanctioned `subsystem` flip); `fishing_rod` is a NEW
  declared table surface EXEMPT under `guard-only-capture` (all three
  sweeps pin write-free bytes — the tier-0 shop/browser renders and the
  "need **10** fish" refusal are pure reads). **Ratchet deviation from
  the build plan, tool-authoritative:** the plan predicted fishing
  `{tables: 4 → 5}`, but `check_parity_depth.py --write-ratchet`
  regenerated the block UNCHANGED — the ratchet floors what the
  subsystem's goldens' db_delta actually touches, and guard-only sweeps
  add no new table (slice 1 moved 3→4 only because sweep_sail itself
  minted the `fishing_venue` row). The one-way floor stays
  `{events: 1, tables: 4}`; R2 is satisfied by the exemption row, and
  the floor rises when the first row-bearing `fishing_rod` golden lands.

## Verification (local, real Postgres 16, pristine parity_replay DB)

- **golden-parity GATE GREEN — all 474 golden(s) across 51 ported
  subsystem(s) replay clean** (the +3 re-home takes fishing 9 → 12,
  `_unmapped` 13 → 10; all three re-homed sweeps replay byte-identical
  against the new panels/handlers on first mint).
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  484 goldens**; `fishing_rod` exempt (`guard-only-capture`).
- **check_migrations: clean (49)**; **manifest_compile: green
  (sha256:1a2009b0…5db4, 48 manifest(s))** (snapshot recompiled).
- **check_money_race: OK — 0 violations under sb/domain (2 allowlisted,
  0 ledgered known-risk)** — the buy_rod leg is advisory-fenced
  (`lock_rod_slot` BEFORE the tier read → debit → bump; the
  vault-upgrade #217 shape) and craft_rod rides the same fence against
  a concurrent double-craft.
- **check_sim_gate: OK — 1360 [A] assignment(s), 543 auto-exempt
  below-floor** — both new panels sit at ≤ 4 declared actions (the
  below-floor rule), so no overlay/lock rows minted.
- **check_compat_frozen: OK** (no new command names/aliases — all three
  commands were already declared; only their routes went live).
- **check_namespace / check_escape_hatches / check_schema_growth /
  check_amendments / check_runtime_smoke / check_symbol_shadowing /
  check_no_skip / check_config_usage / check_metric_cardinality /
  check_egress: clean.**
- **pytest tests/integration -q: 11 passed.**
- **pytest tests/: 2077 passed, 2 skipped** (includes the new
  `tests/unit/band6/test_band6_fishing_rod.py` — ladder/recipe verbatim
  numbers, spend-planner smallest-first order, the craftrod guard byte
  vs the golden, panel spec component trees, store spec/erasure refs,
  manifest + hub route flips).

### 3 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_rod, sweep_rodrecipes, sweep_craftrod — only the `"subsystem"`
line changed (`_unmapped` → `fishing`); calls/events/db_delta bytes
untouched (#193 law). All three pin write-free guard/read bytes, so
`fishing_rod` lands exempt, not covered.

## 💡 Session idea

The build plan's ratchet arithmetic drifted from the tool twice in one
lane (slice 1 "3→4" was right for the wrong-looking reason — a bare
command whose first invocation IS the write; slice 2's predicted "4→5"
was simply wrong because guard-only sweeps move nothing). The fix is to
stop hand-predicting ratchet rows in plans at all: plans should state
only "run `--write-ratchet` and commit whatever splice it produces —
expect movement ONLY when a re-homed/minted golden's db_delta carries a
new table". One sentence of doctrine in the porting plan template would
have saved both slices the reconciliation paragraph and removes a whole
class of plan-vs-tool disagreement a reviewer would otherwise have to
adjudicate.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-fishing-slice1-forecast-sail.md@3bd42d3`.)
Its slice recipe transferred wholesale — the born-red card sequencing,
the #193 re-home mechanics, the exemption-row format and the band6 test
shape were all reusable verbatim, and its session idea (batch the argful
craft lanes so exemption rows land in reviewed blocks) directly shaped
this slice's grouping — the ledger loop closing again. One gap: its
Verification section reported the ratchet move as if it were the generic
outcome ("ratchet fishing {tables: 3 → 4}") without flagging that the
move happened only because sweep_sail's own db_delta carried the row —
a one-line "ratchet moves only with row-bearing goldens" note there
would have kept this slice's plan from predicting a phantom 4→5.
