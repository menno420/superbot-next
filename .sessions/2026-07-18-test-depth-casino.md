# 2026-07-18 — casino test-depth: lobby-handler refusals + poker_action seams + evaluate.py category ladder

> **Status:** `in-progress`

- **📊 Model:** [[fill: model · effort · lane]]

## Scope

Test-depth coverage for `sb/domain/casino` poker: the four lobby-handler
refusal/permission gates (join/leave/start/close), the `poker_action` refusal
seams, and the `evaluate.py` category ladder + guards.

Additive tests ONLY — no product code changes, no golden, DB-free
(`resolve_ref(HandlerRef(...))` + `SimpleNamespace` fake `req` + `asyncio.run`
over the process-memory table/game registries; `reset_*_for_tests` +
`random.seed(42)` per test, mirroring `test_band6_poker_play.py`). New file
`tests/unit/band6/test_band6_casino_depth.py`. Born-red card, tests second,
flip-last; server-side lander on green.

## Deliver

**P1 — the four LOBBY handlers (zero prior behavioral tests):**
`poker_join` (closed / started / already-seated / full / happy-seat),
`poker_leave` (not-seated / non-host-removed-survives / host-teardown /
last-seat-empties teardown), `poker_start` (closed / non-host / already-started
/ <MIN_PLAYERS / happy deal — `open_panel` stubbed), `poker_close` (closed /
non-host / host-teardown). Real assertions on the verbatim shipped BLOCK copy.

**P2 — `poker_action` refusal seams:** game-gone ("This hand has ended."),
deal-next mid-hand ("Finish this hand first."), unknown session_action
("session has expired"), illegal raise surfaced as "♠ {exc}" (crafted state),
deal-next with <2 funded → table auto-closes ("♠ Not enough funded players").

**P3 — `evaluate.py` ladder + guards:** explicit PAIR/TWO_PAIR/TRIPS
`score_five` categories, the monotonic adjacent-category key ordering,
`_straight_high` normal/ace-high/wheel + kicker tiebreak, `score_five`/
`best_hand` length ValueErrors, `best_hand` best-5-of-6/7.

**P4 — view polish:** `public_spectator_view` folded/all-in tags + ▶ marker;
`raise_targets` degenerate guard → {0,0,0}.

## Verification

- `python3 -m pytest tests/unit -q` → [[fill: tail]]
- `python3 tools/check_namespace.py` → [[fill]]
- `python3 tools/check_no_skip.py` → [[fill]]

## Deviation ledger

[[fill: skipped gaps + why]]

## Close-out

[[fill: PR # + test count]]

## 💡 Idea

[[fill: one idea]]

## Previous-session review

[[fill: review of the most recent other .sessions card]]
