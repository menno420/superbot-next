# 2026-07-13 — fishing cast-leg depth wiring, PR-A (venue/rod/bait/gear/structures/weather → the roll)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · feature build/port

## Scope

PR-A of the cast-leg depth wiring (lane claim
`control/claims/fishing-cast-depth.md`, merged via #367; oracle
superbot @ cdb26804): wire the live persisted fishing state into the
cast LEG — the oracle `begin_cast` compound
(`effective_pull = rod × bait × weather × gear × tide_pool`, dock
bite-speed compound, fishery `double_catch_chance = 0.10 + 0.05·lvl`,
boathouse regen interval), roll at cast time, energy spent post-roll,
per-cast bait charge spend with clear-at-0, a pending-cast in-memory
registry mirroring the oracle `active_casts` guard, and
`_record_cast` → `commit_catch` verbatim (bonus → pearl → coral draw
order, coral 0.06 deepwater-only, oracle result copy). New pure
`sb/domain/fishing/minigame.py` + the gear-multiplier half of
`fishing/gear.py` + oracle `energy.regen_seconds_for` (renaming the
mis-named port `regen_seconds_for` → `seconds_until`, `spend`
updated_at drift fix). Runner arms the private fishing `_rng` per
case; `reset_case_state` clears the pending-cast registry.

PARKED (scope-doc only, D-0043 minigame rung): live bite/fake-out/
reel-fight timing, escape/grace/window knobs, `_FishingDoneView`.

NO golden minting here — PR-B carries the cast-write goldens +
parity.yml/curated.py changes; this PR touches neither. Byte-safety
invariant: every existing golden (esp. sweep_fish) replays
byte-identical — fresh-DB reads default to the exact-neutral knobs.

## Shipped

- `sb/domain/fishing/minigame.py` (NEW, pure — only `is_trophy`
  consumed this slice; timing consumers ported-but-parked),
  `gear.py` multiplier half, `energy.py` (`regen_seconds_for` boathouse
  hook + `seconds_until` rename + `spend` updated_at fix), `ops.py`
  (`commit_catch`-verbatim leg + reward-roll helpers + RNG-posture
  header), `service.py` (`begin_cast`-verbatim `cast_open` + pending
  registry + `fish_route` pop), `panels.py` (`_render_cast` venue
  where-line + bait/gear/tide-pool/dock footer notes),
  `sb/adapters/parity/runner.py` (per-case `_rng` arming),
  `boot.py` (registry reset), 16 new unit tests.

## Verification

- `pytest tests/` 2397 passed, 2 skipped · `pytest tests/integration`
  11 passed
- `run_golden_parity.py --gate`: **GREEN — all 484 goldens across 51
  ported subsystems replay clean**; targeted per-case replay of all 20
  fishing goldens (incl. advisory `sweep.fish`): 0 diffs each
- check_parity_depth · check_migrations (51) · manifest_compile ·
  check_compat_frozen · check_namespace · check_money_race ·
  check_sim_gate · check_symbol_shadowing · check_no_skip: all clean

## Enders

- 💡 Session idea: the pending-cast registry now models the oracle's
  45 s view window without a timer — when the D-0043 timing rung
  lands, a `check_settle_once`-style unit guard should assert the
  registry window constant stays equal to the ported
  `_VIEW_TIMEOUT` so the two can't drift apart silently.
- ⟲ Previous-session review: the slice-4 locations session
  (2026-07-13-fishing-slice4-locations) left razor-sharp DEVIATION
  headers naming exactly which knobs were parked and where they'd
  wire — this session consumed them as a checklist and they were
  accurate to the line. Improvement: it could have pre-noted the
  energy `spend`/`seconds_until` naming drift it rode past; the
  survey pass had to rediscover it from the oracle diff.
- 📊 Model: fable-5 (see header line)
