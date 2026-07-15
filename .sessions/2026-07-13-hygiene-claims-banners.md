# 2026-07-13 — Hygiene: stale-claim cleanup + golden-parity banner retirement

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · contained hygiene slice: independently
  re-verify the stale claim-file candidates against LIVE GitHub PR state
  (Q-0120 — the candidate list is leads, not facts; delete only with a
  terminal citation in hand), and retire the stale "red by design" /
  "expected red" golden-parity banner wording now that the report leg is
  live-green. Cosmetic only — zero behavior change.

## Scope

1. **Claims cleanup** (`control/claims/`): for each candidate file, read
   the claim, resolve its PR number(s), verify at live GitHub that every
   tracked PR is MERGED or CLOSED, and delete only with that citation.
   Anything not provably terminal stays, with the reason recorded in the
   PR body. `README.md`, `mining-write-parity-lane.md` (WP stack, #371
   tip) and `energy-lane-slices-1-3.md` (#392) are kept regardless.
2. **Banner retirement**: string/comment/step-name changes only in the
   golden-parity workflow + harness — neutral present-truth wording
   ("golden parity report"), no change to required jobs, job ids, exit
   codes, or thresholds.

## 💡 Session idea

Claim files could carry their lead PR number in the parseable bullet
(e.g. `· PR #309`) once one exists — the cleanup pass then becomes a
mechanical "resolve number → check state → delete", instead of each
sweep re-deriving PR numbers from branch names and search. One extra
token at claim-update time saves a whole verification grep per file per
sweep.

## ⟲ Previous-session review

The server-mgmt projections slice B card shows the stacked-slice recipe
working as designed: slice A landed the load-bearing projection seam and
slice B became a near-pure fields-provider on top of it, with the
hub-open goldens pinned byte-identical across the flip. The card's
review section also fed forward a concrete testing improvement (patch
the module-seam owners from the start rather than hand-driving the
degrade path), which is exactly the friction-to-recipe conversion the
README asks cards to carry.
