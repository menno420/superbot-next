# superbot-next · status
updated: 2026-07-13T08:55Z
phase: SEAT OPEN — coordinator session_01KhzyfUk76YB9Bj2TPF6h5z active; ORDER 017 complete incl. post-encore — 09:00Z refresh of the 05:09Z tally below. Landing mode unchanged: repo auto-merge enabler is canonical for non-draft claude/* PRs (#321).
health: main at `eee9a69` (#364 help editor D-0089, merged 2026-07-13) at refresh sync; golden-parity gate job green at last landing, `report` leg red-by-design.
kit: v1.15.0
orders: acked=001–017 done=002–016; ORDER 017 — this tally closes the night mandate; ORDER 001 still open owner-side (band-1 live-drive needs an owner run with the Discord token; pointer: PR #298 body).
routines: failsafe `trig_01TuQrpMVpDCXB3K3VbjQUoA` cron `0 1-23/2 * * *` + pacemaker send_later chain healthy. Night incidents, both recovered: scheduler wedge 01:07–02:44Z (failsafe slot + pacemaker fires stalled platform-side, flushed 02:44Z, chain re-armed); GitHub Actions check-run outage ~03:40Z (runs not spawning; cleared, queued CI now draining). Business crons unchanged: `trig_01Jm57GAjNCFrYJn1oLMiYGE` kit-lab (never-rebind); `trig_015aNMg5ncoSE2Roe4MKjQnr` trading (other seat); `trig_018wP6XTPmf9DLnxrG4RpGVh` docs-recon (poke-only).

## ORDER 017 MORNING TALLY (2026-07-13T05:09Z)

SHIPPED — superbot-next, 21 merges since ORDER 017 (#323, 00:46Z), each verified in origin/main log at tally sync:
- fishing lane complete: #313 (slice 1 forecast/sail), #330 (slice 2 rod ladder), #342 (slice 3 bait), #350 (slice 4 locations), #338 (bait-only test fill, re-scoped) + lane claim/close #324/#353.
- game-sections lane complete: #329 (D-0082 design), #334 (slice 1 registry/seam), #337 (slice 2 settings surface), #341 (slice 3 games hub) + #346 (anchor-refresh proposal) + #348 (lane release).
- curation report #327 — `docs/review/curation-report-2026-07-13.md`, 1088 items: 918 KEEP / 110 REWORK / 60 DROP.
- completeness table #326; diagnostic operator panels #331; setup wizard interior #340; channel hub ops #356; control #323/#325/#343.
SHIPPED — superbot (prod bot), 7 merges: #2054 #2055 #2056 #2057 #2059 #2060 #2062.

DELTA since 05:09Z tally (verified in origin/main log `5bb5563..eee9a69`), 12 more merges: #357 #359 #358 #339 #347 #349 #351 #360 #361 #362 #363 #364.
- server_management projections complete: #362 (D-0087 access map), #363 (D-0088 help preview), #364 (D-0089 help editor).
- completeness lane closed — 15 merged PRs total; completeness table true at HEAD (#360); session-card mtime-lottery gate defused (#361).
- night reds landed: #357 (checkers) and #358 (operator-hub edits A, supersedes #355 — #355 closed unmerged); btd6 #339, ticket #347, starboard #349, rps #351; #359 was the tally control commit.

OPEN-PRs — 10 on superbot-next:
- mining WP stack #312→#317→#335→#344 — all gate-green, ready for ordered sweep; #320 energy core gate-green but review-merge classifier-denied — owner click. All five awaiting the owner sweep.
- curation tail #332 #333 #345 #352 #354 — in various CI states (cycling post-outage; check-runs, not legacy statuses), being driven to green.
superbot: #2058 + #2061 (mineverse FLAGs 1+2) — DELIBERATE DRAFT deploy-holds; #2061 being mechanically re-resolved against dashboard-refresh conflicts (durable fix flagged: merge driver for generated dashboard files); owner flips ready to deploy.

QUEUED:
- energy slices 1–3 — pre-scoped, sequenced behind the WP stack.
- SBW inventory+spec integration — SIM-REQUEST in outbox, unanswered; swap point `GAME_SECTIONS` in `sb/manifest/games.py`.
- D-0083 anchor decision (proposal merged #346).
- curation backlog remainder (110 REWORK beyond the landed reworks).
- hermes probe — needs owner `CLAUDE_ROUTINE_FIRE_URL` + token.

STALLED-with-error (verbatim quotes live in the PR bodies/comments; heartbeat keeps pointers only):
- coordinator/self merge delegations classifier-held (pointer: #313/#320 comments).
- superbot non-draft PR creation denied from dispatched context (pointer: #2058 body).
- branch deletion 403 (`scratch/union-test-a`, `scratch/union-test-b`).
- the two platform outages above (scheduler wedge, Actions check-runs) — both recovered.

⚑ needs-owner (morning sweep, ordered):
1. Flip superbot #2058 + #2061 to ready (merge=deploy; the second may need a 1-line `mining_player_state.py` resolve).
2. Sweep-merge the WP stack #312→#317→#335→#344, then #320.
3. Ratify the curation DROP list (60 items, report §DROP).
4. D-0083 anchor call (#346 proposal).
5. SBW spec for sections (SIM-REQUEST outstanding).
6. Standing: settings-prune ratification; OWNER-ACTION 3 (ruleset/merge-queue) + 5 (ANTHROPIC_API_KEY/AI_ENABLED); delete scratch/union-test-a,-b; ORDER 001 live-drive token run.
7. Minor: #2061 dashboard-conflict durable fix — gitattributes merge driver for generated dashboard files on superbot.

next-2-tasks:
1. Drive the curation tail #332 #333 #345 #352 #354 to green.
2. Owner sweep then unblocks the WP/energy lane + mineverse deploys.
