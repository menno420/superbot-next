# 2026-07-13 — fishing: bait-only port (coordinated fill, lane #324)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · high · feature build

## Scope

The BAIT-ONLY fill of the fishing gear rung, per the 2026-07-13
coordinator adjudication: PR #328 (`claude/fishing-slice2-rod-bait` @
`3ced297`, the rod+bait slice) collided with the #324 whole-lane fishing
claim (`control/claims/fishing-port-remaining.md`, earlier at HEAD) and
its landed rod slice (#330, merged at `4493cc2`). Ruling: rod is CEDED
to #330; this branch re-scopes the salvageable half — `!bait` and the
bait shop — as a coordinated fill of the one gear surface the #324 lane
has NOT put in flight (verified: no open PR / `claude/*` branch carries
bait work at branch time).

Planned shape (salvaged from `3ced297`, adapted to main's landed #330
shapes — `lock_rod_slot`, `fishing.buy_rod` op naming, the
`fishing.rod_panel` panel ids, the slice-2 PENDING dict):

- **Domain** (`sb/domain/fishing/bait.py`, NEW): the shipped
  `utils/fishing/bait.py` ported verbatim — the 6-bait `BAIT_CATALOG`
  (worm/grub/lure · minnow/spinner · feast), `effect_text`, the
  `CRAFT_RECIPES` + `PEARL_BAIT_RECIPES` shelves carried as DATA (the
  shop embed's craft fields are golden-pinned; the craft LANES stay
  pending — the craft* rung).
- **Store + migration**: `fishing_bait` (no row / 0 charges = bait-less
  — shipped 091 shape; migration `0050_fishing_bait.sql`, renumbered to
  follow main's 0049 ladder) as a MEMBER_ID registered store with the
  `fishing.erase_subject_bait` delete-erasure body (+ checksums).
- **Op (money)**: `fishing.buy_bait` — audited one-leg buy txn
  (advisory `lock_bait_slot` fence → loadout read → `wager.debit_in_txn`
  → load in ONE txn; `_balance_changes` → `economy.balance_changed`
  after commit — the #330 `fishing.buy_rod` / mining vault_upgrade
  precedent). Oracle `buy_bait` copy + the `fishing:bait_purchase`
  reason verbatim; same-bait stacking / different-bait replace carried.
- **Handlers**: `fishing.bait_shop` (panel open — the #330
  `fishing.rod_shop` naming), `fishing.bait_buy_route` (guards as PURE
  reads — unknown-key / insufficient answer without a write; only a
  funded pick runs the op).
- **Panel**: `fishing.bait_panel` (buy / craft-from-fish /
  craft-from-pearls selects with provider-fed rich options + ↩ Fishing
  menu; live pearl count off mining_inventory; ECONOMY_COLOR gold,
  `session_lifecycle`, NO standard nav); hub 🪱 Bait repoints pending →
  `PanelRef`. The craft selects route the `craftbait`/`craftpearl`
  pending terminals, registered at IMPORT in panels.py (burn-down
  pruned: `bait`/`craftbait`/`craftpearl` pending leave ensure-only).
- **Parity**: `goldens/_unmapped/sweep_bait.json` re-homed into the
  gated `fishing` row (#193 law: `git mv` + the one sanctioned
  `subsystem` flip); `fishing_bait` lands EXEMPT (select-driven — the
  D-0064 class); ratchet unchanged (a read-only open adds no covered
  table — the #330 lesson).
- **NO rod work anywhere in the diff** — rod/rodrecipes/craftrod are
  #330's, landed.

## Verification target

The six-gates ladder per docs/operations/local-verification.md: pytest
tests/ green · manifest_compile + checker fleet · bootstrap check
--strict · check_parity_depth · golden-parity --gate GREEN ·
tests/integration green.
