# 2026-07-18 — cover the two untested InvariantSweepLane paths

> **Status:** `complete`

- **📊 Model:** opus-4.8 · small · kernel test-depth

## Scope

`sb/kernel/invariants/sweep.py` (S12 — the invariant-fence sweep lane) is a
critical correctness path: it runs the declared data-invariant checks, dispatches
per-violation repairs/quarantines, and gates CUT-2/CUT-3 verified-restore. Its
steady-state `tick()` postures (report-only, epoch dedup, QUARANTINE_ONLY,
REPAIRABLE once-guard, repair-failure quarantine, circuit breaker) and the
`run_verify_import` seam are covered by `tests/unit/invariants/test_s12_invariants.py`.

Two behaviours have **zero** coverage:

1. **`InvariantSweepLane.reconcile_on_boot`** — the ON_BOOT reconciliation entry
   the PollSupervisor calls at the boot ready-gate. Every sibling lane's
   `reconcile_on_boot` (outbox relay, due-queue, draft janitor) is tested; the
   invariant sweep lane's is not. It carries a load-bearing **crash-loop guard**
   (`epoch = int(now.timestamp()) // 3600`) so a restart within the hour does not
   re-sweep, and it must run ON_BOOT-cadence invariants **only** (skip HOURLY/DAILY).
   If a refactor broke it, boot-time reconciliation would silently stop running,
   or a crash-loop would re-sweep every restart — with no test to catch it.

2. **`ALERT_ONLY` severity dispatch** (`_dispatch`, the `Severity.ALERT_ONLY`
   branch) — records a metric/finding and makes **no** state change. The other two
   severities (QUARANTINE_ONLY, REPAIRABLE) are tested; ALERT_ONLY is not.

Test-only slice: no production code touched. Behaviour-preserving — it pins
behaviour that already exists.

## What landed

Two tests appended to `tests/unit/invariants/test_s12_invariants.py`, reusing
the file's existing `env` fixture (fake idem/db/engine ports + installed guild
source) — no production code touched.

- **`test_reconcile_on_boot_runs_on_boot_only_and_crash_loop_guards`** — declares
  an `ON_BOOT` invariant next to a default-`DAILY` one, then drives
  `reconcile_on_boot`. Asserts: only the ON_BOOT invariant sweeps (the DAILY one
  is skipped); a second boot within the same hour is deduped by the
  `epoch = ts // 3600` once() key (no re-sweep — the crash-loop guard); a boot
  two hours later is a new epoch and reconciles again.
- **`test_alert_only_dispatch_records_finding_never_mutates`** — an enforced
  `ALERT_ONLY` violation increments `alerts` and neither quarantines nor repairs
  (the third severity branch, previously untested alongside the covered
  QUARANTINE_ONLY / REPAIRABLE ones).

## Verification

- `python3 -m pytest -q --ignore=examples` → **3495 passed, 29 skipped**
  (baseline 3493 + 2 new tests). The invariants file alone: 12 passed (was 10).
- Guards clean, no new fires: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`.
- No dependency files touched — pip-audit surface unchanged.

## 💡 Session idea

`reconcile_on_boot` and steady-state `tick` diverge on an empty installed guild
source: `tick` falls back to `targets = guilds or (None,)` (scans global), while
`run_verify_import` iterates `tuple(_guild_source())` with no `or (None,)`
fallback — so an installed-but-empty guild source makes verify-import scan
nothing, skipping any global/None-scoped invariant that the live sweep would
still check. Worth a follow-up to confirm which behaviour is intended and align
them (left untouched here — a behaviour question, not a test gap).

## ⟲ Previous-session review

The prior card (`canonical-all-metrics-seam`, #565) landed a clean behaviour-
preserving seam and flagged an `assert_single_source` micro-guard convention as
its idea; this slice is unrelated (test-depth, not a seam) but shares its
posture — pin real behaviour, touch no production code, keep the change fully
reversible.
