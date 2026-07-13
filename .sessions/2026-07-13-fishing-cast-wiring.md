# 2026-07-13 — fishing cast-leg depth wiring, PR-A (venue/rod/bait/gear/structures/weather → the roll)

> **Status:** `in-progress`

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
