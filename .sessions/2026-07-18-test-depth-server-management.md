# 2026-07-18 — test-depth coverage for sb/domain/server_management

> **Status:** `in-progress`

- **📊 Model:** [[fill: model line]]

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

- `python3 -m pytest tests/unit -q` → [[fill: verbatim tail]]
- `python3 tools/check_namespace.py` → clean
- `python3 tools/check_no_skip.py` → clean

## Deviation ledger

[[fill: skipped gaps + why, or "none — all 10 gaps landed"]]

## Close-out

[[fill: PR # + URL + test count]]

## 💡 Session idea

[[fill: one idea]]

## ⟲ Previous-session review

[[fill: review of the most recent OTHER .sessions card]]
