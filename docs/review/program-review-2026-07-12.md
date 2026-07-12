# Program review — superbot-next (2026-07-12)

> **Status:** `audit` — point-in-time program review answering the owner's seven questions, written in plain language for the owner.
>
> **Provenance.** Audited 2026-07-12 against main at `c792079` (#254) by six
> parallel read-only audit areas (architecture, parity, production +
> foundations, AI, web, sim-lab/backlog); every load-bearing claim cites a
> file:line, commit SHA, PR number, or CI run ID measured at that HEAD.
> While this document was being assembled, main moved one commit to
> `edfeca8` (#255: utility re-homes — gate 396→404, `_unmapped` 74→66);
> counts below are at the audited HEAD `c792079` unless flagged.

Terms used throughout, in one breath each: a **golden** is a recorded
input/output test case captured from the OLD bot (the byte-exact reply,
database changes, and events for one command) that the new bot must
reproduce; the **gate** is the required CI check that replays goldens for
ported subsystems and blocks merging when any fail; **`_unmapped`** is the
pool of captured goldens not yet attributed to a subsystem row (so not yet
gated); a **compensator** is declared undo-logic that runs when a Discord
action fails after the database already committed, so the two never
disagree; **cutover** (CUT-2/CUT-3) is the not-yet-executed step of swapping
the new bot in as the production bot.

---

## Executive summary — the seven questions, one line each

1. **How much better is the new bot constructed?** A generation ahead
   structurally — one audited write path, machine-checked architecture, a
   5-tier test ladder, 6 required CI gates vs the old bot's 1 — while the
   old bot is itself layered and heavily tested, not a mess.
2. **What is still not properly improved?** Cutover not executed; 74
   goldens un-gated (~40 deliberately parked deep-game ports); deep systems
   (deep mining, poker, creature battles, tournaments) unported; some live
   Discord effect adapters unarmed; UI regressed to simple read-views; no
   deploy packaging; a few stale ledger docs.
3. **Has every function been compared against the goldens?** The parity
   program is honest and complete at the row level (50/50 rows, 396/470
   goldens gate-green at the audited HEAD) — but "every function" is not
   true: 463/470 goldens are single-step, interactions are nearly
   un-goldened, and events/tables/settings coverage is thin (21%/25%/2%).
4. **Can this be offered as a production bot?** Not yet. The test plane is
   live-proven (#109), but cutover, deploy packaging, backup/restore
   operation, the AI key, and live effect arming all stand between here and
   a production offer.
5. **Is the AI integration properly done?** Yes — built, tested, and
   fail-closed on every surface; the only missing thing is live-model
   evidence, gated solely on the owner providing the API key
   (OWNER-ACTION 5). Two small partials, both ledgered.
6. **Are the foundational sections solid?** 7 of 9 foundations are present
   and operating with CI enforcement; backup is present-but-never-run
   (owner gate) and the live-drive harness is deliberately manual.
7. **Can the bot be edited from the web?** Not today — the new bot has
   only a read-only health server. The old bot had a full (dormant)
   web-edit stack, and the new repo is pre-plumbed to receive a port of it
   as a small-to-medium diff.

---

## Q1 — How much better is superbot-next constructed than the old bot?

**Verdict: structurally a generation ahead — but the honest framing is
"disciplined rebuild of an already-mature bot", not "clean rewrite of a
mess."** The old bot is NOT naive: ~836 Python files under `disbot/` split
into cogs/views/services/utils/core, ~1,186 test files, 17 CI workflows
including CodeQL, and the very parity-capture harness that produced the
goldens the new bot replays. What the new bot adds is discipline the old
one cannot retrofit:

- **One audited write path.** Every mutation is a declared operation run by
  a single workflow engine: all database steps commit in one transaction
  FIRST (a failed step rolls everything back —
  `sb/kernel/workflow/engine.py:83`), the commit is stamped
  (engine.py:308–310), and only THEN do Discord effects run
  (engine.py:328–341). Success copy is owned by the step that did the work
  (decision ledgered at `docs/decisions.md:391`), so an acknowledgement can never
  claim an effect that didn't happen. The old bot decides ordering
  per-call-site — e.g. its moderation service calls Discord first and
  records after, with try/except discipline scattered through services
  (pinned in the ledger at `docs/decisions.md:489`). Careful hand-written code,
  but no contract.
- **The compensator invariant with an EMPTY allowlist.** A unit test scans
  every declared operation in `sb/domain` (roster asserted ≥97 ops) and
  fails if a Discord effect after a DB write lacks a declared recovery
  posture — and the exception list is deliberately empty
  (`tests/unit/workflow/test_compensator_invariant.py:24`,
  `_ALLOWLIST: dict[str, str] = {}`). This makes a whole defect class
  (committed row + failed, uncompensated Discord action) unwritable at
  authoring time. Both original violators are fixed at HEAD (see Q4).
  Money paths additionally carry locking reads and a static race checker
  (PRs #213 `f71d60b`, #217 `ed8eed3`, #221 `71af879`, #223 `80464ab`).
- **Machine-checkable architecture.** `tools/manifest_compile.py` compiles
  the subsystem declarations into a hash-pinned `manifest.snapshot.json`
  (48 subsystems, 396 commands) and CI fails on drift
  (`.github/workflows/named-gates.yml:58–72`). A 23-checker fleet under
  `tools/` enforces layering, config seams, egress fences, and money-race
  rules. The old bot's layering is by convention and docstring — nothing
  machine-enforces that a cog can't hit the DB directly.
- **A 5-tier test ladder** (documented in
  `docs/status/testing-report-2026-07-09.md`): unit (139 files / ~35.3k
  lines, dependency-free), integration against real Postgres (4 files,
  runs inside the required `golden-parity` job), golden replay (470-case
  corpus captured from the old bot), the sim gate (layout-drift tripwire,
  `tools/check_sim_gate.py`), and manual live-drive passes per band with
  found-defect ledgers. The old bot's ~1,186 test files are genuinely
  large, but its parity replay is manual-dispatch-only and never required,
  and it has no sim gate or required Postgres integration leg.
- **6 required CI gates vs 1.** superbot-next requires `code-quality`,
  `manifest-validate`, `architecture`, `sim-gate`, `golden-parity`, and
  `check_compat_frozen` (`.github/workflows/named-gates.yml`). The old
  bot's only required merge check is "Code Quality"
  (`auto-merge-enabler.yml`); CodeQL is explicitly not required.
- **Process artifacts**: an append-only decision ledger (77 `[D-xxxx]`
  entries in `docs/decisions.md`), per-session retro docs, a heartbeat
  status file. The old repo has planning docs but not the
  decision-per-ruling discipline.

Scale honesty: the old repo's PR counter was past #1275 vs the new repo's
~255 — the old bot embodies far more accumulated feature-hours, which is
exactly the porting debt Q2 tallies.

## Q2 — What is still NOT properly improved (honest gap list)

- **Cutover not executed; the old bot is still the shipped bot.** CUT-2/
  CUT-3 (token swap, rollback window, coverage-debt publication) are
  unexecuted checklist items
  (`docs/status/rebuild-completion-report-2026-07-09.md` §3 items 32–34).
- **74 `_unmapped` goldens are captured but not gated** at the audited HEAD
  (66 after #255) — "attribution work over already-ported rows", but until
  done, ~15% of captured old-bot behavior has no green replay. About 40 of
  them are deliberately PARKED deep-game ports (the deep-systems successor
  decision, `docs/decisions.md:326`: 25 mining-deep +
  15 fishing-gear, `control/status.md:32`), which is port work, not
  attribution.
- **Deep old-bot systems simply aren't ported** (bounded, ledgered
  successors — rebuild-completion-report §4.2–4.3, which stamps each
  decision id): deep mining (27 of mining's 37 commands are honest
  "pending" refusals, `docs/decisions.md:329`), fishing gear/venues, the
  creature battle engine, the poker table engine, blackjack/RPS tournament
  orchestration, btd6 ingestion depth, and ~27 AI tool rows.
  Users of those commands get polite refusals where the old bot
  has full gameplay.
- **The live Discord effect surface is thinner than the old bot's.** The
  live composition root deliberately arms no moderation-actions adapter —
  a live `!ban`/`!kick` writes correct rows and copy but does not touch the
  member (ledgered at `docs/decisions.md:391`, item 4); ban was never live-fired
  in testing (testing-report step 3). Role-grant and channel-permission
  effect adapters are likewise queued (`control/status.md:3`).
- **Rich UI regressed vs the shipped bot.** The shipped button-grid
  operator hubs, settings panel-actions, help overlays, setup wizard
  flows, and PNG rank cards are ledgered "successor-boundary render
  drift"; the interactive BrowserView engine is named-but-unbuilt, so
  every browse surface ships flat text (flag 41,
  rebuild-completion-report §4.4).
- **No deploy packaging** — see Q4 item 2.
- **Ledger staleness**: `docs/current-state.md` (snapshot 2026-07-10) says
  41 subsystems / 276 commands / 22 checkers; measured HEAD is 48 / 396 /
  23. Its own header says source wins, but a fresh reader should be told.

## Q3 — Has every function been compared against the golden standards?

**Verdict: the parity program is honest, but "every function reviewed" is
not a claim it makes — and the program itself says so in writing.**

What IS true:

- All 50/50 program rows (49 subsystems + the kernel coverage home) are
  `ported` with their gated goldens green: **396/470 goldens gate-green at
  the audited HEAD** — CI-verified in run 29192655541, gate job
  86649943892: "gate: GREEN — all 396 golden(s) across 50 ported
  subsystem(s) replay clean" (404/470 after #255).
- The corpus is genuinely oracle-pinned: imported **byte-identical** from
  the old bot at pinned SHA `7f7628e1` with a sha256 tree manifest
  (`parity/parity.yml:38–48`), goldens are a read-only acceptance oracle
  (`parity/README.md:24–32`), and the one deliberate exception — 4
  kernel-band goldens that pin NEW-kernel bytes as drift tripwires — is
  documented (D-0075, `parity/parity.yml:59–65`). Historic cases where new
  code invented behavior were retired oracle-wins at flip time
  (`docs/decisions.md:485, 500–504`).

What is NOT true, with numbers:

- **Depth is thin.** 463 of 470 goldens are single-step; the whole corpus
  contains exactly **1 button click and 3 modal submits**
  (steps histogram `{1: 463, 2: 4, 3: 3}`; input kinds
  `{command: 410, slash: 66, modal: 3, click: 1}`). Panels count as
  "captured" when rendered, never clicked (`parity/COVERAGE.md:24`).
  Component-interaction behavior is essentially un-goldened.
- **Coverage is skewed toward commands.** The import-time coverage report
  (`parity/COVERAGE.md`): 96% of prefix commands and 88% of slash commands
  captured, but only **21% of bus events** (37 of 47 never observed),
  **25% of DB tables** (79 of 105 never touched), and **2% of settings
  keys** (117 of 120 never mutated). Many sweeps drove commands bare as
  admin — mining's `!mine` golden literally pins an old-bot error string,
  not gameplay.
- **27 commands were capture-skipped** with written reasons
  (`parity/goldens/_sweep_skips.json`; mirrored as 16 prefix + 9 slash
  never captured, COVERAGE.md:30–59).
- **Three manifest subsystems have no parity row at all** — `deathmatch`
  (ruled 50→51, still in flight), `governance`, `platform` — so the A-16
  depth floor (`tools/check_parity_depth.py:15–17`) never applies to their
  declared surfaces; their coverage is by argument, not by golden.
- **The denominator is moving**: first corpus retirement landed at #249
  (`c169e92`, sweep_cog, 471→470, owner-vetoable and reversible); two
  further diagnostic retirements are ⚑ approved but NOT landed (→468).
- 51 written depth exemptions exist under 10 closed reason classes
  (`parity/parity.yml:214–262`); the three ruled corpus-red disposition
  classes (flag-13, ORDER 009) are applied symmetrically at diff time
  (`docs/parity/flag-13-disposition-2026-07-10.md`, binding).

So the honest answer: every ported row's declared surface has been
compared and is enforced green in CI, with the gaps named, ledgered, and
mostly deliberate — but roughly 84% of the corpus is gated green, and the
old bot's state/event/interaction surface is covered far more thinly than
its command surface.

## Q4 — Can this be offered as a production bot?

**Verdict: NOT yet — but it is a genuinely functional, live-proven
TEST-PLANE bot with the parity program complete.** It has run live against
Discord: the band-5 live-drive leg is DONE (#109, merge `b813324`,
`control/status.md:210`), with the test-bot token, both privileged
intents, and 12 guild-synced slash commands verified live
(`control/status.md:203–209`).

For the record, first: the two 2026-07-10 runtime-review residuals are
**FIXED at HEAD** — `proof_channel.end_access` now carries its
delete-if-match compensator (`sb/domain/proof_channel/ops.py:164–202`,
wired at :222/:237, landed via #108's twin folded into #111 `569beea`),
and `moderation.timeout` was re-sequenced to the oracle's
effect-before-DB shape so a refused timeout leaves no row and no event
(`sb/domain/moderation/ops.py:131–195`, esp. :138–143); the compensator
allowlist is empty (test_compensator_invariant.py:23).

The numbered blocking list:

1. **Cutover not executed (CUT-3).** The composition root is explicitly
   the "CUT-1 test-mode main()" (`sb/app/main.py:1`): global app-command
   sync is compare-only because "the remote GLOBAL set is still the OLD
   bot's until CUT-3" (main.py:22–29). No CUT-2/CUT-3 runbook execution is
   recorded anywhere in `control/`.
2. **Zero deploy packaging.** No Dockerfile, docker-compose, railway
   config, fly.toml, or Procfile anywhere in the repo (searched, zero
   hits). Railway is the assumed host in prose only
   (`sb/spec/config.py:220–221`;
   `docs/operations/credential-lifecycle.md:20–21`).
3. **Backup / disaster-recovery has never operated.** Both workflows gate
   on an owner-set `BACKUP_ENABLED` variable (`backup-db.yml:57`,
   `restore-verify.yml:45`); measured via the GitHub API, **all 4
   scheduled backup runs concluded `skipped` and restore-verify has ZERO
   runs ever**. The rollback playbook's own rule — a stale restore witness
   means "do not cut over" (`docs/operations/rollback-playbook.md:29–30`)
   — has never been satisfied.
4. **OWNER-ACTION 5: the AI/NL leg is dark.** `ANTHROPIC_API_KEY` is
   absent and `AI_ENABLED` off (default False,
   `sb/spec/config.py:148–149, :166–167`; `control/status.md:231–237`).
   Gates live-AI EVIDENCE, not code (see Q5).
5. **Live effect adapters unarmed** for moderation, role grants, and
   channel permissions (`control/status.md:3`; `docs/decisions.md:391` item 4) — verified
   in replay, not against live Discord.
6. **The 74-golden `_unmapped` pool** (66 after #255) — see Q2/Q3.
7. **Deathmatch is in flight**: domain code complete
   (`sb/domain/deathmatch/`, 910 lines; `sb/manifest/deathmatch.py`) but
   the ruled 50→51 parity row is not born — no row, no goldens.

Also worth knowing: prod data-plane rails are declared but never
exercised — a production boot expects `DISCORD_BOT_TOKEN_PRODUCTION`,
`DATABASE_URL`, `SB_DATA_PLANE=prod`, and `SB_PROD_ATTEST`
(`sb/spec/config.py:124–125, 207–208, 218–221`), and all live evidence to
date is `SB_DATA_PLANE=test`. The KNOWN_RISKS ledger is empty after #223
(`control/status.md:6`); one ledgered latent bug remains open
(`sb/domain/btd6/service.py::_run_op`, unreachable via golden lanes,
guard recipe in the #194 card).

**Bottom line:** the functions are complete enough (50/50 parity rows,
live-driven test plane, races fixed, compensator allowlist empty); the
production OFFER is blocked on items 1–5 — execute cutover, produce a
deploy artifact, get one green restore-verify, arm the live effect ports,
and rule on the AI key.

## Q5 — Is all the AI integration properly done?

**Verdict: yes — properly done for its current phase, and fail-closed by
design.** Every surface is BUILT and TESTED (mocked-provider tests plus
goldens); the single missing thing is live-model evidence, gated solely on
OWNER-ACTION 5 (the owner providing `ANTHROPIC_API_KEY` and turning
`AI_ENABLED` on). The status ledger's own words: this "gates EVIDENCE, not
code" (`control/status.md:235`).

- **Fail-closed everywhere.** `AI_ENABLED` defaults to False
  (`sb/spec/config.py:148`); the default provider is `deterministic` and
  never touches the network (`config.py:150`,
  `sb/kernel/ai/providers/deterministic.py:25–39`); every provider fault
  degrades to a typed response instead of raising
  (`sb/kernel/ai/gateway.py:369–485`); an empty key becomes a named
  degraded outcome, never an exception
  (`anthropic_provider.py:66–70` → gateway.py:443–461); the NL engine
  serves per-task deterministic refusal floors
  (`sb/kernel/ai/nl_engine.py:26–28`).
- **Built + tested surfaces** (each with test counts): provider adapters
  (13 tests, fake SDK clients — SDKs deliberately not installed in CI),
  the gateway chokepoint (19), task→model routing under the owner's
  K10(b) ruling — biased to Haiku, Sonnet reserved for three
  deeper-reasoning tasks (`sb/kernel/ai/routing.py:56–77`; owner ruling of
  2026-07-08, PR #30) (16), the NL engine 9-step pipeline (31 + 14), grounding
  verify-and-regenerate with fail-closed verifiers (20), behavior and
  orchestration presets (D-0071 #185, D-0072 #187; 14 + 17), the band-7
  operator surface at byte parity — 31/31 ai goldens green (#151
  `1bea65d`, #155 `4c8c5b0`, #160, #165, #177), and the eval harness
  whose required tier runs with an armed socket guard so no paid call can
  ever hide in CI (`sb/kernel/ai/evals.py`, `socket_guard.py`, 13 + 15
  tests). Totals: 141 tests in `tests/unit/ai/`, 275 in
  `tests/unit/band7/`.
- **Built-and-gated vs missing — the distinction matters.** The live NL
  reply shell exists and is unit-tested
  (`sb/adapters/discord/nl_shell.py:47–118`) but is deliberately dormant
  in the live message feed until its arming slice
  (`sb/adapters/discord/message_feed.py:153–155`); the memory-observation
  leg IS live. Nothing here is missing — it is built, tested, and waiting
  on the key.
- **Two genuine partials, both ledgered, neither broken:** (1) the
  diagnostics card serves the fallback provider instead of the
  `SETUP_ADVISOR_PROVIDER` override (`sb/spec/config.py:170–173`; parked
  item, `control/status.md:191`) — cosmetic-scale; (2) the dormant NL
  reply shell awaits its arming slice (above).
- Architecture-wise this is an explicit port of the old bot's AI stack
  onto typed config seams (module docstrings cite
  `disbot/core/runtime/ai/...` throughout) — with improvements: one
  gateway with named degrade reasons where the old bot had a documented
  silent-fallback finding, and no raw `os.getenv` reads.

## Q6 — Are the foundational sections solid?

**Verdict: 7 of 9 foundations PRESENT+OPERATING with CI enforcement;
backup half GATED (owner), live-drive harness PARTIAL (manual by
design); games OPERATING with deathmatch PARTIAL.**

| # | Foundation | Status | Key evidence |
|---|-----------|--------|--------------|
| 1 | Persistence / migrations | OPERATING (migrations) / GATED (backup) | Sequential runner with sha256 checksums (`sb/kernel/db/migrations.py:9`) over migrations 0001–0038; CI twin `tools/check_migrations.py` (ci.yml:53). Backup: 4/4 scheduled runs skipped, restore-verify 0 runs ever (owner gate `BACKUP_ENABLED`). |
| 2 | Idempotency postures | OPERATING | Typed posture per op, compile-enforced (`sb/kernel/workflow/compile.py:66–83`); engine consumes the key store (engine.py:228, :234); table `migrations/0001_idempotency_keys.sql`. |
| 3 | Money-race guard | OPERATING | Fixes #213/#217/#221/#223; static lint `tools/check_money_race.py` in CI; real-Postgres race regressions run in the required gate (11 passed, job 86649943892). |
| 4 | Live-drive harness | PARTIAL | Replay root operating (`sb/adapters/parity/boot.py`); live drive is manual per band — band-5 leg DONE (#109 `b813324`); no automated live lane (by design). |
| 5 | Session lifecycle | OPERATING (test-plane) | Boot preflight→db→health→gateway→RUNNING, SIGTERM drain (`sb/app/main.py:1–40`); 75s READY timeout, supervised gateway task (`sb/adapters/discord/gateway.py:43–115`); process restart is the (unpackaged) orchestrator's job. |
| 6 | Moderation | OPERATING | Ported #163, green inside the gate at HEAD; effect-first timeout (ops.py:131–195); ban/unban/kick/warn compensators (ops.py:319–390). |
| 7 | Games | OPERATING; deathmatch PARTIAL | Band-6: 7 slices (#114–#138), both games playable solo+PvP+tournament, all game goldens green; deathmatch domain complete but parity row not born. |
| 8 | Economy | OPERATING | Ported #152 (6/6), treasury #214 (`827b134`), money races fixed, row green in the gate. |
| 9 | Diagnostics | OPERATING | Health server `/health` `/ready` `/lifecycle` `/metrics` (`sb/adapters/http/health.py:181–185`); observability kernel; diagnostic subsystem 37/37 goldens (#183). |

The only foundations not fully operating are the backup/DR half of
persistence (present, scheduled, never once executed — owner gate) and
live-drive automation (manual per band by design).

## Q7 — Can the bot be edited from the web today?

**Verdict: no web-edit surface exists today — and porting one is a
small-to-medium diff onto plumbing that already landed.**

- **Today**: the ONLY HTTP surface is the read-only health/metrics server
  — four GET routes, no POST (`sb/adapters/http/health.py:181–185`;
  `sb/adapters/http/` contains only `__init__.py` + `health.py`). No
  dashboard, no REST config API, no web write path. (The repo-root
  `control/` directory is agent coordination, not a web control surface.)
- **The old bot had a full, working, dormant-by-default stack**: a private
  `/control/*` HTTP API on the bot (GET ping/authority/settings/routing/
  manifest, POST settings/help-overlay/routing, bearer-token auth with
  constant-time compare, write rate limiter, routes registered only when
  `CONTROL_API_TOKEN` is set — `disbot/control_api.py`), a Discord-OAuth
  FastAPI dashboard that edited per-guild settings, help appearance, and
  cog enable/disable live (`dashboard/README.md`), and a read-only public
  site (`botsite/`).
- **The new repo is pre-plumbed for the port**: the deferred-bridge
  decision (`docs/decisions.md:311`) names the exact successor file —
  `sb/adapters/http/control.py`: "ping/authority/manifest/settings
  GET+POST fronting the audited seams, the _SlidingWindow write limiter,
  hmac compare" — and the dormant `CONTROL_API_TOKEN` SecretSpec
  (`sb/spec/config.py:234–238`) plus its credential-registry row
  (`sb/spec/credentials.py:167–175`) already landed.
- **Why compatibility is high by design**: every write a web surface would
  need already exists as an audited internal seam. Per-guild settings all
  flow through the workflow engine's scalar write lane with a
  machine-readable catalogue (`sb/kernel/settings/__init__.py:1–10`,
  `sb/spec/settings.py:1–30`); command routing/access lanes exist
  (`sb/domain/platform/command_access.py:145–170`). Env config is frozen
  at boot (not web-editable by design); manifests are compiled code (web
  can read the snapshot, never write it).
- **Porting sketch** (from the audit): step 1, the bridge — add
  token-gated `/control/*` routes to the existing aiohttp app fronting
  the existing seams, with `disbot/control_api.py` as the line-by-line
  oracle (**small-medium diff**; zero kernel edits needed). Step 2, port
  the `dashboard/` service (**medium** — it never imported the bot and
  speaks only HTTP, so much carries over if the bridge keeps the old
  endpoint shapes). Step 3, optionally port `botsite/` (**small**). One
  prerequisite gap: help-appearance editing needs the ledgered
  help-overlay successor store to land first
  (`sb/domain/help/__init__.py:6–8`).

---

## What the sim lab and backlog say

- **The sim gate is a real drift tripwire, but zero layouts are
  sim-backed yet.** The gate (`tools/check_sim_gate.py`, required CI job)
  pins 788 layout assignments across 46 subsystems against a committed
  baseline and catches silent reshapes (the trap-30 hardening caught a
  real one, PR #197 after #190). But **788/788 pins are `Exempt` and 0
  carry a simulation reference** — `sim/records/` is empty. As provenance
  that layouts were *optimized by simulation*, it currently verifies
  nothing; the honest state, not a regression.
- **CI at the audited HEAD**: golden-parity run **29192655541** — gate job
  86649943892 SUCCESS ("gate: GREEN — all 396 golden(s) across 50 ported
  subsystem(s)"; integration 11 passed); report job 86649943879 FAILURE
  **by design** ("green: 396/470", only non-green row `_unmapped 0/74
  [pending]`, reds dominated by the deep-systems `*_pending` handler families).
  named-gates run 29192655530 all-green. `report` is born red by design
  and must never be required (`docs/status/README-first.md`).
- **The live ladder's last two rungs were never driven.** Testing-report
  rows 8 (band-6 games live pass) and 9 (band-7 AI live, key-gated)
  remain pending — and every previous band's live pass found bugs replay
  could not (silent acks in three bands, dead handlers, clock/RNG leaks).
  Replay-green ≠ live-correct is this ledger's own strongest lesson.
- **Open ORDERs**: 014 (seed the `superbot-plugin-hello` repo — the agent
  write is now sanctioned) and 015 (render CLAUDE.md, fix two dead
  orientation pointers) are filed but unacked at the audited HEAD; ORDER
  001's done-flag was simply never claimed (cosmetic); ORDER 004 is
  deliberately partial (binds future bands' live passes).
- **Open OWNER-ACTIONs**: **2** (create the plugin-hello repo — overtaken
  by ORDER 014), **3** (kill the branch-update merge dance — merge queue
  or ruleset change, admin-only), **5** (the AI key envelope —
  `ANTHROPIC_API_KEY` + `AI_ENABLED`, blocks band-7 live evidence), **6**
  (re-arm the fleet's failsafe routines auto-disabled by the 2026-07-11
  env teardown; no repo evidence shows the siblings re-armed).
- **Retro lessons a program review should carry**: the #193 "flip-sized
  law" — every `_unmapped` re-home family so far required real port work,
  never a bare file move (25-for-25) — prices the remaining pool; park
  claims have a shelf life and must be re-derived at pick-up (trap 37);
  the external codex reviewer produces real line-anchored findings but
  has fabricated commits/PRs three times, so Q-0120 verification is
  load-bearing; and the headline "PARITY PROGRAM COMPLETE AT 50/50" is a
  row-attribution truth, not a product-parity truth — it must always be
  read next to the `_unmapped` pool and the parked deep-game
  surface.

## Top 10 gaps / recommended next moves

1. **Execute the cutover path (CUT-2/CUT-3)** — the single step that turns
   this from a parallel build into the production bot; no cutover work is
   scheduled anywhere in `control/` at HEAD.
2. **Produce a deploy artifact + runbook** (Dockerfile or Railway config;
   currently prose-only) — a prerequisite for #1.
3. **Turn on backup/DR and get one green restore-verify run**
   (`BACKUP_ENABLED` + secrets; the playbook forbids cutover without the
   restore witness).
4. **Rule on OWNER-ACTION 5** (AI key + `AI_ENABLED`) and drive the band-7
   live-NL evidence leg; then drive testing-report rows 8–9 (band-6/7
   live passes) — the ladder's history says live passes find what replay
   cannot.
5. **Arm the remaining live effect adapters** (moderation actions, role
   grants, channel permissions) so live commands touch Discord, not just
   the database.
6. **Finish the `_unmapped` re-home tail** (66 files after #255) and land
   the deathmatch row birth (50→51) plus the two approved diagnostic
   retirements (→468), so the corpus count and ⚑ flags reconcile.
7. **Decide the deep-systems port** (`docs/decisions.md:326` — deep mining, fishing gear,
   poker, creature battles — ~40 parked goldens + 45 pending handler
   refs) — the real remaining product work, distinct from attribution.
8. **Close the interaction-coverage blind spot**: 1 click + 3 modals in
   470 goldens; the D-0073 minting procedure (new-bot capture with
   kernel-spine bytes stripped, verified against the oracle) can now
   golden clicks/modals/selects deliberately.
9. **Port the web bridge** (`sb/adapters/http/control.py` per the
   deferred-bridge decision, `docs/decisions.md:311`) if
   web-based editing matters to the owner — small-medium diff, oracle
   code exists, token plumbing landed.
10. **Housekeeping sweep**: regenerate `parity/COVERAGE.md` (frozen at
    465 cases), refresh `docs/current-state.md` counts and
    `README-first.md`'s pre-flip framing, give governance/platform
    written parity dispositions, ack ORDERs 014/015, and re-arm the fleet
    failsafes (OWNER-ACTION 6).

## Not measured

Stated explicitly so absence of evidence is not mistaken for evidence:

- Old-bot LOC and its exact test-pass count (no local clone; ~836 py
  files under `disbot/` and ~1,186 test files are code-search proxies).
- The exact new-bot green unit-test count at the audited HEAD (last
  CI-verified figure: 1722 passed / 8 skipped at `7334083`, run
  29186950619).
- The full-corpus report fraction was not re-measured between `7334083`
  (370/471) and the audited HEAD's CI run (396/470); wave-9 records cite
  per-merge gate numbers only.
- Any prod-plane (`SB_DATA_PLANE=prod`) boot — never performed, nothing
  to measure.
- Live AI call behavior — deliberately unmeasurable until OWNER-ACTION 5.
- Owner intent on cutover timing — not recorded anywhere in the repo.
- Pre-#204 commit history (shallow local clone); pre-#204 claims cite
  docs/ledger entries rather than git log.

---

## Addendum — 2026-07-12 (post-review resolutions)

> Everything ABOVE this line is the original point-in-time snapshot, audited
> against main at `c792079`/`edfeca8` (#254/#255) and left untouched. This
> addendum is a separate, later evidence log: it re-verifies each Q4 blocker and
> named finding at main HEAD `5ca477b` (#308) and records only what CHANGED
> since the snapshot. No finding above was edited. Every claim below was
> re-measured at HEAD — file:line, PR number, or command output pasted verbatim.

**Audit HEAD for this addendum:** `5ca477bbb9e816458df417d8ac8190959a7f3c0c`
(`docs: CAPABILITIES — verified worker-session port-oracle path (#308)`).

### RESOLVED at HEAD

**Blocker #7 — deathmatch 50→51 birth (snapshot read: "in flight").** Landed.
- `parity/parity.yml:148` now carries `  deathmatch: ported` (grep confirms the
  roster row; the row also has its depth block at `:522` and its capabilities
  entry `deathmatch: {events: 1, tables: 2, settings: 0}` at `:1052`).
- Depth checker is green:
  `$ python3 tools/check_parity_depth.py`
  `check_parity_depth: OK — 51 subsystems (50 ported), kernel ported, 476 goldens`
  (exit code `0`). The snapshot's "50/50 rows" is now 51 rows, 50 ported (the
  51st row, `_unmapped`, is `pending` by design — see LIVE below).
- Birth citation: PR **#261**, commit `5050b8f52c7dc447e9eef135d564ccfbec956725`,
  "deathmatch row 51 born" — recorded in
  `.sessions/2026-07-12-parity-rehomes-wave9.md:78` (the wave-9 wrap card).
  Note on provenance: the local clone at this HEAD is shallow (44 commits), so
  `git show 5050b8f` does not resolve and `git log -S "deathmatch: ported"`
  attributes the row to the clone's earliest-visible commit (#260, a
  shallow-boundary artifact) — the authoritative birth citation is the wave-9
  card line above, not local git log.

**Blocker #2 — zero deploy packaging (snapshot read: "no Dockerfile … zero
hits").** Landed via PR **#266** (`1b08bc8` "deploy-packaging: container image
+ release workflow (Q4 blocker #2)"). All artifacts exist at HEAD:
- `$ ls Dockerfile .dockerignore docker-compose.yml railway.json .github/workflows/release.yml`
  → all five present (`Dockerfile` 3787 B, `.dockerignore` 1020 B,
  `docker-compose.yml` 2204 B, `railway.json` 333 B, `release.yml` 2050 B).
- `.github/workflows/ci.yml:92` defines the `build-image` job (builds the
  container on every PR, `push: false` / `load: false`; deliberately NOT a
  required check — the release workflow owns tag+push). The snapshot's
  "no deploy packaging" finding no longer holds.

### PARTIAL at HEAD (documentation closed, execution still LIVE)

**Blocker #1 — cutover not executed.** Split verdict, stated precisely:
- The **documentation gap is CLOSED**. `docs/operations/cutover-runbook.md`
  (17605 B) and `docs/status/coverage-debt-2026-07-12.md` (1458 B) both exist at
  HEAD, landed via PR **#264** (`2e448ee` "docs(operations): consolidated
  CUT-2/CUT-3 cutover runbook + tooling wiring"). The snapshot's "no CUT-2/CUT-3
  runbook" observation is superseded — the runbook now exists.
- The **execution blocker REMAINS LIVE and owner-gated.** No CUT-2/CUT-3
  cutover has been performed; the runbook is a plan, not a record. Do not read
  "runbook exists" as "cutover done." The rollback playbook still forbids
  cutover without a green restore witness (see Blocker #3, LIVE), which has
  never been produced.

### LIVE at HEAD (still open — re-verified open, not merely asserted)

**Blocker #3 — backup / disaster-recovery never run.** Still true, owner-gated.
- Measured via the GitHub Actions API at this HEAD: `restore-verify.yml` has
  `total_count: 0` — **zero runs ever**. `backup-db.yml` has 4 runs, all with
  `conclusion: skipped` (run numbers 1–4, event `schedule`).
- Both workflows gate on the owner-set variable: `restore-verify.yml:45`
  `if: vars.BACKUP_ENABLED == 'true'` and `backup-db.yml:57`
  `if: vars.BACKUP_ENABLED == 'true'`. Unblocking requires the owner setting
  `BACKUP_ENABLED=true` plus the DB secrets — owner action, no code change.

**Blocker #4 — AI / NL leg dark (OWNER-ACTION 5).** Still true, owner-gated.
- `sb/spec/config.py:148` `ConfigSpec("AI_ENABLED", ConfigType.BOOL, default=False, …)`.
- `sb/spec/config.py:166` `SecretSpec("ANTHROPIC_API_KEY", ConfigType.SECRET, default=None, …)`.
- Fail-closed by default; gates live-AI EVIDENCE, not code. Unblocking is
  OWNER-ACTION 5 (set the key + flip `AI_ENABLED`).

**Blocker #5 — live effect adapters unarmed.** Still true; another-lane /
owner-track work.
- The replay/parity root arms `ParityModerationActions` (records wire verbs
  edit_member/kick/ban/unban), but the **LIVE composition root deliberately
  arms no Discord guild-action adapter** — live moderation/role/channel effects
  stay PARTIAL + "not-installed" finding until the live-adapter successor lands
  (`docs/decisions.md:388`, the band-2 slice-1 findings decision, verdict item
  (4), and its live-adapter-successors pointer at `docs/decisions.md:368`).
  Effects are verified in replay, not against live Discord.

**Blocker #6 — `_unmapped` golden pool.** Still an un-gated pool; count is now
**15**, all fishing.
- `parity/parity.yml:133` `  _unmapped: pending` (still a `pending` roster row,
  not gated). The pool on disk is exactly 15 files:
  `$ ls parity/goldens/_unmapped/*.json | wc -l` → `15`. Every one is a fishing
  surface: `sweep_bait`, `sweep_boathouse`, `sweep_craftbait`, `sweep_craftcharm`,
  `sweep_craftcurio`, `sweep_craftpearl`, `sweep_craftrod`, `sweep_curios`,
  `sweep_dock`, `sweep_fishery`, `sweep_forecast`, `sweep_rod`, `sweep_rodrecipes`,
  `sweep_sail`, `sweep_tidepool`. The snapshot's "74 (66 after #255)" figure was
  measured at an earlier HEAD; the pool has since drained to these 15 fishing
  goldens. Owner-gated: draining them turns on the fishing-deep port under the
  deep-game go/no-go ruling (`docs/decisions.md:326`; `control/status.md`
  ⚑ needs-owner item 1: "25 mining + 15 fishing goldens").

**`governance` + `platform` subsystems still rosterless.** Still true.
- Neither appears as a roster row in `parity/parity.yml`:
  `$ grep -nE '^\s+(governance|platform):' parity/parity.yml` → no matches. The
  only hits for those words are prose comments about A-16 clause 3
  (kernel/governance-owned surfaces) at `parity/parity.yml:25` and `:185` — not
  roster rows. They carry no parity disposition. Owner-track housekeeping
  (snapshot Top-10 item 10: "give governance/platform written parity
  dispositions").

### One-line ledger

| Item | Snapshot read | HEAD verdict | Proof |
| --- | --- | --- | --- |
| Blocker #7 deathmatch birth | in flight | RESOLVED | `parity.yml:148` ported; `check_parity_depth` OK 51/50, exit 0; #261 `5050b8f` |
| Blocker #2 deploy packaging | zero packaging | RESOLVED | 5 files present; `ci.yml:92` build-image; #266 `1b08bc8` |
| Blocker #1 cutover | not executed | PARTIAL | runbook present (#264 `2e448ee`); EXECUTION still LIVE, owner-gated |
| Blocker #3 backup/DR | never run | LIVE (owner) | restore-verify 0 runs; backup 4/4 skipped; `BACKUP_ENABLED` gate |
| Blocker #4 AI leg | dark | LIVE (owner) | `config.py:148` AI_ENABLED=False; `:166` ANTHROPIC_API_KEY=None |
| Blocker #5 effect adapters | unarmed | LIVE (lane/owner) | `decisions.md:388`(4): live root arms no Discord guild-action adapter |
| Blocker #6 `_unmapped` pool | 74/66 | LIVE (owner) | `parity.yml:133` pending; 15 fishing goldens on disk |
| governance/platform roster | rosterless | LIVE (owner) | absent from `parity.yml` roster (comments only :25/:185) |

*Method note: this addendum is an evidence log, not a re-review. Where a
coordinator-supplied expectation disagreed with HEAD it was bucketed by what was
observed — e.g. the `_unmapped` count was independently measured at 15 (all
fishing) rather than trusted, and the deathmatch birth commit was cited from the
wave-9 card because the shallow local clone cannot resolve `5050b8f` directly.*
