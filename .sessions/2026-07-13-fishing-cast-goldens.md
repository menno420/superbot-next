# 2026-07-13 — fishing cast-leg reel WRITE goldens, PR-B (retire the fishing_catch_log capture exemption)

> **Status:** `in-progress`

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

- (flips at completion)

## Verification

- (flips at completion)

## Enders

- 💡 (flips at completion)
- ⟲ Previous-session review: (flips at completion)
- 📊 Model: fable-5 (see header line)
