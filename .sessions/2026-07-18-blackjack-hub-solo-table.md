# 2026-07-18 — blackjack hub-button solo flow: route the interactive table view

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red HOLD so the server-side lander
> can merge PR #551 on green. The born-red first commit (this card + claim) held
> the HOLD gate red; the implementation + tests landed in the second commit;
> this flip is the last.

- **📊 Model:** Opus 4 family · high · routing-fix

## Scope

Item 5 of `docs/ideas/blackjack-remaining-surface-2026-07-10.md` — the
**hub-button solo flow**. The `blackjack.hub` panel's **Solo Free Play**
(`bj_solo_free`) and **Solo Bet** (`bj_solo_bet`, the G-10 bet modal) actions
routed the bare `blackjack.solo_start` WORKFLOW with a `RESULT_CARD` — a
static, unplayable deal — while the shipped `!blackjack` command path
(`blackjack.play`) deals through `solo_start` and OPENS the interactive
`blackjack.table` session-lifecycle view (Hit/Stand/Double, refreshed in
place). The two surfaces disagreed: the command gave a playable table, the hub
buttons a dead card.

Contained routing-correctness fix. No golden touched (the table wire shape is
already pinned by `parity/goldens/blackjack/`; this only changes which surface
the hub buttons land on). DB-free additive tests.

## Deliver

- **`sb/domain/blackjack/handlers.py`** — extracted the shared deal→open-table
  body `_deal_solo_and_open(req, extra_params)` from `blackjack.play`'s solo
  branch (the command now delegates to it), and added the new
  `blackjack.hub_solo` handler: it threads the modal `bet` field (Solo Bet) or
  no bet (Solo Free Play) into `blackjack.solo_start` and opens
  `blackjack.table` on the interaction surface, returning `Reply(SUCCESS,
  None)` — the `casino.poker_open` command+button precedent (one handler, two
  entry surfaces, `open_panel` to a session-lifecycle panel).
- **`sb/domain/blackjack/panels.py`** — routed `bj_solo_free`, `bj_solo_bet`,
  and `SOLO_BET_MODAL.on_submit` to `HandlerRef("blackjack.hub_solo")`; dropped
  the free-play `RESULT_CARD` (now inert — the handler self-presents) and the
  now-unused `WorkflowRef` import.
- **`tests/unit/band6/test_band6_blackjack_solo.py`** — 3 DB-free cases:
  the spec routing (both Solo actions + the modal submit → `blackjack.hub_solo`,
  not the bare `solo_start` op), the free-play handler dealing + opening
  `blackjack.table` with no bet, and the bet handler threading the modal `bet`
  field into `solo_start`.
- **`manifest.snapshot.json`** — recompiled for the hub-action rewiring
  (`tools/manifest_compile.py --write`; the `manifest-validate` / runtime-smoke
  required gate).

## Verification

- `python3 -m pytest tests/ -q` → `3444 passed, 29 skipped, 1 warning in
  96.12s` (full suite, in the isolated worktree)
- `python3 tools/manifest_compile.py` → `green (49 manifest(s))`
- `python3 tools/check_runtime_smoke.py` → `clean — 1303 dispatch target(s),
  308 panel(s) …` (the new `blackjack.hub_solo` HandlerRef resolves)
- `check_namespace` / `check_no_skip` / `check_symbol_shadowing` /
  `check_config_usage` → all clean

## Deviation ledger

- **Brief vs. tree — item 5 IS a genuine deviation, confirmed against source
  (Q-0120).** The brief's preferred pick was real: `handlers.py` `play` opened
  `TABLE_PANEL_ID`, but `panels.py` `blackjack_hub_spec` routed both Solo
  actions to `WorkflowRef("blackjack.solo_start")` with `RESULT_CARD`. Items 2
  (PvP double-down) and 4 (natural-at-deal wire shape) are also still open in
  the tree, but item 5 was the most contained clearly-correct routing fix, as
  the brief anticipated. No invented work.
- **The free-play `RESULT_CARD` drop is inert, not behavioral.**
  `PanelActionSpec.result_render` DEFAULTS to `RESULT_CARD`, so removing the
  explicit one leaves the field value unchanged — but a `HandlerRef` handler
  that returns `Reply(SUCCESS, None)` after `open_panel` never renders a result
  card (no `user_message`), exactly like `casino.poker_open`. The behavioral
  change is the `handler` going `WorkflowRef` → `HandlerRef`; the tests assert
  that, not the (inert) `result_render`.
- **⚠️ Shared-worktree collision (env hazard, surfaced not swallowed).**
  Mid-session a concurrent worker on `claude/rps-solo-edit-in-place` switched
  the shared repo checkout to THEIR branch, intermixing their RPS-solo changes
  into the working tree; a `manifest_compile.py --write` I ran there briefly
  absorbed their changes into the snapshot. Per the working agreement's
  confusing-file-state rule I did NOT resolve their work: I saved my three
  blackjack files as a patch, restored the four files I had touched
  (`git checkout HEAD -- …`) so their tree was left exactly as they had it, then
  landed my change in an ISOLATED `git worktree` on my own branch — no
  disturbance to the sibling session. **Guard recipe:** parallel seat-builder
  workers must not share one working tree; launch each with `isolation:
  worktree` (or the coordinator hands each a distinct checkout) — the failure
  anchor is any `manifest_compile.py --write` picking up a sibling's uncommitted
  edits into `manifest.snapshot.json`.

## Close-out

PR **#551** (menno420/superbot-next) —
https://github.com/menno420/superbot-next/pull/551 · branch
`claude/blackjack-hub-solo-table` · opened READY (non-draft) on the born-red
commit. Three commits: born-red card+claim → implementation+tests+snapshot →
this flip. Full suite + all guards green locally; server-side lander on green.

## 💡 Idea

`blackjack.solo_start` is now reachable from three surfaces (the `!blackjack`
command, the hub Solo Free Play button, the hub Solo Bet modal) that ALL want
the same downstream shape: deal → open the interactive table. This PR unified
two of them onto `_deal_solo_and_open`; the same "one op, then open its
session-lifecycle table view" shape recurs verbatim in `casino.poker_open` and
will recur for every future solo casino game. A tiny kernel helper —
`deal_then_open(req, op_ref, panel_ref, *, extra)` in the games band — would
collapse the copy-pasted `engine.run(...) → check outcome →
dataclasses.replace(req, args={**after}) → open_panel` body into one audited
seam, so a game only declares its op + panel and the deal→open plumbing is
tested once, not per subsystem.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-test-depth-casino.md` (casino test-depth, #545) —
the card that documents the very `casino.poker_open` command+button precedent
this fix leans on. Its posture is sound (full-local suite sweep, both guards, an
honest deviation ledger) and its noted "`open_panel` hits the presenter wall in
headless tests" is exactly why my hub-solo handler tests stub `open_panel` +
`engine.run` rather than driving the live presenter — the same DB-free seam
discipline, one band over. One caution echoed forward: that card's 💡 idea
(hoisting scattered inline refusal-copy literals into one `_LOBBY_COPY` map so a
copy edit can't silently rot a test) is the sibling of my own 💡 here — both
converge on collapsing copy-pasted structure into a single audited seam.
