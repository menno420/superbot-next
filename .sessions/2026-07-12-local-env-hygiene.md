# 2026-07-12 — local-Postgres env-drift hygiene: reproducible local verification

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · adapter-lane baton item (NEXT-2 item 1, `control/status.md` @ `0a96960`)

## Scope

The last open adapter-lane baton item ("local-Postgres env-drift hygiene",
`control/status.md` NEXT-2 baton @ `0a96960`): make local verification
reproducible. The observed drift class: the local Postgres cluster's
provisioning state varies across sessions/containers — #290's session read
11 red integration/btd6_seed_data tests as a stable fact when it was "local
provisioning state" (corrected in
`.sessions/2026-07-12-live-adapter-landing.md` ⟲ review); the ORDER-004
live-drive session found the cluster "WIPED by a container restart" and
re-derived the recovery by hand
(`.sessions/2026-07-12-order004-live-drive-evidence.md`). Every fresh
session pays a re-derivation tax to stand up roles/DBs/env that CI gets
declaratively from its workflow files.

## What shipped

- `tools/setup_local_env.py` — idempotent, NEVER-destructive local
  provisioning: creates role `parity`/DB `parity_replay` (CI-canonical,
  golden-parity.yml:44-46) + the `superbot`/`superbot` runtime-boot pair
  (order-016 card convention) only if missing; best-effort
  `pg_ctlcluster` start for the container-restart case; prints the CI env
  triple (golden-parity.yml:52-54). `--check` mutates nothing. The only
  mutation ever applied to a pre-existing object is a password re-align
  on the login role when the canonical DSN fails to authenticate.
- `docs/operations/local-verification.md` — the runbook: pip tiers
  exactly as CI installs them (ci.yml:32 / golden-parity.yml:60-63), the
  6-step verification ladder with each step's CI-workflow twin cited,
  and a drift-recovery section. Linked from `docs/current-state.md`.

## Evidence

- Script idempotency: run twice on the provisioned cluster — both runs
  exit 0, second run all "exists" lines, no mutation; CREATE path proven
  on scratch role/DB (created then re-run → "exists"; scratch dropped).
- A LIVE drift instance was caught mid-session: the container's
  `parity_replay` had `schema_migrations` at **48** while main HEAD
  `2bde1c5` ships 47 files (a sibling branch's gate run left the ledger
  ahead). Full suite on the drifted DB: `1 failed, 2045 passed, 13
  skipped` — reproduced identically at a PRISTINE origin/main worktree,
  so it was environment, not diff. Failure chain diagnosed: harness boot
  refuses ("Migration 0048 is recorded as applied but its file is absent
  on disk", `sb/kernel/db/migrations.py:215`) → `tests/integration`
  all-skip → the aborted boot leaves the pool global initialized →
  `tests/unit/kernel/test_db_pool.py::test_get_raises_before_init` reds.
  Recovered per the runbook's non-destructive path (fresh sibling DB via
  the script's own create shape).
- Ladder on the pristine DB (branch head, `date -u` 2026-07-12T23:20Z):
  `python3 -m pytest tests/ -q` → **2057 passed, 2 skipped**;
  `check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  481 goldens`; `run_golden_parity.py --gate` → **gate: GREEN — all 466
  golden(s) across 51 ported subsystem(s) replay clean**;
  `pytest tests/integration -q` → **11 passed**;
  `bootstrap.py check --strict` → passes (only the designed born-red
  card HOLD, cleared by this flip); `check_doc_cites: OK`.

## 💡 Session idea

Make the drift fail CLEAN instead of confusing: in
`tests/integration/conftest.py boot_harness()`, when `Harness.start`
raises `HarnessBootError`, reset the `sb.kernel.db.pool` module global
before `pytest.skip` — today the aborted boot leaves the pool
initialized, so a drifted DB doesn't just skip integration, it also reds
the unrelated unit pin
`tests/unit/kernel/test_db_pool.py::test_get_raises_before_init` in a
full-suite run (the exact shape that produced the "11 known-red tests"
misread). One-line cleanup, kills the whole false-red class; CI never
sees it because the unit job has no asyncpg and the golden-parity job
runs `tests/integration` alone — only local full-tier runs hit it.

## ⟲ previous-session review

The close-out baton (`control/status.md` @ `0a96960`) named this item in
five words with no pointer to what the drift actually was — scope had to
be re-derived from three session cards. The cards themselves were honest
and load-bearing: `2026-07-12-treasury-karma-argv-fix.md` correctly
labelled its 11 reds "local-Postgres environment state, pre-existing, not
this diff" (and proved it at a clean worktree — the right instinct this
runbook now institutionalizes), and `2026-07-12-live-adapter-landing.md`
explicitly corrected the record ("local provisioning state, not a stable
fact — do not copy the known-red entry forward"). What no card carried
was the RECIPE — this session's live re-diagnosis took the same
re-derivation tax the baton was minted to end.
