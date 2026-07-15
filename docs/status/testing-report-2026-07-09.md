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
| **PR. Presentation rework** (owner-ordered 2026-07-09: S9b confirm view, help grouping, panel render rules) | Three slices @ main `59755e3`, each live-proven through the real pipeline (driver session, real gateway, real messages in #bot-activity) after PR #63 was unstuck (merge conflict vs #65 resolved forward, auto-merged). **(a) S9b CONFIRM VIEW (PR #67, D-0054)**: `!kick` now prompts with REAL Confirm (danger) / Cancel buttons — the frozen §3.2 recipe exactly (button challenge ⇒ the `sb.confirm:<target>:<rid>` re-entry button; typed challenges ⇒ the Confirm click opens a one-field typed-phrase capture MODAL whose submit re-enters through the modal adapter; kick is typed ⇒ its Confirm carries `sb.confirm.open:`); Cancel = the kernel DECLINED terminal ("Cancelled — nothing was done."), a late Confirm after cancel answers "This action was cancelled.", double-confirm answers "already confirmed" (now RENDERED — the old branch returned copy nobody sent); view times out at `timeout_s` disabling controls + dropping the args stash; invoker-locked through the one panel-session seam the live component feed already mirrors; the wire-type-5 modal-submit path armed for `sb.confirm:` ids ONLY (G-10 panel modals stay dormant); the raw-id text prompt survives solely as the no-discord fallback. LIVE PROOF: prompt with both buttons posted → confirmed component re-entry ran the op with carried args (mod_logs kick row id 8, reason carried; effect leg honestly PARTIAL — nobody kicked) → cancel chain DECLINED both ways. **(b) HELP GROUPING (PR #70, D-0055)**: the shipped three-level "Pick a category…" shape as a pure manifest projection — `help.home` (7 category fields + select; the 6000-char shed GONE) → `help.cat_<hub>` (features + "Pick a feature…" select + Back) → `help.sub_<key>[_pN]` (EVERY command with summary, 24-per-panel chained pages); categories = the shipped mother-hub registry harvested verbatim @7f7628e1 as the legacy seed (hub-topology ratification untouched — flag 21); rosters computed from the live inventory (unmapped keys land in Other 📦; coverage pinned by test: chunk-union == inventory per subsystem). LIVE PROOF: `!help` → 7-category index; select "🎮 Games" → 11-feature panel (shipped order); select "⛏️ Mining" → "page 1/2" with 24 fields + "More (2/2) ▶" (37/37 commands reachable). **(c) RENDER RULES (PR #71)**: empty sections explain themselves — `!adminmenu` live-renders "The `admin` subsystem declares no settings yet. Menu actions for this hub arrive with the operator-spine successor slices." (bare em-dash gone; kernel help_index + diagnostic empty branches same rule) | none direct (presentation surfaces; help 0/3 replay unchanged — the goldens capture the SHIPPED pre-hub help, red stays ledgered per D-0050's class) | **PASS (live, agent-driven; owner hand-verification queued — bot left RUNNING @ 59755e3)** | 1 found + fixed en route: PR #63 was auto-merge-stuck on a real `docs/decisions.md`/test conflict vs #65 — resolved forward (merge commit), full chain preserved. Confirm DECLINED terminals previously returned copy without rendering it — fixed in #67 | no parity movement (all rows stay `pending`; help replay red unchanged in kind). `verified_live`: nothing minted (Q-0244 still needs pipeline_replay green) |
| **O2. Game-plugin contract (ORDER 002, host side)** | Host machinery @ PR #75: out-of-tree game plugins as installed distributions exporting a `SubsystemManifest` through the `sb.plugins` entry-point group; committed pin registry `plugins.lock.json` (the manifest.snapshot.json twin — written by `tools/plugin_pin.py --write`); boot loads plugins at main() step 9b (deliberately after boot-gate legs A/B — plugin refs must not leak into the in-tree recompile hash), verdicts: unpinned-installed or hash drift ⇒ FAILED_STARTUP `plugin_gate`, pinned-but-absent ⇒ warning+skip (hermetic CI / plugin-free containers boot unchanged); ONE joint compile pass (namespace/roles/semantic predicates) over host+plugins; v1 facet fence (commands/panels/settings/events/capabilities in; stores/data_invariants/wizard_sections host-owned); `pyproject.toml` makes `sb` pip-installable for plugin repos (deps read dynamically from requirements.txt — the lock stays the deployable truth). **IN-PROCESS PROOF (real pipeline, gateway-free — the parity composition root + the exact step-9b sequence)**: the hello-world plugin (`examples/superbot-plugin-hello/`, one command + one panel) installed as a REAL distribution → pinned → admitted (`superbot-plugin-hello==0.1.0 [hello]`, joint compile green) → `!hello` dispatched → panel embed rendered ("Hello from a plugin", footer `hello`, nav slot); NEGATIVE gates proven: tampered pin ⇒ hash-drift refusal, empty pins ⇒ unpinned refusal (evidence block below). Contract doc: docs/game-plugin-contract.md (the contract's one ledger home) | none (plugins have no goldens; the parity harness never loads plugins — replay corpus untouched) | **PASS (in-process; live-guild render ACHIEVED by the band-2 slice-2 pass — flag 18b resolved, see step 4; the separate-repo half stays owner-blocked, flag 18a)** | 2 design findings folded in while building: (1) the full-snapshot `stable_hash` is unusable as a plugin pin (its refs projection is the module-global ref table ⇒ drifts with unrelated imports) — pin = sha256 over the P8 serialization scoped to the plugin; (2) injection-mode `compile_manifests` bypasses the P1 `ENSURE_REFS` hooks several in-tree manifests rely on — the plugin host re-arms hooks on already-imported `sb.manifest.*` modules (never imports — unit tests stay roster-free) | no parity movement (0 ported stands); `verified_live`: nothing minted (plugin surfaces mint evidence rows when a real game plugin ships; hello is a contract proof) |
| **4. Operator spine eight (band 2 slice 2)** | Golden replay on a FRESH `parity_band2s2` DB (2 runs, pre/post fix) + live exercise on the test guild + the ORDER-002 live render, all @ main `091f269`→post-#79. **LIVE BOT RESTARTED FIRST** (flag-18b's named precondition): the presentation hand-pass process was SIGTERMed (clean exit) and a fresh `python3 -m sb` booted from latest main — "plugin host: 1 plugin(s) admitted (superbot-plugin-hello==0.1.0 [hello]) — live index re-installed: 524 target(s), +1 plugin panel(s)"; "guild app-command sync: 13 command(s) → … admin, community, counters, diagnostics, economy, games, **hello**, help, karma, moderation, server-management, settings, setup"; `/ready` 200 — left RUNNING. **ORDER-002 LIVE RENDER (flag 18b CLOSED)**: `!hello` through the live pipeline (driver session with the step-9b plugin host armed) posted the REAL "Hello from a plugin" panel into #bot-activity (msg 1524800434479435919; footer `hello`, nav:help). **Live drives (agent-driven, real gateway; destructive-ish ops inside a throwaway channel created+deleted for the purpose; every mutation undone)**: admin reads — `!coglist` (41 manifests) / `!slashes` (12) / `!loglevel` live; `!serverstats` honest BLOCKED (gateway-cache port unarmed); `!adminmenu`/`!servermanagement`/`!channelmenu` + all six operator hubs (`!cleanup` `!automod` `!security` `!welcome` `!counters` `!imagemod`) render their K7 settings read-views (declared defaults resolve: automod 15, security 9, welcome 10, counters 4, image_moderation 8 setting fields); the 17-channel-op family + `!cleanuphistory` + `!counterpreset` answer the ledgered polite pending-terminal refusals (the channel-ops port successor — completion-report boundary); cleanup word-filter K7 lane REAL end-to-end: `!word add` → prohibited_words row + audit_log `word_added` + outbox `audit.action_recorded`, `!word list` reads it back, `!word remove` (undone; `word_removed`); automod DECISION CORE over LIVE settings (K7 `settings.set_scalar` ×4 audited, then restored): spam burst→`["spam"]`, invite link→`["invites"]`, caps→`["caps"]`, clean→`[]`; security cores: RaidWindow trips at join 3/3-in-60s (not outside the window), age gate alert/pass/degrade-to-alert; welcome/counters templates resolve the shipped defaults and render over the REAL census (3 members: 2 humans + 1 bot). **ORDER-004 item 1 (P0, arrived mid-run)**: warn-escalation regression fixed + proven on the real engine/fresh Postgres — no port: warn 3 = PARTIAL, count KEPT at 3, NO phantom escalation/clearwarnings rows (compensator, D-0058); port armed: warn 4 escalates for real (rows + shipped copy) | 0/14 green: admin 0/2, automod 0/1, channel 0/1, cleanup 0/3, counters 0/2, image_moderation 0/1, security 0/1, server_management 0/1, servermanagement 0/1, welcome 0/1 (runs 1–2 identical pre/post fix) | **Replay: RED (expected, classified — NO new class this band)** — every red decomposes into the step-3 classes (D-0057): cross-band xp/ai_decision_audit noise (all 11 prefix goldens); kernel-surface drift (command.dispatched shapes; the 3 slash goldens diff `events: unexpected` — old slash emitted no events at all); successor-boundary render drift on EVERY case (the goldens capture the SHIPPED rich operator hubs — button-grid menus, live status descriptions, ephemeral slash replies, server-management's manager grid + its `panel_anchors` row — where v1 ships the declaration-first hub read-view); the pending-terminal deviation (sweep.cleanuphistory's golden replays the shipped sweep, `logs_from` + 5 wire calls, vs the polite refusal); capture-world config (sweep.wordmenu's golden embeds prohibited word `test` — not reseedable). **Live: PASS** for every ported surface (known-red presentation classes named per the ORDER-004 demo rule) | **3 found + fixed (PRs #79, #80; D-0057, D-0058)**: (1) >2000-char success copy 400s at Discord and `resolve()` swallows the render failure — the invoker gets NOTHING (`!coglist` ~2700 chars); live responders now chunk at line boundaries (ParityResponder untouched); (2) `word add`/`word remove` succeeded SILENTLY + bare `!word add` died in a BUG envelope — the D-0052 item-1/item-2 classes, hit exactly as flag 12 predicted (legs speak acks; ValidatorError user_error); both post-fix behaviors live-proven; (3) ORDER-004 item 1: the warn ladder committed phantom escalation rows + wiped the count when Discord refused the escalation — the WARN op's EFFECT leg now carries a compensator (count restored, rows withdrawn, operator finding; oracle `escalation_blocked` semantics; the enshrining test re-pinned) | All ten operator-spine parity rows STAY `pending` (A-16: kernel-surface drift + cross-band noise alone keep every case red — flag 13 ruling still pending). NO exemption rows (flip-time artifacts). `verified_live`: NO records minted — Q-0244 VERIFIED needs prefix_twin_live AND pipeline_replay; pipeline replay is parity-red for all nine subsystems |
| 5. Economy family (band 3) | — pending | economy 6, treasury 2, inventory 1 | — | — | pending |
| 6. XP + karma + community (band 4) | — pending | xp 3, karma 8, community 2, community_spotlight 1, leaderboard 1 | — | — | pending |
| **7. Governance + roles + platform (band 5)** | **LIVE-DRIVE leg DONE (2026-07-10)**: fresh live boot `python3 -m sb` @ main `5fcc1a9` on a FRESH `superbot_test` DB with `SB_TEST_DB_HOSTS` UNSET — **the ORDER 011 live verification HAPPENED**: boot proceeded on the ONE loud line ("test data plane: DB-host allowlist not set — accepting DSN host '127.0.0.1'"), migrations 0001–0024 applied, gateway READY as the test bot (3 guilds), ZERO intent DEGRADE markers (both `SB_INTENT_*_OK=true` present in the session env — the status.md "not set" note is stale), message feed armed on `!`, `/ready` 200, canary delivered, SIGTERM → clean exit. **Grant-state re-verification**: the OLD SuperBot (1403818430758654132) is GONE from MineSnakeBotTest (REST 404 Unknown Member; census = owner + adlerauge010 + Galaxy Bot) — **flag 15 RESOLVED owner-side**, `!` kept. NOTE: `SB_APPCMD_SYNC_GUILD_ID` now points at a NEW owner guild "Superbot Admin" (1522099141671653417) — the boot synced 12 commands THERE, not to MineSnakeBotTest. **Live drives** (driver = the main() twin incl. step 9b + step-16 rosters, real gateway, real posts in #bot-activity): `!rolemenu`/`!roles` → the 🎭 Role Hub panel (7 action buttons + nav:help); `role:manage` click → pickup stats through the component band; `!setrole`/`!rolesettings`/`!unsetrole` K7 lane REAL end-to-end (row + `role_threshold_set`/`_removed` audits); `!reactroles`/`!listreactroles`/`!removereactrole` K7 lane REAL (rows + `reaction_role_bound`/`_unbound` audits); `!temprole` → honest PARTIAL (GuildRoleActions port unarmed) with `compensate_grant_temp` dropping the row — the PR #105 compensator class LIVE; proof_channel: binding bound/unbound (audited), `!prizestatus` reads the bound channel, `!+prize`/`!timedprize`/`!-prize` all dispatch with `proof_access_granted`/`_revoked` audits and honest PARTIAL (ChannelPermActions unarmed; timed deadline row written then compensated away), `!prizemenu` → 🏆 Prize Channel Manager panel, grant/timed clicks → validator terminal; `reconcile_due_locks()` → 0 due (consistent); outbox 18/18 delivered | role 1, proof_channel 3, general/utility sweeps — **replay leg DONE via PR #95 (D-0062): fresh `parity_band5` DB, 0/12 pre- and post-fix, runs 2–3 byte-identical, every red in a named class, NO new class** (general/utility = documented not-yet-ported surfaces; live: ping/avatar/serverinfo/myprofile/generalmenu/utilitymenu NOT in the dispatch index → not consumed, honest) | **Live: PASS for every ported surface** (degrades honest + compensated). Replay: RED (expected, classified — D-0062) | Replay leg: 4 found / 4 fixed in #95 (rolemenu mis-map → `PanelRef("role.hub")`; refusal-copy 5th victim family; two-clocks 3rd instance; silent prize-hub mutations → `user_message` legs) +1 adjacent: worldcard Reply-shape crash, fixed #97. **Live leg: 3 found / 0 fixed (docs-only leg — recorded for the fix lane)**: (1) role pending terminals UNREGISTERED live — `!roleinfo`/`!createrole`/`!assignroles`/`!debugroles` + the `role:create` click die in `RefUnresolved: handler:role.create_pending has no registered callable` → BUG envelope instead of the polite pending refusal (root cause: `pending_handler()` registration lives ONLY in `ensure_handler_refs()`/ENSURE_REFS, which the live root never invokes when zero plugins are admitted; the parity boot runs the hooks — replay-invisible); (2) ack copy reads a result shape that doesn't exist — setrole/unsetrole/removereactrole read `(result.after or {}).get("record")` → `{}` → "✅ **None** auto-assigns at None day(s)." / "No such tier was configured." / "That binding did not exist." spoken over CORRECT audited writes/deletes (the flag-12 copy class, new shape: right channel, wrong content); (3) `!temprole` failure copy leaks the raw `WorkflowResult(...)` repr (service raises `RuntimeError(repr(result))`) | **CLOSED 2026-07-15**: the 3 live-leg fixes landed in #111 (role pending terminals register at import; role ack copy reads the leg's target_name keys; temprole raise carries honest copy), the live action ports armed at the composition root (GuildRoleActions + ChannelPermActions in sb/app/main.py), and the parity rows FLIPPED — proof_channel pending→ported #145 (3/3 green), role pending→ported #190 (byte parity). Band-5 tail discharged by the returning band-5 seat (D-0091, PR #491): a compensated PARTIAL never renders the withdrawn leg's success copy (speaking-compensator engine seam — grant_access PARTIAL had echoed "<@w> has access …" after compensate_lock dropped the row; silent compensators keep the D-0058 warn ack), the proof success acks read the real `record_lock`/`record_unlock` after-keys (the #111 ack-copy class, left behind in proof: armed-port grants rendered "<#0>"/"?"), and the band-5 compensators (lock/unlock/grant_temp) speak honest refusal copy. Golden gate GREEN at the fix: 502 goldens / 50 ported subsystems replay clean |
| 8. Games (band 6) | — pending | blackjack 2, rps_tournament 1, games 2, farm 1, creature 5, mining 2, fishing 2, counting 3, chain 7, casino 2 | — | — | pending |
| 9. Knowledge + AI (band 7 — needs keys) | — pending | ai 20, btd6 39, project_moon 10+1 | — | — | pending |
| **5. Economy family (band 3: economy + treasury + inventory)** | Golden replay on a FRESH `parity_band3` DB (3 runs: run 1 pre-fix, runs 2-3 byte-identical post-fix) + live exercise on the test guild @ PR #85 branch (real gateway driver, the main() twin incl. plugin-host step 9b), under the ORDER-004 item-3 binding (walking-skeleton + classify-or-fix). **Live (agent-driven, real pipeline)**: `!balance` → wallet line; `!daily` → "🎁 Daily Reward — ⬜ **Common** reward! **+813** 🪙 · Balance **813** 🪙 · 🔥 Streak **1** days · Total claims 1" (the leg ACK — silent before this band); ONE-TXN ATOMICITY proven on every value op (fresh-actor K7 daily/work + prefix pay + panel buy: balance moved EXACTLY by the ledger delta, `new_balance` column == aggregate, aggregate == Σ ledger at every step; a REFUSED op writes NOTHING — cooldown/insufficient/overdraw all checked pre/post); `!daily` again → verbatim domain refusal "⏰ Already claimed today! Come back in **23h 59m**." (unwrapped — the D-0060 envelope fix live); `!work` bare → Job Center list; `!work janitor` → "💼 Worked as **Janitor** — earned **50** 🪙…" + job_progress row; `!pay @syn 25` → both gift rows + conservation (sum of wallets invariant), pay-back drained; `!pay` self → "❌ You can't pay yourself."; PANEL ACTIONS live: `!economymenu` renders the shipped button grid (economy:daily/work/shop/balance/inventory/jobs/treasury/overview verbatim custom_ids), economy:shop click → Item Shop panel, `item_select` pick → audited `economy.buy` ("🛒 Bought **Toolkit** for **2,000** 🪙 — balance **9,380** 🪙" + inventory row + shop:toolkit ledger row), re-pick → "You already own a **toolkit**!", economy:daily click on cooldown → verbatim copy through the COMPONENT surface; `!inventory` → "🔧 **Tools** — 🔧 Toolkit" (unified-inventory assembly; band-6 mining/fishing extra-source ports honestly absent); `!treasury` hub + Contribute click → the G-10 `ModalSpec` OPENS (modal SUBMIT stays the ledgered dormant successor — wire-type-5 is consumed for `sb.confirm:` only; classified, not driven); treasury contribute/disburse round-trip via K7 (100 in → 100 out, `treasury:contribute`/`treasury:disburse` ledger rows, pool 0→100→0), overdraw → verbatim refusal; **INV-F reconciliation sweep CLEAN** (run_verify_import: violations {}, quarantine 0, twice). DB left documented: bot wallet 9,380 🪙 + toolkit ×1 (35 audited ledger rows), synthetic test wallets (9000000000000004xx) drained to 0, treasury 0 | 0/9 green: economy 0/6, treasury 0/2, inventory 0/1 (runs 1-3) | **Replay: RED (expected, classified — NO new class)** — post-fix reds decompose entirely into the band-2 named set: cross-band noise (xp/ai_decision_audit deltas + xp.awarded events on every prefix golden, PLUS the new-nuance RNG-STREAM OFFSET: multi-step goldens' daily amounts sit after the old bot's passive-XP draws in the seeded stream, so `economy.balance_and_daily` diffs 879≠1025 while single-step `sweep.daily` replays its draw EXACTLY); kernel-surface drift (audit_log/event_outbox/economy_balances/`mutation_id` rows + command.dispatched shapes + the slash golden's `events: unexpected`); the shipped invoking-message deletion (every golden's trailing delete_message); successor-boundary render drift (shipped rich wallet/daily/jobcenter/inventory embeds + the economymenu grid's panel_anchors/ensure-row side effects + deferred slash type-5 vs the v1 content acks and declaration-first hubs). **Live: PASS** for every ported surface | **4 found + fixed (PR #85, D-0060)**: (1) `SYSTEM_CLOCK` read a wall-clock seam the harness CANNOT pin (`datetime.now`) — every default-clock epoch stamp (economy last_daily/last_worked, treasury updated_at) diffed on every fresh replay; now reads through `time.time()` (identical live). (2) The daily tier draw used a PRIVATE unseeded `random.Random()` — the per-case `random.seed(case.seed)` never reached it; module-global default restores captured-draw replay (sweep.daily 1025/Uncommon exact). (3) `daily`/`pay`/`buy` succeeded SILENTLY live (the flag-12/D-0052 class, third victim as predicted) — all five value legs now speak golden-derived or honest acks. (4) Domain refusals (insufficient funds/cooldown/already-owned/treasury) rendered wrapped in "Missing/invalid argument: `<whole sentence>`…" because their shipped sentences rode ValidatorError's PARAM slot; `ValidatorError(message=…)` now carries verbatim user copy (param-only form keeps the usage hint — band-2 unchanged); sweep.treasury_contribute's refusal line replays byte-equal | All three rows STAY `pending` (A-16: cross-band noise + kernel drift alone keep every case red; no flips, no exemption rows). `verified_live`: NO records minted — Q-0244 needs pipeline_replay green |
| **6. XP + karma + community (band 4: xp + karma + community + community_spotlight + leaderboard)** | Golden replay on a FRESH `parity_band4` DB (4 runs: run 1 pre-fix, runs 2-4 byte-identical post-fix) + live exercise on the test guild @ PR #88 branch (real gateway driver = the band-3 main() twin incl. plugin-host step 9b PLUS the step-16 subscribe roster — fan-outs need the bus armed), under the ORDER-004 item-3 binding. **Live (agent-driven, real pipeline)**: CHAT AWARD through the REAL feed function (`message_feed.handle_chat_award`, the on_message body verbatim): first human message → award success delta **22** (in [15,25]), xp row {xp 22, messages 1}; second message inside the 60s cooldown → returns None, ROW UNCHANGED; rng sample over 6 fresh actors → draws 20/21/20/15/15/18, ALL in [xp_min,xp_max]; cooldown EXPIRY proven under an audited settings bracket (xp_cooldown→2s via `settings.set_scalar`, RESTORED via clear after): same actor re-awards post-window, delta in bounds, messages incremented; LEVEL-UP FAN-OUT: `settings.bind` xp.announce_channel → throwaway channel, `!givexp @syn 250` → "✅ Gave **250** XP … (Level **1**)" + the fan-out line "🎉 **Level Up!** <@…> reached **Level 1**!" delivered to the BOUND channel (binding unbound + channel deleted after); KARMA LADDER: `!thanks @syn for testing` → "✨ … gave karma to … — they now have **1** karma." + EXACTLY one karma_audit_log row + {points 1, received 1}/{given 1}; repeat inside 1h → blocked, WRITES NOTHING; self-grant → "❌ You can't give karma to yourself." (bare shipped copy — the refusal fix live); `!karma` card + `!karma add` alias grant; LEADERBOARDS/PROVIDERS: 12 rank providers registered (xp/coins/karma + 9 game categories), `!leaderboard` hub, `!leaderboard xp|karma|coins` boards render real standings, `!rank` card (XP rank + coin rank); consecutive same-command drives throttled by the shipped CooldownSpec ("Slow down — try again in 7s" — spaced re-drives succeed); COMMUNITY HUB: `!community` → declaration-first hub, all four panel clicks live (community.hub.xp/karma/leaderboard/spotlight); SPOTLIGHT: `!spotlight` glance (XP earned/coins/leaders/recent level-ups) + xp_leaders/richest clicks; `!xpmenu` panel; **INV-G/INV-K sweep CLEAN** (run_verify_import: violations {}, quarantine 0). DB left documented: xp rows for synthetic block 9000000000000005xx (38/250-L1/15-21) + bot 10xp, karma 2 points + 2 audit rows, brackets/bindings restored, throwaway channel deleted | 0/15 green: xp 0/3, karma 0/8, community 0/2, community_spotlight 0/1, leaderboard 0/1 (runs 1-4) | **Replay: RED (expected, classified — NO new class)** — post-fix reds decompose entirely into the named set: cross-band noise (ai_decision_audit deltas; the old `xp` table's `coins` alias column split to economy_balances at the ledgered coins boundary); kernel-surface drift (audit_log/event_outbox/`mutation_id` rows + command.dispatched shapes + slash `events: unexpected`); the shipped invoking-message deletion; successor-boundary render drift (rank/xpmenu PNG card via `get_from_cdn` + shipped rich karma/community/spotlight/leaderboard embeds + the shipped 5-feature community hub grid vs the v1 hub + `<cid:n>`/`nav:*` ids); capture-world config (`sweep.rank`'s golden captured the OLD bot's own "⚠️ An unexpected error occurred." — the capture world's failure, not a v1 deviation). CASCADE CLOSED: with the passive award armed in the harness, band-3's `xp: missing` + RNG-stream-offset lines vanish (replay now consumes the same per-message draws the captures did — the D-0060 cascade note realized). **Live: PASS** for every ported surface | **4 found + fixed (PR #88, D-0061)**: (1) the chat award had NO CALLER anywhere — live feed armed only the prefix twin, harness no-opped non-command messages; armed on BOTH (every human guild message, commands included, dispatch first). (2) The chat draw used a PRIVATE unseeded `random.Random()` (the exact D-0060 economy bug, 2nd victim); module-global fallback restores captured-draw replay (delta 25, seed 42, exact). (3) Karma stamped `occurred_at`/`last_received` with DB `NOW()` while cooldown/cap reads compare `ctx.clock()` — under the pinned replay clock the per-recipient cooldown NEVER fired (`karma.repeat_cooldown` granted twice where the old bot refused); both stamps now ride the leg's ctx.clock, the repeat blocks and writes nothing. (4) Karma's rejection ladder + xp's guards rendered WRAPPED ("Missing/invalid argument: `You can't give karma to yourself.`…" — live-only symptom, replay hides it behind the embeds-vs-content type diff); karma now rides the economy `_DomainRefusal` copy-only form, xp the two-arg form | All five rows STAY `pending` (A-16: kernel drift + render drift keep every case red; no flips, no exemption rows; flag-13 ruling still the gate). `verified_live`: NO records minted — Q-0244 needs pipeline_replay green |

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

## Presentation-rework evidence (PR row, verbatim key lines)

- PR #63 unstuck: update-branch API → 422 merge conflict; forward-only merge of main (kept the
  extended D-0052 item-5 entry + the args-restore test) → auto-merge completed as main `a6d48d1`.
- Live driver (real gateway session, #bot-activity, main `59755e3`):
  - `help_home`: title "📚 Help", 7 fields `["🎮 Games", "🐵 BTD6 Assistant", "🌑 Project Moon",
    "💰 Economy", "🛡️ Moderation & Safety", "🌱 Community", "⚙️ Server & Admin"]`,
    components `["help.home.category_select"]`
  - category click (values `["🎮 Games"]`) → outcome success; panel "🎮 Games", 11 feature fields
    (shipped roster order), components `["help.cat_games.feature_select", "nav:back:help.home"]`
  - feature click (values `["⛏️ Mining"]`) → "⛏️ Mining — commands · page 1/2", 24 fields,
    components `["nav:back:help.cat_games", "nav:back:help.sub_mining_p2"]` (the More chain)
  - `!adminmenu` → field ("No declared settings", "The `admin` subsystem declares no settings
    yet. Menu actions for this hub arrive with the operator-spine successor slices.")
  - `!kick <@…> presentation proof` → prompt "Are you sure?" with buttons
    `[("Confirm", "sb.confirm.open:kick:29fb4bbf-…"), ("Cancel", "sb.confirm.cancel:kick:29fb4bbf-…")]`;
    confirmed re-entry → outcome `partial` (effect port unarmed), `mod_logs` row id 8
    (action kick, reason "presentation proof"), target still a member
  - cancel chain: cancel → `declined` "Cancelled — nothing was done."; late confirm →
    `declined` "This action was cancelled."
- Post-merge boot `python3 -m sb` @ `59755e3`: READY, /ready 200, tree sync 12 commands,
  component + message feeds armed, canary delivered, 0 ERROR/Traceback — left RUNNING for the
  owner's hand pass.


## Game-plugin contract evidence (O2 row, verbatim key lines)

```
$ python3 tools/plugin_pin.py --write
plugin_pin: wrote plugins.lock.json — 1 plugin(s): superbot-plugin-hello
$ python3 tools/plugin_pin.py
plugin_pin: green — 1 plugin(s) admitted: superbot-plugin-hello==0.1.0 [hello]

EVIDENCE_JSON (order002_proof.py — parity composition root + the main() step-9b sequence):
"plugin_report": {"loaded": ["superbot-plugin-hello==0.1.0 [hello]"], "skipped": [], "violations": [], "admitted_keys": ["hello"]}
"index_has_hello_prefix": true, "index_has_hello_slash": true
calls[0] = send_message(embeds=[{"title": "Hello from a plugin", "description": "👋 This panel is declared in the **superbot-plugin-hello** repository …", "footer": {"text": "hello"}}], components=[[nav:help]])
"drift_gate": {"violations": ["superbot-plugin-hello: manifest hash drift — pinned sha256:tampered != installed sha256:06023075…"], "admitted": []}
"unpinned_gate": {"violations": ["superbot-plugin-hello: installed but NOT pinned in plugins.lock.json — the plugin twin of leg-A DRIFT …"], "admitted": []}
```

## Band-2 slice-2 evidence (step 4 + ORDER-002 render + ORDER-004 item 1, verbatim key lines)

```
fresh boot from latest main (bot-live-band2s2.log):
  15:23:19 plugin host: 1 plugin(s) admitted (superbot-plugin-hello==0.1.0
           [hello]) — live index re-installed: 524 target(s), +1 plugin panel(s)
  15:23:25 guild app-command sync: 13 command(s) → guild 1350952413737259151:
           admin, community, counters, diagnostics, economy, games, hello,
           help, karma, moderation, server-management, settings, setup
  /ready -> {"status": "ready", "phase": "RUNNING", "accepting_commands": true}
ORDER-002 live render (driver, real gateway, #bot-activity):
  !hello -> msg 1524800434479435919 embed "Hello from a plugin"
            (footer "hello", components [nav:help]), outcome success
golden replay (fresh parity_band2s2 DB): 0/14 runs 1-2 (identical pre/post
  fix); every diff line classified — no BUG envelopes, no tracebacks; the
  v1 hubs render inside the reds (title/footer/fields correct)
live drives (all outcomes captured; throwaway channel 1524800481589858324
  "band2s2-throwaway" created -> drives -> deleted, audit reasons logged):
  !serverstats -> blocked "Server stats need the live gateway cache — not
                  armed in this build yet."
  !create/!lock/!slowmode/!del -> blocked "Channel operations aren't armed
                  in this build yet — the channel-ops port lands with the
                  discord adapter slice." (+cleanuphistory/counterpreset kin)
  !word add band2s2word -> prohibited_words ["band2s2word"];
                  audit_log (cleanup, word_added); !word remove -> row gone,
                  (cleanup, word_removed); outbox tail audit.action_recorded
  pre-fix finding: !coglist reply 400 "Must be 2000 or fewer in length" ->
                  responder.render swallowed -> invoker saw NOTHING;
  post-fix: !coglist -> 2 sends (1987 + 396 chars); word ops speak:
                  "✅ Added `band2s2proof` to the prohibited words." /
                  "✅ Removed …"; bare !word add -> "Missing/invalid
                  argument: `word`. `!help ?` for usage."
  automod core (live settings, set+restored, audited): spam burst ->
                  ["spam"]; invite -> ["invites"]; caps -> ["caps"]; clean -> []
  security cores: RaidWindow join3-in-60s -> True (join outside window ->
                  False); age_gate young->alert, old->pass, unknown->alert
  welcome/counters templates (shipped defaults resolved from the live DB):
                  "👋 Welcome @NewMember to **MineSnakeBotTest**! You're
                  member #3."; counters {total "👥 Members: 3",
                  humans "🧑 Humans: 2", bots "🤖 Bots: 1"}
ORDER-004 item 1 proof (real engine, fresh parity_o4 DB, order004_warn_proof.py):
  no port: outcomes [success, success, PARTIAL]; user_message = warn ack
           ONLY ("⚠️ … warned (3/3). Reason: three"); DB count=3 KEPT;
           mod_logs = [warn, warn, warn] — NO phantom rows
  port armed: warn 4 -> success; effects [(timeout, …, 10, "Reached 3
           warnings")]; count reset; mod_logs +[warn, timeout, clearwarnings]
```

## Band-3 evidence (step 5 + ORDER-004 item 4, verbatim key lines)

```
golden replay (fresh parity_band3 DB; run 1 pre-fix, runs 2-3 post-fix
  BYTE-IDENTICAL): 0/9 all runs; post-fix diff deltas prove the seams —
  pre-fix:  economy.last_daily 1853737031 != 1783614506 (real clock leaked)
            sweep.daily delta 1025 != 2301 (private unseeded Random)
            treasury_contribute content "🏛️ Contributing **3** 🪙 is more
            than your **0** 🪙." != "Missing/invalid argument: `🏛️ …`…"
  post-fix: all three lines GONE (clock pinned, draw exact, copy byte-equal);
            remaining lines all named classes, NO new class
live exercise (driver = main() twin incl. step 9b, real gateway,
  #bot-activity; bot uid 1298426054636994611, synthetic actors
  9000000000000004xx):
  !daily -> "🎁 Daily Reward — ⬜ **Common** reward! **+813** 🪙 · Balance
            **813** 🪙 · 🔥 Streak **1** days · Total claims 1"
  daily atomicity (fresh actor): pre coins=None/0 rows -> post 857 == ledger
            row {delta 857, new_balance 857, reason daily} == Σledger; a
            cooldown-refused daily writes NOTHING (rows/balance unchanged)
  !daily again -> "⏰ Already claimed today! Come back in **23h 59m**."
            (verbatim, unwrapped — the refusal-copy fix live)
  work: "💼 Worked as **Cashier** — earned **75** 🪙. Balance: **932** 🪙"
            + job_progress row + work:cashier ledger row, aggregate==Σ
  pay: conservation proven (863+0 -> 838+25; both gift rows); self-pay ->
            "❌ You can't pay yourself."
  panel actions: economymenu grid (economy:daily/work/shop/… verbatim ids);
            economy:shop click -> Item Shop; item_select "toolkit" ->
            "🛒 Bought **Toolkit** for **2,000** 🪙 — balance **9,380** 🪙"
            + inventory row {toolkit, 1} + shop:toolkit ledger row; re-pick
            -> "You already own a **toolkit**!"; economy:daily on cooldown
            speaks the verbatim copy through the COMPONENT surface
  !inventory -> "🎒 …'s Inventory / 🔧 **Tools** — 🔧 Toolkit" (band-6
            extra-source ports honestly absent)
  treasury: contribute click -> ModalSpec(treasury.contribute_form) OPENS
            (G-10 submit = ledgered dormant successor, classified); K7
            round-trip 0->100->0 with treasury:contribute/disburse ledger
            rows; overdraw -> "🏛️ The treasury only holds **0** 🪙 — not
            enough to disburse **10000000** 🪙."
  INV-F reconciliation sweep: run_verify_import -> clean=true, violations {},
            quarantine 0 (ran twice, before and after the buy)
  DB left documented: bot wallet 9,380 🪙 + toolkit ×1 (35 audited
            economy_audit_log rows), synthetic wallets drained to 0,
            guild_treasury 0
ORDER-004 item 4 proof (PR #83, D-0059, real engine + superbot_test):
  degrade set/restore bracket through emit_degrade_notices -> TWO audited
  platform_latch_set rows (settings, guild 0) via settings.platform_latch;
  end state platform.degrade_state restored to "none"; boot from the branch
  -> RUNNING, /ready 200, SIGTERM clean exit
```

## Band-4 evidence (step 6, verbatim key lines)

```
golden replay (fresh parity_band4 DB; run 1 pre-fix, runs 2-4 post-fix
  BYTE-IDENTICAL): 0/15 all runs; post-fix diff deltas prove the seams —
  pre-fix:  karma.repeat_cooldown karma_points 1 != 2 (cooldown never
            fired under the pinned clock — replay granted TWICE),
            xp.chat_award steps[0].events: missing (no caller anywhere),
            db_delta.xp: missing on EVERY prefix golden (no passive award)
  post-fix: repeat grant BLOCKS and step 1 writes nothing (golden's
            write-nothing step matched); xp.chat_award step-0 xp.awarded
            replays EXACTLY (delta 25 = seed-42 first draw of
            randint(15,25)); the xp: missing lines are GONE corpus-wide
            (band-3 re-run: economy.balance_and_daily's RNG-stream offset
            line vanished — the D-0060 cascade note realized);
            remaining lines all named classes, NO new class
live exercise (driver = main() twin incl. step 9b + step-16 subscribe
  roster, real gateway, #bot-activity; bot uid 1298426054636994611,
  synthetic actors 9000000000000005xx):
  chat award (REAL feed fn): first msg -> success {delta 22, new_xp 22,
            source chat}, row {xp 22, messages 1}; second msg inside 60s
            -> None, row byte-unchanged; 6-actor rng sample draws
            20/21/20/15/15/18 all in [15,25]; xp_cooldown bracket 60->2s
            (settings.set_scalar, audited) -> post-window re-award, delta
            in bounds, messages 1->2; bracket RESTORED (clear_scalar)
  level-up fan-out: settings.bind xp.announce_channel -> #band4-levelups;
            !givexp -> "✅ Gave **250** XP to <@…>. They now have **250**
            XP (Level **1**)."; bound channel received "🎉 **Level Up!**
            <@900000000000000502> reached **Level 1**!"; unbind + channel
            deleted in finally
  karma:    !thanks @syn for testing -> "✨ <@bot> gave karma to <@syn> —
            they now have **1** karma." (+1 audit row, {points 1,
            received 1}, giver {given 1}); repeat inside 1h -> blocked
            "❌ You've already thanked <@syn> recently — try again in
            1h." AND WROTE NOTHING (pre==post rows); self ->
            "❌ You can't give karma to yourself." (bare — the D-0061
            refusal fix live; pre-fix it rendered wrapped in
            "Missing/invalid argument: `…`"); !karma -> card (points/
            rank/activity); !karma add -> alias grant
  boards:   12 providers registered (xp coins karma counting deathmatch
            rps mining creatures fishing farm gamexp crafting);
            !leaderboard -> category hub; !leaderboard xp ->
            "🏆 XP Leaderboard 🥇 <@…502> — Level 1 (250 XP) …";
            karma/coins boards render after the shipped per-command
            cooldown window ("Slow down — try again in 7s" when driven
            back-to-back — CooldownSpec, not a bug)
  community: !community hub (community.hub.xp/karma/leaderboard/spotlight
            + nav:help) — ALL four clicks live: XP panel (rank field,
            "15–25 XP per message · 60s cooldown"), karma card,
            leaderboard category select panel, spotlight glance
  spotlight: !spotlight -> "Server at a Glance ⭐ 422 XP · 🪙 9,380 coins"
            + XP Leaders + Richest + Recent Level-Ups (the real givexp
            level-up listed); xp_leaders/richest clicks -> boards
  INV-G/INV-K sweep: run_verify_import -> clean=true, violations {},
            quarantine 0
  DB left documented: xp rows 05{01:38, 02:250 L1, 10-15:15-21} + bot 10;
            karma 05{01,02} 1 point each, bot given_count 2, 2 audit
            rows; settings bracket + binding restored; channel deleted
wrap-up (band-3 session debt, settled this session): PRs #86/#87 were
  stuck "behind" the up-to-date ruleset -> API update_pull_request_branch
  + auto-merge; MERGED 17:03Z/17:04Z. Stale bot (post-#75 main, pid 15779)
  SIGTERMed -> clean exit; fresh boot from the band-4 branch for the
  walking skeleton, then from merged main post-#88 (RUNNING at session
  end: /ready 200, plugin admitted, 13 guild commands, feed armed WITH
  chat award).
```

## Band-5 evidence (step 7 LIVE-DRIVE leg, 2026-07-10, verbatim key lines)

```
live boot (python3 -m sb @ main 5fcc1a9, FRESH superbot_test DB on a fresh
  local PostgreSQL 16.13, SB_TEST_DB_HOSTS UNSET — the ORDER 011 live
  verification; HEALTH_HOST=127.0.0.1 required in this container, no IPv6):
  17:53:33 WARNING sb.db.data_plane: test data plane: DB-host allowlist not
           set — accepting DSN host '127.0.0.1'      (the ONE loud line;
           boot proceeded — no refusal, no owner ask)
  17:53:34 sb.db.pool: PostgreSQL pool initialised (127.0.0.1:5432/superbot_test)
           [migrations 0001–0024 applied on the fresh DB]
  17:53:34 live dispatch index installed: 522 target(s); panel registry
           armed: 96 manifest-declared panel(s)
  17:53:34 plugin pinned but not installed — skipped: superbot-plugin-hello
           (hello not installed in this container — warning+skip by contract)
  17:53:39 gateway READY: logged in as Galaxy Bot#6724
           (id=1298426054636994611), 3 guild(s)
  ZERO intent DEGRADE lines — SB_INTENT_MSGCONTENT_OK=true and
           SB_INTENT_MEMBERS_OK=true are PRESENT in the session env (the
           control/status.md "NOT set" note is stale); message feed armed:
           prefix dispatch on '!' + passive XP chat award
  17:53:39 leg C compare-only (disabled): 12 snapshot slash paths, 12 local
           tree, 78 remote GLOBAL, global drift=68 (REMOTE_LAG stands)
  17:53:39 guild app-command sync: 12 command(s) → guild 1522099141671653417
           ("Superbot Admin" — SB_APPCMD_SYNC_GUILD_ID now points at this
           NEW owner guild, NOT MineSnakeBotTest 1350952413737259151)
  17:53:39 boot complete: RUNNING (canary 9f87a0fb-d809-4733-bde6-5a9be709c959)
           → audit canary delivered; /ready 200 {"status": "ready",
           "phase": "RUNNING", "accepting_commands": true}
  18:05:27 SIGTERM → lifecycle STOPPED — clean exit
grant-state re-verification (REST, the test-app token):
  users/@me → Galaxy Bot (1298426054636994611); guilds = MineSnakeBotTest
  (1350952413737259151), Menno420's server420 (1508892958961832051),
  Superbot Admin (1522099141671653417)
  OLD SuperBot 1403818430758654132 in MineSnakeBotTest → 404 Unknown Member;
  member census = menno4207 + adlerauge010 + Galaxy Bot only
  ⇒ flag 15 (two bots on '!') RESOLVED owner-side — '!' kept for the drives
live drives (driver = the main() twin incl. step 9b + step-16 rosters, real
  gateway, real posts in #bot-activity 1351685557394346024; actor = bot uid;
  synthetic DB-only targets 9000000000000601/9000000000000700):
  !rolemenu -> msg 1525200868859973735 embed "🎭 Role Hub" (fields ⏱️ Time
           Roles / ⚡ XP Roles / 💬 Reaction Roles / 🚫 Exemptions; buttons
           role:create role:manage role:time role:xp role:reaction
           role:diagnostics role:exemptions + nav:help); !roles -> same hub
  role:manage click (component band, in-process through
           handle_component_interaction) -> success "🗂️ **Role pickup
           stats** — No pickup activity recorded yet."
  role:create click -> BLOCKED, BUG envelope (finding: RefUnresolved
           handler:role.create_pending has no registered callable) — bug (1)
  !setrole 7 Band5Tier -> role_thresholds {Band5Tier, 7} + audit
           role_threshold_set; ACK SAYS "✅ **None** auto-assigns at None
           day(s)." — bug (2); !rolesettings -> "⏱️ **Time role tiers** —
           • **Band5Tier** — 7 day(s)"; !unsetrole Band5Tier -> row deleted
           + audit role_threshold_removed, ACK SAYS "No such tier was
           configured." — bug (2)
  !reactroles <mid> 🎉 <@&…0700> -> reaction_roles row + audit
           reaction_role_bound + verbatim ack "✅ Reacting with 🎉 …";
           !listreactroles reads it back; !removereactrole -> row deleted +
           audit reaction_role_unbound, ACK SAYS "That binding did not
           exist." — bug (2)
  !temprole <@…0601> 5m <@&…0700> -> honest PARTIAL (GuildRoleActions not
           installed — the ledgered live-adapter successor);
           compensate_grant_temp DROPPED the row (role_grants empty — the
           PR #105 compensator invariant class proven LIVE); copy leaks the
           raw WorkflowResult repr — bug (3); !temproles -> honest
           "<@…0601> has no active temporary roles."
  !roleinfo/!createrole/!assignroles/!debugroles -> BLOCKED in the BUG
           envelope (RefUnresolved …_pending — bug (1); expected: the four
           polite pending terminals)
  proof_channel (throwaway #band5-proof 1525200937633710310, deleted after):
  settings.bind proof_channel -> success + audit binding_set + row
           {proof_channel, proof_channel, channel, 1525200937633710310}
  !prizestatus -> "<#…>: no active timed prize lock."
  !+prize <@…0601> -> PARTIAL "…has been granted access to <#…>!" + audit
           proof_access_granted (ChannelPermActions not installed — apply
           leg refused, honest)
  !timedprize <@…0601> 1 -> PARTIAL "…has access … for 1 minute(s) —
           auto-unlocks at 2026-07-10T18:05:00…" + audit; deadline row
           written then COMPENSATED away (compensate_lock;
           proof_channel_locks empty — no stranded row)
  !-prize -> PARTIAL "<#…> is now read-only for everyone." + audit
           proof_access_revoked
  !prizemenu -> embed "🏆 Prize Channel Manager" (fields Channel/State;
           buttons proof_channel.hub.prize_grant/prize_timed/prize_end/…);
           prize_grant + prize_timed clicks -> validator terminal
           "Usage: `+prize @winner`" (winner input = the G-10 modal
           successor, dormant by design)
  reconcile_due_locks() -> 0 due (consistent — no stranded deadline rows)
  general/utility sweeps: ping avatar serverinfo myprofile generalmenu
           utilitymenu NOT in the dispatch index -> not consumed (honest
           not-yet-ported; the port-the-small-four idea seed covers them)
  outbox: 18/18 audit.action_recorded delivered, 0 pending; trace
           command.dispatched emitted for EVERY drive (surface=prefix and
           surface=component both live)
```

Live-leg surface ledger: **exercised** = live boot cycle (ORDER 011 posture),
gateway connect+READY, guild visibility (3 guilds), role hub panel +
component band, role K7 lanes (thresholds, reaction bindings), temp-grant
compensator, proof_channel binding + status + grant/timed/end + hub panel,
lock-reconcile sweep, prefix + component dispatch traces, outbox relay.
**degraded** (honest, named successors — build work, not owner grants):
role/proof-channel Discord EFFECT ports unarmed (`GuildRoleActions`,
`ChannelPermActions` → PARTIAL + compensators), prize-hub winner input
(G-10 modal dormant), typed slash options. **blocked-by-bug** (this leg's
finds, fix lane next): the four role pending terminals + role:create click
(bug 1). **not-ported** (documented): general/utility sweep surfaces.
No band-5 surface is blocked on an owner grant.

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
   on the prompt). **RESOLVED (presentation rework, PR #67)**: the confirm
   VIEW renders (Confirm/Cancel buttons; typed challenges capture the
   phrase in a modal) — a human can now complete or cancel a confirm
   end-to-end.
12. **[RESOLVED 2026-07-09, band-3 pass]** Band-3 heads-up (silent-success
   class): economy routes `daily`/`pay` straight at WorkflowRefs like
   moderation did — they replied with silence exactly as predicted (third
   victim of the class). Fixed in PR #85: all five value legs (daily, work,
   pay, buy, treasury contribute/disburse) speak through
   `LegOutcome.user_message`; live acks verified in the step-5 row.
13. **Kernel-surface drift is a standing red class for every MUTATION
   golden** (D-0052): the new architecture writes audit_log/event_outbox
   rows and emits command.dispatched/audit.action_recorded shapes the old
   bot never had. Bands 3+ inherit it; parity flips stay blocked until the
   owner rules how the corpus treats kernel surfaces (exemption class,
   normalizer scope, or accepted-forever red). **UPDATE (band-3 session)**:
   ORDER-004 item 2 (drive `help` to byte-parity and flip the first
   parity.yml row through the A-16 door) stays ⚑ GATED on this ruling —
   help's replay reds include command.dispatched trace shapes, so no
   exemption rows can be minted until the owner names the class's
   disposition.
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
   agent-side). **DONE (presentation rework)**: the stale process was
   SIGTERMed and the bot rebooted from main `59755e3` (post-#67/#70/#71)
   and left RUNNING — the owner's real clicks are the remaining evidence.
17. **Presentation-rework remainders (⚑ where owner input is needed)**:
   (a) ⚑ the settings component EDIT hub and the setup wizard FLOW
   (their band-1 ledger entries name both as successor slices) are
   functionality, not presentation — still awaiting the
   owner's boundary ruling before any worker scopes them in (flag 14's
   open question). (b) ⚑ hub topology / Home-button wiring: categories
   ship as the harvested shipped seed; `parent_hub` [A] manifest growth +
   `register_hub`/Home-nav wiring ride the flag-21 sim-pass-1
   ratification. (c) per-option select descriptions/emoji + edit-in-place
   nav on prefix-origin panels are named render-grammar polish
   successors. (d) typed slash OPTIONS stay a named successor
   (commands register parameterless).
18. **Game-plugin contract remainders (ORDER 002 done-when tail)**:
   (a) ⚑ create the separate repo `menno420/superbot-plugin-hello` —
   integration tokens cannot create repos (GitHub App 403) and the git
   proxy scopes pushes to session repos; the complete package is seeded
   at `examples/superbot-plugin-hello/` and moves verbatim (the pin
   hashes the manifest, not the repo — no re-pin needed for the move).
   (b) **[RESOLVED 2026-07-09, band-2 slice-2 pass]** live-guild render:
   the presentation hand-pass bot was SIGTERMed and a fresh `python3 -m sb`
   from post-#75 main admitted the plugin and synced 13 guild commands
   (incl. `hello`); `!hello` driven through the live pipeline rendered the
   "Hello from a plugin" panel in #bot-activity (step-4 evidence block).
   ORDER 002's done-when now hangs ONLY on (a) — the owner-created
   separate repo (`menno420/superbot-plugin-hello` still does not exist,
   re-verified via GitHub search this session).
