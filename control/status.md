# superbot-next · status
updated: 2026-07-13T02:47Z
phase: SEAT OPEN — coordinator session_01KhzyfUk76YB9Bj2TPF6h5z active; night run executing ORDER 017 (owner night-run mandate, inbox@HEAD, landed verbatim by #323). Landing mode = repo auto-merge enabler (canonical for non-draft claude/* PRs per #321); coordinator merge delegation retired — open PRs stay open per ORDER 017 rule 2.
health: main at `3e4a77d` (#342 fishing slice 3 — bait, merged 2026-07-13T02:44Z); golden-parity gate job green at last landing, `report` leg red-by-design.
kit: v1.15.0
orders: acked=001–017 done=002–016; ORDER 017 executing (night run); ORDER 001 open — band-1 live-drive requires an owner-side run with the Discord token (pointer: PR #298 body).
routines: failsafe `trig_01TuQrpMVpDCXB3K3VbjQUoA` cron `0 1-23/2 * * *` — the 01:07Z-window slot wedged platform-side and fired late at 02:44Z; pacemaker send_later fires stalled 01:37–02:44Z, chain re-armed post-flush (next coordinator tick 03:06Z `trig_013LHWPn1pue3YsjdjHnbq8J`, verified via list_triggers). Backup morning wake planted from the completeness-lane session: `trig_01KpeNktduqT5YTuNgetcwDP` fires 05:05Z → wakes the coordinator for the tally (verified). Business crons unchanged: `trig_01Jm57GAjNCFrYJn1oLMiYGE` kit-lab (never-rebind); `trig_015aNMg5ncoSE2Roe4MKjQnr` trading (other seat); `trig_018wP6XTPmf9DLnxrG4RpGVh` docs-recon (poke-only).

landed this night-shift (each verified merged at GitHub / in origin/main log 2026-07-13T02:46Z): #323 (ORDER 017 verbatim), #313 (fishing slice 1 — forecast/sail), #324 (fishing lane claim), #325 (SBW SIM-REQUEST outbox — minigame inventory+spec), #326 (per-subsystem completeness table, ORDER 017 item 1), #329 (game sections design D-0082, ORDER 017 item 4), #330 (fishing slice 2 — rod ladder, peer lane), #331 (diagnostic operator mutation panels), #327 (curation report `docs/review/curation-report-2026-07-13.md`: 1088 items — 918 KEEP / 110 REWORK / 60 DROP, ORDER 017 item 2), #342 (fishing slice 3 — bait/craftbait/craftpearl/craftcharm). Prod-bot lane (superbot repo, verified): #2054 merged 00:04Z, #2056 merged 00:27Z (Codex P2 follow-up on #2054).

open PRs (verified at GitHub 2026-07-13T02:46Z — 13 on this repo + 2 superbot drafts):
- #312 WP-2 vault write goldens — base main; peer lane session_017bp274t8W1jwJEuj27U5xP.
- #317 WP-3 depth/world/wear write goldens — stacked on #312.
- #335 WP-5 skill-spend PORT write golden — stacked on #317 (new since last stamp).
- #320 mining energy domain core (slice 0) — peer session_01RrzShF7DGcWmmWS4pdjDxo.
- #332 / #333 / #336 curation reworks — panel-nav wiring, cleanup-words panel + logging nav, btd6 paragon surface (D-0046).
- #334 game sections slice 1 (registry + enablement seam, D-0082) — base main, updated 02:44Z.
- #337 game sections slice 2 (settings surface) — stacked on #334.
- #341 game sections slice 3 (games hub renders enabled set) — stacked on #337.
- #338 fishing bait-only fill (lane #324) — opened 02:19Z off pre-#342 main; overlaps the just-merged #342 bait slice — reconcile/close check next wake.
- #339 btd6 paragon calculator (pure-compute port).
- #340 setup wizard interior (ORDER 017).
- superbot#2058 mineverse FLAG 1 read-relay + superbot#2061 mineverse FLAG 2 write endpoint — both deliberately DRAFT (merge=deploy guard); see needs-owner.

⚑ needs-owner (morning queue):
1. superbot mineverse PRs are held as DRAFTS by the merge=deploy guard (Q-0193) — owner flips ready to land+deploy: #2058 (FLAG 1 snapshot read-relay; checks green as reported) and #2061 (FLAG 2 HMAC write endpoint; still iterating, last push 02:41Z).
2. CodeQL raised 6 new alerts (1 high) on superbot#2061 — child session fixing; owner review before deploy (as reported in coordinator chat).
3. Settings-prune corpus ratification (docs/review/admin-surface-audit-2026-07-12.md §8).
4. OWNER-ACTION 3 — ruleset/merge-queue; OWNER-ACTION 5 — ANTHROPIC_API_KEY + AI_ENABLED (six-field records in pre-close status at `694e056`).
5. One-click: delete branches `scratch/union-test-a` + `scratch/union-test-b` (agent branch-deletion returns 403).

next-2-tasks:
1. Morning tally ~06:00Z — SHIPPED / OPEN-PRs / QUEUED / STALLED posted in heartbeat + outbox (ORDER 017 MORNING clause; backup wake 05:05Z armed).
2. Drive the ORDER 017 lanes to green: sections stack (#334→#337→#341), parity stack (#312→#317→#335), curation reworks (#332/#333/#336/#339), setup wizard (#340), #338 reconcile vs #342.
