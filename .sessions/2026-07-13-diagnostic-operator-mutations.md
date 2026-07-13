# 2026-07-13 — diagnostic operator mutations (ORDER 017 fix slice)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1 follow-up (completeness table `docs/status/completeness-table-2026-07-13.md`, diagnostic row)

## Scope

Bring the diagnostic subsystem's 10 pending panel actions + 2 pending
selectors to production-ready (implemented + tested + golden-parity
preserved + final user-facing copy): the flag-manager mutations
(`pf_flag_pick` select + Enable/Disable), the automation-panel
mutations (`pf_auto_rule` select + Enable/Disable/Delete), the
Diagnostics-hub process-state trio (Bot Status / System Info / Recent
Errors), and the `!list_commands_detailed` ◀ Prev / Next ▶ paging
(pages 2–14). Port oracle: menno420/superbot (read-only clone at
/workspace/superbot). Existing diagnostic goldens (subsystem is
`ported` in parity/parity.yml) must stay byte-green on the bare opens.

## What shipped

_(to be filled at close-out)_

## 💡 Session idea

_(to be filled at close-out)_

## ⟲ Previous-session review

Previous session (completeness table, PR #326) produced the exact map
this slice executes against — the diagnostic row's citation
(`sb/domain/diagnostic/handlers.py` `*_pending`) resolved in seconds,
no re-derivation needed; that is the table doing its job. Its card
also carried forward the `.substrate/guard-fires.jsonl` dirt warning —
honored here (restore before committing).
