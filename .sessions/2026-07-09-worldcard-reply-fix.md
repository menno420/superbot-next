# 2026-07-09 — worldcard Reply-shape fix + red-orientation docs

> **Status:** `complete`

- **📊 Model:** claude-fable-5 · high · contained bug fix + docs (single-push session)

## Scope

Gen-1 grand-review session (superbot #1911 lane) sweeping the fleet found, while
root-causing the golden-parity report red (verdict: red-by-design, working as
documented — see the new `docs/status/README-first.md`), one genuine contract
violation in the replay corpus's only non-`RefUnresolved` crash class:

- **`games.world_card_view` returned a raw dict** (`{"text": ...}`) where the
  resolver's HandlerRef leg requires the `Reply` duck-shape
  (`sb/kernel/interaction/resolve.py` reads `.outcome`/`.user_message`) — live
  `!worldcard`/`!mystats` and both `RESULT_CARD` panel actions crashed into a
  BUG-class envelope (`AttributeError: 'dict' object has no attribute 'outcome'`,
  visible verbatim in the report-job logs, target=`worldcard`).

## What shipped

1. `sb/domain/games/service.py` — `_world_card_view` returns
   `Reply(SUCCESS, ...)` per the sibling precedent
   (`sb/domain/blackjack/handlers.py`); 2-line fix + imports.
2. `tests/unit/band6/test_band6_games_substrate.py` —
   `test_world_card_view_handler_reply_shape` pins the duck-shape.
3. `docs/status/README-first.md` — the retro's own E4 prevention
   (self-review §E4): one screen stating red ≠ broken, the A-16 one-way door,
   the flag-13 gate, and where live truth lives; linked from the README.
4. `README.md` — status line was still "bootstrapping — intent-only first
   commit"; now states the real state (7 bands, 41 subsystems, bands 1–4
   live-tested, band 5 in flight) + the READ-FIRST pointer.
5. `docs/current-state.md` — filled the empty kit-template sections with a
   minimal snapshot deferring to `control/status.md` as the live ledger.

## 💡 Session idea

The report job's log output could emit a one-line
`NOTE: this job is red-by-design (docs/status/README-first.md)` header before
the corpus dump — the doc now exists to be pointed at, and the job log is where
every confused reader actually starts.

## ⟲ Previous-session review

The band-5 seams session (PR #95) left a clean, fully-classified replay state
and its PR body accurately describes its diff (verified during the grand
review). What it missed: the `worldcard` AttributeError was already visible in
the report logs it quotes — a standing "any non-RefUnresolved crash class in
the report is a bug, file it" rule would have caught it a session earlier.
Improvement shipped this session: README-first.md makes that rule legible.
