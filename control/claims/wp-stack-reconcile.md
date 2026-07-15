# Claim — WP-stack conflict reconcile (ORDER 019 item 1)

- `claude/wp-stack-reconcile` · **WP-stack conflict reconcile per ORDER 019 item 1** — merge base into each of #312→#317→#335→#344→#371, resolve the 4-file conflict class (`parity/cases/curated.py`, `parity/parity.yml`, 2 count-pin tests), re-mint migration-0052-invalidated WP-2/3 goldens byte-identical to #392 @ `24ca87e`; merges stay owner-click · area: WP branches `mining-write-parity-wp2..wp7`, `parity/cases/curated.py`, `parity/parity.yml`, `parity/goldens/mining/`, `tests/unit/parity_adapter/test_replay_adapter.py`, `tests/unit/parity_gate/test_check_parity_depth.py` · 2026-07-13

**Coordination note.** This claim overlaps two live claims and stays merge-only
with respect to them: `mining-write-parity-lane.md` (the WP lane itself) and
`energy-lane-slices-1-3.md` (slice 3 = PR #392, stacked on WP-3). We only add
merge commits to those branches — never rebase or force-push them, and never
touch #392's branch (`claude/energy-slice-3`); where re-mints overlap #392's
goldens they must land byte-identical to `24ca87e`.
