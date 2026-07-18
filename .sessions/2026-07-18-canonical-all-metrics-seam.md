# 2026-07-18 — fold the metric union into one canonical ALL_METRICS seam

> **Status:** `in-progress`

- **📊 Model:** _pending_

## Scope

Follow-up flagged by the D4 P1 outbox-metrics slice (#562): the metric registry
is built by unioning the two metric-family groups (`METRICS + OUTBOX_METRICS`)
at the composition root, and `tools/check_metric_cardinality` re-derives the
same union independently to validate it. Two sites, one invariant — a third
family group added later must be threaded into both in lockstep or the live
registry and the checked set silently drift apart.

Fold the union into a single canonical `ALL_METRICS` tuple that both the
composition root and the cardinality guard import, so the two consumers can
never disagree.

Pure, behaviour-preserving refactor: same families registered, same set
validated. No metric added, removed, or renamed; no semantic change; no
dependency change.

## What landed

_pending_

## Verification

_pending_

## 💡 Session idea

_pending_

## ⟲ Previous-session review

_pending_
