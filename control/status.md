# control/status.md — coordinator heartbeat

updated: 2026-07-14T21:28:31Z
phase: SEAT DORMANT (owner order 2026-07-14 — EAP FINAL SHUTDOWN)
health: green — all agent-side work terminal or parked-cited; owner-side items below
main at shutdown: ba9241627f1102c0af152b34e1e76df01f1583a5

## REVIVAL — read first
1. Standard orientation: CONSTITUTION.md → this file → docs/status/README-first.md.
2. EAP record: docs/eap-closeout-walkthrough-2026-07-14.md (§C = owner actions) and docs/audits/eap-project-audit-2026-07-14.md.
3. Re-arm this seat's routines (both deleted at shutdown, verified via exhaustive list_triggers 2026-07-14T21:26Z):
   - failsafe cron (was trig_012sSzXkABoZEFW1BqXuqi3v): schedule `0 1-23/2 * * *`, prompt: "FAILSAFE WAKE (SuperBot 2.0, Q-0265): send_later chain alive → verify in one line, end. Stalled → resume the work loop (sync HEAD → inbox → slice after slice, landed per LANDING), re-arm the chain (~15 min), and write your heartbeat (control/status.md, per-seat grammar) as the deliberate last step." Recreate bound to the new coordinator session.
   - pacemaker: one-shot send_later ~15 min, message "continue the work loop: sync HEAD → inbox → next slice → re-arm"; the new coordinator re-arms it on its first working turn.
   - NOT deleted (ownership not this seat's — recorded for the owner): kit-lab daily cron trig_01Jm57GAjNCFrYJn1oLMiYGE (`0 6 * * *`, substrate-kit self-improvement loop, marked NEVER rebind) and superbot docs-recon poke-only trig_018wP6XTPmf9DLnxrG4RpGVh (no schedule; fires on the `reconcile` issue label). ⚑ owner: disable via console if full dormancy is wanted.

## PARKED — owner-side (state verified 2026-07-14 20:55–21:26Z)
- superbot-next WP stack: merge in order #317 (wp3 @ ade9e69, base main) → #335 (wp5 @ 44ce9ee) → #344 (wp6 @ bc0aeda) → #371 (wp7 @ 873f457); all open, clean, green; #312 (WP-2) merged 15:56Z. Goldens byte-identical to #392 @ 24ca87e. Bottom-up re-fold ONLY if stale; re-sum count pins FROM DISK after merges (team memory: wp-stack-staged-for-owner-revival).
- Frozen PRs (do-not-automerge, cards in-progress by design): #466 fishing Cast-again @ 0c1048e, #477 casino section @ 5c4838e, #473 title-equip @ d6421a2, #476 curation row 72 @ dc3efdf. After the WP stack lands: flip each card complete + remove the label; the owning lanes are ended, so a fresh session does the flips per .sessions/README.md.
- superbot #2061 (mineverse FLAG 2): green draft @ 140c384 — mark ready + merge = deploy. If conflict-rotted (dashboard cron, ~2h cadence): run scripts/resolve_generated_conflicts.py during a merge of main (recipe: superbot docs/operations/generated-data-merge-recipe.md). Post-merge env: MINING_WRITE_SHARED_SECRET + MINING_WRITE_GUILD_ALLOWLIST (Railway), MINING_WRITE_ENDPOINT (mineverse). FLAG 1 (#2058) merged + deployed 15:55Z.
- Remaining owner actions: walkthrough §C — require `substrate-gate` as a required context; DROP-list ratification; anchor call 0083; ORDER 001 token; standing tail incl. deleting branch claude/lifeboat-fishing-minigame-timing @ 0c1e3bf (superseded; branch-delete was walled for agents, 403).
- #457 conform sweep: gated on the WP stack landing.

## ORDERS
acked=001–022 done=002–022 (020 ratified 2026-07-14T14:20Z via plugin-hello#2; 022 closed via #480 + reissue validated via #486). ORDER 001 open owner-side. No ORDER ≥ 023 at HEAD. Inbox contains no shutdown ORDER — the EAP FINAL SHUTDOWN directive arrived as a live owner turn in the coordinator session, which binds per the seat's order rules.

## SOURCE OF TRUTH
Fleet doctrine is centralized at fm:docs/prompts/v3/ and fm:projects/UNIVERSAL.md; seat vocabulary at sb:docs/owner/fleet-vocab.md. Known local duplications left in place (reconcile on revival, do not trust as canonical): control/README.md order-grammar prose (canonical: the kit's bootstrap enforcer), docs/collaboration-model.md band-binding notes (overlaps fm collaboration doctrine).

kit: v1.16.0
