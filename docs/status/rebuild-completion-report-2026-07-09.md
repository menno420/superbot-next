# SuperBot Rebuild — Sequence C Completion Report (2026-07-09)

> **Status:** `reference` — final completion report for steps 7–13 of the
> canonical plan (`superbot docs/planning/rebuild-canonical-plan-2026-07-06.md`).
> Compiled from the merged tree at main `e5316d9`, the decision ledger
> (`docs/decisions.md`), and the rebuild progress log. Source + merged PRs win
> over this doc (Q-0120).

## 1. Executive summary

Steps 7–13 of the canonical plan are **complete**:

- **Step 7** — substrate-kit extracted to `menno420/substrate-kit`; superbot-next
  adopted fresh from the kit dist (PR #1), later upgraded to kit v1.0.0
  (PRs #42/#44/#46).
- **Steps 8–10** — kernel S0–S15 across bands K0–K9 + strand 3
  (PRs #2–#17): config/observability, namespace registry, manifest compiler +
  snapshot, DB seam + idempotency, event outbox, lifecycle/health/poll host,
  authority engine, workflow engine + settings resolution, interaction runtime
  (+S9b panel runtime, PR #11), durability band, security/abuse rubric,
  data-integrity invariants, credential lifecycle, backup/DR/rollback,
  platform governance.
- **Step 11** — layer V (PRs #18–#20): 465 parity goldens imported
  byte-identical, born-red `golden-parity` workflow (gate + report jobs),
  A-16 depth checker, sim runner + oracles + A-3 navigation golden + V-2
  procedure, tiered `verified_live` registry.
- **Step 12** — K10 AI invocation kernel (PRs #21–#23): task registry replacing
  the closed AITask enum, provider port (anthropic/openai/deterministic),
  never-raises gateway pipeline, NL front-end, tool orchestration, hoisted
  grounded-answer engine, A-17 socket-denied eval harness.
- **Step 13** — Sequence C port bands 1–7, all merged (PRs #24–#29, #32–#41,
  #43, #45, #47–#49): every band shipped, all 17 legacy AI task ids claimed
  byte-identical, every K10 installable port has a real installer, both
  knowledge domains carry required deterministic A-17 eval gates.

### Verified totals (from source at main `e5316d9`)

| Metric | Value |
|---|---|
| Merged PRs | **49** (#1–#49, every number exists; 50 commits on main = 49 squash merges + the seed intent commit) |
| Tests green | **999** (pytest collect at e5316d9; golden-parity `report` job is the only intended red — by design) |
| Checker gates | **22** `tools/check_*.py`: 19 in `ci.yml` (+ kit `check --strict`, lockfile-fresh `--regen`, pip-audit), `check_parity_depth` in `golden-parity.yml`, `check_compat_frozen` in `named-gates.yml` (6 §6 named-gate jobs), `check_rotation_due` = non-gate ops CLI |
| Workflows | 5: `ci.yml`, `golden-parity.yml`, `named-gates.yml`, `backup-db.yml`, `restore-verify.yml` |
| Migrations | **24** (`0001_idempotency_keys` … `0024_ai_review_presets`; checksums pinned) |
| Manifests | **41** under `sb/manifest/` |
| Decision ledger | **D-0001 … D-0048** (48 entries, `docs/decisions.md`) |
| Snapshot hash | `sha256:b2e5b645995ef810373fc1bc3c0733a3603730876a0cba9f3e6ea215b2150cc4` |
| Sim pins | **575** assignments in `sim/sim-gate-baseline.json` (legacy-seed Exempt overlays under `manifest/layout/`) |
| V-2 coverage | **90.00%** tier-1/2 over 700 units (`tools/grammar_fit/RESULTS.md`; spike line 85.26%/95) |
| Parity corpus | **465 goldens**, 49 subsystem rows in `parity/parity.yml`, all `pending` (0 flips — honest A-16; replay adapter built in PR #27) |
| Config / credentials | 52 `CONFIG_FIELDS`; 14-row `CREDENTIAL_REGISTRY` |
| Oracle pin | superbot main @ `7f7628e12f3b89c5c2a1fbdcfb039787df269e20` (unchanged all run) |

## 2. Repo map (sb/ top levels × what each band contributed)

| Path | What it is | Contributed by |
|---|---|---|
| `sb/spec/` | Frozen grammar leaves: config, observability, refs/roles, events, outcomes, authority, confirmation, panels, scheduler, draft, cost, invariants, credentials, versioning, governance, commands, settings, setup | S1–S15 (PRs #2–#17); facets: band 1 (#24), band 2 (#28) |
| `sb/namespace/` | K1 registry: 16 kinds, reservations, tombstones, bootstrap commands | S2 (#3), S7 (#8) |
| `sb/kernel/config` + `db/` | preflight→Config, data-plane rails, pool/txn seam, migrations runner, idempotency | S1 (#2), S4 (#5) |
| `sb/kernel/outbox` + `events_bus` | exactly-once outbox, relay/reaper, enqueue_all, in-process EventBus | S5 (#6), S9 (#10) |
| `sb/kernel/lifecycle` + `scheduler/` | 7-phase lifecycle, PollSupervisor, due-queue/misfire, user automation | S6 (#7), S10 (#12) |
| `sb/kernel/observability` | metrics registry (47 families), redaction hoist, findings, alerts | S1 (#2), S6 (#7) |
| `sb/kernel/authority` | 10-field AuthorityDecision, owner override, channel access, transparency | S7 (#8) |
| `sb/kernel/workflow` | CompoundOpSpec/run/run_ref/apply/preview, central audit spine | S8 (#9) |
| `sb/kernel/interaction` + `panels/` | resolve() chokepoint, 6 surface adapters, egress port (RC-21), panel engine + §3.4 router, G-10 modals | S9 (#10), S9b (#11), S11 (#13), armed #35 |
| `sb/kernel/settings` + `versioning` + `draft` + `invariants` + `privacy` + `credentials` | F-3.4 read engine, version policy, draft pipeline, sweep lanes + quarantine, erasure/export, rotation | S8 (#9), S10 (#12), S11–S13 (#13–#15) |
| `sb/kernel/ai/` | K10: task registry, gateway, providers, NL engine, grounding, orchestration, evals | K10 (#21–#23) |
| `sb/kernel/platform_governance` | intent DEGRADE markers, guild-cap latches | S15 (#17) |
| `sb/adapters/` | http/health, discord (tier read, responders, panel view, egress, NL shell), **parity replay adapter** | S6 (#7), S9–S11, #27, band 7 (#49) |
| `sb/app/` | boot gate legs A/B/C, build_runtime, tree_sync, poll/panel hosts, verify_boot; **no main() yet — by design** | S3–S14 |
| `sb/domain/` band 1 | settings (124-key vocab), help, diagnostic, setup skeleton | #24–#26 |
| `sb/domain/` band 2 | moderation, server_logging + the operator-spine eight | #28–#29 |
| `sb/domain/` bands 3–4 | economy/treasury/inventory; xp/karma/community/spotlight/leaderboard | #32–#35; #36 |
| `sb/domain/` band 5 | governance (43 subsystems/102 caps), role family, platform/control, proof_channel | #37–#39 |
| `sb/domain/` band 6 | games substrate (g1 sessions, wager, game-XP), blackjack, rps, farm/creature/mining/fishing, counting/chain, deathmatch/casino | #40–#41, #43, #45 |
| `sb/domain/` band 7 | btd6 (74 data blobs + grounding + 16-probe gate), projmoon (minted 12-probe gate), media/video, ai surface | #47–#49 |
| `parity/`, `sim/`, `verification/` | 465 goldens + depth manifest; sim runner/oracles/records; verified_live registry | #18–#20 |
| `tools/`, `migrations/`, `compat/`, `manifest/layout/` | 22 checkers + manifest compiler + reverse importers; 24 migrations; compat-frozen pin (§5.3); layout lock overlays | S3+ throughout; #35 (compat) |

## 3. Consolidated owner-flag list (outstanding, deduplicated)

Items marked **[SATISFIED]** need no action; they are listed for closure.
Provenance: progress-log flags 1–52 + build-brief §8; owner rulings applied in
PR #30 (`c78a87b5`) and the ruleset fix (closed by PR #35/#36 merging).

### (a) Repo settings / CI

1. **CODEOWNERS coverage additions**: route `parity/` (A-16 exemption rows),
   `compat/compat-frozen.json` (§5.3 pin — amended in #36/#38/#39/#41/#43/#45/#47–#49),
   and `docs/planning/escape-hatch-baseline.json` (A-19) to owner review.
   CODEOWNERS itself exists (owner PR #31); these paths are not yet routed.
2. **[SATISFIED]** Required-status-check designation: ruleset fixed mid-band-4
   (flag 40 → 42; auto-merge fires end-to-end since PR #36). Standing rule:
   golden-parity **`gate`** may be required; **`report` must never be**
   (born red by design).
3. **Public→private flip** for superbot-next: raised at step 8, HARD before
   CUT-2 (step 15 artifacts carry real balances); also the free-Actions cost
   checkpoint.

### (b) Secrets / credentials / provisioning

4. `SB_PROD_ATTEST` custody mechanism (CL-5b) — presence-gated SecretSpec built;
   custody model = owner call, re-decide near CUT-1.
5. `DISCORD_WEBHOOK_URL` secret for the A-8 WebhookReporter twin (spec +
   redaction chokepoint built in `sb/kernel/observability/alerts.py`).
6. Backup arm-up: repo var `BACKUP_ENABLED=true`, secret `DATABASE_PUBLIC_URL`,
   artifact-retention max → 400 (`backup-db.yml` / `restore-verify.yml`).
7. AI platform arm-up: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` secrets +
   `AI_ENABLED` flip (dormant until keyed; deterministic default provider).
   First live NL reply also needs the CUT-1 emitter/shell wiring (flag 52).
8. `CONTROL_API_TOKEN` provisioning (Railway + dashboard side) when the
   `/control/*` HTTP bridge ports (SecretSpec + credential row landed dormant,
   PR #39).
9. Railway projects (production + shadow): sealed secrets, region pins,
   backups per Q-D14, project tokens, `EXTRA_OWNER_USER_IDS` env (Q-0245).
   Not needed before CUT-1.
10. RotationProvider wiring + rotation-cadence ops schedule at CUT-1
    (`tools/check_rotation_due.py` is the runnable; CL-2 brake narrowed per
    PR #30: revocation agent-runnable in compromise response, deletion
    ask-first).
11. **[SATISFIED]** Test guild + test-bot token: available owner-side since
    band 6 session 1 (flag 48) — ready for the testing phase; live testing
    starts when the owner/coordinator schedules it.

### (c) Posture ratifications / vetoes

12. **OD-1 delivery-class set**: built v1 = only `audit.action_recorded`
    AT_LEAST_ONCE; the recommended set (+ `xp.awarded`, `xp.level_up`,
    `economy.balance_changed`) is now fully buildable (flag 43) — one ruling
    flips delivery + arms the §12.6 conn-threading prerequisite per producer.
13. Version-policy default for bears_value stores: built default
    `REJECT_AND_PRESERVE` stands until ruled.
14. `audit_log` retention/pruning posture (spec 07 §5) — includes the band-6
    counting/chain audited hot paths (flag 49: shipped was deliberately
    unaudited; busy channels grow the audit spine).
15. Store-drop `disposition` values: per-retirement owner calls (mechanism
    built; `store_retirements.yml` empty).
16. §8-a owner-override scope (member-guilds-only built) + §8-c transparency
    sink wording / durable-row promotion (v1 = operator-notice only).
17. Q-D24: option A shipped (`session_transition` + NATURAL_KEY fence) under
    ships-until-you-rule; easy un-bless if B is picked.
18. S12 invariants: Q1 posture (built = permanent report-only lane),
    Q2 (hard-vs-advisory CUT gates), Q3 per-invariant money directions
    (`ground_truth_store` declarations).
19. Q-0243 pricing session: A-13 category-B ACTION fence stays until it rules;
    also owns AI spend posture (per-request budgets built; no spend
    ledger/ceiling exists).
20. Model routing: PR #30 K10(b) applied (haiku-4-5 fallback). Open tails:
    the Sonnet trio (settings.propose / moderation.assist /
    btd6.strategy_review) is a ledgered judgment call — veto flips rows in
    `sb/kernel/ai/routing.py`; gpt-4o-mini flagged unreliable, replacement TBD.
21. Three sim "why-it-won" ratifications (hub topology, settings grouping,
    dense-panel layout) — bands shipped legacy-seed Exempts; real runs gated on
    telemetry-sidecar capture on the live bot (owner schedules; sidecar is
    seeded-empty).
22. G-19 amendment flip per A-9(2) (agent-authored registry edit, PR #26) —
    owner eyeball invited, vetoable.
23. `!kick` now carries ConfirmationSpec (frozen §2.7 deviation from shipped,
    D-0029) — veto = rule a kick compensator into existence or relax §2.7;
    otherwise kick goldens get exemption rows at flip time.
24. Extension-management commands (cog/loadall/unloadall/syncslash)
    deliberately not ported (D-0030) — owner eyeball invited.
25. Shipped blackjack PvP double-payout not reproduced (D-0042: port settles
    pot only) — if wanted as a feature, small op change; veto path in ledger.
26. RPS stats scope: quick-play writes stats (the shipped site); PvP/tournament
    stats ride the tournament-orchestration port if wanted (flag 50).
27. Governance capability-override write surface: K7 lane exists
    (administrator floor), no command/panel routes at it (shipped had none) —
    optional settings-hub surface (flag 46).
28. BTD6 tool catalogue: only the 8 deterministic rows with real handlers are
    model-visible (D-0048) — wanting the other ~27 at cutover rides the named
    data-layer successors (flag 51).
29. **[SATISFIED]** Ruled in PR #30 and applied (ledger entry of 2026-07-09,
    PR #34): rubric v2 adopted;
    CL-1/CL-3 ratified, CL-2 narrowed; S14 Q1 (24h pg_dump) + Q3 (N=7d);
    PG-1/3/4/5 as built; V-5 debt-list + delegated signer.

### (d) CUT-1/2/3 cutover items (steps 14–17 — untouched by design)

30. **CUT-1** (step 12 tail): write main()/composition root (boot order
    documented across S7–S9/K10/band-7 notes + §4 below), boot container-only
    on the test-bot token, arm the live-adapter ports (role/proof/channel
    actions, message feeds, NL shell, review-feed poster + 👎 listeners,
    strategy-review Sonnet caller), register the last kernel erasure body
    (`kernel.ai.scrub_decision_audit`, flag 18), rotation schedule (item 10).
31. Telemetry-sidecar capture window on the OLD bot (design-spec §2.10.4
    Phase-0.5) — unblocks item 21's sim runs.
32. **CUT-2** (step 15): prod-data import dry-run + published reaction window,
    live permission census (`tools/permission_census.py` GET wiring; PG-5
    same-app-id reuse is a confirmed NON-NEGOTIABLE constraint), verify-import
    (S12 `run_verify_import`), public→private flip BEFORE artifacts (item 3).
33. **CUT-3** (step 17): token swap, N=7d rollback window
    (`platform.cutover_flip_ts` written once at flip), A-18 coverage-debt
    publication (`tools/check_verified_live.py --debt-list`), A-20 day-8–10
    checklist. **Re-flag at CUT-3 planning**: S14 Q2(i) was ruled a HARD gate
    on restore-verify — nothing consumes the workflow conclusion yet.
34. Stage-2 walk continuation (owner-live): the full namespace corpus harvest
    (43 subsystem keys, legacy custom_ids, settings vocab, common-word bans)
    is still the seed-only `legacy_reservations.json`; `tools/compute_corpus.py`
    consumes the walk export.

## 4. Remaining engineering work (non-blocking; named successors)

1. **Parity flips — 0/465** (A-16, honest). The replay adapter exists
   (PR #27: `sb/adapters/parity/` fake-HTTP over the real pipeline; 465/465
   cases reconstructable). Flips need the per-subsystem flip-review pass over
   the Postgres-serviced harness: run the `report` job for real ratios, add
   exemption rows for ledgered deviations (kick-confirm class, nav:* ids,
   RESULT_CARD renders), flip `pending→ported` as each corpus greens
   (`check_parity_depth --write-ratchet` as the flip PR's last commit).
   Cross-subsystem noise in old prefix goldens (xp + ai_decision_audit rows)
   resolves now that all bands exist.
2. **Live/message-band adapter consumers** (the one recurring successor class):
   message feeds (xp chat award, counting, chain, NL shell arming),
   duel turn-timeout view, blackjack/RPS tournament orchestration,
   poker table engine (D-0045), creature battle engine (D-0043),
   review-feed poster + 👎/reply listeners (D-0048), reaction sign-ups,
   role-menu posting, subscribe(bus) roster + IN_MEMORY interval arming at the
   composition root.
3. **Deep-system successors** (bounded, ledgered): D-0043 deep mining
   (17 modules/4,895 lines) + fishing gear/venues (12/1,788); D-0046 btd6
   ingestion subsystem + deep stats/upgrade-detail/CT/maps-modes/paragon
   surfaces; D-0047 limbus numeric ingest + youtube fetch/cache lane
   (+ `YOUTUBE_API_KEY` credential row); D-0048 remaining ~27 tool rows,
   afford_check branch, typed AI policy overlay tables, AI mutation services.
4. **BrowserView engine** (flag 41): named-but-unbuilt K8 work — interactive
   sort/filter/paging for Table/List blocks; every browse surface (inventory
   detail, leaderboards, dex, fishlog) ships RESULT_CARD text consistently.
5. **main()/composition root + CUT-1 wiring**: no main() exists by design.
   Boot order: preflight → install_owner_config → install_secret_presence →
   flags.install_ai_config → install_ai_platform() → boot-gate leg A →
   db.init → build_registry → start_health_server → build_runtime (LIVE
   manifests — build_runtime snapshot-index gap D-0028 stands) →
   error handlers → lifecycle STARTING → gateway → RUNNING + boot-gate legs
   B/C → poll supervisor + subscribe rosters + recover_escrow + intent-degrade
   markers before capability registration.
6. Smaller named items: band-5 `/control/*` HTTP bridge (D-0041); band-1
   remainder (setup wizard flows, A-15 guild restore, help overlay lanes,
   deep-diagnostic fleet, ~14 orphan-spec extraction, settings edit panel
   actions); sim overlay loading into manifest_compile (labeled follow-up in
   the V-3 ledger entry); verify_boot →
   fake-HTTP harness pointer (spec 13 §2.2(a), labeled).

## 5. Suggested testing order (owner's subsystem-by-subsystem phase)

Ordered by dependency + risk: prove the kernel floor first, then the platform
that everything configures through, then the operator spine, then value-bearing
domains, then engagement/games, AI last (needs keys). Each step: what to test /
parity goldens covering it / what a `verified_live` sign-off mints (tiers per
A-18: automated evidence = `prefix_twin_live` + `pipeline_replay` per Q-0244;
human lane never blocks).

1. **Kernel boot + health + DB + outbox** — boot on the test token (CUT-1
   smoke): preflight rails, migrations 0001–0024 apply + checksum verify,
   `/ready` flips 200 only at RUNNING, `/metrics` renders, outbox relay
   delivers the audit canary, due-queue fires, boot-gate legs A/B/C green.
   Goldens: none direct (kernel = the 9-table coverage home in `parity.yml`);
   evidence = `sb/app/verify_boot.py` profile + restore-verify workflow.
   Mints: automated-tier kernel rows (the dashboard's denominator).
2. **Settings + help + diagnostic + setup** (band 1) — declare/read/bind via
   the settings hub, help projection lists every manifest, diagnostic status
   reads lifecycle/findings, setup sections render. Goldens: settings 4,
   help 3, diagnostic 37, setup 8, quicksetup 1 (53 total — the richest
   early corpus). Mints: automated rows for the platform's own surfaces;
   everything later depends on these rails.
3. **Moderation + logging** (band 2 slice 1) — warn/timeout/kick(confirm)/
   ban ladder in-txn, mod_logs/warnings rows, logging fan-out to bound
   channels. Goldens: moderation 8, logging 7. Mints: automated rows;
   kick-confirm deviation (item 23) gets its exemption or veto here.
4. **Operator spine eight** (band 2 slice 2) — admin reads, channel ops,
   cleanup, automod/security decision cores, welcome/counters templates.
   Goldens: admin 2, channel 1, cleanup 3, automod 1, security 1, welcome 1,
   counters 2, image_moderation 1, server_management 2.
5. **Economy family** (band 3) — daily/work/pay/buy one-txn balance+ledger,
   treasury contribute/disburse, inventory merge, INV-F reconciliation sweep
   clean, panel actions + G-10 modals. Goldens: economy 6, treasury 2,
   inventory 1 (curated: economy.balance_and_daily). First value-bearing
   sign-offs; exercises reverse importers' source tables.
6. **XP + karma + community** (band 4) — chat award cooldown+rng, level-up
   fan-out, karma ladder, leaderboards/providers, INV-G/INV-K sweeps.
   Goldens: xp 3 (curated xp.chat_award), karma 8, community 2,
   community_spotlight 1, leaderboard 1.
7. **Governance + roles + platform** (band 5) — subsystem visibility chain,
   capability overrides, role feasibility/automation, temp grants + expiry
   sweep, command-access policy, proof_channel locks, teardown hooks.
   Goldens: role 1, proof_channel 3, general/utility sweeps.
8. **Games** (band 6) — wager first (blackjack/RPS: escrow at accept,
   settle-once FOR-UPDATE, refund on decline; g1 session routing), then
   checkpoint (farm/creature/mining/fishing catch-commit), then message games
   (counting/chain decision engines), deathmatch, casino views;
   games:session_gc + recover_escrow. Goldens: blackjack 2, rps_tournament 1,
   games 2, farm 1, creature 5, mining 2, fishing 2, counting 3, chain 7,
   casino 2. Highest state-machine risk; money paths already proven at step 5.
9. **Knowledge + AI last** (band 7 — needs `ANTHROPIC_API_KEY` + `AI_ENABLED`,
   items 7/30): deterministic first (A-17 gates already required-CI: btd6 16
   probes, projmoon 12), then live NL shell (mention → grounded answer →
   verify_and_regenerate_once → delivered reply charged), review loop
   (👎/corrections), presets, strategy submit/review, routing (haiku default,
   Sonnet trio). Goldens: ai 20, btd6 39, project_moon 10+1. Mints the
   human-lane rows (answer quality) as debt-list entries — never blocking.

Cross-cutting during all steps: flip parity rows per A-16 as each subsystem's
goldens replay green (§4.1), and mint `verified_live` records per surface —
the CUT-3 debt list (`--debt-list`) is the published remainder.

## 6. Pointers

- Decision ledger: `docs/decisions.md` (D-0001…D-0048); owner rulings PR #30.
- Open owner questions: `docs/question-router.md`.
- Parity dashboard: `parity/parity.yml` + the golden-parity `report` job.
- Compat surface pin: `compat/compat-frozen.json` (owner-review artifact).
- Ops runbooks: `docs/operations/{credential-lifecycle,rollback-playbook}.md`.
