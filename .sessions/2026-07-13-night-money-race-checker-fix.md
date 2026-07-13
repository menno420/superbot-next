# 2026-07-13 — check_money_race: conditional-FOR-UPDATE ownership SELECT mis-classification fix (ORDER 019 item 3)

> **Status:** complete

- **📊 Model:** `fable-5` · ORDER 019 item 3 (night lane) · claim:
  control/claims/night-money-race-and-doctrine-doc.md (PR #422)

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

## Close-out

Landed as PR #425 (head e6405fe + this flip). Fix verified red-then-green:
with the `_fence_fixpoint` change stashed, 3 of the 4 new pins fail
(`fence_names` membership, missing rule-A finding, stale allowlist row);
green with it. Full `pytest tests/ -q`: 2871 passed, 15 skipped.
`check_money_race`: OK, 2→3 allowlisted sites, still exit 0. Zero `sb/`
change. Decision flagged: the surfaced `_record_repair` rule-A finding is
ALLOWLISTED (verified safe — the ownership read never sizes the settle),
not KNOWN_RISKS — the checker's own ledger doctrine says allowlist is for
sites verified safe against source, and the repair race test proves it.

## 💡 Session idea

`_strings_under` feeds a function's ENTIRE literal pool (docstrings
included) into `sql_locks` / `_is_select`, so a docstring that merely
*mentions* "FOR UPDATE" (get_mining_inventory's does) marks the function
sql-locking — today masked by the `has_for_update_param` guards, but any
future param-less helper with a lock-discussing docstring would silently
become a fence name. A follow-up could restrict lock/SELECT classification
to literals that appear inside DB_CALL_NAMES call arguments (the CallSite
sql already exists) and drop the whole-function literal sweep; pin with a
fixture whose docstring says "FOR UPDATE" but whose SQL never does.

## ⟲ previous-session review

The previous session's card (2026-07-13-setup-compound-1.md, PR #419) is a
model close-out: it names its two ported ops, ledgers the shared-id gap it
could not honor through the K7 seam instead of faking it, and its 💡 idea
(record the once() outcome AFTER effect legs) is a real engine-shaped
follow-up with a concrete guard recipe. One nit: its Status badge wraps the
word in backticks (`` `complete` ``) where this repo's gate greps the bare
marker — worth normalizing so card-format drift never trips the born-red
gate.
