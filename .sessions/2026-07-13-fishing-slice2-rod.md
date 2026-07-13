# 2026-07-13 — fishing depth slice 2 port: rod / rodrecipes / craftrod (rod ladder)

> **Status:** `in-progress`

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
  sweep_craftrod) re-homed into the gated `fishing` row (#193 law);
  `fishing_rod` exemption row (`guard-only-capture`); ratchet fishing
  `{tables: 4 → 5}` (`--write-ratchet`, splice-only).

## Verification (local, real Postgres, pristine parity_replay DB)

(to be filled at close)

## 💡 Session idea

(to be filled at close)

## ⟲ Previous-session review

(to be filled at close)
