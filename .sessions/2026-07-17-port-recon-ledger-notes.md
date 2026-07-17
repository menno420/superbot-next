# 2026-07-17 — port-backlog recon + ledger notes

> **Status:** `in-progress`

A ledger/upkeep slice landed while the substantive port backlog (NEXT-TASKS
#1/#2) is blocked on the port oracle this session. Carries two
coordinator-directed riders + a dated wall note + a discipline guard recipe.

## WHAT

A ledger/upkeep slice landed while the substantive port backlog (NEXT-TASKS
#1/#2) is blocked on the port oracle this session. Carries two
coordinator-directed riders + a dated wall note + a discipline guard recipe.

## WHY

The parity-facing backlog (#1 finish the port to full parity, #2 game-surface
backlog) cannot be advanced honestly without the `menno420/superbot` oracle
(out of scope this session) and a live Postgres (down: `5432 - no response`).
Minting a golden needs BOTH (tools/mint_golden.py refuses to fake oracle
byte-verification; the db_delta is part of the pin). #3 (effect-leg
compensation gaps) already shipped in #105. #4/#5 are owner-only; #6 is a
next-Project change left untouched. So the honest first rung is the two riders
+ recording the wall so the next session picks up #1 with the prerequisite
named.

## CHANGES

- tests/unit/invariants/test_composition_parity.py — one-line docstring note on
  test_burn_down_entries_are_still_real: ensure-only burn-down fully retired
  (#508), frozenset empty, no future exemption rows.
- docs/current-state.md — dated NEUTRAL note: trigger/routine reconciliation.
- docs/current-state.md — dated NEUTRAL note: port-backlog prerequisite (oracle
  + Postgres) recorded.

## GUARD RECIPE — never push after your PR merges

Auto-delete-branches-on-merge is enabled. Pushing to a branch AFTER its PR
merges recreates the just-auto-deleted ref and leaves an orphan. Rule: the card
flip is your LAST push and happens PRE-merge (the flip releases auto-merge); any
post-merge follow-up goes on a NEW branch. Verified 2026-07-17 — four orphan
branches (claude/energy-slice-2, claude/title-equip-write, claude/curation-row72,
claude/wp-stack-reconcile) each sat exactly at their merged PR head
(#385/#473/#476/#424) from this pattern.

## VERIFICATION

python3 -m pytest tests/unit/invariants/test_composition_parity.py -q →
3 passed in 1.04s. Full unit suite `python3 -m pytest tests/unit -q` →
3158 passed, 2 skipped. Doc/docstring-only changes; six named gates unaffected.

<!-- ender (added at flip): badge -> complete · 💡 idea · model line · prev-session review -->
