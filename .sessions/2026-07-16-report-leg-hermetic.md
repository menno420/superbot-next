# 2026-07-16 — report-leg banner test made hermetic (sever live-Postgres dependence)

> **Status:** `complete`

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

Closed out 2026-07-16T02:28:06Z. PR #501 (READY at open), commits
4d1fec0 (born-red card + claim) → 3d9a4ed (fix) → this flip.

- Repro (pre-fix, Postgres 16 cluster up via `pg_ctlcluster 16 main
  start`, superbot role/db created, `psql "$DATABASE_URL" -c "SELECT 1"`
  → 1): the single test ran until killed at the 150s cap —
  `timeout 150 python3 -m pytest …::test_report_leg_prints_full_corpus_banner -x -q`
  → `Terminated` (exit 143); a second run with `-s` printed NOTHING for
  60s before its kill. Direct probe:
  `rgp._replay_binding()` → `binding: BOUND | reason: ''` — the leg
  binds and replays instead of exiting 1 in <1s, exactly the #457 card's
  diagnosis.
- Single test with DB UP (post-fix):
  `1 passed in 0.13s` (wall 0.392s, same live cluster).
- Cluster stopped (`pg_ctlcluster 16 main stop` → exit 0; connect now
  refused). Full suite, the CI invocation (`python3 -m pytest tests/
  -q`): `3160 passed, 29 skipped, 1 warning in 66.92s (0:01:06)`.
  (Bare `python3 -m pytest -q` from the repo root additionally collects
  `examples/superbot-plugin-hello/tests/`, which import-errors on the
  uninstalled example package — environmental, outside every CI job's
  path; all three workflows run `pytest tests/`.)

## 💡 Session idea

`run_report`'s replay phase is a silent black box: during the repro,
`pytest -s` printed zero bytes for a full 60 seconds — `_replay_corpus`
(tools/run_golden_parity.py) accumulates all 523 results inside one
`asyncio.run(...)` and every per-case line prints only after the whole
corpus finishes, so a bound-in-the-wrong-env run is indistinguishable
from a hang until ~7 min elapse. Guard recipe: a one-line
per-subsystem progress print inside `_replay_corpus` (or a
`--progress` flag on tools/run_golden_parity.py) would make any future
mis-bound invocation self-diagnosing in seconds; pin with a capsys
test in tests/unit/parity_gate/test_check_parity_depth.py asserting
the progress line renders under a stubbed `_replay_corpus`.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-16-conform-sweep-457.md` @
`claude/conform-sweep-457` (PR #500). Model discipline: it hit this
live-DB footgun mid-sweep (had to stop its own cluster to get the
CI-shaped pytest result), and instead of scope-creeping a test fix into
a 31-golden re-mint PR it filed a precise guard recipe — function,
file, line, the sibling monkeypatch idiom, the exact stub tuple — in
its 💡 section. This session executed that recipe in minutes with zero
re-derivation: the anchors were all correct on first read. That is the
.sessions/README.md guard-recipe doctrine working exactly as designed;
symptom-only would have cost a grep pass through the parity driver.
