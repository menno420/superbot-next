# superbot-next · status
updated: 2026-07-13T13:26:39Z
phase: coordinator seat OPEN — SuperBot 2.0 coordinator (project seat, booted 12:33Z); work loop running.
health: main at `d7b18b281d7a69b50932ab3983ecca3b7557eb7b` — curation remainder landed (#333/#352/#373 merged by 12:55Z); pytest green at boot (2435 passed); golden-parity report leg green. A red report = REAL regression.
kit: v1.15.0
orders: acked=001–018 done=002–018; ORDER 001 still open owner-side (Discord-token live-drive; pointer: PR #298 body).

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (cron 0 1-23/2 * * *) armed, bound to this seat; predecessor failsafe trig_01TuQrpMVpDCXB3K3VbjQUoA deleted at cutover 12:44Z (server-confirmed).
- pacemaker send_later chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## LANES (this seat)
- curation remainder — COMPLETE: #333 (90a5cad), #352 (c587544), #373 (d7b18b2, owner-merged 12:54Z). Lane hazard recorded: manifest.snapshot.json stable_hash re-conflicts concurrent recompiling PRs; resolve = merge main in + tools/manifest_compile.py --write.
- energy lane slices 1–3 (claim control/claims/energy-lane-slices-1-3.md): slice 1 = #384 all 14 checks green, parked open stacked on #320 (ORDER-017 park; enabler can't arm non-main-base). Slice 2 = #385 open (head beb134b); its tests/pip-audit reds at 13:19–13:23Z were GitHub Actions "Service Unavailable" infra flakes (jobs never executed), not code failures — lane owns the single environmental re-run. Slice 3 queued (fastmine dig-gating, after WP-3 #317).
- generated-file merge-churn durable fix (⚑ self-initiated, dispatched 13:09Z): superbot-next manifest.snapshot.json + superbot dashboard/data churn; superbot-next PR #386 open.
- superbot mineverse: #2058 (head 22071f5) + #2061 (head a1c95fb) fresh-resolved vs main, green, DRAFT deploy-holds — awaiting owner flip (merge=deploy). #2061's recurring conflict class corrected: generated dashboard.json churn, NOT mining_player_state.py; whichever FLAG lands second needs a trivial mining_player_state.py touch-up.

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — gate-green, owner-click ordered sweep.
- #320 energy domain core — gate-green, owner-click; merging it unblocks the #384→#385 energy stack.
- #384 (green, parked), #385 (in progress), #386 (in progress).
- superbot #2058/#2061 — draft deploy-holds, flip-ready.

## ⚑ needs-owner (the standing eight)

1. Flip superbot #2058 (head 22071f5) + #2061 (head a1c95fb) to ready (merge=deploy) — both fresh-resolved vs main and green at 13:09Z, still DRAFT; a dashboard-refresh merge re-dirties them, so flip soon or request a re-resolve (recipe: checkout --theirs dashboard.json → python3.10 scripts/export_dashboard_data.py → stage regenerated files).
2. Sweep-merge the WP stack #312→#317→#335→#344 (+ #371), then #320.
3. Ratify the curation DROP list (60 items, #327 report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW inventory+spec for sections (SIM-REQUEST 00:55Z, unanswered).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 token run; hermes egress creds (CLAUDE_ROUTINE_FIRE_URL + token).
7. Minor: #2061 dashboard-conflict durable fix — gitattributes merge driver for generated dashboard files on superbot — dispatched 13:09Z (this seat): durable-fix lane covering superbot-next manifest.snapshot.json + superbot dashboard.json, PR #386 open.
8. Minor: cosmetic "RED BY DESIGN"/"EXPECTED RED" banner strings in run_golden_parity.py/harness + golden-parity.yml step name (report leg is live green).

next-2-tasks:
1. Energy slice 2 (#385) to green + slice 3; churn-fix #386 to green; verify all at HEAD.
2. Owner sweep — mineverse flips, WP stack + #320, DROP list, D-0083, SBW answer.

Pointers: previous seat retro = .sessions/2026-07-13-coordinator-seat-close.md (PR #378); boot heartbeat = PR #383.
