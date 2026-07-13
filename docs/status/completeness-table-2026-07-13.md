# Per-subsystem completeness table — 2026-07-13

> **Status:** `audit` — ORDER 017 item 1 (owner NIGHT-RUN mandate, PR #323).
> Point-in-time inventory @ main `b8fcdb7`; drives the night's fix slices via
> the "Top gaps" ranking at the bottom. Regenerate rather than amend.

## Method (evidence-first)

1. **Manifest sweep** — compiled all 49 `sb/manifest/*` modules, ran every
   `ENSURE_REFS` hook (the live root's plugin-host re-arm path), then resolved
   every declared route: **413 commands, 370 panel actions, 57 selectors,
   ~200 panels. Zero unregistered refs** — every declared surface has a
   registered callable (no `RefUnresolved` anywhere; the band-5 bug-1 class is
   dead: role pending terminals now register at module import,
   `sb/domain/role/handlers.py:579`).
2. **Pending-terminal classification** — handlers whose name or body carries
   the declared-honest refusal pattern (`operator_spine.pending_handler`,
   "aren't armed in this build", the deep-systems successor-decision marker)
   were flagged and hand-verified;
   false positives (e.g. `btd6.cmd_strat_pending` = the LIVE staff
   review-queue read, `sb/domain/btd6/oracle_surface.py:332`;
   `mining.stats_view` = live) were reclassified by reading the source.
   Net: **27 pending commands, 89 pending actions, 13 pending selectors** —
   all polite declared terminals, none silent.
3. **Marker scan** — `rg -g '!bootstrap.py' -g '!.substrate' -n
   'TODO|FIXME|NotImplemented|stub|not implemented|coming soon|WIP'` over
   `sb/` + `tests/`: no TODO/FIXME in product code; `placeholder` hits are the
   UI select property (benign); the one `NotImplementedError`
   (`sb/kernel/interaction/resolve.py:89`) is the default panel-engine port
   replaced at composition (benign); `casino/service.py:99` "Roulette is
   coming soon!" is the SHIPPED byte (oracle parity, not a gap class).
4. **Error-path spot-checks** — channel ops (17 commands, real failure copy on
   every branch, `sb/domain/channel/handlers.py`), cleanup history scan
   (honest `HistoryReaderNotInstalled` refusal, `handlers.py:114`), mining
   argful refusals (`service.py:420,939`), moderation/role/channel live-effect
   adapters exist (`sb/adapters/discord/{moderation,role,channel}_actions.py`)
   — the band-2/5 "not installed" degrades are armed code paths now. The
   band-5 live-leg copy bugs (record-shape acks, `WorkflowResult` repr leak)
   no longer grep in `sb/domain/role/`.
5. **Parity picture** — all 48 subsystem rows + kernel are `ported`
   (`parity/parity.yml:166-241`); coverage debt list is 0 rows
   (`docs/status/coverage-debt-2026-07-12.md`); remaining depth exemptions are
   the named `guard-only-capture` / `modal-driven` / `select-driven` /
   env-keyed classes, each with its exit condition ledgered in `parity.yml`.

## Column key

- **core** — the user-facing primary surface (commands + gameplay panels).
- **admin** — staff/operator surface (admin commands, hub mutation actions).
- **setup** — configuration surface (settings pages, config panels, wizard).
- ✅ = every declared surface in the column routes to a live handler (with
  evidence); ⚑ = declared-honest pending terminals or gating remain (cited).

## The table

| Subsystem | core | admin | setup |
|---|---|---|---|
| admin | ✅ 7 cmds live (coglist/slashes/loglevel/serverstats/adminmenu) | ✅ cogmgr select pick + ◀/▶ windowing live (ORDER 017 operator-hub edits C); the Load/Unload/Reload trio + `admin.hub/reload_all` are BY-DESIGN terminals, not gaps (docs/decisions.md — extension management has no compiled-architecture analog; final copy states it) | ✅ honest-empty (declares no settings; explanatory empty state, PR #71) |
| ai | ⚑ env-gated only: NL answer path dormant without `ANTHROPIC_API_KEY` (`parity.yml:361` ai_review_log exemption); all 24 cmds / 36 actions / 17 selectors live | ✅ `!aireview` family live (preset + review-channel writes golden-covered) | ✅ policy/preset/orchestration mutation live — "No chooser pending terminals remain" (`sb/domain/ai/panels.py:39`) |
| automod | ✅ decision core live-proven (band-2s2) | ✅ hub read-view | ✅ 15 settings resolve |
| blackjack | ✅ solo + tournament full flow, paid-pot conservation golden | ✅ `!bjstart` launch | ✅ 1 setting |
| btd6 | ✅ paragon calculator armed (3 actions + 4 selectors live, `btd6.paragon_pending` retired — `sb/domain/btd6/paragon_panel.py`, ORDER 017 slice A; live-API reconciliation stays a named successor, stamped in that module) | ⚑ `btd6.ctteam/set_team` pending (NK-bracket ingestion successor, `sb/domain/btd6/oracle_surface.py:623`); seed-data live | ✅ 1 setting |
| casino | ⚑ roulette disabled = SHIPPED parity byte (`sb/domain/casino/service.py:99`); poker play layer golden-pinned; per-player ephemeral hands = owner-armed live step (ledgered decision) | ✅ | ✅ |
| chain | ✅ 7 cmds + create modal live (`chain_channels` guard-only depth debt, `parity.yml:485` — coverage, not function) | ✅ | ✅ |
| channel | ✅ 17 channel-op cmds implemented over the ChannelActions adapter with real failure copy (`sb/domain/channel/handlers.py`) | ✅ hub 5 sub-panel flows live (create/delete/restrict/move/visibility + the toggle grid over the audited twin lanes — ORDER 017 operator-hub edits B; Send to Top/Bottom + create-new-category answer honest port-extension refusals) | ✅ |
| cleanup | ⚑ `!cleanuphistory` runtime-gated (honest refusal when HistoryReader unarmed, `handlers.py:114-117`; non-prohibited scan modes refuse honestly `:125`) | ⚑ 8 hub/word-panel actions pending (`cleanup.{logging,settings,policies}_pending` + words `word_add/word_remove/word_refresh/scan_history/anti_evasion` → `operator_spine`) — the `!word` K7 command lane IS live | ✅ |
| community | ✅ hub + 10 actions live | ✅ | ✅ |
| community_spotlight | ✅ glance + clicks live | ✅ | ✅ |
| counters | ✅ status/templates over real census | ✅ argful `!counterpreset <name>` apply live — three audited `settings.set_scalar` template writes + the shipped ack (`sb/domain/counters/panels.py` `_preset_view`; ORDER 017 operator-hub edits A); renames ride the sync loop as shipped | ✅ 4 settings |
| counting | ✅ 10 cmds + manager live (`counting_state` select-driven depth exemption, `parity.yml:515`) | ✅ | ✅ |
| creature | ✅ dex/battle/picker/rematch live (D-0079/D-0081 goldens); catch RNG env-exemption `parity.yml:537` | ✅ | ✅ |
| deathmatch | ✅ challenge card live (duel-resolution stats = time-driven exemption `parity.yml:561`) | ✅ | ✅ |
| diagnostic | ✅ 42 cmds live | ✅ 10 actions + 2 selectors implemented (ORDER 017 fix slice): hub `diag_status/sysinfo/errors` live successor reads (`process_state.py`/`log_buffer.py` + gateway-census seam), cmdlist pages 1–14 (oracle-extracted, page 1 golden-verified), flag-manager select→detail + guard-ladder mutations (`flag_catalog.py`), automation-panel pick + shipped guards — zero `*_pending` routes remain in `sb/domain/diagnostic/` | ✅ |
| economy | ✅ full value loop live + atomicity proven (band 3); INV-F clean | ✅ | ✅ |
| farm | ✅ hub + 3 K7 money lanes | ✅ | ✅ |
| fishing | ⚑ all 20 shipped commands ported — the fishing lane landed slices 1–4 tonight (#313 forecast/sail · #330 rod ladder · #342 bait shelf · #350 curios/tidepool/dock/boathouse/fishery; claim closed #353; the deep-system `PENDING` roster is empty, `sb/domain/fishing/service.py:720`); residue: the cast leg still runs the starter shore profile (venue/rod/bait/structure→cast wiring rides the minigame rung, per the service PENDING-roster note) + the 🎣 how-to-fish hub guide (`fishing.howtofish_pending`) — *morning true-up 2026-07-13; row was written pre-landing* | ✅ | ✅ |
| four_twenty | ✅ | ✅ | ✅ |
| games | ✅ hubs + substrate (checkpoints/game-xp covered-elsewhere, `parity.yml:668`) | ✅ | ✅ |
| general | ✅ 8 cmds + menu | ✅ | ✅ |
| governance | ✅ declaration-only manifest by design (settings/stores/events; no commands/panels — kernel-band home) | ✅ | ✅ |
| help | ✅ 60 panels / 10 selectors, three-level shipped shape (PR #70) | ✅ | ✅ |
| hermes | ⚑ egress adapter unarmed: work-order send refuses honestly ("the work order was NOT sent", `sb/domain/hermes/handlers.py:19`) | ✅ | ✅ |
| image_moderation | ✅ decision core + 8 settings | ✅ | ✅ |
| inventory | ✅ unified assembly + browse sort/filter/page goldens (D-0034) | ✅ | ✅ |
| karma | ✅ ladder + cooldowns live-proven (band 4) | ✅ | ✅ |
| leaderboard | ✅ 12 rank providers | ✅ | ✅ |
| logging | ✅ 6 cmds / 13 actions, fan-out live-proven (band 2) | ✅ | ✅ |
| mining | ⚑ core loop + 26-command ladder LIVE; remaining argful write faces pending: `!cook`/`!use` (energy lane — **#320 in flight**), `!skill <branch>` spend (WP-5), argful `!build`/`!craft` (WP-6), `!mine` = shipped-generic-error parity byte (`service.py:199-205`); 12 panel-button writes + workshop craft selector pending (`operator_spine`). **IN-FLIGHT: WP-2 #312, WP-3 #317 — hands off** | ✅ `!mineworld` reseed live (WP-3 #317 pins the write) | ✅ |
| moderation | ✅ warn/timeout/kick/ban ladder + compensators + confirm view (S9b); live adapter `sb/adapters/discord/moderation_actions.py` | ✅ | ✅ |
| platform | ✅ declaration-only manifest by design (stores only — kernel-band home) | ✅ | ✅ |
| projmoon | ✅ 11 cmds / 8 actions, 0 pending | ✅ | ✅ |
| proof_channel | ✅ prize family live (locks table = env-keyed exemption, needs #proof channel, `parity.yml:879`) | ✅ | ✅ |
| role | ✅ 17 cmds incl. temprole compensator; reaction-roles K7 lanes | ✅ hub 📝 Create = the shipped `RoleCreateModal` over the live `!createrole` lane (`role.create_form_submit`; ORDER 017 operator-hub edits A — hoist/mentionable ride the provisioning-port extension, the preset creation menu is a named successor) | ✅ |
| rps_tournament | ✅ `!rpsbot` deep bot-match flow armed (ORDER 017 fix slice, the PR that updates this row): per-player button views on the ledgered home-channel deviation, per-round stats through the audited `rps.bot_round` lane (`rps.bot_route`/`rps.botmatch_move` → `sb/domain/rps/bot_match.py`; zero rps pending routes remain); tournament core + cross-game guard (#277) live | ✅ | ✅ |
| security | ✅ raid window + age gate cores live-proven | ✅ | ✅ 9 settings |
| server_management | ✅ hub renders; channels forwards to ported channel ops | ⚑ 3 hub actions pending (moderation/roles/cleanup → `operator_spine`); access_map/help_preview/help_editor PORTED (ORDER 017 projections slices A/B/C — #362 Access Map = the P1A projection + P1C subpanel, D-0087 `sb/domain/server_management/access_projection.py`+`access_map.py`; Help Preview = the compiled-honest projection consumer, D-0088 `help_preview.py`; Help editor = the named-successor overlay store + audited K7 lanes + editor family, D-0089 `sb/domain/help/{overlay,overlay_ops,editor}.py`, live-Help overlay wiring incl. hide/rename on index+category surfaces) | ✅ |
| settings | ✅ hub + explorer + per-group mutation pages (band-7 settings-mutation slice) | ⚑ 9 actions + 2 selectors pending: hub `needs_setup/invalid/missing_bindings/audit/command_access` + access panel explain/reset/paging + subsystem/scope selects (`operator_spine`) | ✅ K7 declare/read/bind proven live |
| setup | ✅ wizard interior live (wizard-lifecycle slice, ORDER 017): the 10 counted actions + the `essential_kind` selector armed — depth choice persists + lands on the ported sections hub, essential Step-1 applies the starter set through K7 `settings.set_scalar`, the suggestions review/walkthrough/stage lanes mutate state + write the K9 draft; `/setup-skip`+`/setup-unskip` session writes + `/setup-reset` clearing branch live (`sb/domain/setup/wizard.py`) | ✅ | ⚑ final-review apply lane LIVE (final-review slice: `sb/domain/setup/final_review.py` — Apply executes the staged K9 draft through `DraftPipeline` over the audited K7 seams, apply summary + partial-recovery + setup-complete views armed) AND essential steps 2–8 LIVE (essential-steps slice: `sb/domain/setup/essential_steps.py` — Step-1 Save/Skip advances into the guided spine; greet/moderators/spam/log-channels/rewards/help-desk/command-access each direct-apply through `settings.set_scalar`+`settings.bind`+`role.set_threshold`+`ticket.update_config`+`platform.set_access_mode(+channels)` with channel/role auto-create over the armed ports; summary + extras + check-my-setup + the `essential_setup:resume` restart bridge armed) AND the suggestion Edit lane LIVE (suggestion-edit slice: the walkthrough's Edit opens the G-10 "Edit suggestion" rename modal for a `create` suggestion — submit rewrites the draft row, re-accepts it, advances — and answers a `bind` suggestion with the shipped can't-re-pick explanation; the staged `bind_channel` payload carries `target_name` so edits round-trip into the final-review pending line; the native re-pick picker sub-view is the flagged follow-up); AND the section-flow spine + first two flows LIVE (section-flows slice 4: `sb/domain/setup/section_card.py` — the shared card frame, status badges, replace-recommended/stage-custom/skip staging seams over the K9 draft; `sb/domain/setup/wizard_nav.py` — the LINEAR WIZARD STEPS behind ↩ Back to wizard, `setup.back_to_wizard` flipped: Back/Continue/Jump/Cancel + gated Apply Recommended / Apply-all / Skip, last step opens Final Review; `sb/domain/setup/preset_select.py` — `setup.open_section_preset_select` flipped: the 7-preset catalogue verbatim, pick → preview → stage-every-op; `sb/domain/setup/channels.py` — `setup.open_section_channels` flipped: the declared-binding walk, binding pick → channel pick → staged `bind_channel`, the high-confidence Apply-Recommended builder); AND the settings-write flows LIVE (settings-write slice 5: `sb/domain/setup/logging_presets.py` — `setup.open_section_logging_presets` flipped: the Single / Balanced / Detailed / Custom picker staging `create_channel` rows, Apply Recommended = Balanced; `sb/domain/setup/moderation.py` — `setup.open_section_moderation` flipped: the four-knob detail staging `set_setting` rows; `sb/domain/setup/cleanup.py` — `setup.open_section_cleanup` flipped: the scope × level walker + six-profile batch picker staging `set_cleanup_policy` through the K7 `governance.set_cleanup` op) AND the roles-family flows LIVE (roles-family slice 6: `sb/domain/setup/roles.py` — `setup.open_section_roles` flipped: the time/XP tier detail staging `set_role_threshold` rows through the K7 `role.set_threshold` op, time + XP folded per role onto the full-row-upsert leg; `sb/domain/setup/role_templates.py` — `setup.open_section_role_templates` flipped: the six-template permission-free bundle catalogue, pick → preview → stage `create_managed_role` rows fail-closed); remaining named successors (declared-honest terminals, `wizard.py` docstring): the 2 remaining per-section flows (`setup.open_section_{cog_routing,ticket}`), the role-create + channel-create compound ops (the staged `create_managed_role` / `create_channel` rows apply fail-closed as skipped), the on-ready resume sweep (needs an app-boot seam), the automation-rule apply seam (preset `add_rule` rows stage fail-closed), the SectionRecoveryView + workspace-notice ride, the native channel-recommender port (perms-bearing snapshot) |
| starboard | ✅ config command family + ignore writes | ✅ | ✅ threshold modal armed (the shipped `_ThresholdModal` G-10 form over the audited `starboard.configure` op — `sb/domain/starboard/panels.py`, ORDER 017 slice C) |
| ticket | ✅ 12 cmds live (RoleSelect wiring live) | ✅ | ✅ ticket.setup panel armed: 3 actions + 2 selectors live over the audited config/channel ops (`ticket.setup_pending` retired — `sb/domain/ticket/setup_panel.py`, ORDER 017 slice B; the ticket-OPEN provisioning flow stays a named successor, stamped in that module) |
| treasury | ✅ contribute modal + K7 round-trip + overdraw refusals | ✅ | ✅ |
| utility | ✅ 14 cmds | ⚑ 1 of 4 panel actions pending: 🔗 Invite (in-flight peer PR #332 wires it to the live `utility.invite_view`); Poll/Remind = G-10 modal ingresses over the live twin lanes + 420 forwards to the ported `four_twenty.overview` (ORDER 017 operator-hub edits A) | ✅ |
| welcome | ✅ templates over real census | ✅ | ✅ 10 settings |
| ux_lab | ✅ 2 cmds / 9 actions, 0 pending | ✅ | ✅ |
| xp | ✅ chat award + level-up fan-out live-proven (band 4) | ✅ | ⚑ xp.config panel 4 actions pending (`xp.config_{range,cooldown,channel}_pending` + `xp.import_setup_pending` → `operator_spine`; K7 settings lanes ARE the live workaround) |
| kernel (panels/engine) | ✅ render/browserview/engine golden-pinned (browse-interaction batch, kernel band `parity.yml:227` ported); `resolve.py:89` NotImplementedError = default port replaced at composition | ✅ | ✅ |

**Headline counts (49 rows — morning true-up recount 2026-07-13 at HEAD,
after the night's fix slices landed):** core **43 ✅ / 6 ⚑** (ai · casino ·
cleanup · fishing · hermes · mining) · admin **44 ✅ / 5 ⚑** (btd6 ·
cleanup · server_management · settings · utility) · setup **47 ✅ / 2 ⚑**
(setup · xp) *(the original "50 rows" counted the header line; per-slice
flip annotations consolidated into this recount)*. Every flag is a *declared-honest* terminal or an
in-flight/owner-gated lane — the sweep found **zero silent gaps** (no
unregistered refs, no empty-string error paths).

## In-flight peer lanes (flagged, NOT worked here)

- mining write-parity **WP-2 (#312)** / **WP-3 (#317)** — vault + depth/world/
  wear write goldens (stacked; retire the remaining `guard-only-capture` rows);
  **WP-5 (#335)** / **WP-6 (#344)** now open behind them (skill-spend +
  structure-build write goldens).
- mining **energy domain core (#320)** — unblocks the `!cook`/`!use` terminals;
  dig-gating awaits an owner decision, sequenced after WP-3.
- ~~**fishing slice 1 (#313)**~~ — **MERGED** (morning true-up 2026-07-13):
  the whole fishing lane landed overnight — slices 1–4 (#313/#330/#342/#350),
  claim closed (#353).
- settings-hub group-select navigation — claimed
  (`control/claims/operator-hubs-interactive.md`, 2026-07-12).

## Top gaps (ranked, worst first — the night's fix-slice driver)

1. ~~**fishing deep systems**~~ — **DONE** (fishing port lane, ORDER 017
   night-run; morning true-up 2026-07-13): slices 1–4 merged
   (#313/#330/#342/#350; claim closed #353) — all 20 shipped fishing
   commands ported, the deep-system `PENDING` roster is empty
   (`sb/domain/fishing/service.py:720`). Residue (small, ledgered in the
   service's roster note): the cast leg still runs the starter shore
   profile (venue/rod/bait/structure→cast wiring rides the minigame rung)
   and the 🎣 how-to-fish hub guide stays a pending terminal
   (`fishing.howtofish_pending`).
2. ~~**setup wizard interior**~~ — **DONE** (wizard-lifecycle slice, ORDER
   017 night-run): the 10 counted actions + selector + `/setup-skip` armed
   (`sb/domain/setup/wizard.py`). The final-review apply lane is ALSO DONE
   (final-review slice, `sb/domain/setup/final_review.py`), and the
   essential steps 2–8 are ALSO DONE (essential-steps slice,
   `sb/domain/setup/essential_steps.py` — the guided spine, summary,
   extras, health check + restart-resume bridge), and the suggestion
   Edit lane is ALSO DONE (suggestion-edit slice — the rename modal +
   bind explanation in `wizard.py`/`panels.py`), and the section-flow
   spine + linear wizard steps + the preset_select/channels flows are
   ALSO DONE (section-flows slice 4 — `section_card.py`,
   `wizard_nav.py`, `preset_select.py`, `channels.py`). Remaining named
   successors (smaller, now individually sliceable): the 7 remaining
   per-section flows · the on-ready resume sweep (app-boot seam) · the
   automation-rule apply seam · the recovery-view/notice rides.
3. **mining argful write faces** — `!skill` spend (WP-5, **PR #335 open**),
   argful `!build`/`!craft` (WP-6, **PR #344 open**), `!cook`/`!use`
   (energy, #320), 12 panel-button writes; **fully in-flight — WP-5/WP-6
   are now open PRs stacked behind WP-2 (#312) / WP-3 (#317)** (same
   tables re-freezing).
4. **settings access/audit admin surface** — 9 actions + 2 selectors pending
   (command-access matrix, audit view, health chips); the settings hub
   advertises controls that all refuse. Adjacent to the
   `operator-hubs-interactive` claim — coordinate before starting.
5. **diagnostic operator mutations** — **DONE** (ORDER 017 fix slice, the
   PR that updates this row): 10 actions + 2 selectors implemented (flag
   manager, automation panel, process-state trio, cmdlist paging;
   `sb/domain/diagnostic/handlers.py` carries zero `*_pending` routes).
6. **operator-hub admin action cluster** — cleanup words panel (8),
   server_management hub (6), channel hub (5), admin cogmgr (7), utility
   panel (4), xp config (4), counters preset (1), role create (1): ~36
   pending actions whose command twins are mostly live — a
   wire-clicks-to-existing-ops family. Coordinate with the
   `operator-hubs-interactive` claim (read-only nav slice already claimed;
   the EDIT controls are explicitly deferred to a settings-mutation-style
   slice). **PARTIALLY DONE (ORDER 017 night-run): operator-hub edits A
   (this PR, #358 — supersedes #355) delivers utility Poll/Remind modal
   ingress + the 420 forward, role.hub Create over the live createrole
   lane, and the argful counter-preset apply; edits B (#356, merged)
   delivered the channel hub's five sub-panel flows; edits C (#357,
   merged) armed the cogmgr select + windowing and reclassified the
   deploy trio by-design; peers own xp config (#345), cleanup words
   (#333), server_management nav trio + utility Invite (#332).
   Remaining free: ~~server_management access_map/help_preview/
   help_editor~~ — ✅ DONE (ORDER 017 night-run follow-up, projections
   slices A/B/C: #362 + the help-preview + help-editor PRs; D-0087/
   D-0088/D-0089). The hub's remaining pending trio is
   moderation/roles/cleanup (each its own manager port slice).**
7. **btd6 paragon calculator** — ✅ DONE (ORDER 017 night-run slice A):
   the 3 actions + 4 selectors armed as the pure-compute port
   (`sb/domain/btd6/paragon_panel.py`); `btd6.paragon_pending` retired.
8. **ticket setup panel** — ✅ DONE (ORDER 017 night-run slice B): the
   3 actions + 2 selectors armed over the audited config/channel ops
   (`sb/domain/ticket/setup_panel.py`); `ticket.setup_pending` retired.
9. ~~**rps bot-match deep flow**~~ — **DONE** (ORDER 017 night-run fix
   slice): `!rpsbot` armed end-to-end — shipped guards + copy verbatim,
   one bot-match button view per player (the tournament port's ledgered
   home-channel deviation), best-of scoring, per-round stats on the
   audited `rps.bot_round` op (`sb/domain/rps/bot_match.py`).
10. **hermes egress adapter** — work-order send unarmed
    (`sb/domain/hermes/handlers.py:19`). **Probed 2026-07-13 (rps-bot-match
    slice, evidence in docs/CAPABILITIES.md): env/owner-keyed, NOT a free
    slice.** The transmit leg is a small un-ported code slice (the oracle's
    ~40-line aiohttp POST, `disbot/cogs/hermes_cog.py:44-81`), but it sits
    behind DORMANT owner credentials `CLAUDE_ROUTINE_FIRE_URL` +
    `CLAUDE_ROUTINE_TOKEN` (`sb/spec/config.py:197-204`) — both absent in
    the build env (`bridge_configured() == False`; one-shot attempt →
    verbatim `RuntimeError: missing_config`). Unverifiable live until the
    owner keys the env — sequence the port WITH the owner keying.
11. **starboard threshold modal** — ✅ DONE (ORDER 017 night-run slice C):
    the shipped `_ThresholdModal` G-10 form armed over the audited
    `starboard.configure` op; the pending terminal retired.
12. **ai NL live lane** — env-gated on `ANTHROPIC_API_KEY` (owner action, not
    a code slice); `ai_review_log` first row-bearing golden lands with an
    NL-armed capture (`parity.yml:361`).
