# Session — NEXT-TASKS item 2 hygiene 2026-07-18

> **Status:** `in-progress`

## Goal
Rewrite `docs/NEXT-TASKS.md` **item 2** ("Land the scoped game-surface
backlog"): it is now essentially complete and partly stale. Reflect the
landed/settled reality of all three sub-items and stop listing settled work
as pending.

## Scope
Docs-only slice. Branch `claude/docs-nexttasks-item2-hygiene` off
origin/main `2804428`. Born red (`in-progress`) as the first commit; holds
the PR red until the deliberate Status flip lands. No item 1 / other-item
content changes beyond minimal formatting.

The intended edit to item 2:
1. **blackjack remaining surface** — DONE (PR #551, squash `70b8a8a`,
   "blackjack: hub Solo buttons open the interactive table").
2. **RPS remaining surface** — DONE (PR #552, squash `2804428`,
   "rps(solo): edit the picker message in place into the result embed");
   the `!rpsbot` bullet in the idea doc was already built on main, so that
   idea doc is now stale.
3. **tournament open-flag TOCTOU** — STRUCK as do-not-fix: explicit owner
   decision D-0092 (`docs/decisions.md`, decided 2026-07-18: keep the
   non-atomic accepted-posture, no atomic fence; PR #517 pinned it with a
   characterization test). No longer pending work.

## Trail
- Blackjack idea: `docs/ideas/blackjack-remaining-surface-2026-07-10.md`.
- RPS idea (now stale on the `!rpsbot` bullet):
  `docs/ideas/rps-tournament-remaining-surface-2026-07-10.md`.
- TOCTOU idea (`outcome: accepted-posture`) +
  `docs/decisions.md` `[D-0092]`.

<!-- close-out markers (💡 idea, ⟲ previous-session review, 📊 Model) added at the deliberate Status flip -->
