# superbot-next · status
updated: 2026-07-13T14:46:19Z
phase: coordinator seat OPEN — SuperBot 2.0 coordinator (project seat, booted 12:33Z); work loop running.
health: main at `4f5264319669eda5ef8c147dba83b6c1bbf2a91d` — energy slices 0–2 landed (#320, #384, #385); golden-parity report leg green; goldens ratchet 9→10 (first mining_player_state-bearing golden, depth exemption retired). A red report = REAL regression.
kit: v1.15.0
orders: acked=001–018 done=002–018; ORDER 001 still open owner-side (Discord-token live-drive; pointer: PR #298 body).

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (cron 0 1-23/2 * * *) armed, bound to this seat; predecessor failsafe deleted at cutover 12:44Z.
- pacemaker send_later chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## LANES (this seat)
- curation remainder — COMPLETE (#333 90a5cad, #352 c587544, #373 d7b18b2).
- energy lane (claim control/claims/energy-lane-slices-1-3.md): slices 0–2 ON MAIN (#320 e902b0d owner-merged, #384 dc0e73d owner-merged, #385 4f52643 enabler); slice 3 (fastmine dig-gating + sweep_fastmine re-mint) building — spec'd strictly after WP-3 #317, stacks on it if unmerged.
- generated-file merge-churn durable fix — COMPLETE both repos: superbot-next #386 (bec00af; stable_hash removed from tracked snapshot, recipe docs/operations/manifest-snapshot-conflicts.md); superbot #2072 (b9e877b, merged 13:57Z owner-armed; scripts/resolve_generated_conflicts.py + docs/operations/generated-data-merge-recipe.md). Conflict classes retired; resolver proven on #2061's 4-file conflict 14:16Z.
- superbot mineverse: #2058 (a6b8c99) + #2061 (e5a4e1e) re-resolved at main tip, mergeable clean, DRAFT deploy-holds — flip-ready (see ⚑ item 1).

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — gate-green, owner-click ordered sweep (unswept as of 14:45Z).
- superbot #2058/#2061 — draft deploy-holds, flip-ready.

## ⚑ needs-owner (the standing eight)

1. Flip superbot #2058 (head a6b8c99) + #2061 (head e5a4e1e) to ready (merge=deploy) — both re-resolved at main tip 14:16–14:21Z, mergeable clean, DRAFT. Deploy-time env names: FLAG1 MINING_SNAPSHOT_RELAY_URL + MINING_SNAPSHOT_RELAY_GUILD_ID; FLAG2 MINING_WRITE_SHARED_SECRET + MINING_WRITE_GUILD_ALLOWLIST (+ mineverse MINING_WRITE_ENDPOINT). Whichever lands second may need a one-line mining_player_state.py merge.
2. Sweep-merge the WP stack #312→#317→#335→#344 (+ #371), then #320.
3. Ratify the curation DROP list (60 items, #327 report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW inventory+spec for sections (SIM-REQUEST 00:55Z, unanswered).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 token run; hermes egress creds (CLAUDE_ROUTINE_FIRE_URL + token).
7. Minor: cosmetic "RED BY DESIGN"/"EXPECTED RED" banner strings in run_golden_parity.py/harness + golden-parity.yml step name (report leg is live green).

next-2-tasks:
1. Energy slice 3 to PR + green; verify at HEAD; work loop continues.
2. Owner sweep — mineverse flips, WP stack, DROP list, D-0083, SBW answer.

Pointers: previous heartbeats = PRs #383/#388; seat retro = .sessions/2026-07-13-coordinator-seat-close.md (PR #378).
