# 2026-07-13 — fishing cast-leg reel WRITE goldens, PR-B (retire the fishing_catch_log capture exemption)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · parity capture/mint

## Scope

PR-B of the cast-leg depth lane (lane claim
`control/claims/fishing-cast-depth.md`; PR-A #373 merged — the reel
path is live with identity-token-validated pending casts): mint the
FIRST row-bearing `fishing_catch_log` goldens via the canonical
capture path ONLY (`GoldenCase` entries in `parity/cases/curated.py`
captured through `sb/adapters/parity/runner.capture_case`; never
hand-edited, #193):

1. `fishing.cast_reel_write` — fresh player, shore profile: `!fish` →
   Reel click → catch committed (fishing_catch_log + fish grant +
   game XP + the spent energy row in db_delta).
2. `fishing.cast_deepwater_reel_write` — fixture seeds
   `fishing_venue='deepwater'` + a rod tier + bait + structure rows,
   exercising the compound pull/bite/double-catch knobs and the coral
   0.06 deepwater-only branch (pinned either way the seeded draw
   lands).
3. `fishing.cast_bait_spend_write` — fixture seeds a loaded bait with
   exactly 1 charge: the cast spends it and the clear-at-0
   (`fishing_bait` → `('', 0)`) lands in db_delta.

Then retire the `depth.exemptions.fishing` `table:fishing_catch_log`
row (its own text names this exact button-driving capture) and bump
the golden/ratchet count pins (`check_parity_depth.py
--write-ratchet` + the test count pins).

## Shipped

- 3 curated `GoldenCase`s (`parity/cases/curated.py`, the WP-1
  precedent shape) + their captured goldens
  `parity/goldens/fishing/fishing_cast_{reel,deepwater_reel,
  bait_spend}_write.json` — each `!fish` → Reel click by
  `component_index 0` (the identity token rides the panel-args
  binding). Determinism: re-captured twice across fresh harness
  boots; replay-visible bytes identical ×3 (the only raw variance is
  audit_log/event_outbox row ORDER — the uuid-keyed snapshot sort,
  the ruled kernel-surface-drift class dropped symmetrically at
  replay diff; the WP-1 goldens carry the same shape).
- `parity/parity.yml`: retired `table:fishing_catch_log` (its own
  text named this capture) + `table:fishing_bait` (first row-bearing
  delta wins — the WP-2 `mining_player_state` precedent);
  `fishing_rod` stays exempt (still no row-bearing delta).
  `minted_goldens` 22 → 25; ratchet fishing
  `{events 1→3, tables 4→10}` via `--write-ratchet`.
- Count pins 484 → 487 (`tests/unit/parity_adapter/
  test_replay_adapter.py`, `tests/unit/parity_gate/
  test_check_parity_depth.py`).

## Verification

- `run_golden_parity.py --gate`: **GREEN — all 487 goldens across 50
  ported subsystems replay clean** (the 484 pre-existing untouched);
  targeted `replay_case` on the 3 new goldens: 0 diffs each
- `pytest tests/` 2475 passed, 2 skipped · `pytest
  tests/integration` 11 passed
- check_parity_depth (487 goldens) · check_migrations (51) ·
  manifest_compile · check_compat_frozen · check_namespace ·
  check_money_race · check_sim_gate · check_symbol_shadowing ·
  check_no_skip: all clean

## Enders

- 💡 Session idea: dbsnap's row sort keys the RAW `dedup_key`
  (`audit:{guild}:{uuid}`) — any case with ≥2 same-event outbox rows
  orders them 50/50 per capture. Harmless today (the
  kernel-surface-drift disposition drops both tables at replay
  diff), but a normalize-before-sort pass in `dbsnap.snapshot` would
  make raw captures byte-stable too — worth a follow-up if kernel
  rows ever leave the disposition.
- ⟲ Previous-session review: the PR-A session
  (2026-07-13-fishing-cast-wiring) left the runner RNG arming +
  registry reset exactly where its report said, and the
  token-through-panel-args binding worked first try under the
  capture harness — the review-round hardening cost this session
  zero rework. Improvement: its report could have named the
  event-outbox uuid-sort raw variance (WP-1's goldens already
  carried it); this session spent a debug loop rediscovering it.
- 📊 Model: fable-5 (see header line)
