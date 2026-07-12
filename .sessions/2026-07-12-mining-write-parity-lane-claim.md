# 2026-07-12 — deep-mining WRITE-PARITY lane — claim + WP-1 delivery

> **Status:** complete (WP-1 DELIVERED — the born-red claim PR #306 is now the
> WP-1 slice PR: 5 equip/unequip/loadout write goldens minted, the two mining
> exemptions retired, gate + all checkers green. WP-2..6 stay PLANNED.)

## WP-1 delivery (equip / unequip / loadout save·apply·delete)

Pure capture — the write legs are already live (`sb/domain/mining/ops.py`
`record_equip/unequip/save_loadout/apply_loadout/delete_loadout`, routed argful
in `service.py`). Minted 5 row-bearing curated goldens via the sanctioned
`sb/adapters/parity/runner.capture_case` procedure (the D-0073/D-0079 mint path —
`parity/run.py` boots the OLD oracle bot and does not run in this repo):

- `mining.equip_write` — `!equip iron pickaxe` (inventory-seeded) → +mining_equipment
  tool-slot row; `<@u> equipped **Iron Pickaxe** in the **tool** slot.`
- `mining.unequip_write` — `!unequip tool` (equip-seeded) → −mining_equipment row;
  `<@u> cleared the **tool** slot.`
- `mining.loadout_save_write` — `!loadout save mining` (equip-seeded) →
  +mining_loadout_presets row; `<@u> saved your current gear as the **mining**
  loadout (1 slot).`
- `mining.loadout_apply_write` — `!loadout apply combat` (preset+inventory-seeded)
  → +mining_equipment weapon-slot row; `<@u> equipped the **combat** loadout
  (1 slot).`
- `mining.loadout_delete_write` — `!loadout delete combat` (preset-seeded) →
  −mining_loadout_presets row; `<@u> deleted the **combat** loadout.`

Reply copy is byte-identical to the oracle (`services/mining_workflow.py`
equip/unequip/loadout). Retired `depth.exemptions.mining` `table:mining_equipment`
+ `table:mining_loadout_presets`; ratchet mining tables 5 → 7. Corpus 474 → 479
(minted 12 → 17). No product-code change (parity/ + parity.yml + count pins only).

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

Claim + scope the **deep-mining WRITE-PARITY lane**. The command ladder (slices
1–6, #286→#300) shipped all 26 mining deep-system commands; their READ/guard
surface is golden-covered but every write-store carries a
`depth.exemptions.mining` `guard-only-capture` row because no golden DRIVES the
mutation. This lane mints write goldens that drive those mutations (via the
sanctioned `parity/run.py capture` harness — `capture_case` snapshots the DB
before/after and records the row-level `db_delta`), makes the live handlers their
own frozen contract, and RETIRES the exemptions (delete the row +
`check_parity_depth.py --write-ratchet` bump).

**This commit plants the lane flag ONLY** — a born-red card + telemetry row + a
`control/claims/` claim. It carries NO write goldens and NO handler/leg changes;
those wait on an owner go. Full scoping in
`scratchpad/write-parity-scope.md` (PART A capture machinery, PART B write-terminal
enumeration mapped to oracle, PART C slice plan + tractability).

### Planned slices (own PR each, park green; ~4–6 terminals per slice)
1. **WP-1 equip/loadout** [mint] — equip · unequip · loadout save/apply/delete →
   retire `mining_equipment`, `mining_loadout_presets`.
2. **WP-2 vault** [mint] — stash · unstash · stash-all · vaultupgrade (funded
   fixtures) → retire `mining_vault` (+ `mining_player_state.vault_level`).
3. **WP-3 depth/world/wear** [mint] — geared descend · ascend · mineworld reseed ·
   gear-wear add → retire `mining_player_state` (depth), `mining_world`,
   `mining_gear_wear` (add face).
4. **WP-4 workshop** [mint] — repair (funded) · quickcraft (broken-item fixture) →
   close `mining_gear_wear` (remove face) + craft writes.
5. **WP-5 skills/titles** [port+mint] — port `record_skill` allocate/respec + flip
   `skill_route`; skill spend · respec → retire `player_skills`. **title equip
   flagged park-honest-pending** (select-driven ingress — see risk below).
6. **WP-6 structures/craft** [port+mint] — port `build_structure` leg + flip
   `build_route` argful; build (forge/home/campfire) · craft `!craft <gear>` →
   retire `mining_structures`.

Groups WP-1..4 are pure capture (parity/ + parity.yml + ratchet only). WP-5/6
carry real port work and are the terminals the owner checkpoint most directly
gates.

### EXCLUDED — cook / use
`!cook` and `!use` argful writes ride the un-ported mining energy/consumable
system (a **separate lane**). They stay honest D-0043 pending terminals; they
register no covered store, so there is NO exemption to retire. Left untouched.

## Tractability

**YES — deterministic mint + replay.** Every deep-mining write leg is a pure
state delta (no RNG, no wall-clock). The only `random.Random` in the mining domain
(`rewards.py`) drives the already-covered mine/explore read-loop, reachable by
`random.seed(case.seed)`. Serial ids stabilized by `RESTART IDENTITY`; audit/ledger
timestamps+ids normalize.

## 💡 Session idea

The whole ladder was a "render/guard shell over a deferred write core" — 8
`guard-only-capture` exemptions are IOUs that a single sanctioned capture pass can
call in. The elegant move: capture is the ONLY sanctioned mint path, and the
handlers being captured ARE the reference, so the mint reproduces by construction
for the live-but-uncovered terminals (WP-1..4). The lane's real cost is the two
port slices (WP-5 skills, WP-6 structures) where a write LEG must be ported from
the oracle first — which is why this stays born-red HOLD until an owner checkpoint,
rather than auto-proceeding.

## ⟲ Previous-session review

The slice-6 landing card (2026-07-12) closed the command ladder and named the
honest-pending write-terminal roster this lane covers; slices 1–6 landing reports
(scratchpad) documented the exemptions/fences/migrations already in place. This
session re-derived the capture machinery (`parity/harness/`), confirmed the write
legs are already implemented + deterministic (`sb/domain/mining/ops.py`), and
verified the two Group-2 gaps (skill/build routes still D-0043) against the oracle
(`skill_service.allocate`, `mining_workflow.build_structure`). No prior session
error to correct; this is a fresh scoping lane.
