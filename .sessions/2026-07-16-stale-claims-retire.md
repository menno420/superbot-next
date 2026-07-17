# 2026-07-16 — control hygiene: retire six terminal claims, file conform-sweep-457

> **Status:** `complete`

- **📊 Model:** Fable 5 · default effort · control-hygiene slice

## Scope

Control-plane hygiene slice, two moves in one PR (branch
`claude/stale-claims-retire`):

1. **Retire six stale claim files** from `control/claims/`. Every PR each
   claim references was verified MERGED via live GitHub reads this session
   (2026-07-16) — unanimous safe-to-delete; per the claims README a claim
   is a whiteboard note whose durable record is the PR:
   - `mining-write-parity-lane.md` — #306 #312 #317 #335 #344 #371 all merged
   - `energy-lane-slices-1-3.md` — #320 #385 #392 all merged
   - `fishing-cast-again.md` — #466 merged
   - `order-022-titleequip-row72.md` — #473 #476 (#371) merged
   - `stale-stack-reconcile-392-476.md` — #392 #476 merged
   - `wp-stack-reconcile.md` — #312 #317 #335 #344 #371 #392 merged
2. **File the successor claim** `control/claims/conform-sweep-457.md`
   (branch `claude/conform-sweep-457`): the #457 conform sweep — re-mint
   every raw-posture NON-KERNEL golden to the canonical stripped D-0073
   flavor (#420/#449 precedent), plus the `parity/parity.yml` mining
   ratchet-floor correction and count-pin re-sum that stripping forces.
   Kernel goldens stay exempt per D-0075.

No code paths touched — `control/claims/` + this card only.

## Verification

- `python3.11 -m pytest tests/ -q` — full suite green before push:
  `3160 passed, 29 skipped` (container venue: no local Postgres at this
  point in the session, DB-marked tests skip — the docs/CAPABILITIES.md
  subagent-venue posture).
- Claim bullet rendered via `bootstrap claim --dry-run` (kit grammar
  constants) so `check_claims` can parse it — not hand-improvised.

## 💡 Session idea

The six retired claims went stale the same way: the session that merged
their terminal PR was never the session that owned the claim file, so
nobody's close-out step covered the deletion (the merge-queue session
landed #466/#473/#476 but those claims belonged to ended sessions).
A cheap structural fix: teach `check_claims` to cross-reference each
claim bullet's `[DELIVERED — PR #N]` / branch token against merged-PR
state and emit a `claims-terminal` advisory distinct from the ~72h
`claims-stale` timer — "every referenced PR is merged" is a much
stronger prune signal than age, and it would have flagged all six of
these the morning after the merge queue landed instead of waiting for a
manual audit. Anchors: `check_claims` in `bootstrap.py`, grammar in the
kit's `src/engine/grammar.py`.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-16-merge-queue-landed.md` (the merge-queue
session, #497 lane). Exemplary close-out density: the count-pin
union-and-re-sum recipe (`tools/mint_golden.py` `compute_counts`,
verified against the on-disk corpus glob) is written precisely enough
that this session's successor claim cites it as the procedure of record
for the conform sweep's pin re-sum. One gap that session left behind is
exactly what this slice cleans up: it landed the terminal PRs for four
of the six claims retired here but — reasonably, claims being foreign —
did not prune the claim files, and its card did not flag them as now
retirable. A one-line "claims now terminal: X, Y, Z" note in the
close-out would have handed this session the list for free.
