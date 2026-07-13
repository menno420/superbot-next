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
| btd6 | ⚑ paragon calculator panel pending: 3 actions + 4 selectors (`btd6.paragon_pending`, `sb/domain/btd6/service.py`); 74 cmds live incl. the wire-type-5 strategy modal (minted-golden procedure) | ⚑ `btd6.ctteam/set_team` pending (NK-bracket ingestion successor, `sb/domain/btd6/oracle_surface.py:623`); seed-data live | ✅ 1 setting |
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
| fishing | ⚑⚑ **largest pending block**: 15 of 20 cmds pending (forecast/sail/rod/bait/craft* family → `operator_spine`) + 5 hub actions + structures; cast→Reel core loop IS live (`fishing.fish_route` commits `fishing.cast`, `sb/domain/fishing/service.py:96`). **IN-FLIGHT: fishing slice 1 #313, owner-gated deep-systems decision — hands off** | ✅ | ✅ |
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
| server_management | ✅ hub renders; channels forwards to ported channel ops | ⚑ 6 hub actions pending (moderation/roles/cleanup/access_map/help_preview/help_editor → `operator_spine`) | ✅ |
| settings | ✅ hub + explorer + per-group mutation pages (band-7 settings-mutation slice) | ⚑ 9 actions + 2 selectors pending: hub `needs_setup/invalid/missing_bindings/audit/command_access` + access panel explain/reset/paging + subsystem/scope selects (`operator_spine`) | ✅ K7 declare/read/bind proven live |
| setup | ✅ wizard interior live (wizard-lifecycle slice, ORDER 017): the 10 counted actions + the `essential_kind` selector armed — depth choice persists + lands on the ported sections hub, essential Step-1 applies the starter set through K7 `settings.set_scalar`, the suggestions review/walkthrough/stage lanes mutate state + write the K9 draft; `/setup-skip`+`/setup-unskip` session writes + `/setup-reset` clearing branch live (`sb/domain/setup/wizard.py`) | ✅ | ⚑ named successors (declared-honest terminals, `wizard.py` docstring): essential steps 2–8, the 10 per-section flows + linear wizard steps (`setup.open_section_*` / `setup.back_to_wizard`), the suggestion Edit lane, the final-review apply lane |
| starboard | ✅ config command family + ignore writes | ✅ | ⚑ threshold modal pending (`starboard.panel_threshold`, `sb/domain/starboard/panels.py:296-303`; workaround `!starboard #channel <n>` live) |
| ticket | ✅ 12 cmds live (RoleSelect wiring live, `handlers.py:597`) | ✅ | ⚑ ticket.setup panel: 3 actions + 2 selectors pending (`ticket.setup_pending`, `sb/domain/ticket/handlers.py:289`) |
| treasury | ✅ contribute modal + K7 round-trip + overdraw refusals | ✅ | ✅ |
| utility | ✅ 14 cmds | ⚑ 1 of 4 panel actions pending: 🔗 Invite (in-flight peer PR #332 wires it to the live `utility.invite_view`); Poll/Remind = G-10 modal ingresses over the live twin lanes + 420 forwards to the ported `four_twenty.overview` (ORDER 017 operator-hub edits A) | ✅ |
| welcome | ✅ templates over real census | ✅ | ✅ 10 settings |
| ux_lab | ✅ 2 cmds / 9 actions, 0 pending | ✅ | ✅ |
| xp | ✅ chat award + level-up fan-out live-proven (band 4) | ✅ | ⚑ xp.config panel 4 actions pending (`xp.config_{range,cooldown,channel}_pending` + `xp.import_setup_pending` → `operator_spine`; K7 settings lanes ARE the live workaround) |
| kernel (panels/engine) | ✅ render/browserview/engine golden-pinned (browse-interaction batch, kernel band `parity.yml:227` ported); `resolve.py:89` NotImplementedError = default port replaced at composition | ✅ | ✅ |

**Headline counts (50 rows):** core **43 ✅ / 7 ⚑** · admin **43 ✅ / 7 ⚑** ·
setup **47 ✅ / 3 ⚑** *(setup-row core flipped ✅ by the wizard-lifecycle
slice, ORDER 017 night-run; its setup column stays ⚑ for the named
successors; rps_tournament core flipped ✅ by the bot-match slice, same
night-run)*. Every flag is a *declared-honest* terminal or an
in-flight/owner-gated lane — the sweep found **zero silent gaps** (no
unregistered refs, no empty-string error paths).

## In-flight peer lanes (flagged, NOT worked here)

- mining write-parity **WP-2 (#312)** / **WP-3 (#317)** — vault + depth/world/
  wear write goldens (stacked; retire the remaining `guard-only-capture` rows).
- mining **energy domain core (#320)** — unblocks the `!cook`/`!use` terminals;
  dig-gating awaits an owner decision, sequenced after WP-3.
- **fishing slice 1 (#313)** — owner-gated (the deep-systems successor decision); its pending block is
  the lane's scope.
- settings-hub group-select navigation — claimed
  (`control/claims/operator-hubs-interactive.md`, 2026-07-12).

## Top gaps (ranked, worst first — the night's fix-slice driver)

1. **fishing deep systems** — 15/20 commands + 6 panel actions pending
   (`sb/manifest/fishing.py` → `operator_spine`); the single largest pending
   block in the fleet. **Owner-gated (#313, the deep-systems successor decision) — needs owner go, not a
   free slice.**
2. ~~**setup wizard interior**~~ — **DONE** (wizard-lifecycle slice, ORDER
   017 night-run): the 10 counted actions + selector + `/setup-skip` armed
   (`sb/domain/setup/wizard.py`). Remaining named successors (smaller, now
   individually sliceable): essential steps 2–8 · the 10 per-section flows ·
   the suggestion Edit lane · the final-review apply lane.
3. **mining argful write faces** — `!skill` spend (WP-5), argful
   `!build`/`!craft` (WP-6), `!cook`/`!use` (energy, #320), 12 panel-button
   writes; **partially in-flight — only WP-5/WP-6 slices are free AFTER
   WP-2/WP-3 land** (same tables re-freezing).
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
   Remaining free: server_management access_map/help_preview/
   help_editor (a 2.3k-line oracle projection pair — its own slice).**
7. **btd6 paragon calculator** — 3 actions + 4 selectors pending
   (`btd6.paragon_pending`); a self-contained pure-compute port
   (`sb/domain/btd6/service.py`). Free.
8. **ticket setup panel** — 3 actions + 2 selectors pending
   (`ticket.setup_pending`); command twins (`!ticketsetup` family) live. Free.
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
11. **starboard threshold modal** — 1 action (`starboard/panels.py:296`);
    trivial G-10 modal port, workaround exists. Free.
12. **ai NL live lane** — env-gated on `ANTHROPIC_API_KEY` (owner action, not
    a code slice); `ai_review_log` first row-bearing golden lands with an
    NL-armed capture (`parity.yml:361`).
