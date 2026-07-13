# Fishing bait-only fill — coordinated lane fill claim — `fishing-bait-only`

> **CLAIM (2026-07-13)** — bait-only fill of the fishing gear rung,
> branch `claude/fishing-bait-only`. NOT a new lane: the fishing port
> lane belongs to the #324 claim (`fishing-port-remaining.md`, earlier
> at HEAD — its whole-lane claim covers all 13 remaining `_pending`
> fishing commands including `bait`). This is the coordinator-adjudicated
> re-scope of PR #328 (2026-07-13): #328's rod half is CEDED to the
> lane's landed #330 (`4493cc2`); its bait half — verified NOT in the
> lane's pipeline at claim time (no open PR / `claude/*` branch carries
> bait) — lands here as a coordinated fill so the surface isn't built
> twice. The #324 claimant owns the lane; on any collision with a lane
> slice that starts bait, the earlier-at-HEAD lane claim wins and this
> branch stands down.

**Scope.** The `bait` command + bait shop panel ONLY: `sb/domain/fishing/
bait.py`, the `fishing_bait` store + migration 0050, the `fishing.buy_bait`
op, the bait panel + hub repoint, `goldens/_unmapped/sweep_bait.json`
re-home, manifest/service/burn-down bait entries. EXCLUDES rod (landed,
#330) and the craft*/structure surfaces (the lane's next rungs).

- `fishing-bait-only` · **bait command + bait shop — coordinated fill per coordinator adjudication 2026-07-13 (cede rod to #330; re-scope #328 to bait-only)** — salvaged from `claude/fishing-slice2-rod-bait` @ `3ced297`, adapted to main's #330 shapes · sb/domain/fishing/bait.py, sb/domain/fishing/{store,ops,service,panels}.py, sb/manifest/fishing.py, migrations/0050_fishing_bait.sql, parity/goldens/fishing/sweep_bait.json, parity/parity.yml · 2026-07-13
