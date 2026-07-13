# superbot-next · status
updated: 2026-07-13T10:47Z
phase: SEAT CLOSED — coordinator session_01KhzyfUk76YB9Bj2TPF6h5z ended per owner ender 2026-07-13. This file is the successor's boot surface. Landing mode unchanged: repo auto-merge enabler is canonical for non-draft claude/* PRs (#321, workflow at `e9f1cd5`).
health: main at `51879c5` (#376, curation row-73 claim) at close sync — full-corpus parity holds: `report` job live green since 2026-07-13T04:00:14Z (run 29222893993); latest confirmation run 29238825392 (484/484 goldens, 51/51 subsystems, 0 `_unmapped`). A red report = REAL regression.
kit: v1.15.0
orders: acked=001–018 done=002–018; ORDER 001 still open owner-side (Discord-token live-drive; pointer: PR #298 body).

## ROUTINE DISPOSITION at close (as verified)

- pacemaker `trig_01SWUCCwC4JXaGhu2wAq7UQ5` — DELETED (verified absent; exhaustive 1202-trigger account scan).
- FAILSAFE `trig_01TuQrpMVpDCXB3K3VbjQUoA` — left ARMED (cron `0 1-23/2 * * *`, next fire 11:07Z) as the successor's bridge. Successor boot: rebind-then-delete per docs/ROUTINES.md.
- business crons unchanged: kit-lab `trig_01Jm57GAjNCFrYJn1oLMiYGE` (next 07-14 06:08Z, fresh-env — NEVER rebind); docs-recon `trig_018wP6XTPmf9DLnxrG4RpGVh` (poke-only).
- trading `trig_015aNMg5ncoSE2Roe4MKjQnr` — NO LONGER EXISTS account-side (another seat's; recorded, untouched).

## OPEN PRs at close (verified live at GitHub 2026-07-13T10:44Z — 9 open) + landing paths

- WP stack #312→#317→#335→#344 + NEW #371 (WP-7 residual legs) — gate-green, owner-click ordered sweep (non-claude/* branches, outside enabler scope).
- #320 energy domain core — gate-green, owner-click (review-merge classifier-denied earlier).
- #333 + #352 (curation tail, claude/*) — enabler-on-green, but STILL event-starved: close/reopen tried and did not attach checks (zero check runs on both heads at 10:44Z). Next lever: merge main into the branch, else owner Actions poke.
- #373 fishing cast wiring (claude/*) — enabler-on-green; `mergeable_state: dirty` (base `d546399`) ⇒ zero check runs — merge main in to attach checks.
- superbot (prod bot): #2058 + #2061 mineverse FLAGs — deliberate DRAFT deploy-holds; owner flip = deploy.
- Tail dispositions confirmed: #332 MERGED 10:01Z by github-actions[bot] (enabler); #354 CLOSED unmerged (superseded by #358); #345 #370 #376 landed.

## ACTIVE DISPATCHED SESSIONS at close

- curation-backlog session still slicing bottom-up — lands via enabler on green; reports ride the project channel. No coordinator action needed.

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
1. Owner sweep — mineverse flips, WP stack + #320, DROP list, D-0083, SBW answer.
2. Successor boots per STARTUP, rebinds-then-deletes the failsafe, picks up the energy lane (slices 1–3, behind the WP stack) + the curation remainder (#333/#352/#373 to green).

Pointers: seat retro = this PR's session card (`.sessions/2026-07-13-coordinator-seat-close.md`); ORDER-018 full night report = outbox 09:25Z entry; prompt-delta proposal = outbox 10:45Z entry.
