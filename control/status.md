# superbot-next · status
updated: 2026-07-12T20:20Z
phase: SEAT CLOSED — the SuperBot 2.0 coordinator seat is CLOSED per the owner ender v3.3 (2026-07-12, session-ender steps 4–5; this file is the successor's boot surface). Position at close: parity program **51 rows ported** (50 subsystem rows + the kernel coverage home), gate GREEN **427/427**, report **427/468** green / 468/468 replayable — the 41 non-green files are ALL owner-parked (40 D-0043 deep-systems: 25 mining-deep + 15 fishing-gear, + 1 btd6 sweep_paragon); corpus 468 = 465 imported + 6 minted − 3 retired (retirements coordinator-ruled, owner-vetoable and reversible — veto path in the pre-close status at `694e056`). Counts RE-VERIFIED at close against the latest completed main-push golden-parity run: main `2e448ee` run **29206693285** — gate job **86687223317** CI-LOG-VERIFIED: "gate: GREEN — all 427 golden(s) across 51 ported subsystem(s) replay clean" + "golden-parity gate: 51 ported / 1 pending" (pending table down to its last line, `_unmapped [41 goldens]`) + "check_parity_depth: OK — 51 subsystems (50 ported), kernel ported, 468 goldens" + integration 11 passed same job; report job **86687223305** same run: "green: 427/468 replayed cases match their golden" + "replayable: 468/468" + "ported: 51/52 subsystems" with `_unmapped 0/41 green [pending]` the ONLY non-green line ("report: RED — 41 golden(s) not yet at parity (EXPECTED …)" — red-by-design, non-required). NOTE: main was MOVING during this close-out — the owner was click-landing the parked queue (#266 `1b08bc8`, #267 `4628b3c`, #269 `a16cf00` merged mid-close); re-verify HEAD before trusting any count here.
health: green with the standing red-by-design `report` job (red until the two owner decisions on the parked `_unmapped` set land — ⚑ items 1–2 below); the golden-parity GATE is non-vacuous and GREEN (citations in the phase line). The full pre-close waypoint trail (wave records, lane records, ORDER records) lives in this file's previous revision at `694e056` — git history, not re-derived here.
kit: v1.15.0 (#294 `bd0fd17`, substrate-kit 1.14.0→1.15.0; `kit_version` 1.15.0 pinned in substrate.config.json:47; session bumps: v1.13.0 #251 `559a0d8` → v1.14.0 #260 `764a393` → v1.15.0 #294) · engaged: yes
last-shipped: COORDINATOR SEAT CLOSE-OUT (THIS PR — control fast lane: control/status.md + session card + telemetry row only, zero code). The durable session REPORT (SHIPPED with merge shas / PARKED / WALLS / FLAGS) is this PR's body — the owner-side copy. Session card `.sessions/2026-07-12-coordinator-close-out.md` + telemetry row ride this PR (Q-0194).
blockers: NONE order-shaped. Everything still parked is owner-decision-shaped — the ⚑ list below.
orders: acked=001–016 done=002–016 (unchanged by this close-out; the per-order trail is in the pre-close status at `694e056`).

ROUTINE DISPOSITION (verified at close):
- Coordinator wake trigger `trig_01KGcjLfZwGrpAyEyCpJFjnK` DELETED and verified absent — list_triggers paginated to exhaustion (944 triggers), 0 armed wakes remain on the coordinator session.
- Seat failsafe: the Builder failsafe cron `trig_01L5JBefGSCM1fUdwm4SRQnY` is DEAD (ended_reason `auto_disabled_env_deleted` — pre-existing, not changed by this close-out). There is NO live dead-man bridge for this seat; a successor boot needs an owner/fleet wake or a re-armed failsafe (⚑ item 6).
- Sibling failsafe crons (7) and business routines UNTOUCHED.
- Business crons recorded for the successor: `trig_01Jm57GAjNCFrYJn1oLMiYGE` kit-lab loop (`0 6 * * *`, fresh-session-per-fire — recorded, NEVER rebound); `trig_015aNMg5ncoSE2Roe4MKjQnr` trading weekly (`0 9 * * 5`); `trig_018wP6XTPmf9DLnxrG4RpGVh` docs reconciliation (poke-only).

PARKED-PR LIST (16 open PRs, snapshot 2026-07-12T20:15Z — point-in-time: the owner was click-landing this queue during the snapshot; states are job-level check reads at each head; landing path `owner-click` = all checks green with `report` red-by-design, one click to land):
- #300 `598fa039` Mining slice-6 (FINAL): build/buildlist/buildable/workshop/home — checks pending @ 29207126833 (ci) / 29207126816 (golden-parity) / 29207126821 (named-gates) on a fresh head; the prior head `27222be7` had a red `checkers` job (run 29206594331), since re-pushed twice. Landing path: owner-click once the pending runs go green; last of the sequential mining stack.
- #299 `48fbf942` Mining slice-5: skills/skill/titles — green (report red-by-design) → owner-click, after slice-4.
- #298 `c6158181` checker: V010 settle-once fence over the K7 money legs (D-0078 successor) — NO check runs on head at snapshot (CI never started); landing path: kick CI (empty push or re-run), then owner-click. Also the anchor of NEXT-2 baton item 1's adapter-lane remainder.
- #296 `3d91a54a` Mining slice-4: forge/repair/quickcraft/cook/use — green → owner-click, after slice-3.
- #295 `0f811626` Settings-hub group select → read-only operator hubs (SLICE 4) — green → owner-click.
- #292 `bbffe725` Mining slice-3: vault/stash/unstash/vaultupgrade — green → owner-click, after slice-2.
- #291 `6218bd19` parity: browse-interaction goldens mint (D-0034 interaction-golden capstone) — green → owner-click, after the browse stack (#270 → #279/#288) it pins.
- #289 `cb7bb8b1` Mining slice-2: descend/ascend/mineworld — green → owner-click, after slice-1.
- #288 `0448b92f` creature dex as declarative browse surface (D-0034 slice 3) — green → owner-click, stacked on #270.
- #286 `765128de` Mining slice-1: equip/unequip/gear/loadout/character — green → owner-click; base of the mining stack. NB the mining slice stack #286→#300 tracks the D-0043 mining-deep surface (⚑ item 1).
- #284 `c8e2e5d7` casino: Texas Hold'em play layer — checks pending @ 29207125269 (ci) / 29207125258 (golden-parity) / 29207125249 (named-gates) after rebase onto #267's merge; prior head `4894820d` was green. Landing path: owner-click on green.
- #282 `c5ed59ec` Creature battles: Accept resolves the fight + win/loss records — green → owner-click.
- #280 `94bf940a` parity: btd6 !paragon calculator `_unmapped` re-home onto the ported btd6 row — green → owner-click; overlaps ⚑ item 2 (sweep_paragon disposition).
- #279 `85b07812` inventory detail browse controls on the shared BrowserView engine — green → owner-click, stacked on #270.
- #277 `1ff3ffd6` fix(rps): restore the dropped cross-game tournament guard (stranded-pot bug) — green → owner-click.
- #270 `c2388d16` shared BrowserView engine — generic sort/filter/paging for List/Table blocks (K8) — green → owner-click; base of the browse stack (#279/#288/#291).

⚑ needs-owner (paste-ready):
1. D-0043 deep-game ports go/no-go — 25 mining + 15 fishing goldens; the only path to a fully-green report job (games-project overlap noted; NB the open mining slice stack #286→#300 covers the mining-deep surface).
2. sweep_paragon disposition — port or retire (open #280 re-homes the !paragon calculator surface onto the ported btd6 row).
3. Settings-prune corpus ratification for `btd6_strategy_submission_channel` + `skip_roles` (docs/review/admin-surface-audit-2026-07-12.md §8 — both shipped-dead parity artifacts, KEEP-ledgered pending ratification).
4. OWNER-ACTION 3 — ruleset/merge-queue (six-field record in the pre-close status at `694e056`).
5. OWNER-ACTION 5 — ANTHROPIC_API_KEY + AI_ENABLED (six-field record in the pre-close status at `694e056`).
6. Seat failsafes — the Builder seat's own failsafe cron is dead (`auto_disabled_env_deleted`); a successor boot needs an owner/fleet wake or a re-armed failsafe.

NEXT-2-TASKS BATON (for the successor seat; neutral pointers, no ordering beyond the numbering):
1. Moderation ban-compensator refuse-path fix (guard recipe in `.sessions/2026-07-12-order004-live-drive-evidence.md`, flagged from #297) + the adapter-lane queue remainder: V010 checker wrap on #298 incl. codex false-negative triage, AIP-07/08, the karma view-lane `_target_id`, and local-Postgres env-drift hygiene.
2. The owner-decision-dependent work above (⚑ items 1–3) once ruled.
