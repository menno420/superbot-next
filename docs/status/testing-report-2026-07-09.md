# Testing report — subsystem-by-subsystem live phase (started 2026-07-09)

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
| 2. Settings + help + diagnostic + setup (band 1) | — pending | settings 4, help 3, diagnostic 37, setup 8, quicksetup 1 (53) | — | — | pending |
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

## Flagged for owner

1. **Stale remote command tree on the test app**: the test application still
   carries 78 slash commands from the OLD bot's tree; the snapshot declares
   12. Leg C runs compare-only (REMOTE_LAG logged) because the NEW bot's
   app-command registration is an unbuilt successor — enabling
   `AUTO_SYNC_COMMANDS`' sync with an empty local tree would ERASE the
   remote tree. Owner call: leave the stale tree until app-command
   registration lands (recommended), or clear it deliberately.
2. **Privileged-intent approvals on the test app**: `SB_INTENT_MSGCONTENT_OK`
   / `SB_INTENT_MEMBERS_OK` are unset in the test env, so message-band
   surfaces (prefix commands, fuzzy, NL mention shell when it arms) are
   degraded. If the test app has (or gets) the Discord-side approvals, set
   both envs to `true` for the band-1+ live command passes — prefix goldens
   need message_content.
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
