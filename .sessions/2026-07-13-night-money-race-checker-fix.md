# 2026-07-13 — check_money_race: conditional-FOR-UPDATE ownership SELECT mis-classification fix (ORDER 019 item 3)

> **Status:** in-progress

## Scope

ORDER 019 item 3 (night lane, claim landed in PR #422): the WP-2/3/5/6/7 PR
bodies all flag the same never-fixed checker bug — `tools/check_money_race.py`
reads the plain (for_update=False) `get_mining_inventory` ownership SELECT in
`sb/domain/mining/ops.py::_record_repair` (ops.py:619 at a11325d; the order's
`:598` is a stale line number, today it points into the slice-4 comment block)
as a FENCE.

Root cause: `_fence_fixpoint`'s seed correctly excludes lockable readers
(`has_for_update_param`), but its propagation step does not — the conditional
`" ORDER BY item_name FOR UPDATE" if for_update else ""` string literal inside
`get_mining_inventory`'s own `fetchall` call trips `_call_is_fence`, promoting
the helper to an unconditional fence NAME. Every plain call to it (and to
farm's `get_farm`) then classifies "fence", silently masking rule A downstream
of an unlocked read.

Fix (checker-only, zero sb/domain change): skip `has_for_update_param`
functions in the propagation loop — a lockable read fences only at call sites
passing `for_update=True`, judged per call site. The now-surfaced
`_record_repair` rule-A finding is dispositioned as a verified-safe ALLOWLIST
row (ownership read only gates a refusal; the cost-sizing wear read + debit
sit behind `lock_workshop_slot`; proven red-then-green in
`tests/integration/test_mining_repair_race.py`). Regression pins added to
`tests/unit/invariants/test_check_money_race.py`.
