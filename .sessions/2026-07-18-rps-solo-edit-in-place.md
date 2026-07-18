# 2026-07-18 — rps solo result view edit-in-place (the message-edit presenter seam)

> **Status:** `complete`

- **📊 Model:** Opus 4 family · medium · feature (presenter-seam edit-in-place)

## Scope

Item 2 of `docs/ideas/rps-tournament-remaining-surface-2026-07-10.md` — the
**solo result view edit-in-place**. The shipped `views/rps/solo_play._RpsView`
EDITED the picker message into the result embed; v1's `rps_tournament.quickplay`
move buttons dispatched the audited `rps.solo_play` op DIRECTLY (a `WorkflowRef`
action with `ResultRender.RESULT_CARD`) and answered with a `followup_send` TEXT
line — the picker message was left untouched. The idea doc named the blocker as
"needs a message-edit presenter seam"; that seam now exists
(`refresh_session_view`, built for the PvP/match/botmatch lanes — the blackjack
solo `table_click` precedent is identical).

Routed the quickplay move buttons through a new `rps.solo_click` handler that
runs `rps.solo_play` then `refresh_session_view` — editing the picker message IN
PLACE into the result embed (the leg's own `{emoji} vs {bot_emoji} (bot)\n{text}`
copy, verbatim), the single throw terminal so the session expires with the move
buttons disabled. Contained to `sb/domain/rps/`; mirrors the blackjack solo
`table_click` edit-in-place shape exactly.

## Deliver

- **panels.py** — `rps_quickplay_spec()` move actions now carry
  `handler=HandlerRef("rps.solo_click")` + `defer_mode=DeferMode.NONE` (was
  `WorkflowRef("rps.solo_play")` + `ResultRender.RESULT_CARD`); `_render_quickplay`
  gained a terminal **result stage** (result line + GAME_COLOR held + move
  buttons disabled) alongside the open picker.
- **handlers.py** — new `rps.solo_click` handler: run the audited op →
  `refresh_session_view(..., expire=True)`; a vanished live session
  (restart/eviction) degrades to the leg's own result text (the op already
  settled money/stats).
- **tests** — `test_band6_rps_quickplay.py`: the walking-skeleton click now
  pins edit-in-place (interaction_response type 6 + `edit_followup`, result
  embed, stable minted ids disabled in place) + a new result-stage render test.
- **golden** — `rps_tournament_quickplay_bet_settle_write.json` step-2 wire
  `calls` reshaped to the edit-in-place verb structure (mirroring
  `goldens/blackjack/blackjack_solo_round_hit`); `db_delta` unchanged.
  `manifest.snapshot.json` recompiled for the new dispatch target.

## Verification

- `python3 -m pytest tests/ -q` → **3445 passed, 29 skipped**.
- `tools/manifest_compile.py` green (sha256:adfbcb51…); `check_namespace`,
  `check_runtime_smoke`, `check_escape_hatches`, `check_schema_growth`,
  `check_amendments`, `check_symbol_shadowing`, `check_no_skip`,
  `check_config_usage` all clean.

## Deviation ledger

- **Brief preferred item 5 (`!rpsbot` deep bot-match flow) — NOT open.**
  `sb/domain/rps/bot_match.py`, the `rps.bot_route`/`rps.botmatch_move`
  handlers, the `rps_tournament.botmatch` panel + `_render_botmatch`, and the
  `rps.bot_round` op are all fully built on `origin/main`. The idea doc (dated
  2026-07-10) is stale on that item. Fell back to item 2 per the brief; item 6
  (time-driven depth) deliberately not built.
- **Shipped "play again" button — ledgered deferral.** The shipped view edited
  into the result embed *plus* a play-again view; this v1 disables the move
  buttons in place — hub re-entry stays one `!rps` away, identical to item 1(b)'s
  PvP-terminal posture (the shipped back-to-hub button deferred the same way).
- **Result-frame color** kept at GAME_COLOR (purple) across both stages rather
  than win/loss-tinting — the shipped `_RpsView` kept its accent and the solo
  op's `after` carries no clean win/loss/tie flag to key a color on.
- **Golden wire re-mint** is byte-authoritative only under Postgres in the
  red-by-design golden-parity workflow; the container edit reshapes the calls
  faithfully (verb + payload verified against a DB-free harness capture) and
  keeps `db_delta` (money/stats/xp identical).

## Close-out

- PR **#552** — https://github.com/menno420/superbot-next/pull/552 · branch
  `claude/rps-solo-edit-in-place` · opened READY. Named gates the judge; the
  auto-merge enabler lands the non-draft `claude/*` PR on green.

## 💡 Idea

The shipped **"Play Again"** button is the one piece of item 2 left on the
table. A bounded successor: a `rps.solo_replay` action on the terminal result
frame that re-opens a fresh `rps_tournament.quickplay` picker (carrying the
prior bet forward) — a single new handler + one result-stage button, no op
change, completing the shipped `_RpsView` loop end-to-end. Its copy/shape is
unpinned, so it wants an oracle read before it lands.

## ⟲ Previous-session review

The immediately-preceding `claude/blackjack-hub-solo-table` session (item 5,
blackjack hub-button solo flow) routed its hub buttons onto the same
session-lifecycle table view via `open_panel` — its clean claim + born-red
card scaffolding was a faithful template for this slice, and its
`table_click`/`refresh_session_view` shape was the exact precedent this RPS
change mirrors.
