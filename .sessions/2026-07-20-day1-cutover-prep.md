# Session card: day-1 cutover prep

> **Status:** `in-progress`

- date: Mon Jul 20 07:30:12 UTC 2026
- goal: make `main` a clean durable artifact for the recreated Project — add a
  successor day-1 runbook, correct stale factual pointers that describe
  already-completed 2026-07-18 owner work as live blockers, retire terminal
  merged-work claims, and refresh drifted test/golden counts.

## Plan
- [ ] Claim + born-red card committed and pushed first.
- [ ] Add docs/RECREATED-PROJECT-DAY1.md (binding day-1 runbook).
- [ ] Fix factual pointers: control/status.md, docs/design/D6-*, docs/current-state.md, docs/NEXT-TASKS.md.
- [ ] Retire 10 terminal merged-work claims under control/claims/.
- [ ] Verify (pytest or collect-only note).
- [ ] Flip card complete LAST; push; open READY PR.
