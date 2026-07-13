# 2026-07-13 — curation rework night bundle 1: the grid Mine navigator + hub How-to (rows 45 · 59 · 60)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · night lane, ORDER 019 item 2 (curation REWORK
  backlog bundle 1) · mandate: curation report rows 45/59/60
  (`docs/review/curation-report-2026-07-13.md` L987 / L1030 / L1033),
  claim `control/claims/curation-rework-night-bundle.md` (PR #426),
  token `claude/curation-night-1`.

## Scope

Port the oracle grid Mine navigator (`disbot/views/mining/grid_mine_view.py`
+ `utils/mining/grid.py` + the `mining_workflow.dig` seam) and the static
mining How-to panel (`disbot/views/mining/how_to_panel.py`) into the
plugin/manifest architecture:

- row 59 `mining.hub.mi_mine` — retire `mining.grid_view_pending` onto the
  live navigator panel;
- row 60 `mining.hub.mi_how_to` — retire `mining.how_to_pending` onto the
  static How-to panel;
- row 45 `mine` — port the grid-dig deep system (grid module, position +
  fog-of-war persistence, the audited `mining.dig` op).

Adjacency flagged: energy-lane slice 3 (queued) touches
`record_mine`/`fastmine_route` — disjoint routes from this bundle's
navigator work.

## Close-out

(to be written at flip)
