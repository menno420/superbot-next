# superbot-next · status
updated: 2026-07-13T18:03:41Z
phase: coordinator seat OPEN — SuperBot 2.0 coordinator (project seat, booted 12:33Z); work loop running.
health: main at `ecb31989ba00ee1c95afb3b9d0715258645ccd00` — landed today: energy slices 0–2 (#320/#384/#385), curation remainder (#333/#352/#373), churn fixes (#386 + superbot #2072), hygiene (#393), fishing bait race fence (#394), setup-wizard slices 1–3 (#395/#397/#398), settings-admin slice 1 (#399). golden-parity report leg green. A red report = REAL regression.
kit: v1.15.0
orders: acked=001–018 done=002–018; ORDER 001 still open owner-side (Discord-token live-drive; pointer: PR #298 body).

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (cron 0 1-23/2 * * *) armed, bound to this seat; predecessor failsafe deleted at cutover 12:44Z.
- pacemaker send_later chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## LANES (this seat)
- setup-wizard successors (claim on branch; lane active): slices 1–3 MERGED (#395 final-review apply, #397 essential steps 2–8, #398 suggestion Edit); slice 4 = the 10 per-section flows, being sub-sliced into PR-sized pieces.
- settings-admin remainder (claim on branch; lane active): verified residual = 5 hub actions (table was stale post-#375). Slice 1 #399 (diagnostics trio) MERGED; slice 2 #400 (audit view) green/armed; slice 3 #401 (command-access write panel) in CI; #402 opened.
- COMPLETE today: curation remainder · generated-file churn mitigation (both repos) · hygiene (#393: 17 stale claims removed, banners retired) · energy lane (slice 3 #392 parked green on WP-3, auto-lands after the WP sweep — expect a brief parity red on main between the WP sweep and #392 landing; it re-mints 4 goldens invalidated by migration 0052) · fishing bait race fence (#394).
- superbot mineverse: #2058/#2061 DRAFT deploy-holds, flip-ready with the ~2h dashboard-churn caveat (see ⚑ item 1).

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — gate-green, owner-click ordered sweep (unswept).
- #392 (parked on wp3) · #400/#401/#402 (settings/setup lanes, landing via enabler) · superbot #2058/#2061 (draft deploy-holds).

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
1. Lanes finish settings-admin slices 2–3 and setup-wizard slice 4; then remaining completeness rows (server_management trio, cleanup residue, fishing howtofish).
2. Owner sweep — mineverse flips (churn window), WP stack, DROP list, D-0083, SBW answer, history-rewrite confirm.

Pointers: previous heartbeats = PRs #383/#388/#391/#396; backlog scan = this seat 15:22Z.
