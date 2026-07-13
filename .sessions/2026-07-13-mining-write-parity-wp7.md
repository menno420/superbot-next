# 2026-07-13 — deep-mining WRITE-PARITY lane — WP-7 residual pending legs (respec / title-equip / craft) PORT + write goldens

> **Status:** IN FLIGHT (born red) — PORT the residual non-energy pending legs
> the write-parity lane left honest-pending: **respec** (skills-panel ♻ Respec
> coin-sink → `player_skills` wipe), **title-equip** (equipped-title selection),
> and the argful **`!craft <item>`** command (materials → `mining_inventory`
> product). Each is replaced with a real handler routed through the audited
> `@workflow("mining.record_*")` seam + goldens minted by the capture harness.
> Adds a `pg_advisory_xact_lock` fence + a two-txn concurrency regression for the
> read-then-settle money/material legs (respec coins, craft materials). Born red
> by design; flips complete on the last commit. Stacked on WP-6
> (#344, branch `mining-write-parity-wp6`).

- **📊 Model:** opus-4.8 · high · parity/golden-minting (Q-0194)

## WP-7 scope (the residual non-energy pending legs)

The write-parity lane (WP-1..6) retired all 8 mining `guard-only-capture`
exemptions. Three non-energy WRITE terminals were left honest-pending because
their ingress wasn't yet drivable by the capture harness: **respec**
(panel-button coin sink), **title-equip** (select-driven), and the argful
**`!craft <item>`** command (the oracle build/craft alias routes to
`mining_workflow.craft`). None of the three rides an exemption — `player_skills`
(WP-5), `mining_player_state` (WP-2), and `mining_inventory` (already covered by
mine/sell) are all covered — so this slice adds no exemption retire and
`check_parity_depth` stays green without one.

### craft (`!craft <item>` / `!build <item>`) — PORT + MINT
Oracle `services/mining_workflow.py::craft` (materials + product in ONE txn):
resolve recipe (no-recipe copy), forge-gate, materials-check, consume the
recipe materials + `+1` product into `mining_inventory`, award crafting game-XP
— all in one advisory-fenced txn. New `@workflow("mining.record_craft")` leg +
`mining.craft` op; `build_route`'s argful branch flipped from D-0043 pending to
the audited op (mention-prefixed on both faces — the shipped
`ctx.send(f"{mention} {msg}")`).

### respec (♻ Respec skills-panel button) — PORT + MINT
Oracle `services/skill_service.py::respec` (level-scaled coin fee → clear every
`player_skills` branch, ONE txn — coin debit economy-audited, balance event
after commit). New `@workflow("mining.record_respec")` leg + `mining.respec` op;
the skills-panel ♻ Respec button flipped from `mining.skill_respec_pending` to a
live `mining.skill_respec_route` (driven by the session-panel button click via
`component_index` — the WP-6 forge 🔥 Build precedent).

### title-equip — DROPPED (kept honest-pending), with citations
Title-equip has **no command form** (oracle `mining_cog.py::titles_cmd` only
opens the panel) and its only ingress is the `MiningTitlesView` earned-title
**Select** (oracle `views/mining/titles_panel.py` — "this view is only the
select that calls `title_service.equip`"). The target `mining_titles_spec`
renders **no earned-title Select at all** (panels.py — "the earned-title display
Select (the equip WRITE lane) is absent from the view"). Porting it would mean
**building new dynamic, state-derived Select panel UI** (options = the player's
earned titles) into the PanelSpec grammar — new-UI construction with no target
precedent for state-derived session-select options, not a pending-flip. Per
scope PART C (the pre-flagged biggest risk: "park honest-pending unless a command
form exists") this stays an honest D-0043 pending — it is not forced. It retires
no exemption (`mining_player_state` was retired in WP-2), so the gate is
unaffected.

## MONEY-RACE — respec (coins) + craft (materials) fences

Both are read-then-settle: respec reads the alloc + level then debits + wipes;
craft reads the pack then consumes + adds. `record_respec` re-uses
`lock_skill_slot` (same `player_skills` fence as `!skill`) acquired BEFORE the
alloc read (two racing respecs → the loser blocks, re-reads an empty alloc, no
double-charge). `record_craft` re-uses `lock_workshop_slot` (the craft/material
fence, the `quick_craft` precedent) acquired BEFORE the pack read (two racing
crafts → no double-consume). Two-txn Postgres regressions prove each serializes
(RED without lock, GREEN with).

## Goldens (capture_case, byte-stable)

- `mining.craft_write` — `!craft <item>` (materials fixture) → `mining_inventory`
  consume + product `+1` db_delta + crafting game-XP.
- `mining.craft_no_recipe` — `!craft <unknown>` → the no-recipe refusal
  (mention-prefixed), a pure read (no db_delta) — the key craft error branch.
- `mining.respec_write` — `!skills` then the ♻ Respec click (funded + allocated
  `player_skills` fixture) → the branch rows zeroed + the coin debit db_delta.
- `mining.respec_insufficient` — `!skills` then the ♻ Respec click with no coins
  → the insufficient-funds refusal (mention-prefixed), a pure read — the key
  respec error branch.

## Stack

Stacked on WP-6 (#344, branch `mining-write-parity-wp6`) → #335 → #317 → #312 →
main. Open + unmerged; the owner sweeps the stack in the morning. Merge order:
`#312 → #317 → #335 → #344 → this (WP-7)`.
