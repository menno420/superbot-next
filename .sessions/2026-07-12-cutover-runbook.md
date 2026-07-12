# 2026-07-12 — CUT-2/CUT-3 cutover runbook consolidation + tooling wiring (SLICE 4)

> **Status:** `in-progress`

- **📊 Model:** Claude Opus 4.8 · high · docs/runbook + tooling wiring (Q-0194 / ORDER 012)

## Scope

Owner-directed (production lane, 2026-07-12): deliver ONE authoritative
cutover runbook that consolidates the CUT-2 and CUT-3 steps that today
exist only as scattered checklist items
(`docs/status/rebuild-completion-report-2026-07-09.md` §3(d) items 32–33),
plus the SLICE-4 tooling wiring the test plane allows:

1. `docs/operations/cutover-runbook.md` — preconditions/HARD GATES, CUT-2
   (import dry-run, reaction-capture window, live permission census,
   verify-import, public→private flip), CUT-3 (same-app-id token swap,
   `platform.cutover_flip_ts` write-once, N=7d rollback window, A-18
   coverage-debt publication, day-8–10 checklist), a ROLLBACK section, and
   a per-step OWNER (⚑) vs AGENT ownership table.
2. Tooling wiring: exercise `tools/check_verified_live.py --debt-list`,
   commit its output as a dated status artifact; investigate the
   permission-census live-GET wiring gap; drive verify-import as far as the
   test plane allows.

## What shipped

(filled at close)

## 💡 Session idea

(filled at close)

## ⟲ Previous-session review

(filled at close — covers the previous-session review requirement.)
