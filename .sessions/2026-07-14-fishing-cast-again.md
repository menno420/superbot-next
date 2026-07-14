# 2026-07-14 — fishing: Cast-again continuation on the result card (gap 3)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable

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

(to be filled at close-out: pytest + strict check + gate tails)

## 💡 Session idea

(to be filled at close-out)

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-fishing-minigame-timing-2.md` — slice 2
of the timing rung.) Review proper at close-out; noted going in: its
guard recipe (every wall-clock timer callback must due-guard on
SYSTEM_CLOCK) directly constrains this lane's terminal-close work, and
its 💡 (surface discarded `push_session_refresh` EDIT_* outcomes)
remains unbuilt.
