# 2026-07-14 — fishing: minigame timing rung slice 2 — live bite edits + full enforcement (D-0043)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family)

## Scope

Claimed lane (`control/claims/fishing-minigame-timing.md`, slice-2 leg;
branch `claude/fishing-minigame-2`, PR #462, follows PR #460): the
push-edit half of the docs/decisions.md fishing-minigame timing rung —

- **Kernel session push-edit seam** (`sb/kernel/panels/engine.py`):
  `PanelSession.channel_id` + `push_session_refresh(message_key,
  params, actor, …)` — the `refresh_session_view` render-onto-original-
  minted-ids body presented through the `_message_editor` port (no
  ResolveRequest); uninstalled editor ⇒ `EDIT_UNAVAILABLE` no-op, gone
  session/channel-less message ⇒ `EDIT_MISSING`; `expire=True` tears
  the session down (terminal edits).
- **One-shot timer seam** (`sb/kernel/panels/timers.py`, new):
  `schedule(delay_s, callback) → OneShotTimer` — cancel-safe,
  exception-contained (logged via the band logger), process-local
  (ADR-002 restart-loss posture). NOT the S10 due-queue (5 s poll +
  pure-DB fence).
- **Domain wiring** (`sb/domain/fishing/service.py`): cast park arms
  nibble (oracle lead-fit guard `delay − FAKEOUT_LEAD >
  BITE_DELAY_FLOOR`) / 🐟 BITE! arm (green + button flip to "Reel it
  in!"/success) / unprompted got-away (pop + red terminal edit +
  disable + session expiry, NO DB write); hook + every non-final tap
  re-arm the fight-round beat (0.8 s then window expiry). Timers
  cancelled at every resolution/sweep/pop; callbacks identity-guarded
  (the oracle `_round_id` posture) AND due-guarded on SYSTEM_CLOCK
  (`_timer_due`).
- **Enforcement flip**: late reel (past bite_at + window) and late
  fight tap → the oracle `🌊 *...too slow...*` got-away terminal (+
  trophy clue); pre-round-open clicks → the oracle mash-ignore;
  `minigame.reel_is_in_time` finally consumed. Slice-1 "late =
  in-time" posture + ledger notes removed (ops.py / minigame.py /
  panels.py / service.py docstrings flipped).
- **Decision entry**: docs/decisions.md **D-0090** (the sanctioned
  real-time lane; D-0079/D-0081 stamp format).
- **Goldens**: the 3 reel-write goldens retuned with in-window
  `advance_s` + re-minted; parity.yml minted-history narrated.

Untouched by design: control/status.md, control/inbox.md,
control/outbox*, mining domain files, WP parity branch files.

## Verification

Oracle copy read via GitHub MCP `get_file_contents` pinned @ bbc524e
(cast_view.py `_run_bite`/`_run_fight_round`/`_arm`/`_fail`/`reel_btn`)
— nibble/BITE!/too-slow/slack-line/fight-arm strings and the fake-out
lead-fit guard are oracle-verbatim.

- `python3 -m pytest tests/ -q`: **3126 passed, 2 skipped** (the new
  timer/push-seam/enforcement units included).
- `python3 bootstrap.py check --strict`: green up to the DESIGNED
  born-red hold on this very card (flipped by this commit) + the 4
  pre-existing claims advisories (also on main).
- Local gate (docs/CAPABILITIES.md recipe, Postgres 16): `gate: GREEN —
  all 498 golden(s) across 50 ported subsystem(s) replay clean`.
- Golden churn was exactly the 3 reel-write cases (their default 30 s
  clicks flip too-slow under enforcement): retuned in-window
  (`advance_s` 5.0 / 8.0 / 5.0 inside the seed-42 storm windows
  [4.28…6.78] / [7.09…9.89] / [4.28…6.78], computed against the real
  modules) and re-minted via `tools/mint_golden.py --write --force` —
  species/weight/delta trajectories unchanged, only click timestamps +
  input docs moved; counts unchanged. The 4 slice-1 timing goldens
  replay clean untouched.
- **Flagged deviation** (decide-and-flag): bite timers deliberately
  SURVIVE a grace-forgive — the oracle's still-running bite task arms
  the real bite after a forgiven slip (cast_view.py reel_btn comment,
  @bbc524e), so the brief's "cancel on grace-forgive" would erase the
  promised BITE! cue.

## Friction-to-guard (found + fixed in-session)

Replay wall time inside one driven case can EXCEED the bite delay
(per-step DB snapshots), so a wall-clock got-away timer fired mid-case
and popped a cast the goldens still owned — all 7 fishing click goldens
went red at once. Guard recipe: every timer callback must ALSO verify
its logical deadline on SYSTEM_CLOCK (`service._timer_due`, 50 ms
slack; prod wall == logical ⇒ always passes) — pinned by
`test_wall_fired_timer_before_its_logical_moment_noops`
(tests/unit/band6/test_band6_fishing_minigame_timing.py). Any future
wall-clock timer whose callback mutates domain state needs the same
due-guard, or parity replay owns its state race.

## 💡 Session idea

`push_session_refresh` returns the `EDIT_*` outcome but every fishing
call site discards it. A tiny observability counter (per-panel
EDIT_MISSING/FAILED tallies through the metrics band) would make prod
push-edit rot visible — today a wedged editor (permissions revoked,
message deleted) degrades silently and only a player notices the
panel never says BITE.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-fishing-minigame-timing.md` — slice 1.)
Its decision to roll + STORE the fake-out at cast time paid off exactly
as designed: slice 2 flipped enforcement without moving a single pinned
RNG trajectory (the 4 timing goldens replayed byte-clean). Its 💡 (a
`tools/hunt_cast_seed.py` seed-walker) is still unbuilt and was felt
again this session — the in-window `advance_s` retune re-derived the
bite math in a scratch script against the real modules, which is
precisely the two-minute job that tool would make of it. One gap: the
card's "wall-clock timers never fire inside a driven case" assumption
(implicit in parking the push seam) turned out FALSE under replay wall
time — worth a guard-recipe line then; it cost this session a
seven-red gate round to rediscover.
