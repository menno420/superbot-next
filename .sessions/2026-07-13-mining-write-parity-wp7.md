# 2026-07-13 — deep-mining WRITE-PARITY lane — WP-7 residual pending legs (respec / title-equip / craft) PORT + write goldens

> **Status:** complete (WP-7 DELIVERED — the two residual non-energy pending
> WRITE legs the write-parity lane left honest-pending are ported onto the
> audited `@workflow("mining.record_*")` seam and driven by capture goldens:
> **respec** (oracle `skill_service.respec` — level-scaled coin fee via
> `wager.debit_in_txn` → every `player_skills` branch zeroed in ONE
> `lock_skill_slot`-fenced txn; the skills-panel ♻ Respec button flipped from
> `mining.skill_respec_pending` to the live `mining.skill_respec_route`) and the
> argful **`!craft <item>`** / **`!build <item>`** (oracle `mining_workflow.craft`
> — recipe materials consume + `+1` product into `mining_inventory` + crafting
> game-XP in ONE `lock_workshop_slot`-fenced txn; `build_route`'s argful branch
> flipped live). **title-equip stays DROPPED (honest D-0043 pending)** — no
> command form, select-driven ingress, the target titles panel renders no
> earned-title Select (see below). 4 goldens minted byte-identical (corpus
> 494→498, gate 479→483 ported goldens); WP-7 retires NO exemption
> (`player_skills` / `mining_player_state` / `mining_inventory` already covered)
> so `check_parity_depth` stays green with no exemption change; two-txn
> respec/craft concurrency regressions RED→GREEN; gate GREEN + all checkers
> green. PR #371, stacked on WP-6 (#344, branch `mining-write-parity-wp6`).)

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

## 💡 Session idea

WP-7 is where "port the pending leg" and "build new UI" had to be told apart, and
the honest move was to refuse the second. respec and `!craft` each had a real
command/panel ingress the capture harness could already drive, so flipping them
was a pending-flip: same audited seam, oracle copy verbatim, one txn, one fence,
a golden that pins the mutation. title-equip did NOT — its only ingress is a
state-derived earned-title Select the target panel doesn't even render, so
porting it would mean *constructing* new dynamic PanelSpec Select UI with no
target precedent, not flipping a terminal. The durable discipline: a residual
"pending" is only a pending-flip when a drivable ingress already exists at the
target; when the port requires minting new ingress UI, that is new construction
and belongs to its own scoped slice, not smuggled into a coverage-deepening pass.
A checker worth having would flag a route flipped from a `*_pending` terminal
whose target view renders no component capable of reaching the new op — the
mechanical shape of "I forced an ingress that wasn't there." The corollary that
paid off again: a panel-only WRITE (the ♻ Respec button) is still golden-coverable
through `component_index` without a command form (the WP-6 forge-button precedent).

## ⟲ Previous-session review

WP-6 (#344) ported `mining_workflow.build_structure` onto `mining.build ->
record_build`, flipped the forge/home 🔥 Build panel terminals live, minted 2
structure-build goldens, retired the LAST mining exemption (`mining_structures`,
ratchet `{tables:16→17}`), added `lock_structure_slot` + a double-build regression
(RED→GREEN); gate 479 — the write-parity lane's exemption work COMPLETE. Its 💡
warned the exact trap WP-7 sits next to: the spec's assumed ingress can be wrong
(it imagined `!build <structure>` → `build_structure`, but the command routes to
`mining_workflow.craft`), so confirm the command→service EDGE against the oracle
cog before trusting a slice plan. WP-7 honored that by verifying `!craft`/`!build`
actually dispatch `mining_workflow.craft` (the `mining_inventory` product leg) —
and by NOT forcing title-equip's absent Select ingress. Goldens minted via
`sb/adapters/parity/runner.capture_case`; the manifest snapshot recompiled
(`tools/manifest_compile.py --write`) because the new ops add workflow refs.
