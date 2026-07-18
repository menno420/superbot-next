# 2026-07-18 — casino test-depth: lobby-handler refusals + poker_action seams + evaluate.py category ladder

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red HOLD so the server-side lander
> can merge on green. The born-red first commit (this card + claim) held the
> HOLD gate red; the additive tests landed in the second commit; this flip is
> the last.

- **📊 Model:** Opus 4 family · high · test-depth

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

- `python3 -m pytest tests/unit -q` → `3430 passed, 2 skipped, 1 warning in 65.65s` (full unit suite, per the ref-table lesson)
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface funnels through resolve())`

## Deviation ledger

- **Gap 5 (`poker_open` second-table refusal) skipped — already covered.**
  `test_band6_casino_panels.py::test_poker_open_refuses_a_second_table_with_the_shipped_copies`
  already pins both shipped copies verbatim; re-covering would be padding.
- **engine.py betting math + `poker_action` happy-path dispatch NOT re-covered
  — already well-covered** by `test_band6_poker_engine.py` + the
  `test_dispatch_*` block in `test_band6_poker_play.py` (53 cases). This slice
  adds only the *refusal* seams they leave open.
- **`poker_start` / `poker_open` happy paths hit the presenter wall.** Past the
  lobby guards the handler calls `open_panel`, whose default headless presenter
  raises `PanelPresenterNotInstalled` (live-adapter concern). The happy-deal
  test stubs `engine.open_panel` (the shipped `access_map` monkeypatch recipe)
  and asserts the handler's OWN effects — `lobby.started=True` + a hand dealt
  into the game registry — not the panel send. No gap was left infeasible.
- **`last-seat-empties` teardown crafted in isolation.** The `not lobby.seats`
  branch is unreachable through the normal host-always-seat-0 model, so the
  test seats a lone non-host occupant (host_id unseated) to exercise that
  specific branch distinct from the `uid == host_id` teardown lane.

## Close-out

PR **#545** (menno420/superbot-next) — `tests/unit/band6/test_band6_casino_depth.py`,
**30 DB-free cases**, additive only, no product code, no golden. Full unit
suite + both guards green; server-side lander on green. Branch
`claude/test-depth-casino`.

## 💡 Idea

The lobby-handler refusal copies live as bare inline string literals scattered
across `service.py` (`"This table has closed."`, `"Only the host can
start the table."`, …), so every test pins them by re-typing the exact bytes —
one copy edit silently rots a test into a stale-literal assertion nobody
notices until it drifts. Hoisting them into a small `_LOBBY_COPY` frozen map
(or module constants) beside `_POKER_PANEL` would give both the handlers and
the tests ONE seam to reference, turning a copy change into a single-point edit
the suite catches structurally rather than by lucky string match.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-test-depth-xp.md` (xp test-depth, #542) — the
immediate sibling and the branch base (`fd6f71d`): the closest analog, an
additive born-red DB-free depth slice over band-4 xp (18 cases) that this
casino slice mirrors one band over. Its posture is sound — full-local
`tests/unit` sweep (green, 3358) per the ref-table lesson, both guards, honest
deviation ledger — and its Q-0120 finding (the `ops.py` negative-level guard
is DEAD because `reduce_max_levels` drops `level < 0` first) is exactly the
kind of same-session code discovery the working agreement's discovery rule
wants surfaced, not just the test. One caution echoed forward: its 18 cases sit
in a single dense file and it flagged the DB-backed `store.py` SQL legs
(`add_xp`/`top_xp`/…) as an un-exercised follow-up — the same shape of hole
this casino slice leaves at the presenter wall (the `open_panel` send stays a
live-adapter concern). Both cards converge on the same frontier lesson:
test-depth pins the headless refusal/permission seams cleanly, and the
DB-/adapter-backed edges remain a deliberately-scoped follow-up, not a miss.
