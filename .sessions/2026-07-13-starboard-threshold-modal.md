# 2026-07-13 — starboard threshold modal port (ORDER 017 night-run fix slice C)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice C · mandate: ORDER 017
  (PR #323), gap row 11 of `docs/status/completeness-table-2026-07-13.md`

## Scope

Retire the last starboard pending terminal: the config panel's
✏️ Threshold button (`starboard.panel_threshold`,
`sb/domain/starboard/panels.py:296`) becomes the shipped
`_ThresholdModal` G-10 form (ORACLE
disbot/views/starboard/config_panel.py) — one required numeric field,
submit runs the existing audited `starboard.configure` op preserving
channel/emoji/self-star, error copy verbatim ("❌ Threshold must be a
whole number."), the unconfigured guard copy verbatim ("Set a
hall-of-fame channel first (pick one below).").

Definition of done: implemented + tested + golden-parity
(goldens/starboard/sweep_starboard_panel bytes unchanged) + real error
copy + final user-facing copy.
