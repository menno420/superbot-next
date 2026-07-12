# Deep-mining ladder claim — lane `slice1-equip-loadout-character`

This lane claims the WHOLE deep-mining port ladder (all six planned slices)
so parallel sessions don't duplicate any rung. Slice 1 is in flight as this
branch's PR; slices 2–6 are claimed-ahead by the same lane. One bullet per
slice, each parseable by `check_claims` (backticked token + ISO date).

- `slice1-equip-loadout-character` · **deep-mining slice 1 — equipment/gear/loadout/character [IN FLIGHT — this PR]** — equip/unequip/gear/loadout/character → real handlers + EffectiveStats/skills/wear/loadout stores + migrations 0039-0042; re-home 5 `_unmapped` sweeps into gated `mining` · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12 16:16:28Z
- `slice2-descend-ascend-mineworld` · **deep-mining slice 2 — descend/ascend/mineworld [IN FLIGHT — this branch, stacked on #286]** — depth traversal (descent gating off equipped depth_access) + mineworld world-seed state → real handlers + mining_world store + migration 0043; re-home 3 `_unmapped` sweeps into gated `mining` · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12T16:48:03Z
- `slice3-vault-stash` · **deep-mining slice 3 — vault/stash/unstash/vaultupgrade/mineinv [IN FLIGHT — this branch, stacked on #289]** — vault safe-stash + capacity coin-sink: stash/unstash/vaultupgrade/stash-all ops + mining_vault store + vault_level column + the session mining.vault PanelSpec; migrations 0044-0045; re-home 4 `_unmapped` sweeps into gated `mining` (mineinv already re-homed #250) · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12T17:37:07Z
- `slice4-forge-repair-craft` · **deep-mining slice 4 — forge/repair/quickcraft/cook/use [IN FLIGHT — this branch, stacked on #292]** — workshop/campfire/consumable crafting: repair/craft/quickcraft/cook/use ops + forge build + mining_structures store + last_broken_item column + the session mining.forge PanelSpec; migrations 0046-0047; re-home 5 `_unmapped` sweeps into gated `mining` · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12T18:21:38Z
- `deep-mining-slice5-skills-titles` · **deep-mining slice 5 — skills/skill/titles** — skill trees + title awards · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12 16:16:28Z
- `deep-mining-slice6-build-workshop-home` · **deep-mining slice 6 — build/buildlist/buildable/workshop/home** — base building + workshop/home · area: sb/domain/mining/, sb/manifest/mining.py, migrations/, parity/ · 2026-07-12 16:16:28Z
