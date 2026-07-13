# superbot-next · status
updated: 2026-07-13T22:28:36Z
phase: EAP FINAL NIGHT — coordinator seat OPEN, night ORDER 019 ACKED and being worked top-down (owner kickoff live 22:2xZ).
health: main at `605db5a88e553f6f4317ba4bf40293d143ac8168` — today landed: energy lane, curation remainder, churn fixes, hygiene, fence #394, setup wizard complete (7 slices), settings-admin complete, completeness remainders complete, tooling #415/#416, compound-ops slice 1 #419. golden-parity report leg green.
kit: v1.15.0
orders: acked=001–019 done=002–018; ORDER 001 open owner-side; ORDER 019 IN PROGRESS (night worklist, per-item log below).

## ORDER 019 night log (top-down)
1. WP-stack conflict reconcile — DISPATCHED 22:30Z (lane).
2. Curation REWORK backlog bundle (~17 rows) — DISPATCHED 22:30Z (lane).
3. check_money_race mis-classification fix — DISPATCHED 22:30Z (small-items lane).
4. Fishing cast-leg profile wiring — QUEUED wave 2 (verify-first: cast-leg depth wiring landed as #373/#387 today; residual to be confirmed).
5. Setup follow-ups unclaimed subset — QUEUED wave 2 (compound-ops+routing+automation-rule subset CLAIMED, PR #414 lane active — slice 1 #419 merged, slice 2 building).
6. plugins.lock.json pin for idle adapter — QUEUED wave 2 (cross-repo).
7. Windowed-select grammar successor — QUEUED wave 2.
8. Doc-only band-binding doctrine PR — DISPATCHED 22:30Z (small-items lane).
ORDER 031 (relayed, primary owner accepted): mining/fishing/idle review+finalize reports + casino inventory/spec — DISPATCHED 22:30Z (analysis-first lane); casino spec's SBW dependency stays flagged (⚑5); build follow-ups spawn from its report.

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (0 1-23/2 * * *) armed, bound to this seat. Pacemaker chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## ACTIVE LANES
- setup compound-ops (claim #414): slice 1 #419 MERGED; slice 2 (routing resolver + automation-rule seam) building.
- parity hygiene (claim #417): flavor re-mints + dead harness ref + 9-orphan triage — in progress.
- night wave-1 lanes per ORDER 019 log above.

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — gate-green but now 4-file conflicted vs main; reconcile lane dispatched; merge stays owner-click.
- #392 parked green on wp3 (auto-lands after WP sweep; re-mints the 0052-invalidated goldens — coordinate with reconcile lane).
- superbot #2058/#2061 — draft deploy-holds, flip-ready with ~2h churn caveat.

## ⚑ needs-owner (the standing eight)

1. Flip superbot #2058 (head a6b8c99) + #2061 to ready (merge=deploy). NOTE: the 2-hourly dashboard-refresh cron re-dirties #2061 while open (#2072 made resolution mechanical — scripts/resolve_generated_conflicts.py — it does NOT prevent churn); flip within ~2h of a fresh resolve (last: 0cc9a62 ~15:27Z) or run the resolver during a merge of main first. #2058 has no dashboard delta, merges clean. Deploy env names: FLAG1 MINING_SNAPSHOT_RELAY_URL + MINING_SNAPSHOT_RELAY_GUILD_ID; FLAG2 MINING_WRITE_SHARED_SECRET + MINING_WRITE_GUILD_ALLOWLIST (+ mineverse MINING_WRITE_ENDPOINT).
2. Sweep-merge the WP stack #312→#317→#335→#344 (+ #371), then #320.
3. Ratify the curation DROP list (60 items, #327 report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW inventory+spec for sections (SIM-REQUEST 00:55Z, unanswered).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 token run; hermes egress creds (CLAUDE_ROUTINE_FIRE_URL + token).
7. Minor: cosmetic "RED BY DESIGN"/"EXPECTED RED" banner strings in run_golden_parity.py/harness + golden-parity.yml step name (report leg is live green).
8. Confirm the origin/main history rewrite on superbot-next (history now roots at whole-tree snapshot 2cb4d91, ~104 commits; old per-PR squash SHAs like #319's no longer resolve locally though GitHub confirms the merges). If deliberate (e.g. repo squash), reply and the coordinator records it; if not, it needs investigation.

next-2-tasks:
1. Work ORDER 019 top-down through the night; heartbeat per item.
2. Morning: full night report → outbox; owner sweep list unchanged.
