# 2026-07-18 — test-depth coverage for sb/domain/server_management

> **Status:** `complete`

- **📊 Model:** Opus 4 family · high · test-depth

## Scope

Test-depth (characterization) coverage for `sb/domain/server_management` —
additive, DB-free unit tests only. **NO production code changes, NO
golden, NO migration.** Pins the lanes the slice-A/B suites
(`test_band6_access_map.py` / `test_band6_help_preview.py`) left
uncovered:

- **P1 — the erasure/tombstone lane** (MEMBER_ID compliance path, zero
  prior coverage): `ops._tombstone_policy_actor` scrubs the subject's
  `actor_id`→NULL, keeps the policy rows, audits the affected count;
  `routing.tombstone_policy_actor`'s `rsplit` command-tag parse returns
  the int on `UPDATE N` and 0 on a malformed/None tag (the
  `except (ValueError, TypeError): return 0` arm).
- **P2 — `routing.record_set_policy` refusal + coercion**: empty
  `cog_name` → the copy-only refusal *before* any store touch;
  `enabled="false"` → coerced False (and any other string → the
  default-True posture) reaching the upsert verbatim.
- **P3 — access-projection DENY/unknown fail-closed edges**:
  `_axis_command_access` R-16 `role_not_held` deny reason_code +
  `bootstrap_bypass` allow-detail; `_axis_governance` no-member →
  `unknown` (and the composed effective → unknown, never a false allow);
  `_axis_help_visibility` no-category-mapping → `unknown`.
- **P4 — routing read + fail-closed guards**: `routing.list_for_guild`
  ORDER BY (scope_type, cog_name, scope_id NULLS FIRST);
  `help_preview._is_help_hidden` invalid-tier → True (fail closed);
  `routing.is_cog_enabled` category-only (channel=None) short-circuit.

New file: `tests/unit/band6/test_band6_server_management_depth.py` (the
band6 server_management test home). The tombstone/store legs monkeypatch
the module-bound `routing.execute`/`routing.fetchall` over an in-memory
table (the band5 `test_tombstone_erasure_body` direct-call pattern); the
projection axes monkeypatch the ported owners (the band6 `_patch_owners`
pattern).

## Verification

- `python3 -m pytest tests/unit -q` → `3356 passed, 2 skipped, 1 warning
  in 60.57s` (the 2 skips pre-exist — `check_no_skip` is clean; the new
  file alone: `16 passed in 0.19s`).
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface
  funnels through resolve())`

## Deviation ledger

**None — all 10 gaps landed** (16 test functions; a couple gaps carry a
paired positive/negative assertion so the count exceeds 10). One anchor
required a monkeypatch the gap list did not name: gap 7
(`_axis_help_visibility` no-category → unknown) is UNREACHABLE with the
real category functions — `category_for_subsystem` always returns a valid
key (falling back to `OTHER_CATEGORY.key`), so `category_by_key` never
returns `None` on live data. The `if category is None` arm is a
defensive guard; the test pins it by monkeypatching
`categories.category_by_key` → `None`, flagged inline. All other gaps
drive real code paths (real store fn + real `rsplit` parse for the
tombstone lane; real axis/resolver logic elsewhere).

## Close-out

PR **#540** — https://github.com/menno420/superbot-next/pull/540 · one
new file `tests/unit/band6/test_band6_server_management_depth.py`, **16
DB-free test functions** covering all 10 gap-list anchors. Additive
only: no product code, no golden, no migration. Commits: `b8cd559`
(born-red card + claim), `0b36508` (tests). Opened ready/non-draft;
server-side lander merges on green (not self-merged).

## 💡 Session idea

The tombstone lane's command-tag parse
(`routing.tombstone_policy_actor`: `int(str(result).rsplit(" ",1)[-1])`)
is a **duplicated idiom** — the governance `tombstone_subject_*` twins
parse the same `UPDATE N` shape by hand, each with its own
`except (ValueError, TypeError): return 0`. A single
`sb/kernel/db/pool.rows_affected(command_tag) -> int` helper would
collapse every erasure body's parse to one audited call site and let the
next MEMBER_ID store inherit the fail-closed-to-0 behavior for free
instead of re-deriving it. Guard recipe: grep `rsplit(" ", 1)` under
`sb/domain/*/routing.py` + `sb/domain/governance/store.py`; land the
helper + a `tests/unit/db/` pin, then swap the two existing call sites.

## ⟲ Previous-session review

Reviewed the predecessor `.sessions/2026-07-18-setup-launcher-wizard-
except.md` (PR #538, closing backlog C1 — the setup-band except-density
audit). It's the same posture as this slice: an additive, DB-free,
zero-product-change characterization pin that forces each guarded call to
raise and asserts the intended boundary (fail-closed refusal vs.
fail-soft degrade vs. logged-best-effort), mirroring a sibling harness.
Its audit-finding discipline — classifying every swallow as
CLOSED/SOFT/best-effort with the exact line anchor — is worth carrying
forward; this slice applied the same "assert the SPECIFIC branch value"
rigor one domain over (server_management's erasure + projection edges
rather than setup's except boundaries), pinning `deny`/`unknown` vs. a
false `allow` and the scrubbed-value/row-count rather than a swallow's
degrade shape. Confirms the current rhythm holds: small, contained,
new-test-only slices that each pin one unverified behavior class.
