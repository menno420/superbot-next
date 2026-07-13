# superbot-next · status
updated: 2026-07-13T00:04Z
phase: SEAT OPEN — coordinator session_01KhzyfUk76YB9Bj2TPF6h5z active; operating mode merge-on-done per owner directive 2026-07-12 (~21:47Z, coordinator chat).
health: main green at `d030c9b` (#318 merged 2026-07-13T00:01Z) — golden-parity gate job green, `report` leg red-by-design.
kit: v1.15.0
orders: acked=001–016 done=002–016; ORDER 001 open — band-1 live-drive requires an owner-side run with the Discord token (pointer: PR #298 body).
routines: failsafe `trig_01TuQrpMVpDCXB3K3VbjQUoA` cron `0 1-23/2 * * *` (verified via list_triggers); pacemaker send_later chain ~15 min active. Business crons unchanged: `trig_01Jm57GAjNCFrYJn1oLMiYGE` kit-lab (never-rebind); `trig_015aNMg5ncoSE2Roe4MKjQnr` trading (other seat); `trig_018wP6XTPmf9DLnxrG4RpGVh` docs-recon (poke-only).

landed this seat-shift (session PRs + coordinator review-merges; all verified merged at GitHub): #303 #304 #305 #302 #307 #308 #309 #306 #310 #311 #314 #316 #319 #318.

open PRs (verified at GitHub 2026-07-13T00:04Z):
- #313 fishing slice 1 (forecast/sail) — OWNER-GATED on D-0043 go/no-go; ask pending in coordinator chat since 2026-07-12T22:44Z; merge-on-silence attempt refused by classifier (pointer: PR #313 comments).
- #312 WP-2 vault write goldens — merge-state dirty at last check; peer lane session_017bp274t8W1jwJEuj27U5xP.
- #317 WP-3 depth/world/wear write goldens — stacked on #312 (base `mining-write-parity-wp2`); same peer lane.
- #320 mining energy domain core (slice 0) — READY (not draft), peer session_01RrzShF7DGcWmmWS4pdjDxo.
- #321 ci: auto-merge enabler workflow (fm ORDER 029) — opened 2026-07-13T00:02Z by peer session_01UutkJqyMcHC1VyFW8fe1a9.
- superbot#2054 hub upkeep — auto-merge armed, gate-flip pending (repo not reachable from this session; as reported by coordinator).

⚑ needs-owner:
1. D-0043 FISHING go/no-go — mining half de-facto done; a one-letter answer in coordinator chat unblocks #313 + 13 fishing goldens.
2. Settings-prune corpus ratification (docs/review/admin-surface-audit-2026-07-12.md §8).
3. OWNER-ACTION 3 — ruleset/merge-queue (six-field record in pre-close status at `694e056`).
4. OWNER-ACTION 5 — ANTHROPIC_API_KEY + AI_ENABLED (six-field record at `694e056`).
5. One-click: delete branches `scratch/union-test-a` + `scratch/union-test-b` (agent branch-deletion returns 403).

next-2-tasks:
1. On D-0043 answer: merge #313 + continue the fishing lane (13 goldens).
2. Monitor peer lanes (WP-2/WP-3 rebase, energy slice 0) + superbot#2054 landing; backlog otherwise dry.
