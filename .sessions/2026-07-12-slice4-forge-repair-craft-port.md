# 2026-07-12 — slice 4 port: forge / repair / quickcraft / cook / use (workshop · campfire · consumables)

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 4 — the **workshop / campfire / consumable**
crafting rung. Five shipped commands move from honest D-0043 pending terminals
to real handlers, stacked on slice 3 (PR #292, itself on #289 on #286):
`!forge` · `!repair` · `!quickcraft` · `!cook` · `!use`.

Planned delivery:

- **Domain** (`sb/domain/mining/structures.py`): the forge/campfire structure
  math ported VERBATIM from the oracle (`disbot/utils/mining/structures.py`) —
  `FORGE`/`CAMPFIRE`, `BuildCost`, the `_FORGE_BUILD_LADDER`
  (3000🪙 + 25×iron/15×stone → Forge I → gold, then Forge II → diamond),
  `forge_level_name`, `tiers_unlocked_at`, `forge_build_cost`,
  `forge_level_required`, `cooking_unlocked`. Plus `recipes.py` (`load_recipes`)
  and the `workshop.describe_materials` / `repair_cost` helpers.
- **Stores + migrations**: `mining_structures` (built structure levels,
  `user_id` TEXT to match `mining_inventory`) + a `mining_player_state`
  `last_broken_item` column (the quickcraft marker). Migrations
  `0046_mining_structures.sql` (CREATE) + `0047_mining_last_broken.sql` (ALTER)
  (+ checksums).
- **Audited write ops** (`ops.py`): repair (economy debit + wear clear),
  craft / quickcraft (material consume + product grant + auto-equip + marker
  clear), cook (fish → cooked fish), use (consumable consume + energy restore),
  forge build (coin debit + material consume + level raise) — each one-leg
  one-txn, faithful to `services/mining_workflow.py`, each fenced against the
  money-race with a `pg_advisory_xact_lock` on the read-then-settle path.
- **Forge panel** (`panels.py`): the shipped `views/mining/forge_panel.py`
  `MiningForgeView` + `build_forge_embed` as a session `mining.forge` PanelSpec
  — 🔥 Build (success) · ↩ Workshop + the standard nav row, its live 🔥 Forge
  embed built by a renderer override (goldens/mining/sweep_forge pins every
  byte: title, MINING_COLOR, Level/Unlocks/Next fields, footer).
- **Handlers** (`service.py` `_register()`): the repair / cook / use usage
  guards (plain sends), the quickcraft "nothing broken" pure-read success, the
  forge panel route; `use`/`cook`/`forge`/`repair`/`quickcraft` removed from
  `PENDING` + `ensure_handler_refs`.
- **A-16 depth floor**: `depth.exemptions.mining` `guard-only-capture` rows for
  the new `table:mining_structures` (bare `!forge` renders the not-built card;
  the funded build write is in no golden).
- **Golden re-home** (#193 law): the 5 `_unmapped` sweeps
  (sweep_forge/repair/quickcraft/cook/use) re-homed into the gated `mining` row
  (gate 439 → 444) by `git mv` + the one sanctioned `subsystem` flip.

## Verification (local, real Postgres, pristine DB)

_(filled at close-out — see the landing report.)_

## 💡 Session idea

Slice 4 opens the crafting write lanes (`mining_structures`, `last_broken_item`,
plus the already-declared `mining_gear_wear` / `mining_inventory`) but every
imported sweep drove only the bare invocation: `!forge` renders the not-built
card, `!repair`/`!cook`/`!use` pin usage guards, and `!quickcraft` on a fresh
player is a pure read (`last_broken` is NULL → "Nothing has broken recently").
So the row-bearing forge build, the funded repair debit, and the material-consuming
craft land in NO golden. They join the growing `guard-only-capture` ledger
(equip / loadout / wear / skill / geared-descend / world-reseed / vault) — the
one capture run after the ladder completes should seed a persona with a built
forge + worn gear + a stock of materials, drive one `!repair`, one funded
`!forge` build, and one `!quickcraft` off a genuinely broken item, mint the
row-bearing goldens, and DELETE every held exemption at once (the D-0069 class
exit).

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-slice3-vault-stash-port.md`, the slice-3
vault/stash/unstash/vaultupgrade port.) Its headline — PUSHED + PR GREEN,
stacked on #289 — landed the safe-stash + capacity-sink stack clean and CI-green
first push. Two lessons carry directly into slice 4. First, its money-race
find: `_record_vault_upgrade` read `vault_level` then debited-and-bumped over a
possibly-nonexistent natural-key row, and `check_money_race` demanded a
`pg_advisory_xact_lock` fence keyed on (guild,user) BEFORE the read — the
identical read-then-settle shape recurs in every slice-4 write (repair debits
after a wear read; craft consumes after an inventory read; forge build debits +
consumes after a structures read), so each audited op is fenced from minute one
rather than after the checker reds. Second, its sim-gate note: the vault panel's
FIVE action buttons exceeded the 4-action auto-exempt floor and needed legacy-seed
Exempt overlays + a regenerated baseline; the slice-4 forge panel has only TWO
action buttons (🔥 Build · ↩ Workshop) below that floor, so — pending the
checker's confirmation — it should need NO sim-gate overlay, a smaller parity
surface than the vault card. The session-PanelSpec + renderer-override recipe
proven across slices 2–3 is reused verbatim for the forge card.
