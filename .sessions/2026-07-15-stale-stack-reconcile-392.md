# 2026-07-15 — stale-stack reconcile: PR #392 additive merge

> **Status:** `complete`

- **📊 Model:** fable-5 (Claude Fable family) · stale-stack reconcile
  PR #392 (additive merge, worker lane)

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

## What landed

Merge commit `1cf1859` — `origin/mining-write-parity-wp3` @ `ade9e69`
(confirmed still the tip at push time) folded into
`claude/energy-slice-3`. All 6 conflicts resolved by union + re-summed
pins: corpus 501/507 → **508** on disk (`parity/goldens/*/*.json`),
`minted_goldens` 39/45 → **46** (465 imported + 46 − 3 retired = 508;
recounted from disk, never hand-adjusted). The 9 WP-2/WP-3 mining write
goldens existed on both sides byte-identical (the wp-stack-reconcile
lane's re-mints) and merged silently. ops.py/service.py conflicts were
docstring-only — merged truth: wp3's grid ``mining.dig`` (which already
carries the full oracle energy bracket) AND slice-3's fastmine energy
spend are both live; refusal copy verified verbatim against the oracle
clone's `disbot/services/mining_workflow.py dig()`. Also fixed the
slice-3 parity.yml ledger line's `+5` → `+1` (one refusal golden).

## Verification

- `python3 -m pytest tests/ -q`: **3117 passed, 18 skipped** (78s).
- `python3 tools/check_parity_depth.py`: OK — 49 subsystems (49
  ported), kernel ported, **508 goldens**.
- `python3 tools/run_golden_parity.py --gate` (local Postgres 16 per
  the CAPABILITIES recipe): **gate: GREEN — all 508 golden(s) across
  50 ported subsystem(s) replay clean**.
- `python3 tools/run_golden_parity.py --report`: **report: GREEN —
  full-corpus parity.**
- `python3 -m pytest tests/integration -q`: **16 passed**.
- Count-pin files: 46/46 pass DB-down (the CI unit-env condition).
  With the local replay Postgres still up,
  `test_report_leg_prints_full_corpus_banner` fails (`run_report()`
  returns 0 — the corpus actually replays green — where the unit test
  pins the no-binding exit 1): environmental, pre-existing design,
  not a merge defect.

## 💡 Session idea

`test_report_leg_prints_full_corpus_banner` pins `run_report() == 1`
on the assumption a unit env has no replay binding — but any seat with
a live `DATABASE_URL` (the golden-harness recipe itself creates one)
flips it into a 5-minute full replay that then "fails" by succeeding.
A one-line guard — monkeypatch `DATABASE_URL` away (or pin the replay
binding to None) inside that test — would make the pin hermetic to the
seat it runs in. Guard recipe: `TestGateDriver.
test_report_leg_prints_full_corpus_banner`,
`tests/unit/parity_gate/test_check_parity_depth.py:625`, target
`python3 -m pytest tests/unit/parity_gate/ -q` with a live
DATABASE_URL exported.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-order-022-verify-1-5.md`, PR #472.) The
verify-first posture paid off twice — catching #464's title-only
"work" and the audit's wrong ⚑8-withdrawal citation — and its
CAPABILITIES pointers (pip pytest recipe, local-Postgres route) were
exactly what this session needed and both held. One gap: its 💡
`claims-terminal` idea named the symptom well but shipped no guard
recipe anchors for the checker change itself, so the next lane still
starts from a grep.
