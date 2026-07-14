# Claim — curation REWORK night bundles (ORDER 019 item 2, night lane)

- `claude/curation-night-1` · **LANDED** · **Rows 45 + 59 + 60 — mining mine-grid + how-to** — ported the oracle grid Mine navigator (row 45 `mine`: grid system live behind the hub; row 59: retired `mining.grid_view_pending`) and the static how-to copy (row 60: retired `mining.how_to_pending`) · landed via PR #434, merged to main as `9f863a1` · 2026-07-13
- `claude/curation-night-2` · **LANDED** · **Row 2 — `btd6.ctteam.set_team` modal** — modal feeding the existing typed ctteam set leg (`cmd_ctteam`), retired `btd6.ctteam_set_pending` · landed via PR #428, merged to main as `7fdd682` · 2026-07-13
- `claude/curation-night-3` · **PARKED** · **CONDITIONAL: row 72 + farm goldens** — rps_tournament quickplay bet-settle golden + farm goldens x3 (farm_collect / farm_buy_hen / farm_upgrade_coop) via `tools/mint_golden.py` (D-0073) · area: `parity/cases/curated.py`, `parity/parity.yml`, `parity/goldens/`, count-pin tests · still pending the `wp-stack-reconcile` lane — #312/#317/#371 all open as of 2026-07-13T23:5xZ (checked) · 2026-07-13

**Sequencing.** Bundle 3 (row 72 + farm goldens) starts ONLY after the
`wp-stack-reconcile` lane (ORDER 019 item 1) lands — it appends to
`parity/cases/curated.py` and re-pins the `parity/parity.yml` + count-pin
tests that lane is un-conflicting. Bundles 1–2 are done; this claim stays
ACTIVE for bundle 3 only.

**Bundle-3 takeover (2026-07-14).** Row 72 + its farm goldens are now being
executed under ORDER 022 (a)4 via the branch-from-#371-head path (see
`order-022-titleequip-row72.md`), superseding the "after wp-stack-reconcile"
sequencing above.

**Bundle 1 residue (handed off, not claimed here).** Row 45's `!mine`
prefix-byte flip (off the `sweep_mine.json` capture artifact) and durable
grid position/fog state both remain `parity/parity.yml`-walled — handed to
the wp-stack/owner lane with exact recipes in
`.sessions/2026-07-13-curation-night-1.md`.

**Exclusions.** Row 26 (`pay` golden) is NOT claimed — owned by
`mining-write-parity-lane.md` (its report row says land after WP PRs
#312/#317). Adjacency note: energy-lane slice 3 (fastmine gating) is
route-adjacent to bundle 1 but disjoint (`fastmine_route` vs `mine_route`).

Session note: dispatched night lane. Claimed 2026-07-13T22:41:35Z (UTC).
Bundles 1–2 marked LANDED 2026-07-13 (night ledger wrap-up).
