# Old vs. New: superbot → superbot-next — Diff Overview

> **Status:** `reference` — point-in-time diff overview compiled 2026-07-09; a durable
> record for later owner review. Source, merged PRs, and `docs/decisions.md` win over
> this doc.

- **Date:** 2026-07-09
- **Old repo:** `menno420/superbot`, default branch @ `f18db769` (parity oracle pinned at `7f7628e1`)
- **New repo:** `menno420/superbot-next`, `main` @ `e8d393f` (completion-report totals stated against `e5316d9`, the 49-PR merge point)
- **Sources consulted:** `docs/status/rebuild-completion-report-2026-07-09.md` (read in full), `docs/decisions.md` (all 48 entries), `parity/parity.yml` + `parity/COVERAGE.md`, `manifest.snapshot.json` (compiled totals), all 41 `sb/manifest/*.py` sources, both repo trees, the old repo's `disbot/config.py` cog list and a full decorator scan of `disbot/cogs/`.
- **Citation convention:** decision-ledger entries are cited as "ledger NNNN" — resolve each one in `docs/decisions.md` under the matching D-numbered heading. (This repo's doc checker stamps each decision ID at exactly one home doc; the completion report already stamps most of the IDs this overview relies on, so this doc cites them by number instead of repeating the stamped token.) Pull requests are cited as #NN.
- **Honesty notes on coverage:** the old bot's "479 commands" figure comes from a decorator scan of the cog tree; dynamically registered commands (notably the unified `/btd6` tree built programmatically) are undercounted, and panel buttons/selects/modals are not counted at all. Parity ratios and per-subsystem golden counts are taken from the completion report and `parity/COVERAGE.md` as written, not independently re-measured. Where a subsystem mapping is uncertain it is marked as such rather than guessed.

## Executive summary

The old bot (`superbot`) is a large, organically grown Discord bot: ~243,500 lines of Python in 881 files, 58 plug-in modules ("cogs"), 104 database migrations, and roughly 479 registered commands — later decomposed in place into a disciplined layered monolith, but still fundamentally a codebase you understand by reading it. The new bot (`superbot-next`) is a ground-up rebuild of the same product on a spec-driven kernel: every subsystem is *declared as data* (a manifest), compiled and hash-pinned, and runs on eleven shared kernel bands (config, namespaces, database, events, lifecycle, authority, workflows, interactions, durability, AI) instead of each subsystem carrying its own plumbing. 50 pull requests landed the whole rebuild; 999 unit tests are green; a 48-entry decision ledger records every judgment call; 465 recorded behavior transcripts ("goldens") from the old bot are replayable against the new one. Functional coverage is broad but deliberately shallower in places: all major command surfaces exist (276 compiled commands across 41 subsystems), but the deepest game systems (mining depth, fishing gear ladder, poker engine, creature battles, tournaments), the live Discord adapters, and the actual `main()` entrypoint are named successor work — the new bot cannot boot against Discord yet, by design, until cutover step CUT-1. A handful of behaviors were changed on purpose (each with a ledger entry and an owner veto path), most visibly: `!kick` now requires a typed confirmation, the runtime cog-load/unload commands were retired, and blackjack PvP no longer mints house coins on top of the pot. Nothing has been switched over: the old bot is still the production bot, and every parity row is honestly `pending`.

---

## 1. Architecture, old vs. new

### The old bot: a layered organic monolith

- **Shape:** one process (`disbot/`), 58 cogs loaded in a fixed order from `config.INITIAL_EXTENSIONS`, with an enforced dependency direction `cogs → services → core/runtime` (checked by `scripts/check_architecture.py`). Cogs are Discord plumbing; ~230 service modules hold domain logic; ~35 view packages hold UI.
- **Composition root:** `disbot/bot1.py` (63 KB) — a hand-written startup script that wires everything: DB pool + migrations, a runtime-instance lock so only one replica runs, the message pipeline, health server, supervised background tasks, then the 58 cogs. *Practically: the boot order lives in one big file you must read top to bottom, and correctness depends on that order being right.*
- **Database:** Postgres via asyncpg, **104 sequential SQL migrations**, per-domain accessor modules. *Practically: the schema is the accumulated history of three-plus generations of features.*
- **Events:** an in-process `EventBus` — async handlers with a 5-second timeout. If the process dies mid-handling, the event is gone. *Practically: cross-subsystem reactions (level-up feeds, spotlight updates) are best-effort.*
- **Permissions:** a `governance/` engine plus a bootstrap cog that must load first to install the command-admission guard, and a global `before_invoke` hook. *Practically: access control is central, but it is central because a specific cog loads first — a runtime convention.*
- **Panels:** a large panel/anchor runtime (persistent panels, DB-stored message anchors so panels are edited rather than re-sent, live update scheduler, panel recovery after restart). *Practically: the bot's most distinctive UX — always-fresh interactive panels — rides on ~10 cooperating runtime modules.*
- **AI:** an AI kernel under `core/runtime/ai/` — a "never raises" gateway (flags → safety → redaction → routing → provider → metrics → degrade) with Anthropic/OpenAI/deterministic providers, plus ~25 AI service modules. The grounded-answer engine (verify facts before answering) lives inside the BTD6 package and is borrowed cross-domain.
- **Scheduling:** four different mechanisms coexist (an env-gated scheduler service, six `discord.ext.tasks` loops, hand-written sleep loops, and in-memory one-shots that are lost on deploy). *Practically: "will this timer survive a restart?" has four different answers.*
- **Known warts the rebuild plan itself cites:** import-time token crash in `config.py`; no durable event delivery; the settings-resolution engine is load-bearing but organic.

### The new bot: a spec-driven kernel

- **Shape:** `sb/` with three tiers — `sb/spec/` (frozen grammar: the vocabulary every declaration is written in), `sb/kernel/` (eleven shared engines, bands K0–K10), `sb/manifest/` + `sb/domain/` (41 subsystems declared as data, implemented as ports). *Practically: a subsystem is a description, not a plug-in — you read one manifest file and know its entire surface.*
- **Manifest compiler (K2, PR #4):** every subsystem's commands, settings, events, stores, and panels are declared in a `SubsystemManifest` and compiled by a 9-pass pipeline into `manifest.snapshot.json` with a pinned hash (`sha256:b2e5b645…`). A "manifest compiler" means: the bot's whole surface is built like a build artifact — if code and snapshot drift, CI goes red before anything runs. *Practically: no surprise commands, no shadowed names, no undeclared settings — ever.*
- **Namespace registry (K1, PR #3):** one `validate()` oracle for every name in the system (16 kinds), with reservations and tombstones so a deleted name can't be silently reused.
- **DB seam (K3, PR #5):** a fresh, checksum-pinned migration chain (**24 migrations**, vs. 104 accumulated) plus an idempotency-key contract so retried operations can't double-apply.
- **Event outbox (K4, PR #6):** events are written to a database table *in the same transaction* as the change that caused them, then relayed exactly once. An "outbox" means: if the bot crashes between "coins deducted" and "announcement posted", the announcement still happens after restart. *Practically: cross-subsystem effects become guaranteed instead of best-effort.*
- **7-phase lifecycle + one poll host (K5, PR #7):** a single supervised `PollSupervisor` replaces the old four scheduling mechanisms; `/ready` only answers in RUNNING; timers live in a durable due-queue with misfire/catch-up rules.
- **Authority engine (K6, PR #8):** every permission question resolves through one function into a 10-field `AuthorityDecision` with an owner-override lane and a transparency contract. *Practically: access control is compiled into the dispatch path — there is no "guard cog that must load first".*
- **Workflow engine (K7, PR #9):** state-changing operations are declared `CompoundOpSpec`s run through one engine with a central audit row, preview/dry-run, and confirmation fences. *Practically: every write is audited the same way, and "this action needs a typed confirmation" is a declared property, not per-cog code.*
- **Interaction + panel runtimes (K8, PRs #10–#11):** one `resolve()` chokepoint with six surface adapters (slash, prefix, fuzzy, component, modal, natural-language) and one kernel panel engine behind a presenter port — the old ~10-module panel runtime redesigned as a single engine.
- **Durability band (K9, PR #12):** due-queue, versioned-state policy, draft pipeline, invariant sweeps + quarantine, erasure/export, credential rotation.
- **AI kernel (K10, PRs #21–#23):** the old gateway rebuilt with an open task registry (domains register AI tasks instead of a closed enum), a provider port, the NL front-end terminating in K8's adapter, and the grounded-answer engine *hoisted out of BTD6* into the kernel so any domain can use it. All 17 legacy AI task ids are claimed byte-identical.
- **Layer V — verification substrate (PRs #18–#20):** the parity goldens, a design-space simulator (575 pinned layout assignments), a grammar-fit ledger, and a `verified_live` sign-off registry — a whole verification layer that exists *outside* the boot chain. *Practically: "does the new bot behave like the old one" is a measured, gated question, not a vibe.*
- **Deliberately absent:** there is **no `main()`** — the composition root is CUT-1 cutover work (completion report §4.5). The new bot compiles, tests, and replays goldens, but does not yet connect to Discord. That is a planned state, not an omission.

---

## 2. Subsystem-by-subsystem: every old cog's fate

Fate vocabulary: **Ported (band N)** = re-implemented on the kernel in port band N; **Rebuilt-to-spec** = its job now belongs to a kernel band, not a subsystem; **Folded into X** = its surface lives inside another new subsystem's manifest; **Deferred** = named successor work in the completion report / ledger; **Not yet ported** = no manifest exists and no successor is explicitly named (parity row still tracks it); **Not ported (deliberate)** = ruled out with a ledger entry.

All 58 old cogs (from `disbot/config.py` `INITIAL_EXTENSIONS`) mapped to the new repo's 41-manifest roster:

| # | Old cog | Fate in superbot-next | Notable deltas / pointers |
|---|---|---|---|
| 1 | `bootstrap_access_cog` | Rebuilt-to-spec: K6 authority engine (#8) + K8 `resolve()` chokepoint (#10) | Command admission is compiled into dispatch; no "must load first" cog exists anymore |
| 2 | `admin_cog` | Ported, band 2 (#29, ledger 0030) | `cog`/`loadall`/`unloadall`/`syncslash` deliberately not ported (see §3); `coglist`/`slashes` re-homed as read-only views over kernel truth; 11 → 7 commands |
| 3 | `help_cog` | Ported, band 1 (#25, D-0026) | Projection-first port; `help.answer` AI task claimed; help overlay lanes deferred (report §4.6) |
| 4 | `settings_cog` | Ported, band 1 (#24, ledger 0025) | 124-key settings vocabulary minted; settings edit panel actions deferred (report §4.6) |
| 5 | `setup_cog` | Ported as skeleton, band 1 (#26, D-0027) | G-19 `WizardSectionSpec` frozen, the 10 registrants verbatim; full wizard flows + NL/AI setup advisor deferred (report §4.6) |
| 6 | `quicksetup_cog` | Folded into new `setup` subsystem | Single `setup` command (prefix+slash); quicksetup has its own parity golden |
| 7 | `server_management_cog` | Ported, band 2 (#29, ledger 0030) | Operator-spine eight member |
| 8 | `diagnostic_cog` | Ported, band 1 (#25, D-0026) — hub; `!platform` group split | The 39-subcommand `!platform` introspection group maps partly to the band-5 platform/control engine (#39); the deep-diagnostic fleet is deferred (report §4.6). Diagnostic carries the largest golden corpus (37) |
| 9 | `health_maintenance_cog` | Rebuilt-to-spec: K5 findings seam (#7) + K9 due-queue (#12) | Retention sweeps become declared durable tasks |
| 10 | `media_maintenance_cog` | Partly ported, band 7 (#48, ledger 0047) — shared video tasks | YouTube fetch/cache lane + `YOUTUBE_API_KEY` credential row deferred (report §4.3) |
| 11 | `logging_cog` | Ported, band 2 (#28, ledger 0029) as `server_logging` | Fan-out engine; `logging create` is declared but politely refuses until the resource-provisioning port arms (ledger 0029); new roster lists `enable`/`disable` subcommands not present in the old decorator scan |
| 12 | `security_cog` | Ported, band 2 (#29, ledger 0030) | Raid/join screening as declared policy; live join feed waits on member-event adapter (see §5) |
| 13 | `channel_cog` | Ported, band 2 (#29, ledger 0030) — declared, mostly fenced | All 17 commands declared verbatim, but most route to an honest "pending" refusal until the guild-action port arms (see §3) |
| 14 | `role_cog` | Ported, band 5 (#38, D-0040) | Thresholds, reaction-roles, menus as declared grammar; role-menu *posting* + reaction sign-up listeners wait on live adapters (report §4.2) |
| 15 | `role_grants_cog` | Folded into `role` (#38) | `temprole`/`temproles` in the role manifest; expiry via durable due-queue instead of a loop cog |
| 16 | `cleanup_cog` | Ported, band 2 (#29, ledger 0030) | Word-filter lanes ported; `cleanuphistory` is a pending terminal (see §3) |
| 17 | `automod_cog` | Ported, band 2 (#29, ledger 0030) | Policy + settings (15 keys) declared; live message scanning waits on the message-band adapter (report §4.2) |
| 18 | `image_moderation_cog` | Ported, band 2 (#29, ledger 0030) | Policy declared (8 settings); live scanning needs message band + AI keys (dormant until keyed) |
| 19 | `moderation_cog` | Ported, band 2 (#28, ledger 0029) | **`!kick` now confirmation-fenced** (see §3); audited K7 lanes; A-14 decide-at-port anchors |
| 20 | `chain_cog` | Ported, band 6 (#43, D-0044) | RS07 canonical-writer lanes; live channel feed waits on message band |
| 21 | `proof_channel_cog` | Ported, band 5 (#39, ledger 0041) | Prize sessions on kernel state |
| 22 | `ticket_cog` | **Not yet ported** | No manifest; parity row `ticket` exists (pending); not explicitly named in the deferred list — outstanding, mapping uncertain |
| 23 | `hermes_cog` | **Not ported** (dev-ops bridge) | Discord→Claude Code dispatch is tooling around the old repo, not bot behavior; parity row `hermes` exists; no successor named |
| 24 | `ux_lab_cog` | **Not yet ported** | Developer interface-gallery workbench; parity row `uxlab` exists; no successor named |
| 25 | `xp_cog` | Ported, band 4 (#36, D-0036) | Audited progression seam; chat XP award (the on-message feed) waits on message band (report §4.2) |
| 26 | `karma_cog` | Ported, band 4 (#36, D-0037) | One-transaction ledger discipline (INV-K) |
| 27 | `leaderboard_cog` | Ported, band 4 (#36, D-0038) | Provider-registry leaderboards; all 11 old aliases carried |
| 28 | `community_cog` | Ported, band 4 (#36, D-0038) | Router hub |
| 29 | `community_spotlight_cog` | Ported, band 4 (#36, D-0038) | Now consumes a *declared* `xp.level_up` event (old: ad-hoc EventBus wiring) |
| 30 | `welcome_cog` | Ported, band 2 (#29, ledger 0030) | Policy render + 11 settings; live greeting sends need the member-join feed (a DEGRADE-class intent capability, see §3) |
| 31 | `counters_cog` | Ported, band 2 (#29, ledger 0030) | Rename loop → durable scheduler; `counterpreset` is a pending terminal (see §3) |
| 32 | `starboard_cog` | **Not yet ported** | No manifest; reaction feed would wait on the reaction adapter anyway; not explicitly in the deferred list — outstanding, mapping uncertain |
| 33 | `counting_cog` | Ported, band 6 (#43, D-0044) | Verbatim number parser, full 10-command surface, audited hot path; live channel feed waits on message band |
| 34 | `general_cog` | **Not yet ported** | 8 delight commands (8ball, joke, trivia, …); parity row `general` exists; no successor named |
| 35 | `four_twenty_cog` | **Not yet ported** | Parity row `four_twenty` exists; no successor named |
| 36 | `utility_cog` | **Not yet ported** | 15 commands including `ping`, `info`, `poll`, `remind`, `purge`, `myprofile`; parity row `utility` exists; this is the most user-visible gap in the not-yet-ported set |
| 37 | `economy_cog` | Ported, band 3 (#32, D-0031) | Audited money seam, five stores, reverse importers, new INV-F mint/drain reconciliation invariant |
| 38 | `inventory_cog` | Ported, band 3 (#33, D-0032) | Unified browser; interactive sort/filter/paging (BrowserView engine) deferred (report §4.4) |
| 39 | `treasury_cog` | Ported, band 3 (#33, D-0032) | The pool between economy and governance |
| 40 | `blackjack_cog` | Ported, band 6 (#40, ledger 0042) | **PvP pays pot only; PvP double-down disabled; solo replay button dropped** (see §3); tournament orchestration waits on live adapters (report §4.2) |
| 41 | `casino_cog` | Ported (pure layers), band 6 (#45, ledger 0045) | Poker *table engine* (per-player live ephemeral messages) is named deferred work (report §4.2) |
| 42 | `rps_tournament_cog` | Ported, band 6 (#40, ledger 0042) | `rpssettings` values now durable settings (see §3); quickplay-only stats writes; tournament orchestration waits on live adapters |
| 43 | `deathmatch_cog` | Ported, band 6 (#45, ledger 0045) | On the g1 duel recipe; duel turn-timeout view deferred (report §4.2) |
| 44 | `mining_cog` | Ported (core loops), band 6 (#41, ledger 0043) | Full 37-command declared surface; deep mining systems (17 modules / 4,895 lines) are a named ledgered successor port (report §4.3) |
| 45 | `fishing_cog` | Ported (core loops), band 6 (#41, ledger 0043) | Full 20-command surface; gear/venues depth (12 modules / 1,788 lines) named successor (report §4.3) |
| 46 | `farm_cog` | Ported **complete**, band 6 (#41, ledger 0043) | Idle accrual on kernel checkpoint store |
| 47 | `creature_cog` | Ported (catch/collection), band 6 (#41, ledger 0043) | Dex + catching live |
| 48 | `creature_battle_cog` | Folded into `creature` (#41) — commands declared | `cbattle`/`cbrecord`/`cbattletop` in the creature manifest; the battle *engine* is deferred (ledger 0043, report §4.2) |
| 49 | `games_cog` | Ported, band 6 (#40, ledger 0042) | Games substrate: g1 dynamic sessions, escrow-once wager lanes, shared game-XP track, safer session GC (see §3) |
| 50–54 | `btd6_cog` + alias cogs (`btd6_reference_cog`, `btd6_events_cog`, `btd6_strategy_cog`, `btd6_ops_cog`) | Ported, band 7 (#47, ledger 0046) — one `btd6` subsystem | 74 data blobs, grounding, deterministic 16-probe eval gate, strategy memory; ingestion subsystem + deep stats / upgrade-detail / CT / maps-modes surfaces deferred (report §4.3); 8 of ~35 AI tool rows model-visible (ledger 0048) |
| 55 | `paragon_cog` | **Deferred** | Named inside ledger 0046's deferred "paragon surfaces"; no manifest yet |
| 56 | `project_moon_cog` | Ported, band 7 (#48, ledger 0047) as `projmoon` | Minted 12-probe eval gate; Limbus numeric ingest deferred (report §4.3) |
| 57 | `ai_cog` | Ported, band 7 (#49, ledger 0048) on K10 | Diagnostics surface + settings panel over the new kernel gateway |
| 58 | `ai_review_cog` | Folded into `ai` (#49, ledger 0048) | Review loop + vetted presets ported; the 👎-reaction/reply listeners and review-feed poster wait on live adapters (report §4.2) |
| — | *(governance engine — not a cog, `disbot/governance/`)* | Ported, band 5 (#37, D-0039) | Engine-only subsystem: 43 subsystems / 102 capabilities compiled onto the kernel; no commands (the old one had no write surface either, report §3 item 27) |

Also new-side but old-adjacent: `platform` (band 5, #39) absorbs command-access truth, the teardown registry (old `guild_lifecycle.py`), and the consistency report; the old `/control/*` HTTP bridge for the dashboard is **deferred-named** (ledger 0041).

---

## 3. Intentional behavior changes (each vetoable, each ledgered)

These are places where the new bot *deliberately* does not match the old one. Each has a decision-ledger entry and, where flagged, an owner veto path in the completion report §3. Parity goldens will diff on these on purpose — "the design winning," recorded for the flip review.

1. **`!kick` now requires a typed confirmation** — **ledger 0029** (veto path: report §3 item 23). The frozen confirmation grammar rules that irreversible actions need confirmation; kick has no honest compensator (you can't un-kick), while ban/unban compensate each other and warn/timeout are liftable. Old behavior: kick fired immediately.
2. **Extension-management commands retired** — **ledger 0030** (owner eyeball: report §3 item 24). `cog`, `loadall`, `unloadall` have no analog — subsystems are compiled manifests, not runtime-loadable cogs. `syncslash` is deploy-ops now (`sb/app/tree_sync.py` + boot-gate leg C). `coglist` and `slashes` survive as read-only views.
3. **Blackjack PvP pays the pot only; PvP double-down disabled** — **ledger 0042** (veto path: report §3 item 25). The old bot *also* ran the solo house credit/debit at each player's finish on top of the pot settle — minting house coins in a player-vs-player match. The port pays the pot only. PvP double-down is disabled because mid-match re-escrow had no shipped shape. Also dropped: the `blackjack:solo:replay` persistent button (replay = re-invoke the command).
4. **Intent posture: DEGRADE instead of crash** — **D-0018**. If a privileged Discord intent (message_content, members) is not granted, the old bot's dependent features would just be broken; the new bot declares which capabilities degrade (prefix commands, fuzzy matching, NL-on-message, member join/leave, member cache), refuses to register them, and posts a once-per-state-change degrade notice. Plus a latched alert near the ~75/90 unverified-bot guild cap.
5. **Pending-terminal pattern for un-armed operations** — **ledger 0030**. The 17 channel-management ops, `cleanuphistory`, `counterpreset`, and `serverstats`' deeper stats route to a `pending_handler` that gives an honest "BLOCKED / not armed yet" refusal instead of silently failing, until the guild-action/resource ports arm at cutover.
6. **`logging create` declared but refused** — **ledger 0029** (dev-4). Creating log channels needs the resource-provisioning port; until it arms, the command exists and explains itself.
7. **`rpssettings` values are now durable** — **ledger 0042**. The old bot kept RPS mode/best_of/entry_fee in memory — lost on every restart. They are now persisted `SettingSpec`s; `rpssettings` becomes a read view.
8. **Safer games garbage collection** — **ledger 0042**. If a refund fails during session cleanup, the new bot *keeps* the session row (so the money question stays answerable); the old bot cleared it anyway.
9. **RPS stats: quickplay-only writes** — report §3 item 26 (scope ruling recorded with ledger 0045's PvP stat stores). Tournament-mode stat writes are scoped out until tournament orchestration returns.
10. **Erasure forfeits escrow** — **ledger 0042**. When a user exercises data erasure while having coins staked in a live wager, the stake is forfeited (defined semantics where the old bot had none).

---

## 4. What the new repo has that the old never did

| Asset | What it means practically |
|---|---|
| **999 green unit tests** (`tests/unit/`) | The old bot's safety net was mostly the parity harness + manual testing; the new one shipped tests with every code PR |
| **22 CI checkers, 5 workflows** (`tools/check_*.py`; `ci.yml`, `golden-parity.yml`, `named-gates.yml`, `backup-db.yml`, `restore-verify.yml`) | Architecture rules, namespace collisions, cost posture, egress, migration checksums, slash caps etc. are machine-enforced on every PR (the old repo had ~50 process-gate scripts, but the new set gates a compiled system, incl. snapshot-drift = red) |
| **Parity goldens + replay adapter** (`parity/` 465 goldens; `sb/adapters/parity/`, PR #27, ledger 0028) | The old bot's recorded behavior replays against the new pipeline over fake HTTP — behavioral equivalence is testable offline |
| **Sim runner with 575 pinned assignments** (`sim/`, `sim-gate-baseline.json`) | Panel/layout design decisions were searched, scored, and pinned — layout drift is a CI failure, and 3 "why-it-won" ratifications are queued for the owner |
| **`verified_live` registry** (`verification/verified_live.yml`) | A tiered sign-off ledger for "a human saw this work live" — currently all `unverified`, to be minted during live testing; unfinished rows become a published debt list at CUT-3 |
| **Decision ledger** (`docs/decisions.md`, 48 entries) | Every architectural judgment, deviation, and deferral is append-only recorded with verdict/why/provenance — reviewable years later |
| **Hash-pinned lockfile** (`requirements.lock`, 1,015 `--hash` lines + pip-audit in CI) | Supply-chain pinning; the old repo had plain requirements.txt |
| **Credential lifecycle** (14-row `CREDENTIAL_REGISTRY`, resumable 3-txn rotation, blast-tier compromise runbook) | Token/key rotation is a designed procedure, not an incident response improvisation |
| **Backup/DR disposition** (`docs/operations/rollback-playbook.md`; weekly restore-verify workflow) | Daily pg_dump + monthly tier, honest RPO ≤ 24h, per-store rollback classes, reverse importers, and a CI job that *proves restores work* (`last_verified_restore_age` witness) |
| **Governance docs + compiled manifest + compat pin** (`CONSTITUTION.md`, CODEOWNERS, `manifest.snapshot.json`, `compat/compat-frozen.json`) | The working agreement, the bot's entire compiled surface, and the frozen compat pin are all owner-reviewable artifacts |
| **A-17 AI eval gates** (`tests/evals/`: 66 golden cases + BTD6 16-probe + ProjMoon 12-probe, socket-denied) | Deterministic, no-network AI answer checks required in CI — the old bot had evals but not as merge gates per knowledge domain |

---

## 5. What the old repo has that the new one doesn't (yet)

Each item below carries a named successor pointer — nothing here was silently dropped.

| Old asset | Status in superbot-next | Successor pointer |
|---|---|---|
| **Deep game systems** — mining depth (17 modules / 4,895 lines: grid world, structures, skills, titles, vault, market), fishing gear/venues (12 / 1,788), tournament orchestration (blackjack + RPS), poker table engine, creature battle engine | Core loops + full command surfaces ported; depth deferred | Report §4.3 (ledger 0043 deep-systems successor port; ledger 0045 poker; ledger 0043 creature battles), §4.2 (tournaments) |
| **Live/message-band adapters** — chat XP awards, counting/chain channel feeds, NL shell arming, reaction sign-ups, role-menu posting, review-feed poster + 👎/reply listeners, duel turn-timeout view, `subscribe(bus)` rosters | Ports and lanes exist; the Discord-facing consumers are "the one recurring successor class" | Report §4.2 |
| **`main()` / composition root** (`bot1.py`) | **Deliberately absent** — the full boot order is documented, unwritten | Report §4.5; CUT-1 (write main(), boot on test token, arm live adapters, rotation schedule) |
| **BrowserView pattern** — interactive sort/filter/paging browse surfaces (tower/hero browsers, recipe browsers, leaderboard browser) | Browse surfaces ship consistent RESULT_CARD text; interactivity named-but-unbuilt K8 work | Report §4.4 (flag 41) |
| **`botsite/` public website + `dashboard/` developer dashboard + `control_api.py`** | Not rebuilt; the `/control/*` HTTP bridge is deferred-named | ledger 0041; report §4.6 |
| **Hermes bridge** (`hermes_cog` + `scripts/hermes/`) — Discord→Claude Code work-order dispatch | Not ported (dev-ops tooling, not bot behavior); no successor named | — (parity row `hermes` tracks it) |
| **Deployment machinery** — Procfile/Railway worker, runtime-instance replica lock, live health server, Prometheus wiring, webhook boot reporter | Specs exist (K5 lifecycle, A-8 alert sink); live wiring is cutover work | Report §3 owner items (Railway prod+shadow, `DISCORD_WEBHOOK_URL`, backup arm-up); CUT-1/CUT-2 |
| **BTD6 ingestion pipeline** (Ninja Kiwi live sources, wiki fetch, patch diff) + paragon calculator | Knowledge corpus + grounding ported; ingestion + deep surfaces deferred | Report §4.3 (ledger 0046) |
| **Image renderers** (Pillow rank/character/profile/welcome cards) and design-system/Storybook | Not in the new tree | No explicit successor named — outstanding |
| **Ticket, starboard, utility, general, four_twenty, ux_lab subsystems** | Not yet ported (see §2) | Parity rows exist; no explicit successor entries — outstanding |
| **Stage-2 namespace-corpus harvest** (full legacy custom_id/settings walk of the old repo) | Seed-only `legacy_reservations.json` in new repo | Report §3 item 34 (owner-parallel walk; `tools/compute_corpus.py` consumes it) |

---

## 6. Parity status

- **465 goldens** (recorded input/output transcripts of real old-bot behavior) imported **byte-identical** from the old repo (PR #18), source-pinned to superbot @ `7f7628e1`.
- The **replay adapter** (`sb/adapters/parity/`, PR #27, ledger 0028) makes all 465 reconstructable and replayable against the new pipeline over a fake HTTP seam.
- **All 49 subsystem rows in `parity/parity.yml` are `pending` — 0 flips.** This is honest, not alarming: the one-way-door rule says flipping `pending → ported` is a deliberate last commit per subsystem, and a `ported` row never flips back. Flips are the next phase's work (per-subsystem flip review over the Postgres-serviced harness), tracked by the A-16 depth floor (100% declared-surface touch coverage or exemptions from a closed 8-class reason vocabulary; both `depth.exemptions` and `depth.ratchet` currently empty).
- Per-subsystem golden counts (completion report §5): btd6 39, diagnostic 37, ai 20, project_moon 10+1, karma 8, moderation 8, setup 8, logging 7, chain 7, economy 6, creature 5, settings 4, xp 3, help 3, cleanup 3, counting 3, proof_channel 3, treasury 2, admin 2, counters 2, server_management 2, community 2, blackjack 2, games 2, mining 2, fishing 2, casino 2; 1 each for inventory, channel, automod, security, welcome, image_moderation, spotlight, leaderboard, role, rps_tournament, farm, quicksetup.
- Measured golden *coverage* of the old surface (`parity/COVERAGE.md`): prefix commands 390/406 (96%), slash 64/73 (88%), panel custom_ids 60/64 (94%), panels 9/11 (82%) — but bus events 10/47 (21%), DB tables 26/105 (25%), settings keys 3/120 (2%). The thin tails are named per-item with reasons; the AI natural-language answer surface is covered by the separate eval corpus instead (66 cases + 28 domain probes).
- The `golden-parity` CI workflow is **born-red by design** in its `report` job (it reports the honest 0-flip state); the `gate` job may become a required check — the `report` job must never be (owner item, report §3).

---

## 7. Command-surface diff

**Headline numbers:** the old bot's decorator scan found **479 command registrations** across the cog tree; the new bot compiles **276 commands** across 41 subsystems (from `manifest.snapshot.json`, plus 121 settings, 14 declared events, 45 stores, 49 panels). The shrink is mostly *accounting*, not lost function:

- **Prefix/slash de-duplication.** The old tree registered many commands twice (a `commands.command` and an `app_commands.command`) and BTD6 registered them up to *three* times (unified tree + hidden alias cogs). The new `CommandSpec` has `kind=BOTH`, so one row covers both surfaces. BTD6 alone collapses from ~108 decorator rows across 6 cogs to 33 compiled commands with the same reachable surface.
- **Genuine drops** (all ledgered, see §3): `cog`, `loadall`, `unloadall`, `syncslash` (admin 11 → 7, ledger 0030).
- **Not-yet-ported subsystems** account for the rest: utility (15), setup_cog's advanced wizard commands (12 → folded to 1 skeleton entry), ticket (12), diagnostic platform group (39 → engine + deferred fleet), general (8), starboard (6), paragon (1), hermes (2), ux_lab (2), four_twenty (1).
- **Where the surfaces match 1:1** (names and aliases carried **verbatim** by ledger rule, ledger 0029/ledger 0030): mining 37=37, fishing 20=20, channel 17=17, role 15+2=17, counting 10=10, economy 9=9, chain 7=7, cleanup 7=7, rps 7=7, creature 4+3=7, proof_channel 5=5, blackjack 4=4, karma 4=4, xp 6=6, treasury 3=3, deathmatch 2=2, casino 2=2, and all the single-command policy renderers (automod, security, welcome, image_moderation, inventory, leaderboard, farm, spotlight).
- **Apparent small additions** (may be old-scan gaps rather than new commands — unverified): moderation lists a `warnings` command (old scan showed 9 rows without it); server_logging lists `enable`/`disable` (old scan showed 6 rows without them).
- **Fenced-but-present:** the 17 channel ops, `cleanuphistory`, `counterpreset` exist but answer with honest pending refusals until cutover arms their ports (ledger 0030); `kick` gains a confirmation step (ledger 0029); the `blackjack:solo:replay` persistent button is gone (ledger 0042); legacy back-button custom_ids became uniform `nav:*` ids.

**Coverage limits, stated plainly:** the old count is a static decorator scan — the programmatically-registered `/btd6` unified tree is undercounted on the old side, and panel components (buttons/selects/modals) are not counted on either side, though the parity corpus covers 60/64 known old custom_ids. The old repo's own `scripts/scan_commands.py` / `command_surface_ledger.py` remain the authoritative old-surface dumps if an exact reconciliation is ever needed. The new count is exact by construction (compiled snapshot, hash-pinned).

---

*Compiled 2026-07-09 from both repositories' default branches. For the authoritative going-forward state, read `docs/status/rebuild-completion-report-2026-07-09.md` (totals, owner steps, testing order), `docs/decisions.md` (all deviations), and `parity/parity.yml` (live port-progress dashboard).*
