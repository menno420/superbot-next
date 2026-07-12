# 2026-07-12 — slice 2 port: descend / ascend / mineworld (depth bands + world grid → EffectiveStats)

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 2 — the depth-traversal + shared-world-seed
stack. Three shipped commands move from honest D-0043 pending terminals to real
handlers, stacked on slice 1 (PR #286):
`!descend` · `!ascend` · `!mineworld`.

Planned delivery:

- **Domain** (`sb/domain/mining/world.py`): extend the shipped display module
  with the descent-gating half — `max_accessible_depth`, `can_descend`,
  `can_ascend`, `descend`, `ascend`, `descend_hint`, `biome_for_depth` — ported
  VERBATIM from the oracle (`disbot/utils/mining/world.py`). Depth access is
  gated by the equipped `depth_access` stat (all-zero on a fresh gearless
  player, so `!descend` refuses at Surface).
- **Stores + migration**: `mining_world` (per-guild world seed; a guild with no
  row defaults to `seed = guild_id`) as a `DataClass.NONE` registered store;
  `mining_player_state.max_depth` column for the descent record. Migration
  `0043_mining_world.sql` (+ checksums).
- **Audited write ops** (`ops.py`): descend / ascend depth moves and the admin
  `mineworld <seed>` reseed as one-leg one-txn ops (the core-loop precedent).
- **Handlers** (`service.py` `_register()`): the descend refusal / ascend
  Surface guard / mineworld read bytes; the 3 keys removed from `PENDING`.
- **A-16 depth floor**: a `depth.exemptions.mining` `guard-only-capture` row for
  `table:mining_world`; the existing `mining_player_state` exemption prose
  updated to the re-homed golden paths.
- **Golden re-home** (#193 law): the 3 `_unmapped` sweeps
  (sweep_descend/ascend/mineworld) re-homed into the gated `mining` row
  (gate 432 → 435) by `git mv` + the one sanctioned `subsystem` flip.

## Verification

(pending — this card flips to `complete` on the final landing commit)
