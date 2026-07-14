# superbot-next · status
updated: 2026-07-14T07:33:51Z
phase: post-EAP-night morning — dawn lanes complete (ORDER 020 executed + review-parked; D-0043 both slices merged, D-0090 ratified); owner sweep queued.
health: main at `36d47d6bb91e3605259a766b4746b10aa6f3c9e7`. Gate incident 00:00–01:12Z RESOLVED: 4 fishing goldens were minted date-live 07-13 (weather derives from UTC date) → fleet-wide gate red at midnight; fixed by #448 (seed via CAPTURE_WORLD_WEATHER) + #449 (canonical stripped re-mints + fishing ratchet floor 3/10→2/8). Goldens must have their case id in CAPTURE_WORLD_WEATHER before minting (team memory + docs).
kit: v1.15.0
orders: acked=001–019 done=002–019 (019 full trail: outbox 2026-07-14 night report; ORDER 031 relay complete); ORDER 001 open owner-side.

## ORDER 019 night log
All 8 items + relayed ORDER 031 closed out — full citations in the outbox 2026-07-14T04:48:20Z night report.
WP owner table (merge order, all-green mergeable-clean): #312 dc35d48 · #317 259176d · #335 b548687 · #344 e6553a7 · #371 91bc32f.
Extras: night-tail lane #454–#457; gate incident fix #448/#449; ORDER 031 spec hook = docs/specs/casino-section-spec.md.
Dawn: D-0043 fishing minigame timing rung COMPLETE (#460 + #462; kernel timer + push-edit seam ratified D-0090). ORDER 020 executed, plugin PR parked for owner merge.

## ROUTINES
- FAILSAFE trig_012sSzXkABoZEFW1BqXuqi3v (0 1-23/2 * * *) armed, bound to this seat. Pacemaker chain live (~15 min links).
- business crons unchanged: kit-lab trig_01Jm57GAjNCFrYJn1oLMiYGE (fresh-session — NEVER rebind); docs-recon trig_018wP6XTPmf9DLnxrG4RpGVh (poke-only).

## OPEN PRs
- WP stack #312→#317→#335→#344→#371 — all-green, mergeable-clean, owner-click sweep (heads: dc35d48 · 259176d · b548687 · e6553a7 · 91bc32f).
- #392 parked on wp3 (auto-retargets after WP sweep) · superbot #2058/#2061 draft deploy-holds (~2h churn caveat).

## ⚑ needs-owner (the standing eight)

0. Merge superbot-plugin-hello PR #2 (ORDER 020 close, one-line kit_version 1.13.0→1.15.0; independent non-author review PASS on record; classifier denied agent merge — ratification park). done-when: fm gen_kit_versions.py renders the plugin-hello row OK at next regen.
1. Flip superbot #2058 (head a6b8c99) + #2061 to ready (merge=deploy). NOTE: the 2-hourly dashboard-refresh cron re-dirties #2061 while open (#2072 made resolution mechanical — scripts/resolve_generated_conflicts.py — it does NOT prevent churn); flip within ~2h of a fresh resolve (last: 0cc9a62 ~15:27Z) or run the resolver during a merge of main first. #2058 has no dashboard delta, merges clean. Deploy env names: FLAG1 MINING_SNAPSHOT_RELAY_URL + MINING_SNAPSHOT_RELAY_GUILD_ID; FLAG2 MINING_WRITE_SHARED_SECRET + MINING_WRITE_GUILD_ALLOWLIST (+ mineverse MINING_WRITE_ENDPOINT).
2. Sweep-merge the WP stack #312→#317→#335→#344 (+ #371), then #320.
3. Ratify the curation DROP list (60 items, #327 report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW inventory+spec for sections (SIM-REQUEST 00:55Z, unanswered).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 token run; hermes egress creds (CLAUDE_ROUTINE_FIRE_URL + token).
7. Minor: cosmetic "RED BY DESIGN"/"EXPECTED RED" banner strings in run_golden_parity.py/harness + golden-parity.yml step name (report leg is live green).
8. Confirm the origin/main history rewrite on superbot-next (history now roots at whole-tree snapshot 2cb4d91, ~104 commits; old per-PR squash SHAs like #319's no longer resolve locally though GitHub confirms the merges). If deliberate (e.g. repo squash), reply and the coordinator records it; if not, it needs investigation.

next-2-tasks:
1. Owner sweep — WP stack + mineverse flips + DROP list + history-rewrite confirm.
2. Casino section build = new order when ready; coordinator loop holds heartbeat until morning handoff.

Pointers: night ack = PR #421; ORDER 019 close-out = outbox 2026-07-14T04:48:20Z; ORDER 031 hook = docs/specs/casino-section-spec.md; incident detail = PRs #448/#449 bodies.
