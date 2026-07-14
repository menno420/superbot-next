# 2026-07-13 — manifest.snapshot.json stable_hash merge-conflict mitigation

> **Status:** `complete`

- **📊 Model:** `fable-5` · lane-worker slice · mandate: land a durable
  mitigation for the recurring merge-conflict class where the volatile
  `stable_hash` line of `manifest.snapshot.json` re-conflicts any two
  concurrent PRs that both recompiled the snapshot (hit PRs #333 and #352
  on 2026-07-13).

## 💡 Session idea

Any two concurrent PRs that both ran `tools/manifest_compile.py --write`
textually conflict on the single `stable_hash` line even when their body
hunks are disjoint — the line encodes a whole-body digest, so it changes on
EVERY recompile. The manual recipe (merge main in, rerun
`tools/manifest_compile.py --write`, commit) is pure re-derivable toil.

Mechanism chosen (decide-and-flag, evaluated a/b/c/d):

- **(a) `.gitattributes` merge=union — ruled out with evidence:** a local
  three-way merge on a scratch copy with two branches changing the
  `stable_hash` line differently keeps BOTH hunks → duplicate keys +
  missing comma → `json.decoder.JSONDecodeError` (syntactically invalid
  file). Union is line-append semantics; JSON is not.
- **(b) custom merge driver — ruled out:** needs git config on every clone
  (no repo bootstrap installs one — verified, zero hits for
  `merge.driver`/`git config` outside kit machinery) and GitHub's
  server-side merge ignores repo merge drivers (verified live in this repo
  2026-07-12, scratch PR #315 — `docs/operations/telemetry-merge-conflicts.md`).
- **(c) PRIMARY — stop emitting `stable_hash` into the tracked snapshot:**
  the hash membership (frozen spec 01 §5 fork 9) already EXCLUDES
  `stable_hash`, so the field is a pure cache of a value derivable from the
  rest of the file. P9 / boot leg A now recompute the committed body's hash
  via `compute_stable_hash(committed_snapshot)` and compare against the
  source recompile — drift detection power is unchanged, every existing
  hash value stays identical, and the always-conflicting line disappears.
- **(d) COMPANION — runbook:** residual conflicts (real body-hunk
  collisions) keep the one true recipe — merge main, rerun
  `tools/manifest_compile.py --write`, commit — documented in
  `docs/operations/manifest-snapshot-conflicts.md`; trap 10(e) pointer
  updated.

## previous-session review

Boot ritual: synced to origin/main HEAD `d7b18b2` (fishing cast-leg depth
wiring, #373). HANDOFF.md not present at HEAD. Overlap check before work:
no entry in `control/claims/` and no open PR covers a manifest-merge
mitigation (open PRs at check time: #312 #317 #320 #335 #344 #371 #384 —
all mining/energy parity lanes). The mineverse lane flagged this conflict
class but did not claim the fix.

## Close-out

Delivered on PR #386 (branch `claude/manifest-conflict-mitigation`, base
main @ `d7b18b2`):

- `tools/manifest_compile.py` — `full_snapshot` no longer carries
  `stable_hash`; P9 recomputes the committed BODY's hash via
  `compute_stable_hash(committed)` (ignores a legacy field — old branches
  verify unchanged). Recompiled digest identical before/after
  (`sha256:93022897…`), proving the pure-cache claim.
- `sb/domain/platform/consistency.py::_collect_manifests` — recomputes the
  fingerprint from the body (tools/ not importable from sb/domain; inline
  mirrors `compute_stable_hash`, MUST stay in sync).
- Tests — drift tests tamper the body (`schema_version`), new pins:
  no-field-in-snapshot, legacy-field-tolerated, hash-ignores-injected-field.
- `manifest.snapshot.json` recompiled — the diff is exactly the one
  removed line.
- Runbook `docs/operations/manifest-snapshot-conflicts.md` + trap 10(e) +
  telemetry-runbook cross-refs.

Verification: `python3 -m pytest tests/ -q` → 2464 passed, 13 skipped;
`python3 tools/manifest_compile.py` verify green; check_namespace /
check_symbol_shadowing / check_no_skip / check_config_usage /
check_doc_cites / check_escape_hatches / check_schema_growth /
check_amendments / check_runtime_smoke all clean. Scratch-repo three-way
merge demo: old file + disjoint hunks → CONFLICT; new file → clean merge.

Guard recipe: if a future consumer needs the snapshot's hash at runtime,
compute it (`compute_stable_hash` in `tools/manifest_compile.py`, or the
inline mirror in `sb/domain/platform/consistency.py::_collect_manifests`)
— never re-add a cached hash line to the tracked file
(`tests/unit/app/test_main_wiring.py::TestSnapshot` pins its absence).

CI note: first run's `sim-gate` + `manifest-validate` jobs died on a
GitHub Actions infra error ("Failed to resolve action download info.
Error: Service Unavailable" — zero workflow steps executed); a
rerun-failed-jobs pass turned both green with all steps real.
