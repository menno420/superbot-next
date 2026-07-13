# Deep-mining WRITE-PARITY lane claim — `mining-write-parity-lane`

> **✅ LANE COMPLETE (2026-07-13)** — all six planned slices DELIVERED (WP-4
> folded into WP-3 per spec). Every `depth.exemptions.mining`
> `guard-only-capture` row is retired; the mining exemption block is empty of
> tables. The final slice is WP-6 (PR #344, structure build). cook / use stay
> honest D-0043 pendings by design (the excluded energy lane — no exemption to
> retire).

> **CLAIM (2026-07-12T21:33:48Z)** — born-red placeholder, DRAFT PR, NO
> implementation. This lane claims the deep-mining **write-golden parity** work
> (minting the write goldens that drive the mutations the command ladder left as
> `guard-only-capture` exemptions, and retiring those exemptions) so a concurrent
> fleet does not duplicate any slice. Implementation waits on an owner checkpoint.

This lane succeeds the completed COMMAND ladder (`slice1-equip-loadout-character`,
#286→#300). The ladder ported all 26 mining deep-system commands' READ/guard
surface; this lane covers their WRITE surface. Six planned slices, one PR each,
parked green (the ladder cadence). One bullet per slice, parseable by
`check_claims` (backticked token + ISO date). Full scope:
`scratchpad/write-parity-scope.md`.

- `wp1-equip-loadout-writegoldens` · **write-parity WP-1 — equip/unequip/loadout save·apply·delete write goldens [DELIVERED — PR #306]** — minted 5 argful-capture goldens driving `mining.record_equip/unequip/save_loadout/apply_loadout/delete_loadout` (goldens/mining/mining_{equip,unequip,loadout_save,loadout_apply,loadout_delete}_write.json); retired `depth.exemptions.mining` `table:mining_equipment` + `table:mining_loadout_presets`; ratchet mining `{tables:5→9, events:2→3}`; corpus 474→479 · area: parity/cases/, parity/goldens/mining/, parity/parity.yml · 2026-07-12T21:33:48Z
- `wp2-vault-writegoldens` · **write-parity WP-2 — stash/unstash/stash-all/vaultupgrade write goldens [DELIVERED — PR #312]** — minted 4 argful-capture goldens driving `mining.record_stash/unstash/stash_all/vault_upgrade` (goldens/mining/mining_{stash,unstash,stash_all,vault_upgrade}_write.json); retired `depth.exemptions.mining` `table:mining_vault` + `table:mining_player_state`; ratchet mining `{tables:9→13, events:3→4}`; corpus 481→485; added a two-txn vault_upgrade advisory-lock concurrency regression test · area: parity/cases/, parity/goldens/mining/, parity/parity.yml, tests/integration/ · 2026-07-12T21:33:48Z
- `wp3-depth-world-wear-writegoldens` · **write-parity WP-3 — geared descend/ascend/mineworld-reseed + repair/quickcraft write goldens [DELIVERED — PR #317]** — minted 5 argful-capture goldens driving `mining.record_descend/ascend/reseed_world/repair/quick_craft` (goldens/mining/mining_{descend,ascend,reseed_world,repair,quick_craft}_write.json); retired `depth.exemptions.mining` `table:mining_world` + `table:mining_gear_wear` (remove face — the ported mine leg has NO wear tick, so the ADD face is unreachable and the WP-4 workshop repair/quickcraft terminals folded in per spec); ratchet mining `{tables:13→15, events:4}`; corpus 485→490; added two two-txn `lock_workshop_slot` concurrency regressions (quickcraft item-dup priority + repair double-spend, both RED→GREEN observed) · area: parity/cases/, parity/goldens/mining/, parity/parity.yml, tests/integration/ · 2026-07-12T21:33:48Z
- `wp4-workshop-writegoldens` · **write-parity WP-4 — repair/quickcraft write goldens [PLANNED — awaits owner go]** — funded/broken-item fixture goldens driving `mining.record_repair/quick_craft`; close `table:mining_gear_wear` (remove face) + craft-write coverage · area: parity/cases/, parity/goldens/mining/, parity/parity.yml · 2026-07-12T21:33:48Z
- `wp5-skills-titles-writegoldens` · **write-parity WP-5 — skill spend (PORT) write golden [DELIVERED — PR #335]** — ported `record_skill` allocate leg from oracle `skill_service.allocate` (copy verbatim) + flipped `skill_route` (argful `!skill <branch>` was a D-0043 pending terminal); minted 2 goldens driving `mining.skill` (goldens/mining/mining_{skill_write,skill_bad_branch}.json) → retired `depth.exemptions.mining` `table:player_skills`; ratchet mining `{tables:15→16, events:4}`; corpus 490→492; added `lock_skill_slot` advisory fence + a two-txn over-allocation concurrency regression (RED→GREEN observed) plus leg/parse tests; **respec + title equip parked honest-pending** (respec: no command form, panel-button coin-sink ingress rides the deferred skills-panel port; title equip: select-driven per scope PART C) · area: sb/domain/mining/, parity/, parity.yml, tests/ · 2026-07-12T21:33:48Z
- `wp6-structures-craft-writegoldens` · **write-parity WP-6 — structure build (forge/home) PORT write golden [DELIVERED — PR #344]** — ported the oracle `mining_workflow.build_structure` (coin debit + material consume + `mining_structures` level raise in ONE txn) onto the audited `mining.build -> record_build` seam (copy verbatim) + flipped the forge/home 🔥 Build panel terminals from D-0043 pending to live `forge_build_route` / `home_build_route` handlers; minted 2 goldens driving `mining.build` (goldens/mining/mining_build_forge_{write,insufficient}.json) via the `!forge` -> 🔥 Build click → retired `depth.exemptions.mining` `table:mining_structures` (the LAST mining exemption); ratchet mining `{tables:16→17, events:4}`; corpus 492→494; added `lock_structure_slot` advisory fence + a two-txn double-build concurrency regression (RED→GREEN observed) plus leg/copy unit tests. The FINAL slice — **the whole write-parity lane is COMPLETE** (all 8 planned mining exemptions retired). (craft `!build <gear>` stays a D-0043 pending terminal: the oracle command routes to `mining_workflow.craft`, whose product table `mining_inventory` is already covered.) · area: sb/domain/mining/, parity/, parity.yml, tests/ · 2026-07-13T00:00:00Z

**EXCLUDED — cook / use.** The `!cook` / `!use` argful writes depend on the
un-ported mining energy/consumable system (a **separate lane**) and stay honest
D-0043 pending terminals; they register no covered store, so there is NO exemption
to retire. This lane does NOT touch them.

**Exemptions retired by lane end (8 `guard-only-capture` rows):**
`mining_player_state`, `mining_equipment`, `mining_gear_wear`,
`mining_loadout_presets`, `player_skills`, `mining_world`, `mining_vault`,
`mining_structures`.
