# Session: final-closeout (2026-07-21)

> **Status:** in-progress

## Goal
Program-end closeout: publish docs/PROJECT-CLOSEOUT.md, true up the state
docs to HEAD, delete the terminal cutover-prep claim, and overwrite the
final heartbeat — then land on green before the read-only cutover.

## Scope
- docs/PROJECT-CLOSEOUT.md (new, badge `reference`, reachable from current-state.md)
- docs/current-state.md (golden corpus 526 -> 533; add closeout link)
- control/claims/day1-cutover-prep.md (delete; terminal via merged #603)
- control/status.md (final heartbeat, SEAT CLOSED)

## Notes
Born-red card holds the PR until the closeout work is complete; flip to
complete LAST, after the heartbeat, to release the enabler.
