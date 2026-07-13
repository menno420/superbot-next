# superbot-next · status
updated: 2026-07-13T12:43Z
phase: coordinator seat OPEN — SuperBot 2.0 coordinator (project seat) booted 2026-07-13T12:33Z on the v3.6 brief; work loop running, lanes dispatched.
health: main at `441a1e7` at heartbeat sync (boot sync was `441a1e7`) — pytest tests/ -q local 2435 passed / 13 skipped (12:36Z); golden-parity report leg green (run 29238825392, 484/484 goldens, 51/51 subsystems). A red report = REAL regression.
kit: v1.15.0
orders: acked=001–018 done=002–018; ORDER 001 still open owner-side (Discord-token live-drive; pointer: PR #298 body).

## ROUTINES (verified via account-wide list_triggers scan, 1220 rows, 12:34–12:38Z)
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v "SuperBot 2.0 failsafe wake" (cron 0 1-23/2 * * *, next 13:04Z) — armed, bound to this coordinator session.
- pacemaker send_later chain live (one pending link ~15 min ahead at any time).
- predecessor failsafe trig_01TuQrpMVpDCXB3K3VbjQUoA — DELETED at cutover ~12:44Z (server-confirmed), after the new failsafe was verified live.
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session-per-fire — NEVER rebind; next 07-14T06:08Z); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only, schedule-less).

## DISPATCHED SESSIONS (this seat, 12:38Z)
- curation remainder lane: #333/#352 check-attach + #373 conflict resolve via merge-main-in.
- energy lane slices 1–3 (claim: control/claims/energy-lane-slices-1-3.md; behind the WP stack).
- earlier night sessions still active: mineverse FLAGs (superbot #2058/#2061), minigame consolidation scaffold, command/button curation report, PR #298 rescue (V010 checker), core/admin/setup sweep, AIP-07/08 adapter lane, curation-backlog slicing.

## OPEN PRs (carry-over from the 10:47Z close list; owner sweep pending)
- WP stack #312→#317→#335→#344 + #371 — gate-green, owner-click ordered sweep.
- #320 energy domain core — gate-green, owner-click.
- #333/#352/#373 — lane dispatched this seat (check-attach / conflict levers).
- superbot #2058/#2061 mineverse FLAGs — deliberate DRAFT deploy-holds; owner flip = deploy (#2061 carries a conflict-guard red; its lane session is on the resolve).

## ⚑ needs-owner (the standing eight)

1. Flip superbot #2058 + #2061 to ready (merge=deploy; #2061 may need a 1-line `mining_player_state.py` resolve).
2. Sweep-merge the WP stack #312→#317→#335→#344 (+ #371), then #320.
3. Ratify the curation DROP list (60 items, #327 report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW inventory+spec for sections (SIM-REQUEST 00:55Z, unanswered).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 token run; hermes egress creds (CLAUDE_ROUTINE_FIRE_URL + token).
7. Minor: #2061 dashboard-conflict durable fix — gitattributes merge driver for generated dashboard files on superbot.
8. Minor: cosmetic "RED BY DESIGN"/"EXPECTED RED" banner strings in run_golden_parity.py/harness + golden-parity.yml step name (report leg is live green).

next-2-tasks:
1. Verify dispatched lanes at HEAD (curation remainder to green/landed; energy slice 1 PR up) and keep the work loop slicing.
2. Owner sweep — mineverse flips, WP stack + #320, DROP list, D-0083, SBW answer.

Pointers: previous seat retro = .sessions/2026-07-13-coordinator-seat-close.md (PR #378); ORDER-018 night report = outbox 09:25Z entry.
