# 2026-07-13 — deep-mining WRITE-PARITY lane — WP-6 structure-build PORT + write golden (FINAL slice)

> **Status:** IN FLIGHT (born red) — PORT the oracle
> `mining_workflow.build_structure` (coin debit + material consume +
> `mining_structures` level raise in ONE txn) onto the audited
> `mining.build -> record_build` seam, flip the forge/home 🔥 Build panel
> terminals from D-0043 pending to live handlers, mint the structure-build
> write golden(s) byte-identical, and retire the **LAST** mining
> `guard-only-capture` exemption (`mining_structures`). Adds a
> `lock_structure_slot` advisory fence + a two-txn double-build concurrency
> regression. Born red by design; flips complete on the last commit. Stacked on
> WP-5 (#335, branch `mining-write-parity-wp5`).

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
