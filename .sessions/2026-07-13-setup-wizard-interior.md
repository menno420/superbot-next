# 2026-07-13 — setup wizard interior (ORDER 017 night-run slice)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice · mandate: ORDER 017 item 1
  (top gap 2: "setup wizard interior — the whole interactive wizard is
  pending")

## Scope

Arm the setup wizard's interior — the 10 pending panel actions + 1
selector counted by `docs/status/completeness-table-2026-07-13.md`
(`sb/domain/setup/panels.py:125-128`) plus the `/setup-skip` /
`/setup-unskip` mark-skipped write (`handlers.py:207-221`) and the
`/setup-reset` clearing branch — faithful to the oracle
(menno420/superbot: `views/setup/depth_panel.py`,
`views/setup/essential_setup.py`, `views/setup/hub.py`,
`views/setup/ai_review/main_panel.py`, `cogs/setup_cog.py`), keeping
every golden-pinned open-render byte identical (no golden drives a
click on any of these components — the module's own pin).

Named successors stay honest terminals: the essential flow's steps 2–8,
the per-section flows behind the hub's section buttons, the
per-suggestion Edit modal/repick flow, and the final-review apply lane.

## What shipped

_(written at close-out)_

## 💡 Session idea

_(written at close-out)_

## ⟲ Previous-session review

Previous night-run slice (completeness table, PR #326) produced the gap
ledger this slice consumes — its row for `setup` counted the exact
surfaces armed here, and its "zero unregistered refs" sweep result held
when this session re-ran `ENSURE_REFS` over the setup manifest. Its
watch-item about `.substrate/guard-fires.jsonl` dirt is honored below
(restored before every commit).
