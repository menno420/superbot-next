# 2026-07-12 — deep-mining WRITE-PARITY lane — claim (born-red placeholder)

> **Status:** HOLD (born-red — lane-claim placeholder; NO implementation. Awaits
> the owner checkpoint before any write-golden / handler work begins.)

- **📊 Model:** opus-4.8 · high · scoping (Q-0194)

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
