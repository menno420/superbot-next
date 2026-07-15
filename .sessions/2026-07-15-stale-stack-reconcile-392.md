# 2026-07-15 — stale-stack reconcile: PR #392 additive merge

> **Status:** `in-progress`

## Scope

Dispatched worker lane reconciling stale stacked PR #392
(`claude/energy-slice-3` @ `24ca87e`) against its base
`mining-write-parity-wp3` (@ `ade9e69`) by **additive merge only** —
`git merge origin/mining-write-parity-wp3` into the head branch. No
rebase, no force-push, PR stays open (do-not-automerge doctrine —
merges are owner-click).

Known conflict class (6 files): `parity/cases/curated.py`,
`parity/parity.yml`, `sb/domain/mining/ops.py`,
`sb/domain/mining/service.py`,
`tests/unit/parity_adapter/test_replay_adapter.py`,
`tests/unit/parity_gate/test_check_parity_depth.py`. wp3 absorbed main
(incl. PR #312 WP-2 vault goldens) after this head last reconciled.
Doctrine from the predecessor lane: bottom-up re-fold; count pins are
RE-SUMMED FROM DISK (recount the golden corpus after the merge), never
hand-adjusted. Mining ops/service semantic truth = the local superbot
oracle clone.

Sibling worker handles PR #476 / `claude/curation-row72`; this session
only names it in the shared claim.

## Verification

(to be filled at close-out)
