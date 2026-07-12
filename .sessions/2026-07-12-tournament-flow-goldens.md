# 2026-07-12 — Multi-step TOURNAMENT-flow goldens (rps + blackjack parity depth)

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · parity golden-minting (multi-step interaction coverage)

## Scope

One bounded slice: mint the MISSING multi-step interaction goldens for the
full tournament flows the audit found thin on golden coverage. The existing
`rps_tournament` / `blackjack` goldens are single-step SWEEPS (one command,
one refusal) — none drive the end-to-end orchestration wire (register →
play → settle/payout) or the cross-game guard. Minted via the D-0073
procedure (`sb/adapters/parity/runner.capture_case`, kernel-spine stripped
at diff time by `apply_dispositions`), captured in the full-corpus replay
trajectory so leaked in-memory tournament state matches the gate exactly.

## Delivered

- `parity/goldens/blackjack/blackjack_tournament_full_flow.json` — the
  flagship full-tournament wire, a curated 7-step click flow:
  `!bjtournament 0 1` (open a free single-round tournament) → 🃏 Join button
  sign-up → a SECOND Join click by the same player (the
  `You're already registered!` duplicate refusal, verbatim) → a second
  player Joins → `!bjstart` (per-entrant fee/launch + round table views) →
  each entrant Stands their round → all-done settle → champion payout
  (`blackjack.tournament_payout`, the `FREE_TOURNAMENT_REWARD` leg) +
  🏆 results embed. Self-cleaning: `end_tournament` + `clear_active` leave no
  in-memory or DB state, so the case never pollutes a later golden.
- `parity/goldens/rps_tournament/rps_tournament_foreign_active_refusal.json`
  — the #277 cross-game guard regression lock: with the shared
  `active_tournament` `guild_settings` flag seeded to `blackjack` (via the
  case's `fixture_sql`, so no in-memory contamination), `!rpsregister`
  refuses to open with the oracle copy verbatim
  (`A **blackjack** tournament is already active in this server.`). Pins the
  guard that the stranded-pot money-bug fix restored.
- `parity/cases/curated.py` — the two typed curated cases (click steps carry
  `component_index`; the golden normalizes the session custom_ids away).
- `parity/parity.yml` — `source.minted_goldens` 6 → 8 (import pin stays
  465; on-disk corpus 468 → 470).
- `tests/unit/parity_adapter/test_replay_adapter.py` +
  `tests/unit/parity_gate/test_check_parity_depth.py` — the corpus count
  pins (468 → 470, `minted_goldens` 6 → 8).

## Deliberately NOT minted (harness determinism limits, ledgered)

- A full RPS bracket-to-champion flow is INFEASIBLE deterministically: the
  registration window is a 600 s `time.monotonic()` gate (`REGISTRATION_
  WINDOW_S`) that the harness never advances, so `!rpsstart` is permanently
  blocked (`Cannot start the tournament while registration is still
  active.`) and the bracket never activates — no match views, no moves, no
  champion. Blackjack has no such gate (`!bjstart` launches immediately),
  which is why the full wire lands on the blackjack side.
- An RPS Join-button registration/duplicate golden is INFEASIBLE without
  breaking the existing rps sweeps: rps registration leaves in-memory
  `_TOURNAMENTS` state that no user command can clear (the only clear paths
  are champion payout — unreachable — or the elapsed-window abort), so a
  curated rps click-flow would leak `registration_active=True` into the
  later path-sorted `sweep_rpsregister` / `sweep_rpsstart` captures and red
  them. The blackjack full flow captures the same
  `You're already registered!` copy on the self-cleaning path instead.

## Evidence

- `python3 tools/run_golden_parity.py --gate` — GREEN, 429/429 goldens
  across 51 ported subsystems replay clean (the +2 new goldens replay
  record-then-green in the full-corpus trajectory).
- `python3 tools/check_parity_depth.py` — OK, 470 goldens, no ratchet
  movement (both goldens touch already-covered tables/events).
- `python3 -m pytest tests/unit/parity_adapter tests/unit/parity_gate` —
  green with the new count pins.
- `python3 bootstrap.py check --strict` — all checks passed.
- Both goldens double-captured across two independent harness boots and
  byte-identical before commit (the D-0073 mint discipline).

## 💡 Session idea

The parity harness's in-memory-state leak across path-sorted cases is an
invisible coupling: a new curated case can silently RED an existing sweep
three subsystems away by leaving a game's `_TOURNAMENTS` dict populated.
Worth a checker — mint any curated case that opens a stateful game session
and assert the case reaches a state-clearing terminal (`end_tournament` /
`clear_active`) OR seeds its precondition via `fixture_sql` instead of a
live open. Both new goldens here obey that rule by construction; nothing
enforces it yet.

## ⟲ Previous-session review

This slice came out of the tournament golden-coverage audit, not a prior
work order — no ledger row to grade. What the audit under-served: it named
"full tournament flow (register → matches → settlement)" as thin without
noting that HALF of it is unreachable through the golden harness (the RPS
600 s window blocks every bracket start; the click-registration state leak
blocks every rps sign-up golden). The blackjack side carries the whole
wire because `!bjstart` has no time gate and `_finish_tournament` self-
cleans — an asymmetry the audit would have surfaced up front had it graded
each flow against the harness's determinism model (no wall-clock advance,
per-case-persistent in-memory game state) before scoping the coverage.
