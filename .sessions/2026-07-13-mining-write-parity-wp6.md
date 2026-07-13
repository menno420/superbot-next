# 2026-07-13 — deep-mining WRITE-PARITY lane — WP-6 structure-build PORT + write golden (FINAL slice)

> **Status:** complete (WP-6 DELIVERED — the oracle
> `mining_workflow.build_structure` ported verbatim onto the audited
> `mining.build -> record_build` seam, the forge/home 🔥 Build panel terminals
> flipped from D-0043 pending to live `forge_build_route` / `home_build_route`
> handlers, two structure-build write goldens minted byte-identical, the LAST
> mining `guard-only-capture` exemption (`mining_structures`) retired (ratchet
> mining `{tables:16->17}`), a `lock_structure_slot` advisory fence + a two-txn
> double-build concurrency regression added (RED→GREEN observed); gate GREEN
> (479 ported goldens) + all checkers green. PR #344, stacked on #335. **With
> `mining_structures` retired, the deep-mining WRITE-PARITY lane is COMPLETE —
> all 8 planned mining exemptions retired.**)

- **📊 Model:** opus-4.8 · high · parity/golden-minting (Q-0194)

## WP-6 scope (structures/craft — PORT + MINT), the FINAL slice

Stacked on WP-5 (#335). At HEAD the ONLY remaining `depth.exemptions.mining`
`guard-only-capture` row is **`mining_structures`** — this slice retires it, so
after WP-6 the mining exemption list is EMPTY of mining tables and the whole
write-parity lane is COMPLETE.

The structure BUILD write (🔥 Build / 🏠 Build on the forge/home panels) was an
honest D-0043 pending terminal (`_forge_button_handlers` / `_home_button_handlers`
returned the BLOCKED successor copy; NO `record_build` leg). This slice PORTS the
oracle `services/mining_workflow.py::build_structure` faithfully:

- New `@workflow("mining.record_build")` leg (`ops.py`) + `mining.build`
  CompoundOpSpec (audit_verb `mining_structure_built`) — registry-driven
  (material-agnostic): reads the built level, sizes the `structures.build_cost`
  (coins + materials), then debits coins via `wager.debit_in_txn`, consumes the
  materials, and raises the structure level by one — all in ONE advisory-fenced
  txn. Constants/copy VERBATIM from the oracle.
- The forge/home 🔥 Build panel terminals flipped to live `mining.forge_build_route`
  / `mining.home_build_route` handlers that gate the maxed / insufficient-materials
  / insufficient-funds refusals as PURE READS (no audit row on refusal, the
  `vaultupgrade_route` precedent), run the audited op on the success path, and
  prefix the invoker mention on the reply (the target's mining panel-write-button
  convention — `stash_all_route` / `vaultupgrade_route`).
- New `market.structure_build_reason(structure)` = `mining:{structure}_build`
  (oracle-verbatim generic reason, the BUG-0031 fix shape).

## MONEY-RACE — double-build fence

Build is a read-then-settle over coins + materials: two concurrent 🔥 Build
clicks both read level L, both pass the affordability check, both debit + bump →
a double-charge / skipped level. Fenced with a new `lock_structure_slot`
`pg_advisory_xact_lock` (the `lock_vault_upgrade_slot` precedent) acquired BEFORE
the level read, plus a two-transaction Postgres regression proving it serializes
(RED without lock, GREEN with).

## Goldens (capture_case, byte-stable)

- `mining.build_forge_write` — `!forge` then the 🔥 Build click (funded +
  materials fixture) → `mining_structures` upsert (forge -> 1 level) →
  RETIRES `mining_structures` (the LAST mining exemption).
- `mining.build_forge_insufficient` — `!forge` then the 🔥 Build click with no
  materials → the short-on-materials refusal (mention-prefixed), a pure read (no
  `db_delta` on mining_structures) — the key error-branch pin.

## Parked honest-pending (unchanged from WP-5)

- **respec / title equip** (skills lane) — respec: no command form; title equip:
  select-driven (scope PART C). Both already documented; player_skills retired.
- **cook / use** — the excluded energy lane (no exemption to retire).
- **craft `!build <gear>`** — the oracle `!build`/`!craft` COMMAND routes to
  `mining_workflow.craft` (materials -> mining_inventory product, an
  ALREADY-COVERED table), NOT to build_structure; the mining_structures write is
  panel-button-driven (forge/home 🔥 Build) per the oracle. The argful craft
  command stays a D-0043 pending terminal (its product table is already covered,
  so no exemption rides on it).

## 💡 Session idea

WP-6 is the slice where the SPEC's assumed ingress was wrong and the ORACLE was
right: the scope imagined `!build <structure>` flipping to `build_structure`, but
the oracle `!build`/`!craft` COMMAND routes to `mining_workflow.craft` (a
mining_inventory product), while `build_structure` (the mining_structures write)
is reachable ONLY through the forge/home panel 🔥 Build buttons. Had I flipped
`build_route` argful to `build_structure` per the spec's table, I'd have shipped
a live divergence from the oracle that every gate would pass (the golden would
just pin the fork) — the exact failure mode WP-5's idea warned about, one layer
up: not an invented WORD but an invented ROUTE. The durable discipline is to
confirm the command→service EDGE against the oracle cog before trusting a slice
plan's ingress, not just the copy once you're in the handler. A checker worth
having: flag a ported command whose oracle cog dispatches to a DIFFERENT service
function than the target route's op, so a mis-wired ingress is caught at review
instead of by a play-tester. The capturable-ingress corollary also earned its
keep — the session-minted forge panel button is driven by `component_index` (the
stash_all precedent), so a panel-only write is still golden-coverable without a
command form.

## ⟲ Previous-session review

WP-5 (#335) ported `record_skill` from `skill_service.allocate`, flipped
`skill_route`, minted 2 skill goldens, retired `player_skills` (ratchet mining
`{tables:15→16}`), added `lock_skill_slot` + an over-allocation regression; gate
477. Its landing report (`scratchpad/wp5-landing-report.md`) is the mint
ground-truth — goldens via `sb/adapters/parity/runner.capture_case`, and the
manifest snapshot MUST be recompiled (`tools/manifest_compile.py --write`) when a
new op adds workflow registrations. This session stacks WP-6 on that branch and
follows the same procedure, adding the real PORT work (leg + terminal flips)
ahead of the capture — the LAST content commit retires the final exemption.
