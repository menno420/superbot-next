# superbot-next · status
updated: 2026-07-09T12:07Z
phase: live-testing phase — rebuild complete (49 PRs, ~1000 unit tests, 575 sim pins, 465 parity goldens all pending); CUT-1 composition root boots (`python3 -m sb`); testing ledger step 1 (kernel boot) PASS, steps 2–9 pending (docs/status/testing-report-2026-07-09.md)
health: red-by-design (golden-parity workflow red on every main run while all 465 golden rows are `pending` — flips as live-testing bands pass). Secondary: latest main commit's non-required `checkers` job fails at "Kit check --strict" (docs-hygiene class; tests / pip-audit / lockfile-fresh all green)
last-shipped: #55 — seeded docs/status/testing-report-2026-07-09.md (9-step per-subsystem live-testing ledger)
blockers: stale 78-command remote tree on the test app (app-command registration unbuilt; leg C compare-only); SB_INTENT_*_OK privileged-intent approvals needed before message-band passes; auto-merge "branch up to date" friction under concurrent PRs
orders: acked= done=
⚑ needs-owner: privileged-intent approvals for the test app (per docs/status/testing-report-2026-07-09.md)
notes: docs/current-state.md is an unrendered substrate-kit template (unfilled ${...} slots) — real status lives in docs/status/. Manager recon grounded in README, docs/status/testing-report + rebuild-completion-report, PRs #49–#55, Actions runs @ main 1c6d3a3.

⟵ manager-seeded starting point — superbot-next, overwrite this with your own status on your first run.
