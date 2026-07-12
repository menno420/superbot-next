# 2026-07-12 — casino poker betting state machine (headless engine port)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · feature build (poker engine port, slice 1)

## Scope

Port the oracle Texas Hold'em **betting state machine** onto the aboard
casino card model + hand evaluator. The pure deck (`sb/domain/casino/cards.py`)
and the brute-force `C(n,5)` evaluator (`sb/domain/casino/evaluate.py`) are
already aboard (D-0045); the missing piece is `disbot/utils/poker/engine.py`
(~525 LOC) — blinds, action legality, betting-round advancement, all-ins, and
**side pots** — the `PokerGame` state machine the D-0045 note named as the
live-adapter successor's headless core.

This slice is **engine-only**. The play/table layer (dealing + per-player
auto-updating ephemeral hands) stays a blocked terminal in
`sb/domain/casino/service.py::casino.poker_start` per the D-0045 live-adapter
gate — untouched here.

## What shipped

1. **sb/domain/casino/engine.py** — the oracle `PokerGame` ported VERBATIM
   (byte-for-byte betting/pot behavior). Only the two import lines changed:
   `utils.cards` → `sb.domain.casino.cards` and `utils.poker.evaluate` →
   `sb.domain.casino.evaluate` (the aboard modules expose the same
   `Card`/`make_deck` and `HandRank`/`best_hand` names — zero API rename).
   Added one non-behavioral method: `snapshot()` / `to_state()` — a clean,
   JSON-serializable table-state dict (the "clean table-state shape"
   downstream goldens/table-flow consume). It reads state only; it changes no
   betting semantics.
2. **tests/unit/band6/test_band6_poker_engine.py** — full unit coverage of the
   betting machine (blind posting incl. the heads-up button rule, every
   action's legality + effect, min-raise rules, round advancement,
   multi-all-in side-pot construction, showdown distribution incl. odd-chip
   handling, end-to-end hands, and the snapshot serializability).

## Ladder

- units **1758 passed / 8 skipped** (`python3 -m pytest tests/ -q`), +31
  over the pre-branch baseline (the new poker-engine file); the new file
  alone: **31 passed** (`tests/unit/band6/test_band6_poker_engine.py`).
- port fidelity: the `PokerGame`/`Player`/`PotResult` class body diffs
  **byte-for-byte IDENTICAL** against the oracle
  (`disbot/utils/poker/engine.py`, fetched at the oracle's main head) —
  the only deltas are the two import lines, the ported docstring, and the
  added `snapshot()`/`to_state()` reader.
- checker fleet all green: `manifest_compile` (sha unchanged — no manifest
  touched), `check_namespace`, `check_escape_hatches`, `check_schema_growth`,
  `check_amendments`, `check_symbol_shadowing`, `check_no_skip`,
  `check_config_usage`, `check_metric_cardinality`, `check_egress`,
  `check_money_race` (0 violations under sb/domain), `check_sim_gate`,
  `check_compat_frozen`, `check_parity_depth` (OK — 51 subsystems).
- `bootstrap.py check --strict`: green except the **designed born-red HOLD**
  on this card while it read in-progress (flipped complete at close-out) +
  a pre-existing owner-action advisory (not this slice).
- golden-parity gate + tests/integration are Postgres-CI legs; this slice
  mints zero goldens and touches no ported subsystem, so both are
  unaffected and run green in CI.

## Parked (honest)

The play/table layer — dealing into per-player ephemeral hands + the
auto-updating hand messages — is deferred to a later slice pending the
**D-0045** live-adapter gate. `casino.poker_start` stays an honest blocked
terminal; this engine is the headless core it will dock onto.

## 💡 Session idea

The oracle engine ships a Discord-free `PokerGame` that was *already*
unit-test-shaped (its own docstring: "the betting/pot logic is unit-tested
in isolation"), so the whole port cost was two import lines — the friction
was zero because the oracle authors had already paid the headless-purity
tax. The reusable lesson: when an oracle module advertises "Discord-free /
deterministic given a deck", the port is a rename job and the *value* the
slice adds is the serializable snapshot + the exhaustive test corpus, not
the code. Successor pick: the play/table layer (D-0045) should build its
golden shape directly off `snapshot()` — the dict is already the
table-state contract a replay case would pin, so the live-adapter slice can
mint goldens against it without inventing a second serialization.

Guard recipe (for the D-0045 successor): the engine resolves the whole
showdown *synchronously inside* the final `act(...)` call that closes the
last betting round (`PokerGame._end_betting_round` → `_run_out_and_show` →
`_settle_showdown`). A live adapter must therefore read `snapshot()` /
`results` *after* that `act()` returns, never expect a separate "reveal"
step — anchor: `sb/domain/casino/engine.py::_settle_showdown`, test target
`tests/unit/band6/test_band6_poker_engine.py::test_multi_all_in_side_pots`.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-cross-project-requests.md`, #262.) That
session's re-count-at-HEAD discipline transferred directly: it re-verified
its numbers against main at `764a393` rather than trusting the review doc,
and this slice did the same — the recon handoff named HEAD `764a393` but
`git ls-remote` showed `dd76427` (#262 had landed since), so treating the
handoff SHA as stale data and hard-syncing to the real HEAD was the right
call. One thing its card under-served a successor: it did not name where
the casino domain's headless boundary sat (cards/evaluate aboard, engine
pending) — that lived only in D-0045 prose, so this slice had to
re-derive the aboard/pending split from the decision record. A one-line
"casino: cards+evaluate aboard, engine is the next headless slice" in a
successor map would have saved a decisions.md read.

