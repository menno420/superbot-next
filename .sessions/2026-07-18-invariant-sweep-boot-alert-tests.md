# 2026-07-18 — cover the two untested InvariantSweepLane paths

> **Status:** `in-progress`

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

(pending)

## Verification

(pending)

## 💡 Session idea

(pending)

## ⟲ Previous-session review

(pending)
