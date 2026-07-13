# Claim — curation REWORK night bundles (ORDER 019 item 2, night lane)

- `claude/curation-night-1` · **Rows 45 + 59 + 60 — mining mine-grid + how-to** — port the oracle grid Mine navigator (row 45 `mine`: flip `mine_route` off the BLOCKED capture byte onto the navigator panel; row 59: retire `mining.grid_view_pending`) and the static how-to copy (row 60: retire `mining.how_to_pending`) · area: `sb/domain/mining/panels.py`, `sb/domain/mining/service.py`, mining tests · 2026-07-13
- `claude/curation-night-2` · **Row 2 — `btd6.ctteam.set_team` modal** — modal feeding the existing typed ctteam set leg (`cmd_ctteam`), retiring `btd6.ctteam_set_pending` · area: `sb/domain/btd6/panels.py`, `sb/domain/btd6/`, btd6 tests · 2026-07-13
- `claude/curation-night-3` · **CONDITIONAL: row 72 + farm goldens** — rps_tournament quickplay bet-settle golden + farm goldens x3 (farm_collect / farm_buy_hen / farm_upgrade_coop) via `tools/mint_golden.py` (D-0073) · area: `parity/cases/curated.py`, `parity/parity.yml`, `parity/goldens/`, count-pin tests · 2026-07-13

**Sequencing.** Bundle 3 (row 72 + farm goldens) starts ONLY after the
`wp-stack-reconcile` lane (ORDER 019 item 1) lands — it appends to
`parity/cases/curated.py` and re-pins the `parity/parity.yml` + count-pin
tests that lane is un-conflicting. Until then this claim covers bundles 1–2
only.

**Exclusions.** Row 26 (`pay` golden) is NOT claimed — owned by
`mining-write-parity-lane.md` (its report row says land after WP PRs
#312/#317). Adjacency note: energy-lane slice 3 (fastmine gating) is
route-adjacent to bundle 1 but disjoint (`fastmine_route` vs `mine_route`).

Session note: dispatched night lane. Claimed 2026-07-13T22:41:35Z (UTC).
