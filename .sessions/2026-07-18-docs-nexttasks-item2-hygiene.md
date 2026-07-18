# Session — NEXT-TASKS item 2 hygiene 2026-07-18

> **Status:** complete

- **📊 Model:** Opus 4.8 · effort med · docs-only

## Goal
Rewrite `docs/NEXT-TASKS.md` **item 2** ("Land the scoped game-surface
backlog"): it was stale — all three sub-items had either landed or become a
settled do-not-fix, yet still read as forward backlog. Mark item 2
essentially complete and stop listing settled work as pending.

## Scope
Docs-only slice. Branch `claude/docs-nexttasks-item2-hygiene` off
origin/main `2804428`. Born red (`in-progress`) as the first commit; held
the PR red until this deliberate Status flip. No item 1 / other-item content
changes beyond minimal formatting.

The landed edit to item 2:
1. **blackjack remaining surface** — DONE (PR #551, squash `70b8a8a`,
   "blackjack: hub Solo buttons open the interactive table").
2. **RPS remaining surface** — DONE (PR #552, squash `2804428`,
   "rps(solo): edit the picker message in place into the result embed");
   the `!rpsbot` bullet in the idea doc was already built on main, so that
   idea doc is now stale.
3. **tournament open-flag TOCTOU** — STRUCK as a settled owner-decision
   do-not-fix: keep the non-atomic accepted-posture, no atomic fence; PR
   #517 pinned it with a characterization test. Canonical home is
   `docs/decisions.md`; NEXT-TASKS points there WITHOUT re-stamping the
   decision-ID token (each decision stamped at one home).

## Trail
- Blackjack idea: `docs/ideas/blackjack-remaining-surface-2026-07-10.md`.
- RPS idea (now stale on the `!rpsbot` bullet):
  `docs/ideas/rps-tournament-remaining-surface-2026-07-10.md`.
- TOCTOU: idea doc `docs/ideas/tournament-open-flag-toctou-2026-07-12.md`
  (`outcome: accepted-posture`), owner decision recorded in
  `docs/decisions.md` (its single citation home).
- Verify: `pytest -q` → 3442 passed, 17 skipped, 1 pre-existing collection
  gap (`examples/superbot-plugin-hello` package not installed in this env)
  ignored; docs-only diff is behaviorally inert.

## 💡 Session idea
The substrate-gate `[stamp]` finding ("stamp each decision at one home")
fires on the raw `D-0XXX` token wherever it appears — including forward
ledgers and session cards that only mean to *reference* a decision, not
re-home it. A lightweight reference form (e.g. a `see: decisions.md`
convention, or a `ref:D-0XXX` marker the stamp check ignores) would let
NEXT-TASKS and cards cite a decision by pointing at its home without
tripping the one-home guard — separating "cite" from "stamp".

## ⟲ Previous-session review
The 2026-07-18 tournament-open-toctou posture-pin session resolved that row
as an accepted-posture do-not-fix rather than a behaviour change — exactly
the settled state this hygiene pass now records in the forward ledger, so
item 2's TOCTOU sub-item points at that decision instead of re-listing it as
pending work. The chain held: read the ledger, then reflect it forward.
