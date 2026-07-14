# 2026-07-14 — mining title-equip write slice (ORDER 022 (a)3)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · ORDER 022 (a)3 EQUIP-WRITE slice · claim
  live via control/claims (PR #471)

## Scope

Port the mining title-equip surface: a state-derived earned-title Select
on `sb/domain/mining/panels.py::mining_titles_spec` (absent when the
player has no earned titles; oracle caps at 10 options so no windowing),
plus an audited equip WRITE handler through the proper seam with
oracle-verbatim validation and response strings. Oracle read pinned at
`menno420/superbot@bbc524e`: `disbot/views/mining/titles_panel.py`,
`disbot/services/title_service.py::equip`,
`disbot/cogs/mining_cog.py::titles_cmd` (panel open only — no command
form). D-0073 goldens for the new surface, canonical stripped flavor;
CAPTURE_WORLD_WEATHER registered first before any capture.

Definition of done: implemented + tested + goldens minted + PR READY
(parked green under coordinator WP-stack freeze; flips after the owner's
WP sweep).

## 💡 Session idea

_(to be filled at close-out)_

## ⟲ Previous-session review

_(to be filled at close-out)_
