# 2026-07-13 — fishing depth slice 2 port: rod / bait (the gear-shop rung)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · high · feature build (Q-0194)

## Scope

The faithful port of fishing depth slice 2 — the gear-shop rung of the
D-0043 fishing ladder (slice 1 landed weather + venue on
`claude/fishing-slice1-forecast-sail`, PR #313; this branch is based on
that PR's post-merge head, unmerged at branch time). Two shipped commands
move from honest D-0043 pending terminals to real surfaces:
`!rod` · `!bait` — the oracle's own module grouping
(`utils/fishing/rods.py` + `utils/fishing/bait.py` +
`views/fishing/rod_shop.py` + `views/fishing/bait_shop.py`; the craft*
family is the NEXT rung — slice 1's 💡 idea: batch the argful craft lanes
last so their exemption rows land in one reviewed block).

Planned delivery:

- **Domain** (`sb/domain/fishing/rods.py` + `bait.py`, NEW): the shipped
  pure modules ported verbatim — the 5-rung `ROD_LADDER` (knobs + prices),
  `rod_for_tier`/`next_rod`, the `ROD_RECIPES` fish→rod shelf (data only —
  the craft LANE rides the craft* rung); the 6-bait `BAIT_CATALOG`
  (rarity/speed/combo families), `effect_text`, the `CRAFT_RECIPES` +
  `PEARL_BAIT_RECIPES` shelves (data only — the shop embed lists them,
  the craft lanes stay pending).
- **Stores + migrations**: `fishing_rod` (owned tier; no row = starter
  tier 0 — shipped migration-087 shape) and `fishing_bait` (loaded key +
  charges; no row / 0 charges = bait-less — shipped migration-091 shape)
  as MEMBER_ID registered stores with delete-erasure bodies; migrations
  `0049_fishing_rod.sql` + `0050_fishing_bait.sql` (+ checksums).
- **Ops (money)**: `fishing.rod_upgrade` + `fishing.bait_buy` — the
  audited one-leg buy txns (advisory-fenced read → `wager.debit_in_txn`
  → tier bump / bait load; balance event after commit — the
  mining.vault_upgrade precedent; oracle `buy_rod`/`buy_bait` verbatim
  messages + reasons `fishing:rod_purchase`/`fishing:bait_purchase`).
- **Panels**: `fishing.rod_shop` (Upgrade/Craft/Recipes buttons + the
  ladder embed) and `fishing.bait_shop` (buy/craft/pearl selects + the
  shelf embed) — goldens/_unmapped/sweep_rod + sweep_bait pin the
  fresh-player bytes; hub 🎒 Rod / 🪱 Bait buttons repoint pending →
  the live panels. Craft/Recipes lanes stay honest pending terminals
  (the craft* rung).
- **Parity**: the 2 `_unmapped` sweeps re-home into the gated `fishing`
  row (#193 law: `git mv` + the one sanctioned subsystem flip); the two
  new tables sit behind run-minted button/select interactions no
  imported golden can drive → 2 exemption rows (button/select-driven —
  the fishing_catch_log / role_automation_exemptions precedents);
  ratchet re-derived (`--write-ratchet`, splice-only).

## Verification

(planned: full local ladder — pytest, manifest_compile + checker fleet,
bootstrap check --strict, check_parity_depth, run_golden_parity --gate,
integration)
