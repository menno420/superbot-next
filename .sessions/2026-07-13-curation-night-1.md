# 2026-07-13 — curation rework night bundle 1: the grid Mine navigator + hub How-to (rows 45 · 59 · 60)

> **Status:** `complete`

- **📊 Model:** `fable-5` · night lane, ORDER 019 item 2 (curation REWORK
  backlog bundle 1) · mandate: curation report rows 45/59/60
  (`docs/review/curation-report-2026-07-13.md` L987 / L1030 / L1033),
  claim `control/claims/curation-rework-night-bundle.md` (PR #426),
  token `claude/curation-night-1`, PR #434.

## Scope

Port the oracle grid Mine navigator (`disbot/views/mining/grid_mine_view.py`
+ `utils/mining/grid.py` + the `mining_workflow.dig` seam @ 9c16365) and the
static mining How-to panel (`disbot/views/mining/how_to_panel.py`) into the
plugin/manifest architecture; retire the hub's two pending terminals.

## What shipped

- **Rows 59 + 60 — DONE.** Hub ⛏️ Mine / 📖 How-to repoint byte-neutrally
  (labels/styles/`custom_id_override` untouched — `sweep_minemenu` replays
  unchanged) to the new `mining.grid` / `mining.howto` PanelSpecs;
  `mining.grid_view_pending` + `mining.how_to_pending` retired (trap 12a —
  no longer register; pinned by test).
- **Row 45 — the SYSTEM is ported and live; the `!mine` prefix byte is
  deliberately NOT flipped** (see the honesty note below).
- `sb/domain/mining/grid.py` — the pure seed-deterministic world, oracle
  verbatim (splitmix64 cell hash, 70/10/18/2 feature weights, richness
  folds, fog-of-war map render, light-widened `reveal_radius`).
- Migration `0056_mining_grid.sql` — `pos_x`/`pos_y` (oracle columns) +
  `discovered` JSONB on `mining_player_state`. **Flagged deviation:** the
  oracle keeps fog of war in a dedicated `mining_discovered` table; a NEW
  declared store table on ported mining reds `check_parity_depth` R2
  without a `parity/parity.yml` depth-exemption row, and parity.yml is the
  wp-stack reconcile lane's file tonight — so the visited-cell set rides a
  single-statement idempotent `discovered || $patch::jsonb` merge on the
  covered player-state store (erasure via `mining.erase_subject_state`
  covers the columns with the row).
- `mining.dig` audited op (`sb/domain/mining/ops.py::_record_dig`) — the
  oracle dig verbatim: energy spend + move (lateral position / light-gated
  depth) + cell-folded loot grant + fog mark + wear ticks + depth-record &
  mine XP in ONE txn. First wear-tick writer in the tree
  (`_wear_candidates`/`_apply_wear_writes`, oracle-verbatim); the
  `rewards.mine_multiplier` equipped-tool curve landed with it (legacy
  callers still pass `multiplier=None` — fastmine bytes untouched).
- `mining.grid` panel — session-lifecycle (120s, invoker-locked), the
  oracle D-pad rows verbatim, renderer override building the shipped
  embed (depth/position/energy/seed fields, map code block + legend,
  note+color re-render via `refresh_session_view`; a refresh miss degrades
  to an honest text reply — the settings access-explorer posture).
- `mining.howto` panel — the `_HOW_TO` copy verbatim + ↩ Mining Hub back
  button; footer literal on a renderer override.
- Sim gate: 3 additive legacy-seed Exempt rows for the grid arrangement in
  `manifest/layout/mining.lock.json` + `--write-baseline` regen (trap 2/31).
- Tests: `tests/unit/mining/test_mining_grid.py` (17 — pure grid, store SQL
  shapes, record_dig leg write-set/refusals) +
  `tests/unit/band6/test_band6_mining_grid_panels.py` (7 — spec pins,
  retirement, compile fences, the pinned `!mine` byte).

## Row 45 honesty note (⚑ decide-and-flag, PL-001)

`goldens/mining/sweep_mine.json` pins the capture-world error artifact on
every `!mine` (trap 11b), and the REQUIRED golden-parity `gate` job replays
ported subsystems green (`run_golden_parity.py --gate`) — flipping
`mine_route` to `open_panel` reds the required gate on every PR. The
sanctioned exit (retire the golden: delete + `_sweep_skips` entry +
`parity.yml source.retired_goldens` + the 2 count-pin tests + a
depth-ratchet decrease that likely needs an owner ruling) runs through
exactly the files the wp-stack reconcile lane owns tonight. So: the
navigator is live behind the hub button; `mine_route` keeps the pinned
literal with the flip site named in its docstring.

**Guard recipe (the follow-up):** flip = `mining.mine_route`
(`sb/domain/mining/service.py`, the `Reply(BLOCKED, _GENERIC_ERROR)` body →
`open_panel(PanelRef("mining.grid"))`), retire
`parity/goldens/mining/sweep_mine.json` via `_sweep_skips` +
`parity.yml source.retired_goldens` 3→4 + count pins in
`tests/unit/parity_adapter/test_replay_adapter.py` /
`tests/unit/parity_gate/test_check_parity_depth.py`; update
`test_band6_mining_grid_panels.py::test_dig_op_registered_and_prefix_mine_still_carries_the_pinned_byte`.

## Adjacencies flagged

- Energy lane slice 3 (queued): `fastmine_route`/`record_mine` — disjoint
  from this bundle's routes; `mining.dig` owns its own energy spend.
- WP-3 (#317, open) folds WP-4 wear goldens: this PR's wear helpers are
  append-only in ops.py; if #317 lands its own, fold onto theirs.
- Fog-of-war table graduation (`mining_discovered` + StoreSpec + erasure +
  depth exemption) — follow-up for whoever holds the parity.yml pen.

## Verification

- `python3 -m pytest tests/ -q` — **2891 passed, 15 skipped** (57s).
- `python3 bootstrap.py check --strict` — clean once this card flips (the
  only red mid-session was the designed born-red hold; the 4 claims
  advisories are pre-existing and never exit-affecting).
- `tools/check_parity_depth.py` OK (49/49 ported, 494 goldens);
  `check_sim_gate` OK; `check_migrations` clean (54);
  `check_symbol_shadowing` / `check_namespace` clean.

## 💡 Session idea

The required golden-parity gate makes every capture-artifact golden (trap
11b class: bytes that pin the CAPTURE ENVIRONMENT's failure, not shipped
behavior) a one-way ratchet against porting the real feature's front door —
sweep_mine is the first case where the artifact literal now sits in front
of a fully live system. Worth an owner-lane ruling that mints a FOURTH
disposition class ("capture-artifact superseded by port": golden retires
without a ratchet decrease penalty, prefix flips same-PR) so future deep
ports don't strand their prefix bytes one lane behind their systems.

## ⟲ Previous-session review

The boot-report recon session (this seat's morning pass) called the ORDER
019 item 2 "~17 rows" stale and re-derived the true residue as 6 rows in 3
bundles — verified here: rows 59/60 were exactly as it mapped
(panels.py:178/:211 pendings), row 45's blocker landscape (sweep_mine pins
+ required-gate replay) was real but UNDER-called — the recon said "flip
mine_route onto the navigator panel" without noticing the required gate
replays mining green, which this session had to resolve by decide-and-flag.
Its oracle clone path and line anchors were all accurate; no residue
collided.
