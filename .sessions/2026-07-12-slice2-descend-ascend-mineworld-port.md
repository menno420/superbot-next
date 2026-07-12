# 2026-07-12 — slice 2 port: descend / ascend / mineworld (depth bands + world grid → EffectiveStats)

> **Status:** `complete`

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

## Verification (local, real Postgres, pristine DB)

- **golden-parity GATE GREEN — all 435 golden(s) across 51 ported
  subsystem(s) replay clean** (was 432; the +3 re-home takes it to 435,
  mining 17 → 20, `_unmapped` 36 → 33), incl. sweep_descend / sweep_ascend
  / sweep_mineworld. Each verified byte-identical against the REAL handlers
  by a targeted `replay_case` pass BEFORE the `git mv` (all three GREEN),
  then again in the full gate after.
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported**
  (the new `table:mining_world` declared surface held by a
  `guard-only-capture` exemption; the `mining_player_state` exemption prose
  refreshed for the now-live re-homed sweeps; R3 ratchet unchanged —
  re-home added no new covered surface).
- **check_migrations: clean (43)** — `0043_mining_world.sql` appended to
  `checksums.json`. **manifest_compile: green** (snapshot recompiled).
- **pytest: 1759 passed, 5 skipped** on a pristine DB (1754 in the full
  serial run + the 5 money-race/btd6-seed integration tests that pass in
  isolation — the slice-1-documented DB-pollution false-reds when run after
  1700+ tests share one DB; CI's `tests` job runs them GREEN in its own
  fresh container). `tests/unit/invariants/test_composition_parity.py`: 3
  passed (the three now-live `*_pending` refs pruned from the burn-down).
- `bootstrap.py check --strict`: **exit 0** (the only red was the
  by-design born-red HOLD while this card declared `in-progress`; nothing
  else).

### CI on head `0a1336b` — ALL REQUIRED GREEN
golden-parity **success**, gate **success**, tests / code-quality /
manifest-validate / architecture / sim-gate / check_compat_frozen /
checkers / pip-audit / lockfile-fresh **success**; `report` **failure =
red-by-design** (never a required check).

### 3 re-homed goldens (git mv `_unmapped → mining`, subsystem flip only)
sweep_descend, sweep_ascend, sweep_mineworld — rename similarity R098 (only
the `"subsystem"` line changed; asserted bytes untouched — #193 law).

## 💡 Session idea

The two write lanes this slice's exemptions hold open — the GEARED
`!descend` (needs an equipped light so `depth_access ≥ 1`, then writes
`mining_player_state.depth`/`max_depth` + the one-time `depth_record` game
XP) and the owner `!mineworld <seed>` reseed (writes `mining_world`) — are
now CORPUS-EXPRESSIBLE against LIVE handlers. They join the four slice-1
`guard-only-capture` holds (argful equip / loadout save / wear tick / skill
spend) as a single natural "argful mining capture" follow-up: seed a
persona with a lantern + manage_guild, drive one geared descent and one
reseed, mint two row-bearing goldens, and DELETE both new exemptions
(the D-0069 class's own exit: "a future argful/geared capture deletes it").
Sequence it after slice 3–5 land the remaining depth commands so a single
capture run covers every held write at once rather than one PR per table.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-slice1-equip-loadout-character-port.md`, the
slice-1 equipment/loadout/character port.) Its headline — PUSHED + PR GREEN
via a recovered local clone — carried the durability lesson this slice took
to heart: PUSH EARLY AND OFTEN. Slice 1 nearly lost a full seat's work when
a worker hit its tool-call cap before pushing; this slice pushed the
born-red card immediately and re-pushed after every logical commit (4
pushes total), so the branch was durable from minute one. Its substrate
map was exactly right and saved hours: the `mining_player_state` exemption
it pre-wrote ALREADY named descend/ascend with the light-gated refusal
byte, so this slice's depth work was a documented, expected deepening of
the same row, not a discovery. One thing its 💡 idea under-scoped: it
framed the follow-up "argful capture" as covering only its own four
slice-1 holds — but each subsequent slice adds MORE guard-only holds
(this slice added `mining_world`), so the right sequencing is one capture
run AFTER the ladder completes, not a per-slice cleanup. The correction:
treat the `guard-only-capture` exemptions as a growing ledger the whole
ladder shares, drained once at the end, not per-rung.
