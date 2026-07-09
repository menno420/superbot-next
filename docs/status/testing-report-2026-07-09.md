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
| **12-tail. CUT-1 successors: app-command registration + live message feed** | PR #61 @ main `1f64b69`: app-command tree built from the live manifests ("app-command tree built: 12 slash command(s)"); GUILD-scoped sync opt-in (`SB_APPCMD_SYNC_GUILD_ID`, test plane only) synced 12 commands to MineSnakeBotTest ("guild app-command sync: 12 command(s) → guild 1350952413737259151: admin, community, counters, diagnostics, economy, games, help, karma, moderation, server-management, settings, setup"); the GLOBAL set untouched (leg C compare-only: 12 snapshot / 12 local / 78 remote GLOBAL, drift=68 REMOTE_LAG until CUT-3); prefix message feed armed behind the intent markers ("message feed armed: prefix dispatch on '!'"). **HUMAN-DRIVEN PROOF (owner at the keyboard, 2026-07-09 13:11–13:15 UTC)**: owner-typed `!help` → `command.dispatched surface=prefix command_key=help actor_id=340415158583296000 outcome=success`; owner-invoked `/help` → `surface=slash … outcome=success`; owner-typed `!warn`/`!timeout`/`!kick`/`!adminmenu` all dispatched (see step 3). Typed slash OPTIONS are a named successor (commands registered parameterless) | none direct (composition surfaces) | **PASS (live, human-driven)** | built by the parallel CUT-1 successor worker (PR #61, D-0051) | prefix_twin_live EVIDENCE now capturable; VERIFIED flips still need pipeline_replay green per surface (Q-0244) |
| **3. Moderation + logging (band 2 slice 1)** | Golden replay on a FRESH `parity_band2` DB (3 runs) + live exercise on the test guild + owner-attended session @ PR #62/#63. **Live (agent-driven, real gateway, in-process dispatch through the real pipeline)**: member census first (target safety — only non-owner human targeted, undo applied); `!warn` → shipped ack "⚠️ … warned (1/3)" posted + mod_logs/warnings rows + audit_log `member_warned` + `moderation.action_taken` → **logging fan-out posted "🛡️ **warn** — …" to the BOUND mod channel** (settings.set_scalar `logging_enabled`/`logging_moderation_enabled` + settings.bind logging/mod → #bot-activity, all audited-success); `!timeout @m 1` → REAL Discord timeout applied via the guild-action PORT (driver-side adapter impl; `timed_out_until` stamped) then UNDONE; `!warnings`/`!modlogs` read-backs live; `!kick` → ledgered typed-challenge (completion-report item 23) confirm prompt with `sb.confirm:kick:<request_id>`, then the confirmed component re-entry ran the op with RESTORED args (mod_logs kick row; effect leg honestly PARTIAL + not-installed finding — nobody kicked); `!clearwarnings` → "✅ Warnings cleared…" + row (warn count reset); `!logging status`/`!logging test` live ("🧪 logging test — routing OK" posted to the bound channel); fan-out counters sent_total=4. **Owner-typed ladder through the real message feed**: `!warn` (mod_logs row moderator_id=owner), `!timeout … 3` (row, reason "3 minutes"), `!kick` → confirm prompt (human-driven kick-confirm-deviation proof). Ban NOT live-fired: it carries NO confirm (compensatable by unban — the ledgered ban posture) and no sacrificial member exists (flag below) | 0/15 green: moderation 0/8, logging 0/7 (runs 1–3, pre/post fixes) | **Replay: RED (expected, classified)** — post-fix reds are ALL named classes (D-0052): cross-band xp/ai_decision_audit noise (D-0050's class); kernel-surface drift NEW this band (audit_log/event_outbox rows + command.dispatched/audit.action_recorded shapes on every MUTATION golden — bands 3+ inherit); kick-confirm deviation (the pre-approved exemption class, completion-report item 23 — golden kicks immediately, new prompts); golden-embedded SHIPPED defects (sweep.timeout's golden captured the old bot erroring with no row — new correctly writes it; shipped had no `warnings` command); unported invoking-message deletion + unban get_user; capture-world config not reseedable (ban delete_message_seconds=86400); ledgered logging port shapes (6 binding slots vs 11, `logging create` polite refusal, projection hub render). **Live: PASS** for every ported surface | **5 found + fixed (PR #62 + #63, D-0052)**: (1) op-routed commands SILENT on success (no success-copy channel; `LegOutcome.user_message` minted, moderation legs speak the shipped acks verbatim); (2) `!unban <id>` died in a BUG envelope (mention-only parse; bare ids + ValidatorError now); (3) `!timeout` duration IGNORED (argv[1] became the reason; every timeout ran 10 min); (4) §2.7 confirm gate dead-end — resolver never saw the op's ConfirmationSpec, prefix confirm ids couldn't re-enter, and the re-entry dropped the original args (three coupled fixes, full chain live-proven); (5) replay harness had no GuildModerationActions capture port (every moderation EFFECT leg PARTIAL in replay) + plain-content sends lacked the goldens' `components: []` wire shape | Both rows STAY `pending` (A-16: flips need full-corpus green; kernel-surface drift + cross-band noise alone keep every case red). NO exemption rows (flip-time artifacts; kick-confirm cites its ledger entry then). `verified_live`: NO records minted — Q-0244 VERIFIED needs prefix_twin_live AND pipeline_replay; the feed now makes prefix_twin_live evidence capturable (owner `!help` captured) but pipeline replay is parity-red |
| **OF. Owner-feedback triage** (hands-on session, 9 observations from the screen-recording frame notes) | Triage of the owner's live test @ the 13:07:46Z boot. **(1) "help not ordered"**: ordering was deterministic (subsystems alphabetical); real causes = bare grouped subcommand names + declaration-order within subsystems (both FIXED, PR #65: qualified names, per-subsystem sort) + the single-embed projection silently shedding past Discord budgets (16 of 39 subsystems render, the intro text sheds first) — the ledgered help category/pagination successor, now owner-ordered priority rework. **(2) "adminmenu shows nothing"**: NOT a wiring bug — replay renders the full embed; `admin` declares zero settings so the hub v1 read-view shows its honest empty row (diagnostics' "102" counts the platform-wide registry); per-hub menu actions are the declaration-first successor slices (owner-ordered rework). **(3) "help button dead"**: GENUINE CUT-1 GAP, FIXED (PR #65) — NO live listener routed component interactions (main() armed slash + on_message only; every nav:*/panel/`sb.confirm:` click died in the view's no-op default); new `sb/adapters/discord/component_feed.py` (additive `on_interaction`, wire-type-3 gate, invoker-lock mirror, K8 envelope fence) proven in-process through the exact live entry — evidence below. **(4) kick confirm**: arg-drop = PR #63 (in flight); a typed "Yes" can never complete BY SHAPE (confirm is component-shaped; text-only surface = flag 11, rework); new id per retry = per-request dedup, by design. **(5) warn "stuck at 1/3"**: NOT a current-main bug — replay-proven 1/3→2/3→3/3 + threshold escalation on a fresh DB; the owner's only live warn (13:12:11Z) was correctly 1/3 (count cleared 12:59:24Z by the band-2 exercise); the doubled "1/3" replies were band-2 exercise scrollback + the OLD bot answering the same prefix (flag 15). **(6) "Missing/invalid argument: route/member" bursts**: scrollback of already-fixed bug classes ("route" = the pre-PR-#58 snapshot-dispatch class, band-1's four hub commands; "member" = the PR-#63 confirm arg-drop); ZERO user_error dispatches in the live session's own trace; the envelope template renders per spec. **(7) help content quality**: bare names fixed (#65); `word`/`word list` are the same shipped op (two spellings, now visibly so); "community twice" = two real subsystems (community, community_spotlight); the 16 "port-armed later" channel placeholders are honest declared-not-ported terminals. **(8) generic error**: diagnosed — the 13:12:51Z finding `[workflow:moderation.timeout] GuildModerationActions not installed` (flag 10's exact successor; DB rows written, no Discord effect, honest PARTIAL). **(9) 6-min "latency"**: none exists — the owner's 13:05Z `!help` predates the 13:07:46Z boot (offline messages are never replayed by Discord); every traced dispatch answered sub-second; the real hazard is BOTH bots sharing `!` (flag 15) | none direct (triage row; component-feed + confirm-chain proofs replayed on a fresh `parity_triage` DB) | **3 fixed (PR #65) · 2 already-fixed classes confirmed (#58) / in flight (#63) · 3 deferred → owner-ordered presentation rework · 2 by-design · 2 owner-side (flags 14-15)** | PR #65 (component feed + help listing; details in D-0053); PR #63 (confirm args, band-2); presentation-rework scope handed off | no parity movement (live-surface fixes; all rows stay `pending`). NOTE: the RUNNING bot process predates every fix — restart from post-#65 main before re-testing (flag 16) |
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

## Band-2 slice-1 evidence (step 3 + 12-tail, verbatim key lines)

```
golden replay (fresh parity_band2 DB): 0/15 pre- and post-fix; post-fix reds all
named classes (D-0052). Convergence proof inside the reds after PR #62:
  warn ack byte-matches the golden send; timeout replays edit_member +
  "⏳ … timed out for 3 minute(s)."; unban replays the unban wire call + row;
  0 PARTIAL findings, 0 unhandled tracebacks (run 1 had both).
live drive (agent, real gateway, live DB superbot_test, target = the one
non-owner human; kick/ban never executed on him):
  !warn  -> msg 1524761856001052832 "⚠️ <@…> warned (1/3). Reason: band2 live warn"
            + fan-out 1524761854491234466 "🛡️ **warn** — target <@…> by <@bot>: …"
            rows: mod_logs(warn), warnings(count 1), audit_log(member_warned)
  !timeout @m 1 -> REAL timeout (timed_out_until 13:00:19Z) then UNDONE (None);
            ack 1524761881880035541; mod_logs(timeout,"1 minutes")
  !kick   -> prompt 1524766922598649886 "Are you sure? (confirm id:
            `sb.confirm:kick:b7eae67c-…`)" -> confirmed component re-entry ->
            outcome partial: mod_logs kick row id 7 committed, effect leg
            finding "GuildModerationActions not installed", target STILL a
            member (the live adapter is the D-0049 successor — by design)
  !clearwarnings -> "✅ Warnings cleared…" + row; warnings table emptied
  !logging test  -> "🧪 logging test — routing OK" posted to the bound channel
  fan-out counters: {"sent_total": 4}
owner-attended session (bot = python3 -m sb @ main+PR#62, READY 13:07:46Z):
  13:11:37 command.dispatched surface=prefix command_key=help
           actor_id=340415158583296000 outcome=success        (human !help)
  13:11:49 command.dispatched surface=slash command_key=help  (human /help)
  13:12:11 command.dispatched surface=prefix command_key=warn (human !warn ->
           mod_logs row 5: moderator_id=340415158583296000)
  owner !timeout -> mod_logs row 6 ("3 minutes"); owner !kick -> confirm
  prompt sb.confirm:kick:d409d36a-… (human-driven kick-confirm-deviation proof)
```

## Owner-feedback triage evidence (OF row, verbatim key lines)

```
live boot timeline (bot-live.log): process start 13:07:42Z, gateway READY
13:07:46Z; first owner dispatch 13:11:37Z (!help, answered sub-second) —
the unanswered 13:05Z !help predates the process (offline, never replayed).
finding 13:12:51Z: [workflow:moderation.timeout] EFFECT leg 'apply':
  GuildModerationActions not installed (→ outcome=partial on the owner's !timeout)
component-feed proof (fresh parity_triage DB, real pipeline + the real
DiscordPanelPresenter, driven through handle_component_interaction — the
exact live entry PR #65 binds to on_interaction):
  click nav:help            -> real discord.Embed "Help" (16 fields; fields now
                               qualified+sorted: `admin`, `adminmenu`, …)
  click g9:defunct:session  -> "This session has expired — start a new one."
                               (ephemeral; the §3.4 polite-expiry terminal)
  click sb.confirm:kick:<request_id> -> confirmed re-entry ran resolve()
                               (reached the pre-#63 arg-drop exactly — the
                               plumbing is proven; the args fix is PR #63's)
  slash-typed interaction (wire type 2) -> not consumed (the tree owns it)
warn-count proof (fresh parity_triage DB, current main):
  !warn ×3 (same target) -> "warned (1/3)", "(2/3)", "(3/3)" + threshold
  escalation "⏳ … timed out for 10 minutes (3 warnings)."; warnings row
  count=3; add_warning upsert increments (PK (user_id,guild_id) present)
adminmenu proof: !adminmenu replay -> full embed (title "Admin", blurb,
  field ("no declared settings","—"), footer "admin", nav:help button)
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
6. **[RESOLVED 2026-07-09, PR #61 + owner session]** The on_message feed
   adapter landed (D-0051) and was proven by the OWNER's own keystrokes:
   `!help` (prefix), `/help` (guild-synced slash), and a full human-typed
   moderation ladder all dispatched with outcome=success (step-3 and
   12-tail rows). prefix_twin_live evidence is now capturable for every
   band.
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
9. **Sacrificial test member needed for the kick/ban live-effect proof**:
   the guild has no expendable member (SuperBot = the OLD prod bot,
   adlerauge010 = a real human, menno4207 = the owner). Kick was proven to
   the confirm step + confirmed-op-run (effect leg honestly PARTIAL — no
   adapter armed, nobody kicked); ban was NOT fired at all — **ban carries
   NO confirm** (compensatable by unban, the ledgered ban posture), so once the guild-action
   adapter arms, any `!ban @x` dispatch bans immediately. Invite a
   throwaway account and tell the testing worker its id for the full
   ladder with real effects + unban undo.
10. **The moderation guild-action live adapter is the next CUT-1
   live-adapter successor to schedule** (D-0049): the owner's own
   `!timeout … 3` wrote the row, ack, and fan-out — but did NOT actually
   time the member out (effect leg PARTIAL + operator finding, by design).
   A ~40-line `GuildModerationActions` impl over discord.py (the band-2
   driver contains a working model) + `install_moderation_actions` in
   main() arms warn-escalation/timeout/kick/ban/unban for real.
11. **The confirm surface is text-only v1** (S9b successor): `!kick`'s
   typed-challenge prompt carries the confirm id in text; there is no
   button a human can click, and no message-band path to a component
   interaction — a human alone cannot complete a confirm today. The
   kernel confirm VIEW (buttons/modal) is the S9b panel-runtime successor.
   **UPDATE (owner-feedback triage, PR #65)**: the component PATH is now
   live — any rendered `sb.confirm:` control dispatches for real; the
   rework worker only needs to render the control (a danger-style button
   on the prompt).
12. **Band-3 heads-up (silent-success class)**: economy routes `daily`/
   `pay` straight at WorkflowRefs like moderation did — they will reply
   with silence until their legs adopt the new `LegOutcome.user_message`
   channel (D-0052). Cheap fix during the band-3 pass.
13. **Kernel-surface drift is a standing red class for every MUTATION
   golden** (D-0052): the new architecture writes audit_log/event_outbox
   rows and emits command.dispatched/audit.action_recorded shapes the old
   bot never had. Bands 3+ inherit it; parity flips stay blocked until the
   owner rules how the corpus treats kernel surfaces (exemption class,
   normalizer scope, or accepted-forever red).
14. **Presentation rework = owner-ordered priority (2026-07-09)**: the
   deferred surfaces the OF row classifies (help category/pagination, the
   operator-spine hub menus, the S9b confirm view, help content/grouping
   pass) are scheduled for a dedicated presentation-rework worker; the
   triage scope map (governing ledger entries, what's fixed, what remains,
   and the ⚑ boundary question on the band-1 settings component hub and
   setup-wizard slices) was handed to the coordinator. Note the boundary
   question needs an owner ruling — settings-EDIT workflows and wizard
   FLOW are functionality, not just presentation.
15. **Two bots answer `!` on the test guild**: the OLD SuperBot
   (1403818430758654132) shares MineSnakeBotTest and the `!` prefix with
   Galaxy Bot — duplicate/confusing replies contaminated the owner's
   session (the doubled warn acks and part of the error-burst scrollback).
   Owner-side: remove the old bot from the test guild (or change one
   prefix) before the next hands-on pass.
16. **Restart the live bot before re-testing**: the RUNNING process
   (booted 13:07:46Z from the band-2 branch) predates PR #63/#65 — the
   help button and confirm fixes are invisible until a fresh
   `python3 -m sb` from current main. A real human click on the 📚 Help
   button post-restart is the one missing evidence line for the
   component feed (a real interaction token cannot be synthesized
   agent-side).
