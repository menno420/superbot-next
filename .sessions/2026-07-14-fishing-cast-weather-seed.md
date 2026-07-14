# 2026-07-14 — parity: seed capture-world weather for 4 fishing cast goldens (stop daily gate flap)

> **Status:** `in-progress`

- **📊 Model:** Opus · high · cross-lane parity hygiene (Q-0194)

## Scope

Coordinator-authorized cross-lane hygiene fix (the fishing lane is
closed for the night). Fishing PR #387 minted four write goldens
WITHOUT a capture-world weather seed:

- `fishing.cast_reel_write`
- `fishing.cast_deepwater_reel_write`
- `fishing.cast_bait_spend_write`
- `fishing.howtofish_rules_card`

Their curated cases carry no `CAPTURE_WORLD_WEATHER` entry, so at
replay the shipped `current_weather()` falls through to the LIVE wall
clock (`datetime.now()`) instead of the frozen case clock. The goldens
were captured 2026-07-13 — a ⛈️ Storm day under the reconstructed
weather table — and their asserted bytes pin that Storm face. They
only replay green on days whose real UTC date still picks Storm: green
2026-07-13, RED 2026-07-14 when the live date picks 🌧️ Rain. A
wall-clock time-bomb sitting on **main**, so main + every open PR go
red on the required `gate` / `golden-parity` job daily until seeded at
the source (failing run from PR #335: 29295488760).

Fix (identical to the one proven on PR #335, branch
`mining-write-parity-wp5`, head `3220d17`): pin the capture-day Storm
condition into `CAPTURE_WORLD_WEATHER` for the four case ids — the same
trap-20 reconstruction the `sweep.fish` / `sweep.fishing` /
`sweep.forecast` rows already use for Rain. Runner-file-only
(`sb/adapters/parity/runner.py`); **zero golden bytes edited**; re-minting
would only reset the time-bomb.

## Verification

Branched `fix/fishing-cast-weather-seed` off `origin/main` @ `abe80c0`.

- `python tools/run_golden_parity.py --gate`: **GREEN — all 494
  golden(s) across 50 ported subsystem(s) replay clean** (exit 0). The
  four cast/howtofish goldens replay byte-identical to their 07-13
  Storm face again, date-independently.
- `python tools/check_parity_depth.py`: **OK — 49 subsystems (49
  ported), kernel ported, 494 goldens** (exit 0).
- `python bootstrap.py check --strict`: **all checks passed** (exit 0;
  the 4 claims advisories are pre-existing on main and never
  exit-affecting) — measured with only the runner seed applied, before
  this born-red card was added.
- No golden JSON edited; `control/status.md` + `control/inbox.md`
  untouched.

## 💡 Session idea

The real defect is that `current_weather()` reads the live clock at
replay at all — every future weather-bearing golden minted without a
`CAPTURE_WORLD_WEATHER` seed is a fresh time-bomb. A mint-time guard
(fail the capture if a case renders a weather face but registers no
seed) would move this class from "found red daily on main" to "caught
at mint", retiring the reconstruction-by-hand pattern these four rows
and the three sweep rows all lean on.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-fishing-cast-goldens.md`, PR #387 — the
session that minted these four goldens.) Its capture-only discipline
(canonical `capture_case`, never hand-edited) was correct and is why
the fix belongs in the runner seed, not the golden bytes. The gap: the
capture ran on a Storm day and nothing pinned that world state, so the
goldens shipped depending on the wall clock — invisible until the date
rolled. This card closes that gap at the source on main; the 💡 above
proposes the mint-time guard that would have caught it in #387.
