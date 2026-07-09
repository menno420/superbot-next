# Testing report — subsystem-by-subsystem live phase (started 2026-07-09)

> **Status:** `living-ledger` — the testing-phase results ledger; rows are
> appended/amended as each step of the 9-step order is exercised.

The live-testing ledger for the owner's 9-step order (rebuild completion
report §5). One row per subsystem/step as it is exercised against the live
boot (`python3 -m sb`, test data plane, owner test bot). Append rows —
entries are amended, never deleted.

## Environment

- Runner: agent container, local PostgreSQL 16.13 (fresh `superbot_test` DB),
  superbot-next @ main `6428157` (PR #54 squash), owner-confirmed
  TEST bot token (`DISCORD_BOT_TOKEN_PRODUCTION` — the test app; connects as
  the test bot, 3 guilds).
- Env: `SB_DATA_PLANE=test`, `SB_TEST_DB_HOSTS=localhost,127.0.0.1`,
  `HEALTH_PORT=8080`; `SB_INTENT_*_OK` unset (both privileged intents
  DEGRADE by design); AI dormant (no `ANTHROPIC_API_KEY`, `AI_ENABLED`
  default false).

## Results

| Subsystem / step | Boot/commands tested | Goldens replayed | Pass/fail | Bugs found / fixed | Parity / verified status |
|---|---|---|---|---|---|
| **1. Kernel boot + health + DB + outbox** (CUT-1 smoke) | `python3 -m sb` live boot on the test token: preflight rails (data-plane allowlist, intent DEGRADE markers); migrations 0001–0024 apply + `verify_applied_checksums` + `checksums.json` verified on a FRESH DB; `SB_VERIFY_BOOT` profile (`verified: true`, 0 quarantined); boot-gate leg A pre-db.init and leg B pre-connect both green; leg C compare-only (12 snapshot paths vs 78 stale remote — REMOTE_LAG, non-fatal by contract; sync deliberately off until app-command registration lands); gateway READY ~4s (test bot, 3 guilds); `/ready` 503 `gateway_not_ready` during STARTING → **200 only at RUNNING**; `/health`, `/lifecycle`, `/metrics` (lifecycle_phase gauge, db_query_seconds) all render; outbox relay delivered the durable `audit.action_recorded` boot canary on the first RUNNING tick (row → `delivered`); due-queue lane ticked cleanly; poll supervisor lanes isolated; subscribe rosters armed (spotlight/economy/role/server_logging/xp); `recover_escrow` swept blackjack/rps PvP escrows (0 stranded on a fresh DB); SIGTERM → DRAINING → outbox drained (0 pending) → SHUTTING_DOWN → STOPPED, **exit 0**; second run: 0 ERROR/Traceback lines in the full boot log | none direct (kernel = the 9-table coverage home; evidence class = verify_boot profile + live boot) | **PASS** | **1 found + fixed**: `sb/kernel/db/draft.py reap_stuck_applying` failed PREPARE on real Postgres every DraftJanitor tick (`$1 - make_interval(...)` resolves through the preferred datetime type → `timestamptz < interval`); fixed with `$1::timestamptz` (PR #54). Invisible to unit fakes — first-ever live boot caught it | kernel rows: automated-tier evidence minted by this run (verify_boot + live smoke); `verified_live` records not yet flipped (flip PR = the registry mint, follows the golden-evidence convention) |
| **2. Settings + help + diagnostic + setup (band 1)** | Golden replay on a FRESH `parity_band1` DB (migrations auto-applied) + live exercise on the test guild @ main `f04fd4f`. **Live**: gateway READY with BOTH privileged intents accepted (portal toggles now ON — `SB_INTENT_*_OK=true` verified empirically, 0 degrade markers); Galaxy Bot has ADMINISTRATOR on MineSnakeBotTest; 49 manifest panels armed; live dispatch index 514 targets; `!help`/`!settings`/`!diagnostics`/`!setup` driven through the REAL pipeline (dispatch_prefix → resolve → panel engine → DiscordPanelPresenter) posted the four hub panels into #bot-activity (Help 16 fields over 41 manifests; Settings 17 subsystem fields + `nav:help`; Diagnostics 4 fields reading lifecycle RUNNING/findings/AI collector; Server setup 10 wizard-section fields); settings declare/read/bind PROVEN on the live DB through the audited K7 lanes (102 declarations/17 subsystems; `settings.set_scalar` + `settings.bind` → success + `audit_log` rows `setting_set`/`binding_set`; `resolve("logging","enabled")` → explicit "true") | 0/53 green: settings 0/4, help 0/3, diagnostic 0/37, setup 0/8, quicksetup 0/1 (local run == CI report leg run 29015353209: 465/465 replayable, 0 green) | **Replay: RED (expected, ledgered)** — post-fix reds are render/content drift against SHIPPED surfaces that are named successor work: the settings panel-action family, the help overlays + the deep `platform_*` diagnostic fleet (36/37 diagnostic goldens), and the whole setup wizard + quicksetup (`setup_session` store, section flows, `/setup-*` fleet) — the ledgered band-1 successor-work boundaries, itemized with their D-numbers in D-0050, plus cross-band noise (old prefix goldens embed `xp.awarded`/`ai_decision_audit` from unported passive hooks). **Live: PASS** for the ported v1 surfaces (all four hubs render; K7 settings lanes audited-green) | **2 found + fixed**: (1) manifest-declared PanelSpecs were never registered by EITHER composition root — every PanelRef-routed command died in a `LookupError` BUG envelope (PR #56); (2) live dispatch ran on `build_runtime`'s snapshot projection whose specs are empty `_SnapshotSpec` shells — EVERY live command blocked `no routable ref` (the replay-adapter decision's labeled follow-up, executed as PR #58; D-0050). Also fixed: `bootstrap.py check --strict` red on main (missing Status badge on this file, PR #56) | All five rows STAY `pending` (A-16 one-way door: flip needs full-corpus green; no pre-approved exemption kind covers missing subsystems — D-0050). `verified_live`: NO records minted — Q-0244 VERIFIED needs `prefix_twin_live` + `pipeline_replay` PASSES; pipeline replay is parity-red and no live message feed exists yet for a true prefix twin |
| 3. Moderation + logging (band 2 slice 1) | — pending | moderation 8, logging 7 | — | — | pending |
| 4. Operator spine eight (band 2 slice 2) | — pending | admin 2, channel 1, cleanup 3, automod 1, security 1, welcome 1, counters 2, image_moderation 1, server_management 2 | — | — | pending |
| 5. Economy family (band 3) | — pending | economy 6, treasury 2, inventory 1 | — | — | pending |
| 6. XP + karma + community (band 4) | — pending | xp 3, karma 8, community 2, community_spotlight 1, leaderboard 1 | — | — | pending |
| 7. Governance + roles + platform (band 5) | — pending | role 1, proof_channel 3, general/utility sweeps | — | — | pending |
| 8. Games (band 6) | — pending | blackjack 2, rps_tournament 1, games 2, farm 1, creature 5, mining 2, fishing 2, counting 3, chain 7, casino 2 | — | — | pending |
| 9. Knowledge + AI (band 7 — needs keys) | — pending | ai 20, btd6 39, project_moon 10+1 | — | — | pending |

## Kernel-boot evidence (step 1, verbatim key lines)

```
INFO sb.db.pool: PostgreSQL pool initialised (127.0.0.1:5432/superbot_test)
INFO sb.http.health: Health server listening on 127.0.0.1:8080
INFO discord.gateway: Shard ID None has connected to Gateway (Session ID: cfc6612b8f1710db054dac603bc676b3)
INFO sb.adapters.discord.gateway: gateway READY: logged in as the test bot (3 guilds)
INFO sb.app.main: leg C compare-only (disabled): 12 snapshot slash paths, 78 remote, drift=68 (REMOTE_LAG expected until app-command registration)
INFO sb.app.main: intent DEGRADE: message_content → prefix, fuzzy, triggers, nl_message, passive_onmessage not registered
INFO sb.app.main: intent DEGRADE: members → member_join, member_leave, member_cache not registered
INFO sb.app.main: bus rosters armed: sb.domain.community.spotlight, sb.domain.economy.service, sb.domain.role.service, sb.domain.server_logging.service, sb.domain.xp.service
INFO sb.app.main: boot complete: RUNNING (canary enqueued 71b8ffb4-de76-4eca-8926-81acfaa1fb91)
INFO sb.app.main: audit canary delivered: mutation_id=71b8ffb4-de76-4eca-8926-81acfaa1fb91
INFO sb.app.main: lifecycle STOPPED — clean exit
```

HTTP probes: `/ready` `{"status":"not_ready","reason":"gateway_not_ready","phase":"STARTING"}` [503] during boot → `{"status":"ready","phase":"RUNNING"}` [200] at RUNNING; `/health` 200; `/metrics` `lifecycle_phase{phase="RUNNING"} 1.0`. Shutdown exit code captured via `wait`: **0**.

## Band-1 evidence (step 2, verbatim key lines)

```
INFO sb.app.main: panel registry armed: 49 manifest-declared panel(s)
INFO sb.app.main: live dispatch index installed: 514 target(s)
INFO sb.adapters.discord.gateway: gateway READY: logged in as Galaxy Bot#6724 (id=1298426054636994611), 3 guild(s)
  [with SB_INTENT_MSGCONTENT_OK=true SB_INTENT_MEMBERS_OK=true → accepted; intent_degradations = []]
pre-#58: WARNING sb.kernel.interaction: dispatch user_error (user_error): target 'setup' has no routable ref
post-#58 drives into #bot-activity (message ids):
  !help        -> 1524751006603411587  embed "Help" (16 fields)
  !settings    -> 1524751014530388041  embed "Settings" (17 fields) + nav:help
  !diagnostics -> 1524751022860406987  embed "Diagnostics" (4 fields, footer "diagnostic · diagnostic.hub")
  !setup       -> 1524751031366582364  embed "Server setup" (10 fields) + nav:help
K7 lanes (live DB): settings.set_scalar -> success; settings.bind -> success
  settings row:  (1350952413737259151, logging_enabled, true)
  binding row:   (1350952413737259151, logging, mod, channel, 1351685557394346024)
  audit_log:     (settings, setting_set, settings.set_scalar, user),
                 (settings, binding_set, settings.bind, user)
golden replay (fresh parity_band1 DB): 0/53 green pre- and post-fix; post-fix reds
are shipped-surface render drift (ledgered successor work) — see D-0050.
```

## Flagged for owner

1. **Stale remote command tree on the test app**: the test application still
   carries 78 slash commands from the OLD bot's tree; the snapshot declares
   12. Leg C runs compare-only (REMOTE_LAG logged) because the NEW bot's
   app-command registration is an unbuilt successor — enabling
   `AUTO_SYNC_COMMANDS`' sync with an empty local tree would ERASE the
   remote tree. Owner call: leave the stale tree until app-command
   registration lands (recommended), or clear it deliberately.
2. **[RESOLVED 2026-07-09, band-1 pass]** Privileged-intent approvals: the
   portal toggles are now ON — a live boot with `SB_INTENT_MSGCONTENT_OK=true`
   `SB_INTENT_MEMBERS_OK=true` reached READY with both intents accepted
   (0 degrade markers). Galaxy Bot also has ADMINISTRATOR on the test guild,
   so server-side permission gaps won't block live command testing. NOTE:
   human-typed prefix commands still get no response — the on_message feed
   adapter is the ledgered live-adapter successor (flag 6 below).
3. **Retrospective doc**: `rebuild-orchestration-retrospective-2026-07-09.md`
   was missing at session start (flagged by the orientation pass); it landed
   mid-flight via PR #51/#53 — RESOLVED, no action needed.
4. **Auto-merge + "Require branches up to date"**: with several agents
   landing doc PRs concurrently, each PR needed manual branch-update pushes
   before auto-merge could fire (PR #54 went "behind" twice). Owner may want
   the ruleset's up-to-date requirement relaxed for doc-only paths, or the
   merge queue enabled, before the multi-worker testing phase scales up.
5. **Draft-janitor bug class**: the PREPARE-time type-inference failure fixed
   in PR #54 (`$1::timestamptz`) is invisible to unit fakes. Any later-band
   SQL of the shape `param - make_interval(...)` where the param's type is
   not pinned elsewhere in the statement has the same hazard; live-boot
   smoke per band is the cheap catch.
6. **The on_message feed adapter is now THE blocker for human-driven live
   testing**: intents are approved (flag 2 resolved) and dispatch is fixed
   (PR #58), but main() arms no message-band capability — a human typing
   `!help` in the guild gets silence. Building the prefix message feed
   (on_message → dispatch_prefix + MessageResponder, bot-author guard) is
   the smallest CUT-1 live-adapter successor and unlocks `prefix_twin_live`
   evidence for every band's verified_live rows.
7. **Band-1 golden corpus vs successor-work boundary**: the 53 band-1
   goldens exercise the SHIPPED settings hub family / help categories /
   deep `platform_*` diagnostic fleet / setup wizard — all named successor
   slices in the decisions ledger (itemized in D-0050). Until those port, band-1 parity
   rows cannot flip no matter how healthy the v1 projections are (D-0050).
   Owner may want the successor slices scheduled before bands 2+ repeat
   this pattern (moderation/logging goldens likely embed the same
   cross-band xp/ai_decision_audit noise at minimum).
8. **CI `report` leg health**: the golden-parity report job DOES bind and
   replay (465/465 replayable) — the repeated `FATAL: database "parity"
   does not exist` lines in its service-container log are just
   `pg_isready -U parity` health probes defaulting dbname to the username;
   benign, no action.
