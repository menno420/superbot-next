# 2026-07-18 — fold the metric union into one canonical ALL_METRICS seam

> **Status:** `complete`

- **📊 Model:** opus-4.8 · small · kernel refactor

## Scope

Follow-up flagged by the D4 P1 outbox-metrics slice (#562, its `💡 Session
idea`): the metric registry is built by unioning the two metric-family groups
(`METRICS + OUTBOX_METRICS`) at the composition root, and
`tools/check_metric_cardinality` re-derives the same union independently to
validate it. Two sites, one invariant — a third family group added later must
be threaded into both in lockstep or the live registry and the checked set
silently drift apart.

Fold the union into a single canonical `ALL_METRICS` tuple that both the
composition root and the cardinality guard import, so the two consumers can
never disagree.

Pure, behaviour-preserving refactor: same families registered, same set
validated. No metric added, removed, or renamed; no semantic change; no
dependency change.

## What landed

- **Canonical seam** — `ALL_METRICS: tuple[MetricSpec, ...] = METRICS +
  OUTBOX_METRICS` defined once in `sb/kernel/outbox/metrics.py`, alongside
  `OUTBOX_METRICS` where the module docstring already framed the union. Homed
  at kernel level because `sb/spec` cannot import the kernel-band
  `OUTBOX_METRICS` (spec→kernel edge is forbidden); the outbox module already
  imports spec (`METRICS`), so the fold is a clean kernel→spec edge with no
  backward band import (avoids observability K0 → outbox K4).
- **Composition root** — `sb/app/main.py` now imports `ALL_METRICS` and calls
  `build_registry(ALL_METRICS)` instead of re-deriving `METRICS +
  OUTBOX_METRICS`.
- **Cardinality guard** — `tools/check_metric_cardinality.py` imports
  `ALL_METRICS` from the kernel rather than re-deriving it; the checked set is
  now the registered set by construction (same tuple object).
- **Drift-guard test** — three assertions in `tests/unit/kernel/
  test_outbox_metrics.py`: `ALL_METRICS == METRICS + OUTBOX_METRICS` (no family
  lost/duplicated); the guard's `ALL_METRICS` is the *same object* the kernel
  exports and is `check()`'s default; the composition root imports the seam and
  builds from it with no re-derived union surviving.

Flag (decide-and-flag): homed the seam in `sb/kernel/outbox/metrics.py` rather
than `sb/kernel/observability/metrics.py` — the latter (K0) importing
`OUTBOX_METRICS` (K4) would be a backward band edge, whereas outbox already
imports spec `METRICS` and its docstring already owns the union relationship.

## Verification

- `python3 -m pytest -q --ignore=examples` → **3493 passed, 29 skipped**
  (baseline 3490 + 3 new drift-guard tests).
- Guards clean, no new fires: `check_metric_cardinality` (51 families,
  unchanged), `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`.
- No dependency files touched (requirements/lock/pyproject) — pip-audit surface
  unchanged.

## 💡 Session idea

The same fold pattern applies to any other place where two sites re-derive a
declared registry union — an `assert_single_source` micro-guard (checked set
`is` the registered object, as this card's test does for metrics) could be a
reusable convention wherever a spec tuple feeds both a runtime builder and a CI
gate.

## ⟲ Previous-session review

The motivating D4 P1 card (#562) closed cleanly and explicitly parked this fold
as its `💡 Session idea` ("a future third metric tuple can't drift
live-vs-checked") — this slice is the direct discharge of that flag, and its
`test_default_registry_leaves_outbox_families_dark` class-killer still holds
untouched (the fold changed how the union is *sourced*, not what it contains).
