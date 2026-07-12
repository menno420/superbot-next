# superbot-next · status
updated: 2026-07-12T20:53Z
phase: SEAT OPEN — successor coordinator booted 2026-07-12 (session_01KhzyfUk76YB9Bj2TPF6h5z). Boot HEAD `e23355a`; main has since advanced to `c21b1ea` (#289 mining slice-2 merged 20:47Z). At `c21b1ea`: `ci` + `named-gates` green (run set 20:47:42Z), golden-parity required `gate` job green (job 86691804487 — gate + check_parity_depth + F-001/F-002 concurrency all success), `report` leg red-by-design ("Red-until-parity full-corpus report (EXPECTED RED)").
health: pytest tests/ green at boot HEAD `e23355a` (2005 passed / 13 skipped).
kit: v1.15.0
orders: acked=001–016 done=002–016; ORDER 001 open — band-1 live-drive requires an owner-side run with the Discord token (pointer: PR #298 body).
routines: failsafe `trig_01TuQrpMVpDCXB3K3VbjQUoA` "SuperBot 2.0 failsafe wake" cron `0 1-23/2 * * *`, armed 20:42Z, verified via list_triggers (account-wide sweep; sole trigger bound to this session). Pacemaker send_later chain running ~15 min. Business crons recorded, untouched: `trig_01Jm57GAjNCFrYJn1oLMiYGE` kit-lab daily (fresh-env, never rebound); `trig_015aNMg5ncoSE2Roe4MKjQnr` trading weekly (other seat's session); `trig_018wP6XTPmf9DLnxrG4RpGVh` docs reconciliation (poke-only, schedule-less).

PARKED PRs (open at 2026-07-12T20:53Z; landing path owner-click on green):
- #291 `9e78133` browse-interaction goldens mint (D-0034 capstone) — base now main.
- #292 `bbffe72` Mining slice-3: vault/stash/unstash/vaultupgrade — stacked, after #289 (merged).
- #295 `0f81162` Settings-hub group select → read-only operator hubs (slice 4).
- #296 `3d91a54` Mining slice-4: forge/repair/quickcraft/cook/use — stacked on slice-3.
- #298 `c615818` checker: V010 settle-once fence (D-0078 successor) — NO check runs on head (verified 20:52Z); needs a CI kick (empty push or re-run) before owner-click.
- #299 `48fbf94` Mining slice-5: skills/skill/titles — stacked on slice-4.
- #300 `598fa03` Mining slice-6 (FINAL): build/buildlist/buildable/workshop/home — stacked on slice-5.
- Separate: #302 `21090d9` tournament-flow goldens — post-close peer-session PR (session_01W5GG3JsuSfdkEzEb7i192U), not this seat's; no CI runs on head when last checked (20:52Z).

in-flight: ban-compensator refuse-path fix dispatched to a worker session (expected branch `claude/ban-compensator-refuse-path`).

claims: 8 stale claims swept this commit (each verified merged at GitHub: #279, #270, #267, #284, #288, #277, #269, #282); live claim kept: `slice1-equip-loadout-character` (deep-mining ladder — #292/#296/#299/#300 still open; #286/#289 merged).

⚑ needs-owner (paste-ready):
1. D-0043 deep-game ports go/no-go — 25 mining + 15 fishing goldens; the only path to a fully-green report job (NB the mining slice stack #292→#300 covers the mining-deep surface; #286/#289 already merged).
2. Settings-prune corpus ratification for `btd6_strategy_submission_channel` + `skip_roles` (docs/review/admin-surface-audit-2026-07-12.md §8 — both shipped-dead parity artifacts, KEEP-ledgered pending ratification).
3. OWNER-ACTION 3 — ruleset/merge-queue (six-field record in the pre-close status at `694e056`).
4. OWNER-ACTION 5 — ANTHROPIC_API_KEY + AI_ENABLED (six-field record in the pre-close status at `694e056`).

Resolved since the predecessor heartbeat: seat-failsafe re-arm DONE (trig_01TuQrpMVpDCXB3K3VbjQUoA, above); sweep_paragon disposition landed (#280 merged 20:24Z).

next-2-tasks:
1. V010 checker wrap on #298 (incl. codex false-negative triage) + AIP-07/08 + karma view-lane `_target_id` + local env-drift hygiene (pytest missing in this container's interpreter, noted).
2. Owner-decision-dependent work (⚑ items above) once ruled.
