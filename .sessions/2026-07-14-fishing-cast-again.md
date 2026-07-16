# 2026-07-14 — fishing: Cast-again continuation on the result card (gap 3)

> **Status:** `complete`

- **📊 Model:** fable-5

## Scope

Claimed lane (`control/claims/fishing-cast-again.md`, branch
`claude/fishing-cast-again`, claim PR #465): the Cast-again
continuation — ranked gap 3 in
docs/review/games-finalization-2026-07-13.md. Today the post-catch
fishing result is a terminal plain-text Reply
(`sb/domain/fishing/ops.py::_record_cast` → `after["message"]`,
returned by `service.py::fish_route`) and the cast panel is left
behind with a stale Reel button. Oracle (menno420/superbot @ bbc524e,
`disbot/views/fishing/cast_view.py` `_FishingDoneView`, doc-pinned
:545/:562): a green 🎣 "Cast again" button on the catch terminal AND
the click-failure terminals (premature spook, too-slow, fight snap),
NOT on timer-expiry; never pre-disabled; click re-runs the full cast
path; author-only.

## Plan

1. New cast-result PanelSpec in `sb/domain/fishing/panels.py`
   (cast_spec conventions, session_lifecycle=True), renderer params =
   title/description/tone; one PanelActionSpec
   `fishing_cast_again` · "Cast again" · 🎣 · success style ·
   `HandlerRef("fishing.cast_open")`. Register in
   `sb/manifest/fishing.py`.
2. `service.py::fish_route`: at the catch terminal and the
   click-driven failure terminals, expire the cast session (existing
   terminal-close mechanics), open the result panel with the result
   params, return `Reply(SUCCESS, None)`. Timer-driven got-away /
   window-expiry stays disable-only (oracle parity).
3. Verify EARLY that `open_panel` works from a panel-action handler
   context; if not, fall back to terminal-rendering the cast session
   in place with a `fishing_cast_again` action on `cast_spec()` and
   flag the fallback.
4. Unit tests in the band6 fishing style; goldens: re-mint affected
   fishing cases + ONE new curated continuation case (register its
   capture-day weather in CAPTURE_WORLD_WEATHER before minting).

Untouched by design: control/status.md, control/inbox.md,
control/outbox*, mining domain files, WP parity files, other lanes'
claims.

## Verification

- Design outcome: `open_panel` from a click-handler context WORKS (the
  hub-Cast → cast_open precedent) — no fallback taken. One addition
  the brief did not name: the result card is
  `AnchorPolicy.CHANNEL_ANCHOR`, because a click-opened panel on the
  default REPLY policy rides the interaction response and the parity
  transport mints NO message id for those (mint error verbatim:
  `ValueError: step targets <msg:2> but only 1 bot messages were
  minted`) — CHANNEL_ANCHOR is the sanctioned fresh-channel-message
  seam (blackjack tournament / poker precedent, live twin at
  sb/adapters/discord/panel_view.py:347-353) and matches the oracle's
  public result message.
- `python3 -m pytest tests/ -q`: **3121 passed, 15 skipped**.
- `python3 bootstrap.py check --strict`: green up to the DESIGNED
  born-red hold on this card + the 4 pre-existing claims advisories
  (all also on main).
- Local gate (docs/CAPABILITIES.md recipe, Postgres 16): `gate: GREEN
  — all 499 golden(s) across 50 ported subsystem(s) replay clean`.
- Goldens: +1 minted `fishing.cast_again_continuation` (storm
  registered in CAPTURE_WORLD_WEATHER BEFORE the mint); 6 re-minted
  (`fishing.cast_{reel,deepwater_reel,bait_spend}_write`,
  `fishing.cast_premature_spook`,
  `fishing.cast_trophy_fight_{land,escape}`) — same seeds, same
  draws, only the terminal reply's wire shape moved;
  `fishing.cast_premature_grace` replays clean UNTOUCHED (verified:
  it never went red under the new code — a forgiven slip is not a
  terminal).
- Flagged (decide-and-flag): the click-driven failure terminals now
  answer `Reply(SUCCESS, None)` + the error-tone result card instead
  of `Reply(BLOCKED, text)` — the card carries the copy and the
  oracle presented these as ordinary messages, not denials. The
  stale/timed-out-line clicks keep their BLOCKED text terminals.

## 💡 Session idea

`mint_golden --force` re-bumped nothing but I hand-bumped
`minted_goldens` on top of the tool's own rewrite before catching it
in the diff — the tool could print "counts already re-pinned by this
run; do not edit them" in its MANUAL STEPS block to fence that
double-edit off.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-fishing-minigame-timing-2.md` — slice 2
of the timing rung.) Review proper at close-out; noted going in: its
guard recipe (every wall-clock timer callback must due-guard on
SYSTEM_CLOCK) directly constrains this lane's terminal-close work, and
its 💡 (surface discarded `push_session_refresh` EDIT_* outcomes)
remains unbuilt.
