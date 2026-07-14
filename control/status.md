# superbot-next · status
updated: 2026-07-14T01:44:04Z
phase: EAP FINAL NIGHT — coordinator seat OPEN; ORDER 019 worked top-down, most items landed; loop continues to morning.
health: main at `36d47d6bb91e3605259a766b4746b10aa6f3c9e7`. Gate incident 00:00–01:12Z RESOLVED: 4 fishing goldens were minted date-live 07-13 (weather derives from UTC date) → fleet-wide gate red at midnight; fixed by #448 (seed via CAPTURE_WORLD_WEATHER) + #449 (canonical stripped re-mints + fishing ratchet floor 3/10→2/8). Goldens must have their case id in CAPTURE_WORLD_WEATHER before minting (team memory + docs).
kit: v1.15.0
orders: acked=001–019 done=002–018; ORDER 001 open owner-side; ORDER 019 log below.

## ORDER 019 night log (as of 2026-07-14T01:44:04Z)
1. WP-stack reconcile — IN FLIGHT (lane active; wp5/wp6/wp7 branches updated; merge stays owner-click).
2. Curation bundles — DONE to real extent: rows 2/45/59/60 landed (#428, #434); order's "~17 rows" was stale (21 of 27 pre-shipped); row 26 owned by WP lane, row 72 parked pending WP count-pin files (claim held, mint recipe verified).
3. check_money_race fix — DONE (#425; checker-only, 4 red-proven pins).
4. Fishing cast-leg wiring — DONE-ALREADY (#373/#387/#394); table trued (#436), stamp fix (#439).
5. Setup follow-ups — 5a on-ready resume DONE (#437); 5c channel-recommender DONE (#446); 5b SectionRecoveryView IN FLIGHT (#444, conflict-resolve).
6. Idle plugins.lock pin — DONE-ALREADY (#370/0cae0e1); verification record #441.
7. Windowed-select grammar — DONE (#435; premise correction: title-equip needs a write slice, not windowing).
8. Band-binding doctrine doc — DONE (#427; ORDER 004 done= citation hook).
ORDER 031 (relayed, accepted) — COMPLETE lane-side: reviews + casino inventory/section spec published at docs/review/games-finalization-2026-07-13.md and docs/specs/casino-section-spec.md (THIS heartbeat line is the ORDER 031 reference hook; the spec fills the SBW SIM-REQUEST / D-0082 §7 slot). Improve slices landed: #442 minestats, #450 fishing fidelity, #451 farm leaderboard. Casino SECTION BUILD remains a separate order.

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (0 1-23/2 * * *) armed, bound to this seat. Pacemaker chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — reconcile in flight; owner-click sweep after.
- #392 parked on wp3 (auto-lands after WP sweep) · #444 (item 5b, in flight) · superbot #2058/#2061 draft deploy-holds (~2h churn caveat).

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
1. Finish item 1 (WP reconcile) + 5b (#444); then curation row-72 (post-WP) and any remaining honest tails; morning report → outbox.
2. Owner sweep — WP stack + mineverse flips + DROP list + history-rewrite confirm; casino section build = new order when ready.

Pointers: night ack = PR #421; ORDER 031 hook = docs/specs/casino-section-spec.md; incident detail = PRs #448/#449 bodies.
