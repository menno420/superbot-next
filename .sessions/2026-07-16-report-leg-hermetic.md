# 2026-07-16 — report-leg banner test made hermetic (sever live-Postgres dependence)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable · high effort · test-hermeticity slice
- **Born:** 2026-07-16T02:23:51Z (born-red first commit)

## Scope

Execute the guard recipe filed by the #457 conform-sweep session
(`.sessions/2026-07-16-conform-sweep-457.md` @ `claude/conform-sweep-457`):
`TestGateDriver::test_report_leg_prints_full_corpus_banner`
(tests/unit/parity_gate/test_check_parity_depth.py:647) asserts
`run_report() == 1` relying on NO local Postgres being reachable, but
`_replay_binding` (tools/run_golden_parity.py:57) probes a live
`Harness.start()` — on any box where the CAPABILITIES-recipe Postgres is
still up, the report leg binds, replays the full 523-golden corpus
(~7 min) inside a unit test, returns 0, and the test fails. Every
sibling TestGateDriver test already monkeypatches `_replay_binding` (or
`_load_parity_yml`/`_replay_corpus`); this one is the lone gap.

Fix: monkeypatch `_replay_binding` in that test to return
`(None, "no bot-under-test binding (unit env)")` — the exact sibling
idiom from `test_gate_leg_gates_ported_rows_for_real` — keeping all
three assertions (exit 1, banner substring, "523 goldens"). NO
production code change; `tools/run_golden_parity.py` untouched.

Definition of done: repro captured with a live local Postgres, fix in,
single test passes fast with the DB up, full suite green with the DB
down, PR READY.

Claim: `control/claims/claude-report-leg-hermetic.md` (branch
`claude/report-leg-hermetic`).

## Plan

1. Repro: start the container's Postgres 16 cluster per
   docs/CAPABILITIES.md, run the single test, capture the hang/bind.
2. Fix: add `monkeypatch` to the test signature, stub `_replay_binding`,
   rewrite the stale "no replay binding in the unit env" comment.
3. Verify: single test with DB UP (must pass fast), stop the cluster,
   full `python3 -m pytest -q` (must be green).

## Verification

- Repro (pre-fix, Postgres 16 cluster up, superbot role/db created):
  [[fill:repro-evidence]]
- Single test with DB UP (post-fix): [[fill:single-test-evidence]]
- Full suite (DB stopped): [[fill:full-suite-evidence]]

## 💡 Session idea

[[fill:session-idea]]

## ⟲ Previous-session review

[[fill:previous-session review]]
