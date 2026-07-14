# 2026-07-14 — fishing: minigame timing rung slice 1 — click-gated resolution (D-0043)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family)

## Scope

Claimed lane (`control/claims/fishing-minigame-timing.md`, PR #459;
branch `claude/fishing-minigame-1`): wire the ported-but-dormant pure
timing math (`sb/domain/fishing/minigame.py`) into the live cast flow
as SLICE 1 — click-gated timing resolution — per the docs/decisions.md
fishing-minigame rung. Concretely:

- **Parity clock-grammar seam**: `Step.advance_s: float | None`
  (parity/harness/cases.py), threaded through the replay driver
  (sb/adapters/parity/runner.py `_drive`) into the harness drive
  methods (sb/adapters/parity/boot.py) so a driven step can advance
  the logical clock by less than the fixed 30.0 s; round-tripped in
  `_describe_step` / `_step_from_input`. Default `None` ⇒ 30.0 ⇒
  zero churn to the existing corpus.
- **Roll at cast time** (`cast_open`, strictly AFTER the existing
  catch roll on the same private cast RNG): bite delay (consuming the
  previously-discarded `effective_bite_speed`), fake-out (stored,
  outcome-inert this slice), reaction window (venue + rod
  `window_bonus`), rod `premature_grace`, trophy → `reel_fight_taps`.
- **Resolve at Reel click** (`fish_route`): premature → one
  `premature_grace` forgive (panel refresh, cast stays parked) else
  the spook terminal (no DB write); in-window non-trophy → the
  existing audited `fishing.cast` commit, unchanged; in-window
  trophy → the reel-fight (per-tap `roll_escape` → escape terminal
  or tap advance → commit on the last tap). Late-window is
  **deliberately NOT enforced** this slice (decide-and-flag — see
  the PR body): the bite is invisible until the slice-2 push-edit
  seam, so late enforcement would be unwinnable-by-design.
- **Goldens**: CAPTURE_WORLD_WEATHER entries FIRST for every new /
  re-minted case; re-mint the three cast-write goldens (their RNG
  trajectory grows the two new cast-time rolls); new curated cases
  for premature spook / premature grace / trophy fight land / trophy
  fight escape via `tools/mint_golden.py`.
- **Units** in tests/unit/band6/ for the resolution branches + a
  `Step.advance_s` round-trip test; ledger docstrings updated to
  slice-1 reality (ops.py / minigame.py / service.py / panels.py).

Untouched by design: control/status.md, control/inbox.md,
control/outbox*, mining domain files, WP parity files; the existing
waiting-panel bytes; the 45 s pending sweep (stays the outer bound).

## Verification

PR #460 (`claude/fishing-minigame-1`). Oracle copy read via GitHub MCP
`get_file_contents` pinned @ bbc524e (cast_view.py + minigame.py) — the
premature-spook 🌀 / grace 😅 / hooked 🎣 / tension-bar 💪 / snapped 💥
strings are oracle-verbatim; flagged in the PR: the oracle's premature
spook carries NO trophy clue (its 🌀 copy never rides `_got_away`), so
neither does the port.

- `python3 -m pytest tests/ -q`: **GREEN** (full suite; the new
  band6 timing file + the advance_s round-trip tests included).
- `python3 bootstrap.py check --strict`: green up to the DESIGNED
  born-red hold on this very card (flipped by this commit) + the 4
  pre-existing claims advisories (never exit-affecting, on main too).
- Local gate (docs/CAPABILITIES.md recipe, Postgres 16 on :5432):
  `gate: GREEN — all 498 golden(s) across 50 ported subsystem(s)
  replay clean`.
- The three existing cast-write goldens needed **NO re-mint**: the two
  new cast-time draws shift the RNG stream but every commit-draw
  OUTCOME at seed 42 coincides — verified by capturing all three and
  byte-diffing against disk (zero diff) before the gate confirmed it.
- Four new goldens minted dry-run-first (`tools/mint_golden.py`,
  corpus 494 → 498), each weather-seeded storm in
  CAPTURE_WORLD_WEATHER BEFORE its mint: cast_premature_spook
  (seed 42), cast_premature_grace (seed 4, Diamond-Rod fixture),
  cast_trophy_fight_land (seed 2, deepwater + level-2 game_xp
  fixture), cast_trophy_fight_escape (seed 15).

## Honest remainder (slice 2)

Late-window enforcement + fake-out visibility need the push-edit seam
(the unprompted BITE!/nibble panel edits); the fake-out is rolled +
stored now so slice 2 shifts no pinned trajectory. The OLD harness
capture path (parity/harness/runner.py `_drive` + world payload
factories) does NOT thread `advance_s` — only the new-bot lane
(sb/adapters/parity) does; the old lane needs disbot and is not used
by the gate. venue.py's module docstring still says "this repo has no
minigame module yet" — pre-existing stale line, out of this slice's
named ledger list.

## 💡 Session idea

The seed hunt for branch-specific goldens (grace forgive, trophy,
escape-at-tap-N) was a hand-rolled sim of the cast_rng draw order
(scratchpad script, ~60 lines). A `tools/hunt_cast_seed.py --branch
grace|trophy-land|trophy-escape` that walks seeds against the REAL
modules and prints the first N hits (with bite time + window bounds
for advance_s) would make every future timing-case mint a two-minute
job — and it doubles as a drift alarm: if a documented seed stops
producing its branch, the RNG trajectory moved.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-fishing-cast-weather-seed.md` — the
weather time-bomb fix this slice leans on.) Its runner-seed-not-bytes
call was exactly right and its 💡 (a mint-time guard failing any
weather-bearing capture without a CAPTURE_WORLD_WEATHER seed) is still
unbuilt — this session honored the doctrine by hand (seeds registered
before every mint), which is precisely the manual step that guard
would retire. One gap worth naming: that session's card recorded the
capture-day reconstruction table but not WHERE the date→condition
mapping is computed, costing this session a short re-derivation grep
(weather.py `weather_for_date`); a guard-recipe line with the function
anchor would have saved it.
