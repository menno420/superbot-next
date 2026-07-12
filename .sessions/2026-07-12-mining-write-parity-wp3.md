# 2026-07-12 — deep-mining WRITE-PARITY lane — WP-3 depth/world/wear write goldens

> **Status:** in flight (born red — session card + telemetry + claim planted
> first; goldens minted next, card flips complete on the last commit). Stacked
> on WP-2 (#312, branch `mining-write-parity-wp2`). Born-red first-commit CI red
> is expected noise.

- **📊 Model:** opus-4.8 · high · parity/golden-minting (Q-0194)

## WP-3 scope (depth / world / wear + workshop fold-in — pure capture, legs live)

Stacked on WP-2 (#312). At HEAD, WP-2 already RETIRED `table:mining_player_state`
(vault_level rides it) and `table:mining_vault`. The remaining
`depth.exemptions.mining` `guard-only-capture` rows are `mining_gear_wear`,
`player_skills`, `mining_world`, `mining_structures`. WP-3 retires
**`mining_world`** and **`mining_gear_wear`**.

The spec's "gear-wear ADD via a geared mine wear-tick" is UNREACHABLE — the
ported mine leg has NO wear tick (`set_gear_wear` has zero runtime write
ingress). The only write ingress that touches `mining_gear_wear` is
`clear_gear_wear` via `!repair` (the REMOVE face). So WP-3 folds in the WP-4
workshop terminals (`!repair` / `!quickcraft`, spec: "may fold into WP-3") — that
is the only tractable path to retire `mining_gear_wear`, and it delivers the
priority `quick_craft` concurrency regression.

Terminals (5, all legs already ported + wired live in `ops.py` / `service.py`):
- `mining.descend_write` — geared `!descend` (torch equipped, `max_depth`
  pre-seeded so the descent is NOT record-setting → no game-XP tail) →
  `mining_player_state` depth 0→1; `<@u> descended to 🪨 Cavern (depth 1/3).`
- `mining.ascend_write` — `!ascend` (depth 1 seeded) → `mining_player_state`
  depth 1→0; `<@u> climbed up to 🌳 Surface (depth 0/3).`
- `mining.reseed_world_write` — `!mineworld 12345` (admin persona =
  guild-operator) → `mining_world` seed row; `<@u> …`/`🌐 Reseeded this server's
  mining world to **12345**. …` → RETIRES `mining_world`.
- `mining.repair_write` — `!repair pickaxe` (worn wear-row + owned pickaxe +
  funded balance) → economy debit + `clear_gear_wear` (removed delta);
  `<@u> Repaired **pickaxe** to full durability for **7** 🪙. Balance: **493**
  🪙.` → RETIRES `mining_gear_wear` (remove face).
- `mining.quick_craft_write` — `!quickcraft` (last_broken=torch seeded, wood
  materials) → material consume + `mining_inventory` +torch + auto-equip;
  `<@u> Crafted **torch** and equipped it in the **light** slot!`

Reply copy is byte-identical to the oracle (`services/mining_workflow.py`
repair/quick_craft, `mining_cog.py` descend/ascend/mineworld). The
descend/ascend XP/wear tails ride the D-0043 port (never surfaced by the ported
handler, `service.py:29`), so the non-record descend + the surface ascend are
the byte-identical-to-oracle faces.

## Concurrency fold-in (money-reviewer follow-up)

`repair` and `quick_craft` are both advisory-fenced by `lock_workshop_slot`, so
this slice adds TWO dedicated TWO-TRANSACTION Postgres concurrency regressions
mirroring WP-2's `test_mining_vault_upgrade_race.py`:
- **`quick_craft` (priority)** — its double-craft / item-dup race is NOT covered
  by `check_money_race` at all (materials, not coins), so the lock is its ONLY
  guard: two concurrent quickcrafts of one broken item must serialize (one
  crafts, the other sees `last_broken` cleared → refuses) — no item duplication.
  Verified RED without the lock, GREEN with it.
- **`repair`** — two concurrent repairs must serialize (no double coin spend).

## ⟲ Previous-session review

WP-2 (#312) landed 4 vault write goldens green, retired `mining_vault` +
`mining_player_state`, ratchet mining `{events:3→4, tables:9→13}`, gate 466→470,
plus the vault_upgrade advisory-lock concurrency regression. Its landing report
(`scratchpad/wp2-landing-report.md`) is the mint ground-truth: goldens minted via
`sb/adapters/parity/runner.capture_case` (the NEW-bot path), never the oracle
bot. This session stacks WP-3 on that branch and follows the same procedure.
