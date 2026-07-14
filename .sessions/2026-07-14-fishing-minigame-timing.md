# 2026-07-14 — fishing: minigame timing rung slice 1 — click-gated resolution (D-0043)

> **Status:** `in-progress`

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
