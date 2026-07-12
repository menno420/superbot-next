# 2026-07-12 — casino poker betting state machine (headless engine port)

> **Status:** `in-progress`

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

(filled at close-out)

## Parked (honest)

The play/table layer — dealing into per-player ephemeral hands + the
auto-updating hand messages — is deferred to a later slice pending the
**D-0045** live-adapter gate. `casino.poker_start` stays an honest blocked
terminal; this engine is the headless core it will dock onto.

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out)
