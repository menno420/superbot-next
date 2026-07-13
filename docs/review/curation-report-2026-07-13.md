# Command & component curation — 2026-07-13

> **Status:** `audit` — delivered ORDER 017 item 2 curation report: every
> declared command and interactive component (1088 rows) measured and given
> exactly one KEEP / REWORK / DROP verdict with a one-line evidence citation.
> **Report-only: nothing was deleted, renamed, or rewired by this document.**
> Follows the audit-discipline of
> [admin-surface-audit-2026-07-12.md](admin-surface-audit-2026-07-12.md);
> prune calls are owner-ratifiable proposals, not decisions.

## Summary

**Reviewed HEAD: main `8ea3773` (inventory pin; branch base for this report).**

- **Total items: 1088** — commands 407, components 681 (panels 226, buttons 370, selects 57, modals 28).
- **Verdicts:** KEEP **918** · REWORK **110** · DROP **60** · NOT-MEASURED **0**
  - commands: KEEP 335 · REWORK 30 · DROP 42
  - components: KEEP 583 · REWORK 80 · DROP 18
- **REWORK split:** shipping tonight 17 rows (3 curation-rework PR bundles) · with sibling lane 66 rows · backlog 27 rows.

**Method.** Inventory built from `manifest.snapshot.json` (compiler 1.0.0, 48
subsystems) + `sb/manifest/*.py` with every declared ref resolved against the
live registry; verdicts evidenced by parity goldens (`parity/goldens/`, 485
files), the test tree (`tests/`, 187 files), handler source reads, and the
oracle clone `menno420/superbot@cdb2680` (vitality/legacy classifications).
Evidence = code / goldens / oracle only — no invented user data; no live
Discord or AI-model output was invoked (AI rows carry an explicit
"live AI output not measured" annotation where relevant).

**Reconciliation.** The 1088 rows were reviewed in six parallel chunks
(themed C1-C5 + C6 completeness backstop), 1167 verdict rows
total. Overlaps deduped on key (id, kind, subsystem): 77
rows were double-covered (all C1×C6 — C6 backstopped chain/counting/
deathmatch/farm/general exactly as its header planned); 74 agreed
(one kept, evidence merged), 3 disagreed (three farm money-path
buttons: C1 REWORK vs C6 KEEP — reconciled KEEP per the KEEP>REWORK>DROP
precedence, split-verdict noted on the rows, and the farm golden gap kept on
the backlog fix list). Two C6 contingency gap rows resolved outside the table:
`!warnings` is **not** a manifest gap — C3's evidenced finding wins (the
oracle never shipped it; golden `moderation/moderation_warn_flow.json` pins
the did-you-mean reply, sb/manifest/moderation.py:122-125); `/setup-depth`
**is** a genuine gap (oracle-live, undeclared in next) — carried as a REWORK
gap finding in §Rework below. Coverage gaps: 0 rows.

### Per-subsystem verdict rollup

| subsystem | total | KEEP | REWORK | DROP | NOT-MEASURED |
|---|---|---|---|---|---|
| domain/admin | 32 | 23 | 1 | 8 | 0 |
| domain/ai | 107 | 107 | 0 | 0 | 0 |
| domain/automod | 3 | 3 | 0 | 0 | 0 |
| domain/blackjack | 20 | 20 | 0 | 0 | 0 |
| domain/btd6 | 101 | 60 | 8 | 33 | 0 |
| domain/casino | 18 | 18 | 0 | 0 | 0 |
| domain/chain | 17 | 17 | 0 | 0 | 0 |
| domain/channel | 25 | 20 | 5 | 0 | 0 |
| domain/cleanup | 19 | 14 | 5 | 0 | 0 |
| domain/community | 12 | 12 | 0 | 0 | 0 |
| domain/community_spotlight | 8 | 8 | 0 | 0 | 0 |
| domain/counters | 5 | 4 | 1 | 0 | 0 |
| domain/counting | 19 | 19 | 0 | 0 | 0 |
| domain/creature | 25 | 25 | 0 | 0 | 0 |
| domain/deathmatch | 11 | 11 | 0 | 0 | 0 |
| domain/diagnostic | 74 | 69 | 5 | 0 | 0 |
| domain/economy | 25 | 24 | 1 | 0 | 0 |
| domain/farm | 9 | 9 | 0 | 0 | 0 |
| domain/fishing | 32 | 15 | 17 | 0 | 0 |
| domain/four_twenty | 5 | 5 | 0 | 0 | 0 |
| domain/games | 20 | 20 | 0 | 0 | 0 |
| domain/general | 21 | 21 | 0 | 0 | 0 |
| domain/help | 71 | 71 | 0 | 0 | 0 |
| domain/hermes | 3 | 3 | 0 | 0 | 0 |
| domain/image_moderation | 3 | 3 | 0 | 0 | 0 |
| domain/inventory | 16 | 16 | 0 | 0 | 0 |
| domain/karma | 5 | 5 | 0 | 0 | 0 |
| domain/leaderboard | 3 | 2 | 1 | 0 | 0 |
| domain/logging | 25 | 25 | 0 | 0 | 0 |
| domain/mining | 72 | 45 | 26 | 1 | 0 |
| domain/moderation | 25 | 24 | 0 | 1 | 0 |
| domain/projmoon | 20 | 20 | 0 | 0 | 0 |
| domain/proof_channel | 12 | 12 | 0 | 0 | 0 |
| domain/role | 26 | 23 | 1 | 2 | 0 |
| domain/rps_tournament | 30 | 29 | 1 | 0 | 0 |
| domain/security | 3 | 3 | 0 | 0 | 0 |
| domain/server_management | 13 | 9 | 4 | 0 | 0 |
| domain/settings | 16 | 5 | 11 | 0 | 0 |
| domain/setup | 25 | 13 | 11 | 1 | 0 |
| domain/starboard | 12 | 12 | 0 | 0 | 0 |
| domain/ticket | 26 | 21 | 5 | 0 | 0 |
| domain/treasury | 7 | 7 | 0 | 0 | 0 |
| domain/utility | 33 | 27 | 3 | 3 | 0 |
| domain/ux_lab | 11 | 0 | 0 | 11 | 0 |
| domain/welcome | 3 | 3 | 0 | 0 | 0 |
| domain/xp | 20 | 16 | 4 | 0 | 0 |
| **total** | **1088** | **918** | **110** | **60** | **0** |

## Verdict table — every item

One row per inventory item, grouped by subsystem. `REWORK — with sibling
lane` names the open lane/claim the fix rides; evidence is a one-line
citation (golden path, test file, or handler `file:line`).

### domain/admin (32 — KEEP 23 · REWORK 1 · DROP 8)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `adminmenu` | command | domain/admin | DROP | sb/manifest/admin.py:32-34 — `admin` is CommandKind.BOTH routing the same panel:admin.hub; golden admin/sweep_adminmenu.json |
| `admin` | command | domain/admin | KEEP | golden parity/goldens/admin/sweep_slash_admin.json; tests: tests/unit/band2/test_hub_empty_states.py (+5) |
| `serverstats` | command | domain/admin | KEEP | golden parity/goldens/admin/sweep_serverstats.json; tests: tests/unit/app/test_main_wiring.py |
| `coglist` | command | domain/admin | KEEP | golden parity/goldens/admin/sweep_coglist.json; tests: tests/unit/interaction/test_responder_chunking.py |
| `slashes` | command | domain/admin | KEEP | golden parity/goldens/admin/sweep_slashes.json |
| `loglevel` | command | domain/admin | KEEP | golden parity/goldens/admin/sweep_loglevel.json |
| `restart` | command | domain/admin | KEEP | sb/manifest/admin.py:47-48 → handler admin.restart (K5 request_restart per docs/decisions.md:223); capture-skipped in parity/goldens/_sweep_skips.json (process lifecycle); tests hit 1 file |
| `admin.hub` | panel | domain/admin | KEEP | spec sb/domain/admin/panels.py:121; open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; tests: tests/unit/app/test_component_feed.py |
| `admin.hub.server_stats` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; live handler:admin.serverstats_view |
| `admin.hub.cog_list` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:admin.cogmgr |
| `admin.hub.reload_all` | button | domain/admin | DROP | docs/decisions.md:223 'NOT ported ... cog / loadall / unloadall / syncslash (deploy-ops)'; sb/domain/admin/panels.py:147; sb/domain/admin/cogmgr.py docstring cites 'the hub's Reload All precedent' |
| `admin.hub.log_level` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; live handler:admin.loglevel |
| `admin.hub.admin_settings` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:settings.hub |
| `admin.hub.admin_sm` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:server_management.hub |
| `admin.hub.admin_channels` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:channel.hub |
| `admin.hub.admin_ai` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:ai.hub |
| `admin.hub.admin_platform` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:diagnostic.platform_hub |
| `admin.hub.admin_diagnostics` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:diagnostic.hub |
| `admin.hub.admin_uxlab` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:ux_lab.home |
| `admin.hub.admin_logging` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:logging.hub |
| `admin.hub.admin_cleanup` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:cleanup.hub |
| `admin.hub.admin_help` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:help.home |
| `admin.hub.admin_overview` | button | domain/admin | KEEP | declared in sb/domain/admin/panels.py:121 (admin.hub spec); panel open pinned by goldens/admin/sweep_adminmenu.json + admin/sweep_slash_admin.json; nav -> panel:admin.hub |
| `admin.server_stats` | panel | domain/admin | KEEP | spec sb/domain/admin/panels.py:211; open pinned by goldens/admin/sweep_serverstats.json |
| `admin.cogmgr` | panel | domain/admin | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | sb/domain/admin/cogmgr.py:149 (spec) + docstring:29-36 — roster is a golden-pinned CAPTURE LITERAL of the oracle's 58 discord.py extensions; 'the manifest registry (admin.subsystems_view) is the honest successor read'; golden admin/sweep_coglist.json pins the open |
| `admin.cogmgr.cogmgr_load` | button | domain/admin | DROP | sb/domain/admin/cogmgr.py:173 + under-port note 'Load/Unload/Reload reloaded discord.py extensions IN-PROCESS — deploy-ops'; docs/decisions.md:223 NOT-ported class |
| `admin.cogmgr.cogmgr_unload` | button | domain/admin | DROP | sb/domain/admin/cogmgr.py:178 + under-port note 'Load/Unload/Reload reloaded discord.py extensions IN-PROCESS — deploy-ops'; docs/decisions.md:223 NOT-ported class |
| `admin.cogmgr.cogmgr_reload` | button | domain/admin | DROP | sb/domain/admin/cogmgr.py:183 + under-port note 'Load/Unload/Reload reloaded discord.py extensions IN-PROCESS — deploy-ops'; docs/decisions.md:223 NOT-ported class |
| `admin.cogmgr.cogmgr_refresh` | button | domain/admin | KEEP | sb/domain/admin/cogmgr.py:190 — real REFRESH_PANEL nav; golden admin/sweep_coglist.json pins the id admin:cogmgr:refresh |
| `admin.cogmgr.cogmgr_prev` | button | domain/admin | DROP | sb/domain/admin/cogmgr.py:199 + under-port note 'Prev/Next re-windowed the select in place' |
| `admin.cogmgr.cogmgr_next` | button | domain/admin | DROP | sb/domain/admin/cogmgr.py:203 + under-port note 'Prev/Next re-windowed the select in place' |
| `admin.cogmgr.cogmgr_select` | select | domain/admin | DROP | sb/domain/admin/cogmgr.py:161-162 + under-port note 'the cog SELECT armed those deploy-ops buttons' |

### domain/ai (107 — KEEP 107)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `ai` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai.json; test tests/unit/diagnostic_band/test_band1_diagnostic.py |
| `ai.status` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_status.json; +1 more golden(s); test tests/unit/band2/test_band2_slice1.py [wiring+guard verdict; live AI output not measured — AI_ENABLED default OFF in oracle] |
| `ai.readiness` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_readiness.json; +1 more golden(s) [wiring+guard verdict; live AI output not measured — AI_ENABLED default OFF in oracle] |
| `ai.settings` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_settings.json; +1 more golden(s); test tests/unit/settings_band/test_platform_latch.py |
| `ai.policy` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_policy.json; +1 more golden(s); test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py |
| `ai.diagnostics` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_diagnostics.json; test tests/unit/app/test_main_wiring.py [wiring+guard verdict; live AI output not measured — AI_ENABLED default OFF in oracle] |
| `ai.providers` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_providers.json [wiring+guard verdict; live AI output not measured — AI_ENABLED default OFF in oracle] |
| `ai.routing` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_routing.json; +1 more golden(s) [wiring+guard verdict; live AI output not measured — AI_ENABLED default OFF in oracle] |
| `ai.why-no-response` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_why-no-response.json |
| `ai.forget` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_forget.json; +1 more golden(s) |
| `ai.support-report` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_ai_support-report.json; +1 more golden(s) |
| `aimenu` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aimenu.json; +1 more golden(s); test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py — dual prefix+slash declaration, expected dedup artifact (KEEP, not a drop); menu pair ai+aimenu mirrors oracle (aimenu prefix+slash registry entry_point) |
| `aireview` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview.json; test tests/unit/band7/test_band7_ai_review_walking_skeleton.py |
| `aireview.list` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_list.json; test tests/unit/band6/test_band6_channel_hub.py |
| `aireview.resolve` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_resolve.json; test tests/unit/band6/test_band6_games_substrate.py |
| `aireview.export` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_export.json |
| `aireview.channel` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_channel.json; test tests/unit/platform_governance/test_s15_governance.py |
| `aireview.off` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_off.json; test tests/unit/band6/test_live_channel_adapters.py |
| `aireview.preset` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_preset.json; test tests/unit/ai/test_k10_nl_engine_evals.py |
| `aireview.preset.add` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_preset_add.json; test tests/unit/app/test_cut1_surfaces.py |
| `aireview.preset.from` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_preset_from.json; test tests/unit/band3/test_band3_economy.py |
| `aireview.preset.list` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_preset_list.json; test tests/unit/band6/test_band6_channel_hub.py |
| `aireview.preset.remove` | command | domain/ai | KEEP | golden parity/goldens/ai/sweep_aireview_preset_remove.json |
| `ai.hub` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/manifest/ai.py:120 |
| `ai.hub.ai_refresh` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:217 |
| `ai.hub.ai_diagnostics` | button | domain/ai | KEEP | test tests/unit/diagnostic_band/test_band1_diagnostic.py; component spec/handler sb/domain/ai/panels.py:217 |
| `ai.hub.ai_providers` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:217 |
| `ai.hub.ai_routing` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:217 |
| `ai.hub.ai_settings` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:218 |
| `ai.hub.ai_policy` | button | domain/ai | KEEP | test tests/unit/settings_band/test_band1_settings.py; component spec/handler sb/domain/ai/panels.py:218 |
| `ai.hub.ai_behavior` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:218 |
| `ai.hub.ai_tools` | button | domain/ai | KEEP | test tests/unit/ai/test_k10_tasks_flags_routing.py; component spec/handler sb/domain/ai/panels.py:218 |
| `ai.settings` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py; panel spec sb/domain/ai/panels.py:191 |
| `ai.settings.back_to_hub` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:1120 |
| `ai.settings.open_panel` | button | domain/ai | KEEP | test tests/unit/band6/test_band6_rps_quickplay.py; component spec/handler sb/domain/ai/panels.py:1125 |
| `ai.settings.edit_setting` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py; select spec/handler sb/domain/ai/panels.py:1136 |
| `ai.settings.reset_setting` | select | domain/ai | KEEP | select spec/handler sb/domain/ai/panels.py:1142 |
| `ai.card` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_verdict009_card_nav.py; panel spec sb/domain/ai/panels.py:225 |
| `ai.card_nav` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_verdict009_card_nav.py; panel spec sb/domain/ai/panels.py:254 |
| `ai.policy_chooser` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:193 |
| `ai.policy_chooser.policy_channel` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:331 |
| `ai.policy_chooser.policy_category` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:333 |
| `ai.policy_chooser.policy_role` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_policy_pickers_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:336 |
| `ai.policy_chooser.policy_preview` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:338 |
| `ai.policy_chooser.policy_list` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:341 |
| `ai.behavior_chooser` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:195 |
| `ai.behavior_chooser.behavior_channel` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_behavior_presets.py; component spec/handler sb/domain/ai/panels.py:407 |
| `ai.behavior_chooser.behavior_category` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_behavior_presets.py; component spec/handler sb/domain/ai/panels.py:410 |
| `ai.behavior_chooser.behavior_preview` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_behavior_presets.py; component spec/handler sb/domain/ai/panels.py:413 |
| `ai.behavior_chooser.behavior_matrix` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:416 |
| `ai.behavior_chooser.behavior_advanced` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:421 |
| `ai.tools_chooser` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:197 |
| `ai.tools_chooser.tools_guild` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_orchestration_mutation.py; component spec/handler sb/domain/ai/panels.py:505 |
| `ai.tools_chooser.tools_channel` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_orchestration_mutation.py; component spec/handler sb/domain/ai/panels.py:507 |
| `ai.tools_chooser.tools_category` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_orchestration_mutation.py; component spec/handler sb/domain/ai/panels.py:509 |
| `ai.tools_chooser.tools_preview` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; component spec/handler sb/domain/ai/panels.py:512 |
| `ai.settings_edit_presets` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:1220 |
| `ai.settings_edit_presets.preset_0` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1262 |
| `ai.settings_edit_presets.preset_1` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1262 |
| `ai.settings_edit_presets.preset_2` | button | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py; component spec/handler sb/domain/ai/panels.py:1262 |
| `ai.settings_edit_presets.preset_3` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1262 |
| `ai.settings_edit_presets.preset_4` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1262 |
| `ai.settings_edit_presets.preset_5` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1263 |
| `ai.settings_edit_presets.override_btn` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1238 |
| `ai.settings_edit_presets.override_btn.ai.settings_number_form` | modal | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_settings_mutation_walking_skeleton.py; modal spec sb/domain/ai/panels.py:1196 |
| `ai.settings_edit_enum` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:1270 |
| `ai.settings_edit_enum.enum_value` | select | domain/ai | KEEP | select spec/handler sb/domain/ai/panels.py:1277 |
| `ai.settings_edit_text` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:1300 |
| `ai.settings_edit_text.edit_value` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:1309 |
| `ai.settings_edit_text.edit_value.ai.settings_text_form` | modal | domain/ai | KEEP | test tests/unit/band7/test_band7_modal_arming_walking_skeleton.py; modal spec sb/domain/ai/panels.py:1209 |
| `ai.policy_channel_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:332 |
| `ai.policy_channel_picker.policy_channel_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:641 |
| `ai.policy_category_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:335 |
| `ai.policy_category_picker.policy_category_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:653 |
| `ai.policy_role_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:337 |
| `ai.policy_role_picker.policy_role_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:665 |
| `ai.policy_preview_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:340 |
| `ai.policy_preview_picker.policy_preview_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:677 |
| `ai.policy_scope_edit` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:697 |
| `ai.policy_scope_edit.edit_scope_policy` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:705 |
| `ai.policy_scope_edit.edit_scope_policy.ai.policy_mode_form` | modal | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_policy_pickers_walking_skeleton.py; modal spec sb/domain/ai/panels.py:552 |
| `ai.policy_role_edit` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:725 |
| `ai.policy_role_edit.edit_role_policy` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:733 |
| `ai.policy_role_edit.edit_role_policy.ai.policy_role_form` | modal | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_policy_pickers_walking_skeleton.py; modal spec sb/domain/ai/panels.py:570 |
| `ai.policy_list` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/policy_widgets.py:346 |
| `ai.policy_list.list_prev` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:763 |
| `ai.policy_list.list_next` | button | domain/ai | KEEP | component spec/handler sb/domain/ai/panels.py:768 |
| `ai.behavior_channel_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:409 |
| `ai.behavior_channel_picker.behavior_channel_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_behavior_presets.py; select spec/handler sb/domain/ai/panels.py:814 |
| `ai.behavior_category_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:412 |
| `ai.behavior_category_picker.behavior_category_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_behavior_presets.py; select spec/handler sb/domain/ai/panels.py:832 |
| `ai.behavior_preview_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:415 |
| `ai.behavior_preview_picker.behavior_preview_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:850 |
| `ai.behavior_preset_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:881 |
| `ai.behavior_preset_picker.behavior_preset_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:893 |
| `ai.behavior_matrix_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:418 |
| `ai.behavior_matrix_picker.behavior_matrix_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/panels.py:870 |
| `ai.tools_guild_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:506 |
| `ai.tools_guild_picker.tools_guild_profile_pick` | select | domain/ai | KEEP | select spec/handler sb/domain/ai/panels.py:945 |
| `ai.tools_channel_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:508 |
| `ai.tools_channel_picker.tools_channel_scope_pick` | select | domain/ai | KEEP | select spec/handler sb/domain/ai/panels.py:958 |
| `ai.tools_category_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:511 |
| `ai.tools_category_picker.tools_category_scope_pick` | select | domain/ai | KEEP | select spec/handler sb/domain/ai/panels.py:976 |
| `ai.tools_profile_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/orchestration_widgets.py:138 |
| `ai.tools_profile_picker.tools_profile_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/orchestration_widgets.py:55 |
| `ai.tools_preview_picker` | panel | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; panel spec sb/domain/ai/panels.py:514 |
| `ai.tools_preview_picker.tools_preview_pick` | select | domain/ai | KEEP | test tests/unit/band7/test_band7_ai_surface.py; select spec/handler sb/domain/ai/orchestration_widgets.py:54 |

### domain/automod (3 — KEEP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `automod` | command | domain/automod | KEEP | golden parity/goldens/automod/sweep_automod.json; tests: tests/unit/band2/test_band2_slice2.py (+1) |
| `automod.hub` | panel | domain/automod | KEEP | spec sb/domain/operator_spine.py:94 hub_spec; tests: tests/unit/band6/test_band6_settings_panels.py |
| `automod.status` | panel | domain/automod | KEEP | spec sb/domain/automod/panels.py:45; open pinned by goldens/automod/sweep_automod.json |

### domain/blackjack (20 — KEEP 20)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `blackjack` | command | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_solo_round_hit.json + tests/integration/test_games_checkpoint_race.py |
| `bjtournament` | command | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json + tests/unit/band6/test_band6_blackjack_tournament.py |
| `bjstart` | command | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json + tests/unit/band6/test_band6_blackjack_tournament.py |
| `bjstatus` | command | domain/blackjack | KEEP | golden parity/goldens/blackjack/sweep_bjstatus.json + tests/unit/band6/test_band6_blackjack_tournament.py |
| `blackjack.hub` | panel | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_solo.py::test_walking_skeleton_blackjack_solo_end_to_end (hub solo lanes drive workflow:blackjack.solo_start) |
| `blackjack.hub.bj_solo_free` | button | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_rps.py::test_solo_start_deals_and_checkpoints (workflow:blackjack.solo_start) |
| `blackjack.hub.bj_solo_bet` | button | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_rps.py::test_solo_start_refuses_overdraft_bet (bet-arg lane of workflow:blackjack.solo_start) |
| `blackjack.hub.bj_solo_bet.blackjack.solo_bet_form` | modal | domain/blackjack | KEEP | modal submits into workflow:blackjack.solo_start; bet lane tested tests/unit/band6/test_band6_blackjack_rps.py::test_solo_start_refuses_overdraft_bet |
| `blackjack.hub.bj_status` | button | domain/blackjack | KEEP | shares handler:blackjack.status_view with !bjstatus golden parity/goldens/blackjack/sweep_bjstatus.json |
| `blackjack.table` | panel | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_solo_round_hit.json (click Hit re-render) + tests/unit/band6/test_band6_blackjack_solo.py::test_table_render_in_hand_shape |
| `blackjack.table.hit` | button | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_solo_round_hit.json step 3 (Hit click) + tests/unit/band6/test_band6_blackjack_solo.py |
| `blackjack.table.stand` | button | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_rps.py::test_solo_stand_settles_and_clears (handler:blackjack.table_click) |
| `blackjack.table.double` | button | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_rps.py::test_solo_double_needs_funding + test_band6_blackjack_solo.py::test_table_render_free_play_disables_double |
| `blackjack.pvp` | panel | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_pvp.py::test_pvp_render_match_stage_shows_both_hands + test_walking_skeleton_blackjack_pvp_end_to_end |
| `blackjack.registration` | panel | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json (join clicks) + tests/unit/band6/test_band6_blackjack_tournament.py::test_registration_render_pins_the_golden_bytes |
| `blackjack.registration.bj_join` | button | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json steps 2-4 (three join clicks) + test_band6_blackjack_tournament.py::test_try_join_guards_and_copy |
| `blackjack.tournament_table` | panel | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json + tests/unit/band6/test_band6_blackjack_tournament.py::test_tournament_table_render_terminal_chip_line |
| `blackjack.tournament_table.tourn_hit` | button | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json post-start clicks (handler:blackjack.tournament_click) + test_band6_blackjack_tournament.py::test_round_move_chips_bookkeeping |
| `blackjack.tournament_table.tourn_stand` | button | domain/blackjack | KEEP | golden parity/goldens/blackjack/blackjack_tournament_full_flow.json post-start clicks (handler:blackjack.tournament_click) + test_band6_blackjack_tournament.py::test_walking_skeleton_blackjack_tournament_end_to_end |
| `blackjack.tournament_results` | panel | domain/blackjack | KEEP | tests/unit/band6/test_band6_blackjack_tournament.py::test_results_render_medal_lines_and_payout_field + test_blackjack_champion_payout_fires_exactly_once |

### domain/btd6 (101 — KEEP 60 · REWORK 8 · DROP 33)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `btd6` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6.json; test tests/integration/test_btd6_seed_data.py |
| `btd6.income` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_income.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.rbe` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_rbe.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band7/test_band7_btd6_freeplay_scaling.py |
| `btd6.round` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_round.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band6/test_band6_rps_tournament.py |
| `btd6.tower` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_tower.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.estimate` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_estimate.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.hero` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_hero.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band7/test_band7_btd6_strategy_form.py |
| `btd6.relic` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_relic.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ct` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ct.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band6/test_band6_message_games.py |
| `btd6.ask` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ask.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.status` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_status.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band2/test_band2_slice1.py |
| `btd6.diagnostics` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_diagnostics.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/app/test_main_wiring.py |
| `btd6.test-intent` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_test-intent.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ctteam` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ctteam.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.strat` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat.json; handler sb/domain/btd6/oracle_surface.py; canonical dotted bare-group usage view (handler:btd6.grp_bare), oracle live-wired |
| `btd6.strat.browse` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_browse.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/panels/test_browserview_contract.py |
| `btd6.strat.mine` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_mine.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/ai/test_k10_tasks_flags_routing.py |
| `btd6.strat.strategy` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_strategy.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.strat.strategy-audit` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_strategy-audit.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.strat.submit` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_submit.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.strat.pending` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_pending.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/kernel/test_lifecycle.py; REAL despite name — whitelisted staff read view (inventory.md:278) |
| `btd6.strat.strategies` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_strategies.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.strat.why-no-response` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_strat_why-no-response.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/kernel/test_lifecycle.py; canonical dotted bare-group usage view (handler:btd6.grp_bare), oracle live-wired |
| `btd6.ops.readiness` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops_readiness.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops.runs` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops_runs.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops.source_enable` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops_source_enable.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops.source_disable` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops_source_disable.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops.seed-data` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_slash_btd6_ops_seed-data.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.ops.announcechannel` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_ops_announcechannel.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band2/test_band2_slice1.py; canonical dotted bare-group usage view (handler:btd6.grp_bare), oracle live-wired |
| `btd6.events.live` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_live.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events.event` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_event.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/parity_adapter/test_dispositions.py |
| `btd6.events.leaderboard` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_leaderboard.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/interaction/test_adapters_and_runtime.py |
| `btd6.events.sources` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_sources.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events.source-health` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_source-health.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events.latest-data` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_latest-data.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events.refresh-source` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_refresh-source.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6.events.grounding` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6_events_grounding.json; handler sb/domain/btd6/oracle_surface.py |
| `btd6menu` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_btd6menu.json; test tests/unit/band7/test_band7_btd6.py; menu-pair with `btd6` (both -> panel:btd6.hub), oracle-context.md:136 registry entry_point — deliberate alias, fold-candidate note only |
| `paragon` | command | domain/btd6 | KEEP | golden parity/goldens/btd6/sweep_paragon.json; test tests/unit/ai/test_k10_grounding.py |
| `btd6ref` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.grp_bare, same handler as dotted `btd6 …` twin |
| `btd6ref.tower` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_tower, same handler as dotted `btd6 …` twin |
| `btd6ref.hero` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_hero, same handler as dotted `btd6 …` twin |
| `btd6ref.round` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_round, same handler as dotted `btd6 …` twin |
| `btd6ref.income` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_income, same handler as dotted `btd6 …` twin |
| `btd6ref.rbe` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_rbe, same handler as dotted `btd6 …` twin |
| `btd6ref.relic` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_relic, same handler as dotted `btd6 …` twin |
| `btd6ref.ct` | command | domain/btd6 | DROP | oracle-context.md:154 `btd6ref` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ct, same handler as dotted `btd6 …` twin |
| `btd6strat` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.grp_bare, same handler as dotted `btd6 …` twin |
| `btd6strat.browse` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_browse, same handler as dotted `btd6 …` twin |
| `btd6strat.mine` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_mine, same handler as dotted `btd6 …` twin |
| `btd6strat.strategy` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_strategy, same handler as dotted `btd6 …` twin |
| `btd6strat.strategy-audit` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_audit, same handler as dotted `btd6 …` twin |
| `btd6strat.submit` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_submit, same handler as dotted `btd6 …` twin |
| `btd6strat.pending` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_pending, same handler as dotted `btd6 …` twin |
| `btd6strat.strategies` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_strategies, same handler as dotted `btd6 …` twin |
| `btd6strat.why-no-response` | command | domain/btd6 | DROP | oracle-context.md:162 `btd6strat` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_strat_why, same handler as dotted `btd6 …` twin |
| `btd6events` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.grp_bare, same handler as dotted `btd6 …` twin |
| `btd6events.live` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_live, same handler as dotted `btd6 …` twin |
| `btd6events.event` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_event, same handler as dotted `btd6 …` twin |
| `btd6events.leaderboard` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_leaderboard, same handler as dotted `btd6 …` twin |
| `btd6events.sources` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_sources, same handler as dotted `btd6 …` twin |
| `btd6events.source-health` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_source_health, same handler as dotted `btd6 …` twin |
| `btd6events.latest-data` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_latest, same handler as dotted `btd6 …` twin |
| `btd6events.refresh-source` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_refresh, same handler as dotted `btd6 …` twin |
| `btd6events.grounding` | command | domain/btd6 | DROP | oracle-context.md:138 `btd6events` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_events_grounding, same handler as dotted `btd6 …` twin |
| `btd6ops` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.grp_bare, same handler as dotted `btd6 …` twin |
| `btd6ops.readiness` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_readiness, same handler as dotted `btd6 …` twin |
| `btd6ops.runs` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_runs, same handler as dotted `btd6 …` twin |
| `btd6ops.source_enable` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_source_enable, same handler as dotted `btd6 …` twin |
| `btd6ops.source_disable` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_source_disable, same handler as dotted `btd6 …` twin |
| `btd6ops.seed-data` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_seed, same handler as dotted `btd6 …` twin |
| `btd6ops.announcechannel` | command | domain/btd6 | DROP | oracle-context.md:147 `btd6ops` group 'legacy-duplicate (oracle-marked); hidden=True'; inventory: routes handler:btd6.cmd_ops_announcechannel, same handler as dotted `btd6 …` twin |
| `btd6.hub` | panel | domain/btd6 | KEEP | register_panel spec sb/domain/btd6/panels.py |
| `btd6.hub.ask` | button | domain/btd6 | KEEP | handler sb/domain/btd6/oracle_surface.py |
| `btd6.hub.ask.btd6.ask_form` | modal | domain/btd6 | KEEP | handler sb/domain/btd6/oracle_surface.py |
| `btd6.hub.events` | button | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.units` | button | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.units.btd6.tower_form` | modal | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.rounds` | button | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.rounds.btd6.round_form` | modal | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.maps` | button | domain/btd6 | KEEP | handler sb/domain/btd6/oracle_surface.py |
| `btd6.hub.strategy` | button | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.hub.status` | button | domain/btd6 | KEEP | handler sb/domain/btd6/oracle_surface.py |
| `btd6.hub.admin` | button | domain/btd6 | KEEP | handler sb/domain/btd6/service.py |
| `btd6.card` | panel | domain/btd6 | KEEP | register_panel spec sb/domain/btd6/panels.py |
| `btd6.ctteam` | panel | domain/btd6 | KEEP | register_panel spec sb/domain/btd6/panels.py |
| `btd6.ctteam.set_team` | button | domain/btd6 | REWORK | sb/domain/btd6/panels.py:298 handler=HandlerRef('btd6.ctteam_set_pending'); oracle-context.md:88 btd6.ctteam 'View or set' live-wired |
| `btd6.strategy_submit` | panel | domain/btd6 | KEEP | register_panel spec sb/domain/btd6/panels.py |
| `btd6.strategy_submit.open_strategy_form` | button | domain/btd6 | KEEP | handler sb/domain/btd6/oracle_surface.py |
| `btd6.strategy_submit.open_strategy_form.btd6.strategy_form` | modal | domain/btd6 | KEEP | golden parity/goldens/btd6/btd6_strategy_form_submit.json; handler sb/domain/btd6/oracle_surface.py; test tests/unit/band7/test_band7_btd6_strategy_form.py |
| `btd6.paragon` | panel | domain/btd6 | KEEP | register_panel spec sb/domain/btd6/panels.py |
| `btd6.paragon.calc` | button | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.requirements` | button | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.stats` | button | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.back` | button | domain/btd6 | KEEP | test tests/integration/test_tournament_entry_race.py |
| `btd6.paragon.paragon` | select | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.players` | select | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.difficulty` | select | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |
| `btd6.paragon.tier5` | select | domain/btd6 | REWORK | sb/domain/btd6/service.py:366 paragon_pending (named successor port, docs/decisions.md:347); sb/domain/btd6/panels.py:348-403 wire to it; math already ported: sb/domain/btd6/paragon_math.py + paragon_degrees.py |

### domain/casino (18 — KEEP 18)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `casino` | command | domain/casino | KEEP | golden parity/goldens/casino/sweep_casino.json + tests/unit/band6/test_band6_deathmatch_casino.py |
| `poker` | command | domain/casino | KEEP | golden parity/goldens/casino/casino_poker_full_hand.json + tests/unit/band6/test_band6_deathmatch_casino.py |
| `casino.hub` | panel | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.hub.casino_new_poker` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.hub.casino_roulette` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_table` | panel | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_table.poker_join` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_table.poker_leave` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_table.poker_start` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_table.poker_close` | button | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_game` | panel | domain/casino | KEEP | tests/unit/band6/test_band6_casino_panels.py |
| `casino.poker_game.poker_fold` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_checkcall` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_raise_min` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_raise_pot` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_allin` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_deal_next` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |
| `casino.poker_game.poker_end` | button | domain/casino | KEEP | tests/unit/band6/test_band6_poker_play.py |

### domain/chain (17 — KEEP 17)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `chain` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/chain/sweep_chain.json; handler sb/domain/chain/service.py; test tests/unit/band6/test_band6_message_games.py |
| `chain.create` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain_create.json + tests/unit/app/test_main_wiring.py; C6 backstop concurs: golden parity/goldens/chain/sweep_chain_create.json; handler sb/domain/chain/service.py; test tests/unit/app/test_main_wiring.py |
| `chain.delete` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain_delete.json + tests/unit/band6/test_band6_channel_hub.py; C6 backstop concurs: golden parity/goldens/chain/sweep_chain_delete.json; handler sb/domain/chain/service.py; test tests/unit/band6/test_band6_channel_hub.py |
| `chain.setlimit` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain_setlimit.json; C6 backstop concurs: golden parity/goldens/chain/sweep_chain_setlimit.json; handler sb/domain/chain/service.py |
| `chain.removelimit` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain_removelimit.json; C6 backstop concurs: golden parity/goldens/chain/sweep_chain_removelimit.json; handler sb/domain/chain/service.py |
| `chain.list` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chain_list.json + tests/unit/band6/test_band6_channel_hub.py; C6 backstop concurs: golden parity/goldens/chain/sweep_chain_list.json; handler sb/domain/chain/service.py; test tests/unit/band6/test_band6_channel_hub.py |
| `chainmenu` | command | domain/chain | KEEP | golden parity/goldens/chain/sweep_chainmenu.json |
| `chain.hub` | panel | domain/chain | KEEP | golden parity/goldens/chain/sweep_chainmenu.json (panel render on !chainmenu open); C6 backstop concurs: register_panel spec sb/domain/chain/panels.py |
| `chain.hub.chain_create` | button | domain/chain | KEEP | tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_create.chain.create_form` | modal | domain/chain | KEEP | modal submits into handler:chain.create_route, golden parity/goldens/chain/sweep_chain_create.json + tests/unit/band6/test_band6_message_games.py::test_chain_create_preserves_existing_limit; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_delete` | button | domain/chain | KEEP | shares handler:chain.delete_route with !chain delete golden parity/goldens/chain/sweep_chain_delete.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_delete.chain.delete_form` | modal | domain/chain | KEEP | modal submits into handler:chain.delete_route, golden parity/goldens/chain/sweep_chain_delete.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_set_limit` | button | domain/chain | KEEP | shares handler:chain.setlimit_route with !chain setlimit golden parity/goldens/chain/sweep_chain_setlimit.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_set_limit.chain.set_limit_form` | modal | domain/chain | KEEP | modal submits into handler:chain.setlimit_route, golden parity/goldens/chain/sweep_chain_setlimit.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_clear_limit` | button | domain/chain | KEEP | shares handler:chain.removelimit_route with !chain removelimit golden parity/goldens/chain/sweep_chain_removelimit.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_clear_limit.chain.clear_limit_form` | modal | domain/chain | KEEP | modal submits into handler:chain.removelimit_route, golden parity/goldens/chain/sweep_chain_removelimit.json; C6 backstop concurs: handler sb/domain/chain/service.py |
| `chain.hub.chain_refresh` | button | domain/chain | KEEP | clean handler review sb/domain/chain/panels.py (hub_refresh re-renders panel:chain.hub whose render is golden-pinned via sweep_chainmenu.json); C6 backstop concurs: handler sb/domain/chain/panels.py |

### domain/channel (25 — KEEP 20 · REWORK 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `channelmenu` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_channelmenu.json; test tests/unit/band2/test_band2_slice2.py |
| `set` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_set.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `evt` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_evt.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `create` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_create.json; handler sb/domain/channel/handlers.py; test tests/unit/app/test_main_wiring.py |
| `bulkdelete` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_bulkdelete.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `del` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_del.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `list` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_list.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `clone` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_clone.json; handler sb/domain/channel/handlers.py; test tests/unit/band2/test_band2_slice2.py |
| `move` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_move.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_blackjack_rps.py |
| `lock` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_lock.json; handler sb/domain/channel/handlers.py; test tests/unit/band2/test_channel_state_rehome.py |
| `unlock` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_unlock.json; handler sb/domain/channel/handlers.py; test tests/unit/band2/test_channel_state_rehome.py |
| `channelinfo` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_channelinfo.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `rename` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_rename.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `slowmode` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_slowmode.json; handler sb/domain/channel/handlers.py; test tests/unit/band2/test_channel_state_rehome.py |
| `topic` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_topic.json; handler sb/domain/channel/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `permissions` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_permissions.json; handler sb/domain/channel/handlers.py; test tests/unit/platform_governance/test_s15_governance.py |
| `bulkcreate` | command | domain/channel | KEEP | golden parity/goldens/channel/sweep_bulkcreate.json; handler sb/domain/channel/handlers.py; test tests/unit/band2/test_band2_slice2.py |
| `channel.hub` | panel | domain/channel | KEEP | register_panel spec sb/domain/channel/panels.py |
| `channel.hub.create` | button | domain/channel | REWORK — with sibling lane: operator_spine stub sweep (core/admin/setup completeness sibling) | inventory: handler channel.*_pending -> operator_spine pending terminal; typed channel command surface is fully real (sb/domain/channel/handlers.py) |
| `channel.hub.delete` | button | domain/channel | REWORK — with sibling lane: operator_spine stub sweep (core/admin/setup completeness sibling) | inventory: handler channel.*_pending -> operator_spine pending terminal; typed channel command surface is fully real (sb/domain/channel/handlers.py) |
| `channel.hub.restrict` | button | domain/channel | REWORK — with sibling lane: operator_spine stub sweep (core/admin/setup completeness sibling) | inventory: handler channel.*_pending -> operator_spine pending terminal; typed channel command surface is fully real (sb/domain/channel/handlers.py) |
| `channel.hub.move` | button | domain/channel | REWORK — with sibling lane: operator_spine stub sweep (core/admin/setup completeness sibling) | inventory: handler channel.*_pending -> operator_spine pending terminal; typed channel command surface is fully real (sb/domain/channel/handlers.py) |
| `channel.hub.visibility` | button | domain/channel | REWORK — with sibling lane: operator_spine stub sweep (core/admin/setup completeness sibling) | inventory: handler channel.*_pending -> operator_spine pending terminal; typed channel command surface is fully real (sb/domain/channel/handlers.py) |
| `channel.info_card` | panel | domain/channel | KEEP | register_panel spec sb/domain/channel/panels.py |
| `channel.list_card` | panel | domain/channel | KEEP | register_panel spec sb/domain/channel/panels.py |

### domain/cleanup (19 — KEEP 14 · REWORK 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `cleanup` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_cleanup.json; tests: tests/unit/band2/test_band2_slice1.py (+5) |
| `wordmenu` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_wordmenu.json; tests: tests/unit/band6/test_band6_cleanup_panels.py |
| `cleanuphistory` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_cleanuphistory.json; tests: tests/unit/band6/test_band6_cleanup_panels.py |
| `word` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_word.json; tests: tests/unit/band2/test_band2_slice2.py (+1) |
| `word.add` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_word_add.json; tests: tests/unit/app/test_cut1_surfaces.py (+1) |
| `word.remove` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_word_remove.json |
| `word.list` | command | domain/cleanup | KEEP | golden parity/goldens/cleanup/sweep_word_list.json; tests: tests/unit/band6/test_band6_channel_hub.py (+1) |
| `cleanup.hub` | panel | domain/cleanup | KEEP | spec sb/domain/cleanup/panels.py:148; open pinned by goldens/cleanup/sweep_cleanup.json; tests: tests/unit/band6/test_band6_cleanup_panels.py |
| `cleanup.hub.words` | button | domain/cleanup | KEEP | declared in sb/domain/cleanup/panels.py:148 (cleanup.hub spec); panel open pinned by goldens/cleanup/sweep_cleanup.json; nav -> panel:cleanup.words |
| `cleanup.hub.logging` | button | domain/cleanup | REWORK | sb/domain/cleanup/panels.py:168-171 pending; handler copy 'ports with the server-logging slice' (sb/domain/cleanup/handlers.py:73-75) — but domain/logging is LIVE (25/25 real rows, panel logging.hub registered) |
| `cleanup.hub.settings` | button | domain/cleanup | KEEP | deliberate pending terminal — 'ports with the settings-mutation slice' (sb/domain/cleanup/handlers.py:76-78); mutation deferral matches control/claims/operator-hubs-interactive.md (EDIT controls stay deferred) |
| `cleanup.hub.policies` | button | domain/cleanup | KEEP | deliberate pending terminal — 'ports with the cleanup-policy slice' (sb/domain/cleanup/handlers.py:79-81) |
| `cleanup.hub.cl_refresh` | button | domain/cleanup | KEEP | declared in sb/domain/cleanup/panels.py:148 (cleanup.hub spec); panel open pinned by goldens/cleanup/sweep_cleanup.json; nav -> panel:cleanup.hub |
| `cleanup.words` | panel | domain/cleanup | KEEP | spec sb/domain/cleanup/panels.py:222; open pinned by goldens/cleanup/sweep_wordmenu.json; tests: tests/unit/band6/test_band6_cleanup_panels.py |
| `cleanup.words.word_add` | button | domain/cleanup | REWORK | sb/domain/cleanup/panels.py:236-238 pending while the command twin workflow:cleanup.word_add_op is LIVE (golden cleanup/sweep_word_add.json) |
| `cleanup.words.word_remove` | button | domain/cleanup | REWORK | sb/domain/cleanup/panels.py:240-242 pending while workflow:cleanup.word_remove_op is LIVE (golden cleanup/sweep_word_remove.json) |
| `cleanup.words.word_refresh` | button | domain/cleanup | REWORK | sb/domain/cleanup/panels.py:244-246 pending; sibling cleanup.hub.cl_refresh at :187-190 is a real REFRESH_PANEL nav |
| `cleanup.words.scan_history` | button | domain/cleanup | REWORK | sb/domain/cleanup/panels.py:249-251 pending; handler copy itself names the live front door: '`!cleanuphistory` is the command front door' (sb/domain/cleanup/handlers.py:88-90); handler cleanup.history_scan LIVE (golden cleanup/sweep_cleanuphistory.json) |
| `cleanup.words.anti_evasion` | button | domain/cleanup | KEEP | deliberate pending terminal — 'the anti-evasion toggle ports with the word-mutation panel slice' (sb/domain/cleanup/handlers.py:42,91); a settings mutation, deferred class |

### domain/community (12 — KEEP 12)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `community` | command | domain/community | KEEP | golden parity/goldens/community/sweep_community.json; +1 more golden(s); test tests/unit/band4/test_band4_community.py — dual prefix+slash declaration, expected dedup artifact (KEEP, not a drop) |
| `community.hub` | panel | domain/community | KEEP | test tests/unit/band4/test_band4_community.py; panel spec sb/manifest/community.py:21 |
| `community.hub.co_ticket` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:257 |
| `community.hub.co_xp` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:257 |
| `community.hub.co_karma` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:257 |
| `community.hub.co_community_spotlight` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:257 |
| `community.hub.co_welcome` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:258 |
| `community.hub.co_counters` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:259 |
| `community.hub.co_role` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:259 |
| `community.hub.co_counting` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:260 |
| `community.hub.co_chain` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:260 |
| `community.hub.co_leaderboard` | button | domain/community | KEEP | component spec/handler sb/domain/community/panels.py:260 |

### domain/community_spotlight (8 — KEEP 8)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `spotlight` | command | domain/community_spotlight | KEEP | golden parity/goldens/community_spotlight/sweep_spotlight.json |
| `community_spotlight.hub` | panel | domain/community_spotlight | KEEP | test tests/unit/band4/test_band4_community.py; panel spec sb/manifest/community_spotlight.py:24 |
| `community_spotlight.hub.xp_leaders` | button | domain/community_spotlight | KEEP | component spec/handler sb/domain/community/panels.py:333 |
| `community_spotlight.hub.richest` | button | domain/community_spotlight | KEEP | component spec/handler sb/domain/community/panels.py:337 |
| `community_spotlight.hub.games` | button | domain/community_spotlight | KEEP | test tests/integration/test_tournament_entry_race.py; component spec/handler sb/domain/community/panels.py:341 |
| `community_spotlight.hub.spotlight_refresh` | button | domain/community_spotlight | KEEP | component spec/handler sb/domain/community/panels.py:347 |
| `community_spotlight.games` | panel | domain/community_spotlight | KEEP | test tests/unit/band4/test_band4_community.py; panel spec sb/domain/community/panels.py:343 |
| `community_spotlight.games.game_select` | select | domain/community_spotlight | KEEP | select spec/handler sb/domain/community/panels.py:429 |

### domain/counters (5 — KEEP 4 · REWORK 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `counters` | command | domain/counters | KEEP | goldens parity/goldens/counters/sweep_counters.json + sweep_slash_counters.json; tests tests/unit/band2/test_band2_slice2.py; oracle-context.md:207-209 primary entrypoint |
| `counterpreset` | command | domain/counters | REWORK | sb/domain/counters/panels.py:186-197 — the `!counterpreset <name>` argv branch returns counters.preset_pending terminal; golden parity/goldens/counters/sweep_counterpreset.json pins the bare open only; oracle-context.md:208 live-wired in prod (hidden partial) |
| `counters.hub` | panel | domain/counters | KEEP | ensure_hub('counters') sb/manifest/counters.py:16 -> sb/domain/operator_spine.py:96 hub_spec; nav target of the landed settings-hub group select (control/claims/operator-hubs-interactive.md); tests tests/unit/band6/test_band6_settings_panels.py |
| `counters.status` | panel | domain/counters | KEEP | renderer sb/domain/counters/panels.py:66 (counters.status_render); byte-pinned via parity/goldens/counters/sweep_counters.json (counters routes panel:counters.status) |
| `counters.presets` | panel | domain/counters | KEEP | renderer sb/domain/counters/panels.py:138 (counters.presets_render); rendered by the counterpreset bare open, golden parity/goldens/counters/sweep_counterpreset.json |

### domain/counting (19 — KEEP 19)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `countingmenu` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_countingmenu.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_countingmenu.json; test tests/unit/band6/test_band6_message_games.py |
| `start_match` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_start_match.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_start_match.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `end_match` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_end_match.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_end_match.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `reset_count` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_reset_count.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_reset_count.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `toggle_turns` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_toggle_turns.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_toggle_turns.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `count_info` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_count_info.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_count_info.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `counttop` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_counttop.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_counttop.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `count_rules` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_count_rules.json + tests/unit/app/test_main_wiring.py; C6 backstop concurs: golden parity/goldens/counting/sweep_count_rules.json; test tests/unit/app/test_main_wiring.py |
| `set_skip_numbers` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_set_skip_numbers.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_set_skip_numbers.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `toggle_reset_on_wrong_count` | command | domain/counting | KEEP | golden parity/goldens/counting/sweep_toggle_reset_on_wrong_count.json + tests/unit/band6/test_band6_message_games.py; C6 backstop concurs: golden parity/goldens/counting/sweep_toggle_reset_on_wrong_count.json; handler sb/domain/counting/service.py; test tests/unit/band6/test_band6_message_games.py |
| `counting.hub` | panel | domain/counting | KEEP | golden parity/goldens/counting/sweep_countingmenu.json (panel render on !countingmenu open); C6 backstop concurs: register_panel spec sb/domain/counting/panels.py |
| `counting.hub.counting_toggle_turns` | button | domain/counting | KEEP | _targeted wrapper sb/domain/counting/panels.py:343 onto handler:counting.toggle_turns_route, golden parity/goldens/counting/sweep_toggle_turns.json; C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_toggle_reset` | button | domain/counting | KEEP | _targeted wrapper sb/domain/counting/panels.py:345 onto handler:counting.toggle_reset_route, golden parity/goldens/counting/sweep_toggle_reset_on_wrong_count.json; C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_reset` | button | domain/counting | KEEP | _targeted wrapper sb/domain/counting/panels.py:346 onto handler:counting.reset_route, golden parity/goldens/counting/sweep_reset_count.json; C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_disable` | button | domain/counting | KEEP | _targeted wrapper sb/domain/counting/panels.py:347 onto handler:counting.end_match_route, golden parity/goldens/counting/sweep_end_match.json; C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_refresh` | button | domain/counting | KEEP | clean handler review sb/domain/counting/panels.py:305 (_reopen re-render of golden-pinned hub); C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_pick_channel` | select | domain/counting | KEEP | clean handler review sb/domain/counting/panels.py:290-303 (re-targets manager then _reopen); C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.hub.counting_enable_mode` | select | domain/counting | KEEP | clean handler review sb/domain/counting/panels.py:309-325 (runs workflow:counting.enable_channel); enable lanes tested tests/unit/band6/test_band6_message_games.py::test_counting_enable_disable_lanes; C6 backstop concurs: handler sb/domain/counting/panels.py |
| `counting.rules_card` | panel | domain/counting | KEEP | golden parity/goldens/counting/sweep_count_rules.json (!count_rules routes to panel:counting.rules_card); C6 backstop concurs: register_panel spec sb/domain/counting/panels.py |

### domain/creature (25 — KEEP 25)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `catch` | command | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creatures` | command | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_checkpoint_games.py |
| `dex` | command | domain/creature | KEEP | golden parity/goldens/creature/sweep_dex.json + tests/unit/band6/test_band6_creature_panels.py |
| `dextop` | command | domain/creature | KEEP | golden parity/goldens/creature/sweep_dextop.json |
| `cbattle` | command | domain/creature | KEEP | golden parity/goldens/creature/creature_battle_accept.json + tests/unit/band6/test_band6_creature_panels.py |
| `cbrecord` | command | domain/creature | KEEP | golden parity/goldens/creature/sweep_cbrecord.json |
| `cbattletop` | command | domain/creature | KEEP | golden parity/goldens/creature/sweep_cbattletop.json |
| `creature.hub` | panel | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_creature_panels.py |
| `creature.hub.creature_catch` | button | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_checkpoint_games.py |
| `creature.hub.creature_dex` | button | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_creature_panels.py |
| `creature.hub.creature_challenge` | button | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_creature_panels.py |
| `creature.hub.creature_ladder` | button | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_creature_panels.py |
| `creature.hub.creature_howto` | button | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json + tests/unit/band6/test_band6_creature_panels.py |
| `creature.dex_card` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.dex` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.collectors_card` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.record_card` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.battletop_card` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.challenge` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.challenge.cbattle_accept` | button | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.challenge.cbattle_decline` | button | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.challenge.cbattle_rematch` | button | domain/creature | KEEP | shipped Rematch port sb/domain/creature/panels.py:593-601 + tests/unit/band6/test_band6_creature_panels.py (rematch stage gating) |
| `creature.challenge_select` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |
| `creature.challenge_select.challenge_opponent` | select | domain/creature | KEEP | golden parity/goldens/creature/creature_challenge_picker.json step 3 clicks custom_id creature.challenge_select.challenge_opponent with member values |
| `creature.rules_card` | panel | domain/creature | KEEP | tests/unit/band6/test_band6_creature_panels.py |

### domain/deathmatch (11 — KEEP 11)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `dm_challenge` | command | domain/deathmatch | KEEP | golden parity/goldens/deathmatch/sweep_dm_challenge.json + tests/unit/band2/test_band2_slice1.py; C6 backstop concurs: golden parity/goldens/deathmatch/sweep_dm_challenge.json; handler sb/domain/deathmatch/service.py; test tests/unit/band2/test_band2_slice1.py |
| `dm_help` | command | domain/deathmatch | KEEP | golden parity/goldens/deathmatch/sweep_dm_help.json + tests/unit/band6/test_band6_deathmatch_casino.py; C6 backstop concurs: golden parity/goldens/deathmatch/sweep_dm_help.json; handler sb/domain/deathmatch/service.py; test tests/unit/band6/test_band6_deathmatch_casino.py |
| `deathmatch.hub` | panel | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py::test_slice4_manifests_and_providers + games hub nav golden-render test_band6_games_panels.py; C6 backstop concurs: register_panel spec sb/domain/deathmatch/panels.py |
| `deathmatch.hub.dm_fight_bot` | button | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py::test_bot_duel_no_stats + test_bot_action_bias (workflow:deathmatch.bot_start); C6 backstop concurs: handler sb/domain/deathmatch/ops.py |
| `deathmatch.hub.dm_stats` | button | domain/deathmatch | KEEP | clean handler review sb/domain/deathmatch/service.py:191-205 (stats_view read); C6 backstop concurs: handler sb/domain/deathmatch/service.py |
| `deathmatch.hub.dm_top` | button | domain/deathmatch | KEEP | clean handler review sb/domain/deathmatch/service.py:207-218 (top_view leaderboard read); C6 backstop concurs: handler sb/domain/deathmatch/service.py |
| `deathmatch.hub.dm_help` | button | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py; C6 backstop concurs: handler sb/domain/deathmatch/service.py |
| `deathmatch.challenge_card` | panel | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py::test_challenge_accept_move_settle (renderer_override deathmatch.render_challenge); C6 backstop concurs: register_panel spec sb/domain/deathmatch/panels.py |
| `deathmatch.challenge_card.dm_accept` | button | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py::test_challenge_accept_move_settle (handler:deathmatch.challenge_click); C6 backstop concurs: handler sb/domain/deathmatch/service.py |
| `deathmatch.challenge_card.dm_decline` | button | domain/deathmatch | KEEP | tests/unit/band6/test_band6_deathmatch_casino.py::test_challenge_guards_and_decline (handler:deathmatch.challenge_click); C6 backstop concurs: handler sb/domain/deathmatch/service.py |
| `deathmatch.help_card` | panel | domain/deathmatch | KEEP | golden parity/goldens/deathmatch/sweep_dm_help.json (!dm_help routes to the help card); C6 backstop concurs: register_panel spec sb/domain/deathmatch/panels.py |

### domain/diagnostic (74 — KEEP 69 · REWORK 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `diagnostics` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_diagnostics.json; tests: tests/unit/app/test_main_wiring.py |
| `latency` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_latency.json; tests: tests/unit/app/test_main_wiring.py |
| `lifecycle` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_lifecycle.json |
| `check_database` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_check_database.json |
| `find_command` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_find_command.json |
| `list_commands_detailed` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_list_commands_detailed.json |
| `test_notification` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_test_notification.json |
| `validate_json_files` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_validate_json_files.json |
| `platform` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform.json (+1 more); tests: tests/unit/settings_band/test_platform_latch.py (+2) |
| `platform.access` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_access.json; tests: tests/unit/band6/test_band6_settings_panels.py |
| `platform.anchors` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_anchors.json |
| `platform.bindings` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_bindings.json; tests: tests/unit/rollback/test_s14_rollback.py |
| `platform.caches` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_caches.json |
| `platform.cleanup-preview` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_cleanup-preview.json |
| `platform.command-access` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_command-access.json |
| `platform.consistency` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_consistency.json |
| `platform.counting-health` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_counting-health.json |
| `platform.customization` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_customization.json |
| `platform.economy` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_economy.json; tests: tests/unit/verified_live/test_verified_live.py (+5) |
| `platform.economytrend` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_economytrend.json |
| `platform.findings` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_findings.json |
| `platform.flags` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_flags.json; tests: tests/unit/parity_adapter/test_hermes_followup.py (+4) |
| `platform.identity` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_identity.json |
| `platform.lifecycle` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_lifecycle.json |
| `platform.locks` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_locks.json |
| `platform.media` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_media.json |
| `platform.migrations` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_migrations.json; tests: tests/unit/kernel/test_migrations.py (+1) |
| `platform.participation-schemas` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_participation-schemas.json |
| `platform.provisioning` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_provisioning.json |
| `platform.resource-requirements` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_resource-requirements.json |
| `platform.resources` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_resources.json |
| `platform.schemas` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_schemas.json |
| `platform.sessions` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_sessions.json |
| `platform.settings-registry` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_settings-registry.json |
| `platform.setup-readiness` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_setup-readiness.json |
| `platform.tasks` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_tasks.json; tests: tests/unit/sim_runner/test_oracles.py |
| `platform.views` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_views.json |
| `platform.backfill` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_backfill.json; tests: tests/unit/invariants/test_s12_invariants.py (+1) |
| `platform.setting` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_setting.json; tests: tests/unit/band6/test_band6_settings_panels.py (+2) |
| `platform.finding` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_finding.json |
| `platform.flag` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_flag.json; tests: tests/unit/band6/test_band6_message_games.py |
| `platform.automation` | command | domain/diagnostic | KEEP | golden parity/goldens/diagnostic/sweep_platform_automation.json |
| `diagnostic.hub` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:340; open pinned by goldens/diagnostic/sweep_diagnostics.json; tests: tests/unit/app/test_main_wiring.py |
| `diagnostic.hub.diag_status` | button | domain/diagnostic | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | pending (Bot Status); source views ruled out of the PARITY CORPUS only — sb/manifest/diagnostic.py:31-38: platform status/health class + query_logs/recent_errors sweeps RETIRED as nondeterministic process-state (2026-07-12 corpus ruling); custom pending fn sb/domain/diagnostic/handlers.py:404 |
| `diagnostic.hub.diag_latency` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:340 (diagnostic.hub spec); panel open pinned by goldens/diagnostic/sweep_diagnostics.json; live handler:diagnostic.diag_latency |
| `diagnostic.hub.diag_sysinfo` | button | domain/diagnostic | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | pending (System Info); source views ruled out of the PARITY CORPUS only — sb/manifest/diagnostic.py:31-38: platform status/health class + query_logs/recent_errors sweeps RETIRED as nondeterministic process-state (2026-07-12 corpus ruling); custom pending fn sb/domain/diagnostic/handlers.py:404 |
| `diagnostic.hub.diag_database` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:340 (diagnostic.hub spec); panel open pinned by goldens/diagnostic/sweep_diagnostics.json; live handler:diagnostic.check_database_view |
| `diagnostic.hub.diag_json` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:340 (diagnostic.hub spec); panel open pinned by goldens/diagnostic/sweep_diagnostics.json; live handler:diagnostic.validate_json_view |
| `diagnostic.hub.diag_commands` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:340 (diagnostic.hub spec); panel open pinned by goldens/diagnostic/sweep_diagnostics.json; nav -> panel:diagnostic.command_list |
| `diagnostic.hub.diag_errors` | button | domain/diagnostic | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | pending (Recent Errors); source views ruled out of the PARITY CORPUS only — sb/manifest/diagnostic.py:31-38: platform status/health class + query_logs/recent_errors sweeps RETIRED as nondeterministic process-state (2026-07-12 corpus ruling); custom pending fn sb/domain/diagnostic/handlers.py:404 |
| `diagnostic.hub.diag_notify` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:340 (diagnostic.hub spec); panel open pinned by goldens/diagnostic/sweep_diagnostics.json; live handler:diagnostic.test_notification_view |
| `diagnostic.card` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:387; open pinned by goldens/diagnostic/sweep_latency.json |
| `diagnostic.command_list` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:409; open pinned by goldens/diagnostic/sweep_list_commands_detailed.json |
| `diagnostic.command_list.cmdlist_prev` | button | domain/diagnostic | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | sb/domain/diagnostic/panels.py:420-426 pending (custom fn handlers.py:265-267); the roster is a pure registry read already rendered by diagnostic.render_command_list |
| `diagnostic.command_list.cmdlist_next` | button | domain/diagnostic | REWORK — with sibling lane: completeness-sweep sibling (core/admin/setup stubs) | sb/domain/diagnostic/panels.py:420-426 pending (custom fn handlers.py:265-267); the roster is a pure registry read already rendered by diagnostic.render_command_list |
| `diagnostic.platform_hub` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:461; open pinned by goldens/diagnostic/sweep_platform.json (2 goldens) |
| `diagnostic.platform_hub.pf_overview` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens); live handler:diagnostic.hub_reopen |
| `diagnostic.platform_hub.pf_flag_manager` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens); nav -> panel:diagnostic.flag_manager |
| `diagnostic.platform_hub.pf_runtime` | select | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens) |
| `diagnostic.platform_hub.pf_catalogues` | select | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens) |
| `diagnostic.platform_hub.pf_resources` | select | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens) |
| `diagnostic.platform_hub.pf_validation` | select | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:461 (diagnostic.platform_hub spec); panel open pinned by goldens/diagnostic/sweep_platform.json (2 goldens) |
| `diagnostic.flag_manager` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:518; open pinned by goldens/diagnostic/sweep_platform_flag.json |
| `diagnostic.flag_manager.pf_flag_enable` | button | domain/diagnostic | KEEP | deliberate pending terminal — 'The flag rollout pipeline is not ported yet' (sb/domain/diagnostic/handlers.py:391-396); per-guild flag mutation is its own slice; panel read view live (golden diagnostic/sweep_platform_flag.json) |
| `diagnostic.flag_manager.pf_flag_disable` | button | domain/diagnostic | KEEP | deliberate pending terminal — 'The flag rollout pipeline is not ported yet' (sb/domain/diagnostic/handlers.py:391-396); per-guild flag mutation is its own slice; panel read view live (golden diagnostic/sweep_platform_flag.json) |
| `diagnostic.flag_manager.pf_flag_refresh` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:518 (diagnostic.flag_manager spec); panel open pinned by goldens/diagnostic/sweep_platform_flag.json; live handler:diagnostic.flag_reopen |
| `diagnostic.flag_manager.pf_flag_back` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:518 (diagnostic.flag_manager spec); panel open pinned by goldens/diagnostic/sweep_platform_flag.json; live handler:diagnostic.hub_reopen |
| `diagnostic.flag_manager.pf_flag_pick` | select | domain/diagnostic | KEEP | deliberate pending terminal — 'The flag rollout pipeline is not ported yet' (sb/domain/diagnostic/handlers.py:391-396); per-guild flag mutation is its own slice; panel read view live (golden diagnostic/sweep_platform_flag.json) |
| `diagnostic.automation_panel` | panel | domain/diagnostic | KEEP | spec sb/domain/diagnostic/panels.py:578; open pinned by goldens/diagnostic/sweep_platform_automation.json |
| `diagnostic.automation_panel.pf_auto_enable` | button | domain/diagnostic | KEEP | deliberate pending terminal — 'The automation scheduler is not ported yet' (sb/domain/diagnostic/handlers.py:398-402); panel read view live (golden diagnostic/sweep_platform_automation.json) |
| `diagnostic.automation_panel.pf_auto_disable` | button | domain/diagnostic | KEEP | deliberate pending terminal — 'The automation scheduler is not ported yet' (sb/domain/diagnostic/handlers.py:398-402); panel read view live (golden diagnostic/sweep_platform_automation.json) |
| `diagnostic.automation_panel.pf_auto_delete` | button | domain/diagnostic | KEEP | deliberate pending terminal — 'The automation scheduler is not ported yet' (sb/domain/diagnostic/handlers.py:398-402); panel read view live (golden diagnostic/sweep_platform_automation.json) |
| `diagnostic.automation_panel.pf_auto_refresh` | button | domain/diagnostic | KEEP | declared in sb/domain/diagnostic/panels.py:578 (diagnostic.automation_panel spec); panel open pinned by goldens/diagnostic/sweep_platform_automation.json; live handler:diagnostic.automation_reopen |
| `diagnostic.automation_panel.pf_auto_rule` | select | domain/diagnostic | KEEP | deliberate pending terminal — 'The automation scheduler is not ported yet' (sb/domain/diagnostic/handlers.py:398-402); panel read view live (golden diagnostic/sweep_platform_automation.json) |

### domain/economy (25 — KEEP 24 · REWORK 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `economymenu` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_economymenu.json; test tests/unit/band3/test_band3_economy.py; menu pair economy+economymenu mirrors oracle (economymenu registry entry_point) |
| `economy` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_slash_economy.json; +1 more golden(s); test tests/unit/verified_live/test_verified_live.py |
| `daily` | command | domain/economy | KEEP | golden parity/goldens/blackjack/blackjack_solo_round_hit.json; +2 more golden(s); test tests/unit/band3/test_band3_panel_actions.py |
| `work` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_work.json; test tests/unit/band3/test_band3_panel_actions.py |
| `shop` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_shop.json; test tests/unit/band3/test_band3_panel_actions.py |
| `balance` | command | domain/economy | KEEP | golden parity/goldens/economy/economy_balance_and_daily.json; +1 more golden(s); test tests/unit/verified_live/test_verified_live.py |
| `pay` | command | domain/economy | REWORK — with sibling lane: parity corpus count-pin — land after mining WP PRs #312/#317 | sb/manifest/economy.py:124 routes workflow:economy.pay (op sb/domain/economy/ops.py:409); parity/goldens/economy/ has no pay golden and parity/goldens/_sweep_skips.json has no pay/transfer entry — only manifest command with neither; wiring tested (tests/unit/band3/test_band3_economy.py, 37 passed) |
| `setlogchannel` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_setlogchannel.json; test tests/unit/band3/test_band3_economy.py |
| `joblist` | command | domain/economy | KEEP | golden parity/goldens/economy/sweep_joblist.json; test tests/unit/band3/test_band3_panel_actions.py |
| `economy.hub` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/manifest/economy.py:87 |
| `economy.hub.daily` | button | domain/economy | KEEP | test tests/unit/settings_band/test_platform_latch.py; component spec/handler sb/manifest/economy.py:104 |
| `economy.hub.work` | button | domain/economy | KEEP | test tests/integration/test_games_checkpoint_race.py; component spec/handler sb/manifest/economy.py:111 |
| `economy.hub.shop` | button | domain/economy | KEEP | test tests/unit/verified_live/test_verified_live.py; component spec/handler sb/manifest/economy.py:118 |
| `economy.hub.balance` | button | domain/economy | KEEP | test tests/integration/test_tournament_entry_race.py; component spec/handler sb/manifest/economy.py:120 |
| `economy.hub.inventory` | button | domain/economy | KEEP | test tests/integration/test_farm_mining_money_race.py; component spec/handler sb/domain/economy/store.py:117 |
| `economy.hub.jobs` | button | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; component spec/handler sb/manifest/economy.py:132 |
| `economy.hub.treasury` | button | domain/economy | KEEP | test tests/unit/spec/test_events.py; component spec/handler sb/domain/economy/store.py:80 |
| `economy.hub.overview` | button | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; component spec/handler sb/domain/economy/panels.py:239 |
| `economy.jobcenter` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/domain/economy/panels.py:209 |
| `economy.jobcenter.job_select` | select | domain/economy | KEEP | select spec/handler sb/domain/economy/panels.py:289 |
| `economy.shop_panel` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/manifest/economy.py:118 |
| `economy.shop_panel.item_select` | select | domain/economy | KEEP | select spec/handler sb/domain/economy/panels.py:343 |
| `economy.daily_card` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/domain/economy/panels.py:57 |
| `economy.wallet_card` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/domain/economy/panels.py:58 |
| `economy.joblist_card` | panel | domain/economy | KEEP | test tests/unit/band3/test_band3_panel_actions.py; panel spec sb/domain/economy/panels.py:59 |

### domain/farm (9 — KEEP 9)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `farm` | command | domain/farm | KEEP | golden parity/goldens/farm/sweep_farm.json + tests/unit/band6/test_band6_checkpoint_games.py; C6 backstop concurs: golden parity/goldens/farm/sweep_farm.json; test tests/unit/band6/test_band6_checkpoint_games.py |
| `farm.hub` | panel | domain/farm | KEEP | golden parity/goldens/farm/sweep_farm.json (!farm opens panel:farm.hub); C6 backstop concurs: register_panel spec sb/domain/farm/panels.py |
| `farm.hub.farm_collect` | button | domain/farm | KEEP | handler sb/domain/farm/ops.py — split verdict — C1 said REWORK, C6 said KEEP; reconciled to KEEP per KEEP>REWORK>DROP precedence (C1 evidence: workflow:farm.collect tested tests/unit/band6/test_band6_checkpoint_games.py::test_farm_collect_pays_and_resets + tests/integration/test_farm_mining_money_race.py, but no interaction golden on this coin-paying click) |
| `farm.hub.farm_shop` | button | domain/farm | KEEP | declarative nav -> panel:farm.shop (sb/domain/farm/panels.py:141); shop render handler:farm.render_shop; C6 backstop concurs: inventory notes: label='Shop'; nav -> panel:farm.shop |
| `farm.hub.farm_refresh` | button | domain/farm | KEEP | declarative nav -> panel:farm.hub (sb/domain/farm/panels.py:145); hub render golden-pinned via sweep_farm.json; C6 backstop concurs: inventory notes: label='Refresh'; nav -> panel:farm.hub |
| `farm.shop` | panel | domain/farm | KEEP | renderer handler:farm.render_shop (sb/domain/farm/panels.py); buy lanes tested tests/unit/band6/test_band6_checkpoint_games.py; C6 backstop concurs: register_panel spec sb/domain/farm/panels.py |
| `farm.shop.farm_buy_hen` | button | domain/farm | KEEP | handler sb/domain/farm/ops.py — split verdict — C1 said REWORK, C6 said KEEP; reconciled to KEEP per KEEP>REWORK>DROP precedence (C1 evidence: workflow:farm.buy_chicken tested tests/unit/band6/test_band6_checkpoint_games.py::test_farm_buy_settles_at_old_flock_first + test_farm_buy_insufficient_uses_shipped_copy, but no interaction golden on this coin-debit click) |
| `farm.shop.farm_upgrade_coop` | button | domain/farm | KEEP | handler sb/domain/farm/ops.py — split verdict — C1 said REWORK, C6 said KEEP; reconciled to KEEP per KEEP>REWORK>DROP precedence (C1 evidence: workflow:farm.upgrade_coop shares the audited farm ops leg (sb/domain/farm/ops.py) with the tested buy lane, but has neither direct test nor golden) |
| `farm.shop.farm_shop_back` | button | domain/farm | KEEP | declarative nav -> panel:farm.hub (sb/domain/farm/panels.py); hub render golden-pinned via sweep_farm.json; C6 backstop concurs: inventory notes: label='Back'; nav -> panel:farm.hub |

### domain/fishing (32 — KEEP 15 · REWORK 17)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `fish` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_fish.json; handler sb/domain/fishing/service.py (cast_open); tests/unit/band6/test_band6_fishing_venue.py PASS |
| `fishing` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_fishing.json; route panel:fishing.hub; tests/unit/band6/test_band6_checkpoint_games.py |
| `fishlog` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_fishlog.json; route panel:fishing.log |
| `fishtop` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_fishtop.json; handler fishing.top_view |
| `trophies` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_trophies.json; handler fishing.trophies_view |
| `forecast` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_forecast.json; tests/unit/band6/test_band6_fishing_venue.py PASS (PR #313 merged) |
| `sail` | command | domain/fishing | KEEP | golden parity/goldens/fishing/sweep_sail.json; tests/unit/band6/test_band6_fishing_venue.py PASS (PR #313 merged) |
| `rod` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_rod.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `bait` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_bait.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `craftbait` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_craftbait.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `craftcharm` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_craftcharm.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `craftrod` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_craftrod.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `rodrecipes` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_rodrecipes.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `craftpearl` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_craftpearl.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `curios` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_curios.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `craftcurio` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_craftcurio.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `tidepool` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_tidepool.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `dock` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_dock.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `boathouse` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_boathouse.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `fishery` | command | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | pending terminal (deep-systems port, docs/decisions.md:326); oracle golden parked at parity/goldens/_unmapped/sweep_fishery.json; oracle-context: live-wired in prod (fishing_cog.py) |
| `fishing.hub` | panel | domain/fishing | KEEP | spec sb/domain/fishing/panels.py:135 (fishing_hub_spec); opened by golden fishing/sweep_fishing.json |
| `fishing.hub.fishing_cast` | button | domain/fishing | KEEP | sb/domain/fishing/panels.py:162; handler fishing.cast_open (same as live !fish); tests/unit/band6/test_band6_checkpoint_games.py |
| `fishing.hub.fishing_sail` | button | domain/fishing | KEEP | sb/domain/fishing/panels.py:167; handler fishing.sail_route; tests/unit/band6/test_band6_fishing_venue.py PASS |
| `fishing.hub.fishing_rod` | button | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | sb/domain/fishing/panels.py:172; handler fishing.rod_pending (same terminal as claimed !rod) |
| `fishing.hub.fishing_bait` | button | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | sb/domain/fishing/panels.py:176; handler fishing.bait_pending (same terminal as claimed !bait) |
| `fishing.hub.fishing_structures` | button | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | sb/domain/fishing/panels.py:180; handler fishing.structures_pending |
| `fishing.hub.fishing_log` | button | domain/fishing | KEEP | sb/domain/fishing/panels.py:185; nav -> panel:fishing.log (real) |
| `fishing.hub.fishing_rules` | button | domain/fishing | REWORK — with sibling lane: fishing-port lane (claim control/claims/fishing-port-remaining.md, slices 2-4) | sb/domain/fishing/panels.py:189; handler fishing.howtofish_pending |
| `fishing.cast_panel` | panel | domain/fishing | KEEP | spec sb/domain/fishing/panels.py:243 (cast_spec); renderer fishing.render_cast |
| `fishing.cast_panel.fishing_reel` | button | domain/fishing | KEEP | sb/domain/fishing/panels.py:256; handler fishing.fish_route (live reel leg of !fish) |
| `fishing.log` | panel | domain/fishing | KEEP | spec sb/domain/fishing/panels.py:283 (log_spec); target of golden fishing/sweep_fishlog.json |
| `fishing.card` | panel | domain/fishing | KEEP | spec sb/domain/fishing/panels.py:218 (fishing_card_spec); tests/unit/band6/test_band6_fishing_venue.py PASS |

### domain/four_twenty (5 — KEEP 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `420` | command | domain/four_twenty | KEEP | golden parity/goldens/four_twenty/sweep_420.json; handler four_twenty.panel_view; oracle: registry entry_point (four_twenty_cog.py) |
| `four_twenty.overview` | panel | domain/four_twenty | KEEP | spec sb/domain/four_twenty/panels.py:53; opened by golden four_twenty/sweep_420.json |
| `four_twenty.overview.wisdom` | button | domain/four_twenty | KEEP | sb/domain/four_twenty/panels.py:69; handler four_twenty.wisdom_view (real) |
| `four_twenty.overview.four_twenty_fact` | button | domain/four_twenty | KEEP | sb/domain/four_twenty/panels.py:73; handler four_twenty.fact_view (real) |
| `four_twenty.overview.four_twenty_overview` | button | domain/four_twenty | KEEP | sb/domain/four_twenty/panels.py:78; nav -> panel:four_twenty.overview |

### domain/games (20 — KEEP 20)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `games` | command | domain/games | KEEP | golden parity/goldens/games/sweep_games.json + tests/unit/band6/test_band6_blackjack_rps.py |
| `world` | command | domain/games | KEEP | golden parity/goldens/games/sweep_world.json + tests/unit/band6/test_band6_games_panels.py |
| `worldcard` | command | domain/games | KEEP | golden parity/goldens/games/sweep_worldcard.json + tests/unit/band6/test_band6_games_substrate.py |
| `games.hub` | panel | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_blackjack` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_casino` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_deathmatch` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_rps_tournament` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_mining` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_fishing` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_creature` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_farm` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_counting` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.hub.ga_chain` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world` | panel | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world.world_mine` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world.world_fish` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world.world_farm` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world.world_card` | button | domain/games | KEEP | tests/unit/band6/test_band6_games_panels.py |
| `games.world_card` | panel | domain/games | KEEP | tests/unit/band6/test_band6_games_substrate.py |

### domain/general (21 — KEEP 21)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `generalmenu` | command | domain/general | KEEP | golden parity/goldens/general/sweep_generalmenu.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_generalmenu.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `fact` | command | domain/general | KEEP | golden parity/goldens/general/sweep_fact.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_fact.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `joke` | command | domain/general | KEEP | golden parity/goldens/general/sweep_joke.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_joke.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `quote` | command | domain/general | KEEP | golden parity/goldens/general/sweep_quote.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_quote.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `trivia` | command | domain/general | KEEP | golden parity/goldens/general/sweep_trivia.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_trivia.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `motivate` | command | domain/general | KEEP | golden parity/goldens/general/sweep_motivate.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_motivate.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `eightball` | command | domain/general | KEEP | golden parity/goldens/general/sweep_eightball.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_eightball.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `greet` | command | domain/general | KEEP | golden parity/goldens/general/sweep_greet.json + tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: golden parity/goldens/general/sweep_greet.json; handler sb/domain/general/handlers.py; test tests/unit/band6/test_band6_general_menu.py |
| `general.menu` | panel | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: register_panel spec sb/domain/general/panels.py |
| `general.menu.fact` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py::test_content_handlers_reply_from_the_pools (general.fact_view); C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.joke` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.quote` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.trivia` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.motivate` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.eightball` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.eightball.general.eightball_form` | modal | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py::test_eightball_submit_echoes_the_question; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.greet` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |
| `general.menu.general_overview` | button | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: test tests/unit/band6/test_band6_general_menu.py |
| `general.card` | panel | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: register_panel spec sb/domain/general/panels.py |
| `general.trivia_card` | panel | domain/general | KEEP | tests/unit/band6/test_band6_general_menu.py; C6 backstop concurs: register_panel spec sb/domain/general/panels.py |
| `general.trivia_card.trivia_reveal` | button | domain/general | KEEP | clean handler review sb/domain/general/handlers.py:187-194 (oracle-verbatim reveal reply) + trivia_card render test test_band6_general_menu.py; C6 backstop concurs: handler sb/domain/general/handlers.py |

### domain/help (71 — KEEP 71)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `help` | command | domain/help | KEEP | golden parity/goldens/help/help_panel_open.json; +2 more golden(s); test tests/unit/interaction/test_dispatch_and_envelope.py |
| `help.sub_games` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_blackjack` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_casino` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_deathmatch` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_rps_tournament` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_mining` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_mining_p2` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_counting` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_chain` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_fishing` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_creature` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_farm` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_games` | panel | domain/help | KEEP | test tests/unit/help_band/test_help_categories.py; generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_games.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_btd6` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_btd6_p2` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_btd6_p3` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_btd6_p4` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_btd6` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_btd6.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_projmoon` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_project_moon` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_project_moon.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_economy` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_inventory` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_leaderboard` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_treasury` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_economy` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_economy.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_moderation` | panel | domain/help | KEEP | test tests/unit/help_band/test_help_categories.py; generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_automod` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_image_moderation` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_cleanup` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_logging` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_proof_channel` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_security` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_moderation` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_moderation.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_community` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_xp` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_karma` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_community_spotlight` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_role` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_welcome` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_counters` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_ticket` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_community` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_community.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_utility` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_general` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_four_twenty` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_utility` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_utility.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_admin` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_ux_lab` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_channel` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_server_management` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_ai` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_settings` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_diagnostic` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_diagnostic_p2` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_setup` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_admin` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_admin.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.sub_hermes` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.sub_starboard` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:239 (_subsystem_panels; panel_id via _chunk_panel_id :217-218); reachable from help.home golden parity/goldens/help/sweep_help.json chain |
| `help.cat_other` | panel | domain/help | KEEP | generated panel spec sb/domain/help/service.py:261 (_category_panel); reachable from help.home select (service.py:199) |
| `help.cat_other.feature_select` | select | domain/help | KEEP | select spec/handler sb/domain/help/service.py:272 |
| `help.home` | panel | domain/help | KEEP | test tests/unit/band6/test_band6_server_management_hub.py; panel spec sb/manifest/help.py:21 |
| `help.home.category_select` | select | domain/help | KEEP | test tests/unit/help_band/test_help_categories.py; select spec/handler sb/domain/help/service.py:304 |

### domain/hermes (3 — KEEP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `bugreport` | command | domain/hermes | KEEP | golden parity/goldens/hermes/sweep_slash_bugreport.json; handler sb/domain/hermes/handlers.py; test tests/unit/parity_adapter/test_hermes_followup.py |
| `dispatch` | command | domain/hermes | KEEP | golden parity/goldens/hermes/sweep_slash_dispatch.json; handler sb/domain/hermes/handlers.py |
| `hermes.bridge_unconfigured` | panel | domain/hermes | KEEP | register_panel spec sb/domain/hermes/panels.py |

### domain/image_moderation (3 — KEEP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `imagemod` | command | domain/image_moderation | KEEP | golden parity/goldens/image_moderation/sweep_imagemod.json |
| `image_moderation.hub` | panel | domain/image_moderation | KEEP | spec sb/domain/operator_spine.py:94 hub_spec; tests: tests/unit/band6/test_band6_settings_panels.py |
| `image_moderation.status` | panel | domain/image_moderation | KEEP | spec sb/domain/image_moderation/panels.py:48; open pinned by goldens/image_moderation/sweep_imagemod.json |

### domain/inventory (16 — KEEP 16)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `inventory` | command | domain/inventory | KEEP | 4 goldens incl. parity/goldens/inventory/inventory_browse_filter_ore.json + sweep_inventory.json; tests/unit/band3/test_band3_panel_actions.py PASS |
| `inventory.hub` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:162 (inventory_hub_spec); tests/unit/band3/test_band3_panel_actions.py PASS |
| `inventory.hub.open_mining_materials` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_mining_materials -> panel:inventory.cat_mining_materials); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.hub.open_crafted_items` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_crafted_items -> panel:inventory.cat_crafted_items); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.hub.open_tools` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav); tests/unit/band3/test_band3_panel_actions.py PASS |
| `inventory.hub.open_fishing` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_fishing -> panel:inventory.cat_fishing); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.hub.open_collectibles` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_collectibles -> panel:inventory.cat_collectibles); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.hub.open_economy_items` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_economy_items -> panel:inventory.cat_economy_items); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.hub.open_other` | button | domain/inventory | KEEP | sb/domain/inventory/panels.py:169 (generated nav open_other -> panel:inventory.cat_other); browse goldens inventory/inventory_browse_*.json exercise the hub |
| `inventory.cat_mining_materials` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_mining_materials) |
| `inventory.cat_crafted_items` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_crafted_items) |
| `inventory.cat_tools` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223; tests/unit/band3/test_band3_panel_actions.py PASS |
| `inventory.cat_fishing` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_fishing) |
| `inventory.cat_collectibles` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_collectibles) |
| `inventory.cat_economy_items` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_economy_items) |
| `inventory.cat_other` | panel | domain/inventory | KEEP | spec sb/domain/inventory/panels.py:223 (category_detail_specs, panel inventory.cat_other) |

### domain/karma (5 — KEEP 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `thanks` | command | domain/karma | KEEP | golden parity/goldens/karma/karma_repeat_cooldown.json; +3 more golden(s); test tests/unit/app/test_main_wiring.py |
| `karma` | command | domain/karma | KEEP | golden parity/goldens/karma/karma_slash_card.json; +3 more golden(s); test tests/unit/settings_band/test_band1_settings.py — dual prefix+slash declaration, expected dedup artifact (KEEP, not a drop) |
| `karma.add` | command | domain/karma | KEEP | golden parity/goldens/karma/sweep_karma_add.json; sb/manifest/karma.py:100 routes HandlerRef('karma.thanks') same as thanks (:87-88) — deliberate oracle-verbatim mirror (oracle-context.md: karma_cog.py declares both !thanks and !karma add live-wired); duplication investigated, not a drop |
| `karma.card` | panel | domain/karma | KEEP | test tests/unit/app/test_cut1_surfaces.py; panel spec sb/domain/karma/panels.py:41 |
| `karma.error_card` | panel | domain/karma | KEEP | panel spec sb/domain/karma/panels.py:42 |

### domain/leaderboard (3 — KEEP 2 · REWORK 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `leaderboard` | command | domain/leaderboard | REWORK | golden parity/goldens/leaderboard/sweep_leaderboard.json (canonical command real); aliases lb/rankings/minelb/miningleaderboard/fishlb/dm_leaderboard/dm_lb/rpslb/farmlb/countlb/counting_leaderboard declared sb/manifest/leaderboard.py:27-30; oracle marks the alias set legacy_duplicate (oracle-context.md: leaderboard_cog:211 alias_classification) |
| `leaderboard.board` | panel | domain/leaderboard | KEEP | test tests/unit/band4/test_band4_community.py; panel spec sb/domain/community/handlers.py:51 |
| `leaderboard.board.category_select` | select | domain/leaderboard | KEEP | test tests/unit/help_band/test_help_categories.py; select spec/handler sb/domain/community/panels.py:290 |

### domain/logging (25 — KEEP 25)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `logging` | command | domain/logging | KEEP | golden parity/goldens/logging/logging_enable_and_bind.json; test tests/unit/settings_band/test_band1_settings.py |
| `logging.status` | command | domain/logging | KEEP | golden parity/goldens/logging/sweep_logging_status.json; test tests/unit/band2/test_band2_slice1.py |
| `logging.set` | command | domain/logging | KEEP | golden parity/goldens/logging/logging_enable_and_bind.json; handler sb/domain/server_logging/handlers.py; test tests/unit/band6/test_band6_channel_hub.py |
| `logging.create` | command | domain/logging | KEEP | golden parity/goldens/logging/sweep_logging_create.json; handler sb/domain/server_logging/handlers.py; test tests/unit/app/test_main_wiring.py |
| `logging.routes` | command | domain/logging | KEEP | golden parity/goldens/logging/sweep_logging_routes.json; handler sb/domain/server_logging/handlers.py |
| `logging.test` | command | domain/logging | KEEP | golden parity/goldens/logging/sweep_logging_test.json; handler sb/domain/server_logging/handlers.py; test tests/unit/rollback/test_s14_rollback.py |
| `logging.hub` | panel | domain/logging | KEEP | register_panel spec sb/domain/server_logging/panels.py |
| `logging.hub.refresh_status` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.set_mod` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.set_cleanup` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.create_mod` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.create_cleanup` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.test` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.routes` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.hub.hub_overview` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.status_card` | panel | domain/logging | KEEP | register_panel spec sb/domain/server_logging/panels.py |
| `logging.routes` | panel | domain/logging | KEEP | register_panel spec sb/domain/server_logging/panels.py |
| `logging.routes.routes_bind` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.routes.routes_create` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.routes.routes_refresh` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.routes.routes_back` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.routes.select` | select | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.bind_picker` | panel | domain/logging | KEEP | register_panel spec sb/domain/server_logging/panels.py |
| `logging.bind_picker.clear` | button | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |
| `logging.bind_picker.pick` | select | domain/logging | KEEP | handler sb/domain/server_logging/handlers.py |

### domain/mining (72 — KEEP 45 · REWORK 26 · DROP 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `minemenu` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_minemenu.json; route panel:mining.hub |
| `mine` | command | domain/mining | REWORK | sb/domain/mining/service.py:198 mine_route returns BLOCKED generic copy (grid navigator un-ported; golden mining/sweep_mine.json pins the capture-world error byte) |
| `fastmine` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_fastmine.json; real audited op mining.mine (service.py:207) |
| `chop` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_chop.json; handler mining.chop_route (service.py:220) |
| `explore` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_explore.json; handler mining.explore_route (service.py:230) |
| `sell` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_sell.json; handler mining.sell_route (service.py:261); tests/unit/band6/test_band6_games_substrate.py |
| `sellall` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_sellall.json; handler mining.sellall_route |
| `buy` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_buy.json; handler mining.buy_route (service.py:291) |
| `market` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_market.json; handler mining.market_view |
| `mineinv` | command | domain/mining | DROP | sb/domain/mining/service.py:304 inventory_view delegates verbatim to HandlerRef('inventory.view'); oracle-context: legacy-duplicate (oracle-marked), hidden=True (mining_cog.py mineinv) |
| `minestats` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_minestats.json; handler mining.stats_view (service.py:314) |
| `build` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-6 (planned, claimed) | sb/domain/mining/service.py:412 — bare !build live (buildlist card, golden mining/sweep_build.json); argful craft write is a BLOCKED deep-systems-port terminal (docs/decisions.md:326) |
| `buildlist` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_buildlist.json; handler mining.buildlist_route (service.py:430) |
| `buildable` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_buildable.json; handler mining.buildable_view |
| `use` | command | domain/mining | REWORK — with sibling lane: energy lane (PR #320, docs/scoping/energy-system-scope.md) | sb/domain/mining/service.py:912 — bare usage copy live (golden mining/sweep_use.json); argful consume is a BLOCKED terminal on the un-ported energy/consumable system |
| `cook` | command | domain/mining | REWORK — with sibling lane: energy lane (PR #320, docs/scoping/energy-system-scope.md) | sb/domain/mining/service.py:895 — bare usage copy live (golden mining/sweep_cook.json); argful cook is a BLOCKED terminal on the un-ported energy/campfire system |
| `equip` | command | domain/mining | KEEP | golden parity/goldens/mining/mining_equip_write.json (WP-1 write golden, PR #306 merged) + sweep_equip.json |
| `unequip` | command | domain/mining | KEEP | golden parity/goldens/mining/mining_unequip_write.json + sweep_unequip.json; tests/unit/mining/test_equipment_stats.py PASS |
| `gear` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_gear.json; handler mining.gear_view |
| `loadout` | command | domain/mining | KEEP | 3 write goldens parity/goldens/mining/mining_loadout_{save,apply,delete}_write.json (WP-1, merged) + sweep_loadout.json |
| `character` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_character.json; handler mining.character_view |
| `descend` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-3 folds WP-4 (PR #317) | sb/domain/mining/service.py:662 — real audited depth op; sweep golden pins only the gearless refusal; geared write golden mining.descend_write in flight |
| `ascend` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-3 folds WP-4 (PR #317) | sb/domain/mining/service.py:692 — real audited op; write golden mining.ascend_write in flight |
| `mineworld` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-3 folds WP-4 (PR #317) | sb/domain/mining/service.py:713 — real audited reseed op (golden mining/sweep_mineworld.json pins bare read); admin reseed write golden in flight |
| `vault` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_vault.json; route panel:mining.vault |
| `stash` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-2 (PR #312) | sb/domain/mining/service.py:754 — real audited deposit op (golden mining/sweep_stash.json pins bare usage byte); row-bearing write golden in flight |
| `unstash` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-2 (PR #312) | sb/domain/mining/service.py:777 — real audited withdraw op; write golden in flight |
| `vaultupgrade` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-2 (PR #312) | sb/domain/mining/service.py:797 — real audited funded upgrade op; write golden + concurrency regression in flight |
| `skills` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_skills.json; route panel:mining.skills |
| `skill` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/service.py:928 — bare branch-picker guard live (golden mining/sweep_skill.json); argful point-spend is a BLOCKED terminal (player_skills guard-only-capture) |
| `titles` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_titles.json; route panel:mining.titles |
| `forge` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_forge.json; route panel:mining.forge |
| `home` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_home.json; route panel:mining.home; tests/unit/interaction/test_resolve_order.py |
| `workshop` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_workshop.json; route panel:mining.workshop |
| `repair` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-3 folds WP-4 (PR #317) | sb/domain/mining/service.py:845 — real audited repair op (golden mining/sweep_repair.json pins guard); write golden + race regression in flight |
| `quickcraft` | command | domain/mining | REWORK — with sibling lane: mining-write-parity WP-3 folds WP-4 (PR #317) | sb/domain/mining/service.py:867 — real audited quick_craft op; write golden + dup-race regression in flight |
| `reset_inventory` | command | domain/mining | KEEP | golden parity/goldens/mining/sweep_reset_inventory.json; handler mining.reset_inventory_route (admin, guild-scoped) |
| `mining.hub` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:160 (mining_hub_spec); opened by golden mining/sweep_minemenu.json |
| `mining.hub.mi_mine` | button | domain/mining | REWORK | sb/domain/mining/panels.py:176; handler mining.grid_view_pending (same un-ported grid navigator as !mine) |
| `mining.hub.mi_harvest` | button | domain/mining | KEEP | sb/domain/mining/panels.py:181; handler mining.chop_route (real, golden-backed via sweep_chop) |
| `mining.hub.mi_explore_hub` | button | domain/mining | KEEP | sb/domain/mining/panels.py:187; nav -> panel:games.world |
| `mining.hub.mi_character` | button | domain/mining | KEEP | sb/domain/mining/panels.py:192; handler mining.character_view (real) |
| `mining.hub.mi_gear` | button | domain/mining | KEEP | sb/domain/mining/panels.py:198; handler mining.gear_view (real) |
| `mining.hub.mi_workshop` | button | domain/mining | KEEP | sb/domain/mining/panels.py:204; nav -> panel:mining.workshop |
| `mining.hub.mi_how_to` | button | domain/mining | REWORK | sb/domain/mining/panels.py:209; handler mining.how_to_pending |
| `mining.card` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:244 (mining_card_spec); renderer mining.render_card |
| `mining.vault` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:964 (mining_vault_spec); opened by golden mining/sweep_vault.json |
| `mining.vault.va_deposit` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-2 (PR #312) | sb/domain/mining/panels.py:987; handler mining.vault_deposit_pending (argful ingress missing; op record_stash live) |
| `mining.vault.va_withdraw` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-2 (PR #312) | sb/domain/mining/panels.py:991; handler mining.vault_withdraw_pending |
| `mining.vault.va_stash_all` | button | domain/mining | KEEP | sb/domain/mining/panels.py:995; handler mining.stash_all_route (real); click-driven write golden mining.stash_all_write in flight (PR #312) |
| `mining.vault.va_upgrade` | button | domain/mining | KEEP | sb/domain/mining/panels.py:1000; handler mining.vaultupgrade_route (real) |
| `mining.vault.va_hub` | button | domain/mining | KEEP | sb/domain/mining/panels.py:1005; nav -> panel:mining.hub |
| `mining.forge` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:335 (mining_forge_spec); tests/unit/invariants/test_composition_parity.py |
| `mining.forge.fo_build` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-6 (planned, claimed) | sb/domain/mining/panels.py:357; handler mining.forge_build_pending |
| `mining.forge.fo_workshop` | button | domain/mining | KEEP | sb/domain/mining/panels.py:361; nav -> panel:mining.workshop |
| `mining.skills` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:454 (mining_skills_spec); opened by golden mining/sweep_skills.json |
| `mining.skills.sk_mining` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/panels.py:477; handler mining.skill_spend_pending |
| `mining.skills.sk_combat` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/panels.py:481; handler mining.skill_spend_pending |
| `mining.skills.sk_fortune` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/panels.py:485; handler mining.skill_spend_pending |
| `mining.skills.sk_crafting` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/panels.py:489; handler mining.skill_spend_pending |
| `mining.skills.sk_respec` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-5 (planned, claimed) | sb/domain/mining/panels.py:493; handler mining.skill_respec_pending |
| `mining.skills.sk_titles` | button | domain/mining | KEEP | sb/domain/mining/panels.py:497; nav -> panel:mining.titles |
| `mining.skills.sk_hub` | button | domain/mining | KEEP | sb/domain/mining/panels.py:501; nav -> panel:mining.hub |
| `mining.titles` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:565 (mining_titles_spec); opened by golden mining/sweep_titles.json (WP-5 notes title equip may stay select-driven pending) |
| `mining.titles.ti_hub` | button | domain/mining | KEEP | sb/domain/mining/panels.py:592; nav -> panel:mining.hub |
| `mining.workshop` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:720 (mining_workshop_spec); opened by golden mining/sweep_workshop.json |
| `mining.workshop.ws_quickcraft` | button | domain/mining | KEEP | sb/domain/mining/panels.py:753; handler mining.quickcraft_route (real; write golden rides PR #317) |
| `mining.workshop.ws_back` | button | domain/mining | REWORK | sb/domain/mining/panels.py:759; handler mining.workshop_hub_pending — a back-nav wired to a pending terminal |
| `mining.workshop.ws_craft` | select | domain/mining | REWORK — with sibling lane: mining-write-parity WP-6 (planned, claimed) | sb/domain/mining/panels.py:744; select on_select mining.workshop_craft_pending (options provider live) |
| `mining.home` | panel | domain/mining | KEEP | spec sb/domain/mining/panels.py:874 (mining_home_spec); opened by golden mining/sweep_home.json |
| `mining.home.ho_build` | button | domain/mining | REWORK — with sibling lane: mining-write-parity WP-6 (planned, claimed) | sb/domain/mining/panels.py:896; handler mining.home_build_pending |
| `mining.home.ho_hub` | button | domain/mining | KEEP | sb/domain/mining/panels.py:900; nav -> panel:mining.hub |

### domain/moderation (25 — KEEP 24 · DROP 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `modmenu` | command | domain/moderation | DROP | sb/manifest/moderation.py:103-106 — `moderation` is CommandKind.BOTH routing the same panel:moderation.hub; golden moderation/sweep_modmenu.json |
| `moderation` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_slash_moderation.json; tests: tests/unit/band2/test_band2_slice1.py (+5) |
| `warn` | command | domain/moderation | KEEP | goldens moderation/moderation_warn_flow.json + sweep_warn; workflow:moderation.warn (escalation ladder, docs/decisions.md:182); the flow's step-2 `!warnings` is NOT a gap — oracle never shipped it, golden pins the did-you-mean reply (sb/manifest/moderation.py:122-125) |
| `timeout` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_timeout.json; tests: tests/unit/band2/test_band2_slice1.py (+2) |
| `kick` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_kick.json; tests: tests/unit/band2/test_band2_slice1.py (+5) |
| `ban` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_ban.json; tests: tests/unit/band2/test_band2_slice1.py (+5) |
| `unban` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_unban.json; tests: tests/unit/band2/test_band2_slice1.py (+2) |
| `clearwarnings` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_clearwarnings.json; tests: tests/unit/band2/test_band2_slice1.py |
| `modlogs` | command | domain/moderation | KEEP | golden parity/goldens/moderation/sweep_modlogs.json |
| `moderation.hub` | panel | domain/moderation | KEEP | spec sb/domain/moderation/panels.py:117; open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; tests: tests/unit/band6/test_band6_settings_panels.py |
| `moderation.hub.warn` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live workflow:moderation.warn |
| `moderation.hub.warn.moderation.warn_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.timeout` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live handler:moderation.timeout_command |
| `moderation.hub.timeout.moderation.timeout_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.kick` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live workflow:moderation.kick |
| `moderation.hub.kick.moderation.kick_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.ban` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live workflow:moderation.ban |
| `moderation.hub.ban.moderation.ban_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.unban` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live workflow:moderation.unban |
| `moderation.hub.unban.moderation.unban_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.logs` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live handler:moderation.modlogs_view |
| `moderation.hub.logs.moderation.modlogs_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.hub.clearwarn` | button | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json; live workflow:moderation.clearwarnings |
| `moderation.hub.clearwarn.moderation.clearwarnings_form` | modal | domain/moderation | KEEP | declared in sb/domain/moderation/panels.py:117 (moderation.hub spec); panel open pinned by goldens/moderation/sweep_modmenu.json + sweep_slash_moderation.json |
| `moderation.modlogs_card` | panel | domain/moderation | KEEP | spec sb/domain/moderation/panels.py:241; open pinned by goldens/moderation/sweep_modlogs.json |

### domain/projmoon (20 — KEEP 20)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `pm` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm.json; +1 more golden(s); test tests/unit/band7/test_band7_projmoon_video.py — dual prefix+slash declaration, expected dedup artifact (KEEP, not a drop) |
| `pm.lookup` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_lookup.json; test tests/unit/ai/test_k10_providers.py |
| `pm.list` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_list.json; test tests/unit/band6/test_band6_channel_hub.py |
| `pm.origins` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_origins.json |
| `pm.sinner` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_sinner.json |
| `pm.sin` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_sin.json |
| `pm.status` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_status.json; test tests/unit/band2/test_band2_slice1.py |
| `pm.ego` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_ego.json |
| `pm.damage` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_damage.json; test tests/unit/band6/test_band6_creature_battle_engine.py |
| `pm.mechanic` | command | domain/projmoon | KEEP | golden parity/goldens/project_moon/sweep_pm_mechanic.json; test tests/unit/mining/test_equipment_stats.py |
| `projmoon.hub` | panel | domain/projmoon | KEEP | panel spec sb/manifest/projmoon.py:45 |
| `projmoon.hub.pm_overview` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:66 |
| `projmoon.hub.pm_sinners` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:68 |
| `projmoon.hub.pm_sins` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:69 |
| `projmoon.hub.pm_damage` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:70 |
| `projmoon.hub.pm_mechanics` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:71 |
| `projmoon.hub.pm_ego` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:73 |
| `projmoon.hub.pm_statuses` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:74 |
| `projmoon.hub.pm_origins` | button | domain/projmoon | KEEP | component spec/handler sb/domain/projmoon/panels.py:75 |
| `projmoon.card` | panel | domain/projmoon | KEEP | test tests/unit/band7/test_band7_projmoon_video.py; panel spec sb/domain/projmoon/panels.py:101 |

### domain/proof_channel (12 — KEEP 12)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `+prize` | command | domain/proof_channel | KEEP | golden parity/goldens/proof_channel/sweep_+prize.json; handler sb/domain/proof_channel/handlers.py; test tests/unit/band5/test_band5_platform.py |
| `-prize` | command | domain/proof_channel | KEEP | golden parity/goldens/proof_channel/sweep_-prize.json; handler sb/domain/proof_channel/handlers.py; test tests/unit/band5/test_band5_platform.py |
| `prizestatus` | command | domain/proof_channel | KEEP | golden parity/goldens/proof_channel/sweep_prizestatus.json; handler sb/domain/proof_channel/handlers.py; test tests/unit/band5/test_band5_platform.py |
| `prizemenu` | command | domain/proof_channel | KEEP | golden parity/goldens/proof_channel/sweep_prizemenu.json; test tests/unit/band5/test_band5_platform.py |
| `timedprize` | command | domain/proof_channel | KEEP | golden parity/goldens/proof_channel/sweep_timedprize.json; handler sb/domain/proof_channel/handlers.py; test tests/unit/band5/test_band5_platform.py |
| `proof_channel.hub` | panel | domain/proof_channel | KEEP | register_panel spec sb/domain/proof_channel/handlers.py |
| `proof_channel.hub.prize_grant` | button | domain/proof_channel | KEEP | handler sb/domain/proof_channel/ops.py |
| `proof_channel.hub.prize_grant.proof_channel.grant_form` | modal | domain/proof_channel | KEEP | inventory notes: 1 fields; on_submit=null; submit rides the opening action's handler (w |
| `proof_channel.hub.prize_timed` | button | domain/proof_channel | KEEP | handler sb/domain/proof_channel/ops.py |
| `proof_channel.hub.prize_timed.proof_channel.timed_form` | modal | domain/proof_channel | KEEP | inventory notes: 2 fields; on_submit=null; submit rides the opening action's handler (w |
| `proof_channel.hub.prize_end` | button | domain/proof_channel | KEEP | handler sb/domain/proof_channel/ops.py |
| `proof_channel.hub.prize_refresh` | button | domain/proof_channel | KEEP | inventory notes: label='🔄 Refresh Status'; nav -> panel:proof_channel.hub |

### domain/role (26 — KEEP 23 · REWORK 1 · DROP 2)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `roles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_roles.json; tests tests/unit/band5/test_band5_role.py; oracle-context.md:406 live-wired canonical hub opener |
| `rolesettings` | command | domain/role | KEEP | golden parity/goldens/role/sweep_rolesettings.json; oracle-context.md:407 live-wired admin alias (NOT oracle legacy-marked, unlike rolemenu/rolecreator) |
| `roleinfo` | command | domain/role | KEEP | golden parity/goldens/role/sweep_roleinfo.json; handler sb/domain/role/handlers.py roleinfo; oracle-context.md:408 live-wired |
| `rolemenu` | command | domain/role | DROP | oracle-context.md:409 — legacy-duplicate (oracle-marked), hidden=True, help text 'use !roles instead'; routes panel:role.hub (4-way with roles/rolesettings/rolecreator) |
| `rolecreator` | command | domain/role | DROP | oracle-context.md:410 — legacy-duplicate (oracle-marked), hidden=True, 'use !roles instead'; routes panel:role.hub |
| `assignroles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_assignroles.json; oracle-context.md:411 panel-action hidden (deliberately panel-first; hidden != dead per oracle-context.md:546-547) |
| `createrole` | command | domain/role | KEEP | goldens parity/goldens/kernel/kernel_audited_prefix_command.json + role/sweep_createrole.json; tests tests/unit/band5/test_live_role_adapters.py |
| `deleterole` | command | domain/role | KEEP | golden parity/goldens/role/sweep_deleterole.json; tests tests/unit/band5/test_live_role_adapters.py |
| `setrole` | command | domain/role | KEEP | golden parity/goldens/role/sweep_setrole.json; tests tests/unit/band5/test_band5_role.py |
| `unsetrole` | command | domain/role | KEEP | golden parity/goldens/role/sweep_unsetrole.json; tests tests/unit/band5/test_band5_role.py |
| `debugroles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_debugroles.json; oracle-context.md:416 internal-admin hidden, live in prod |
| `refreshmembers` | command | domain/role | KEEP | golden parity/goldens/role/sweep_refreshmembers.json; oracle-context.md:417 internal-admin hidden, live in prod |
| `reactroles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_reactroles.json; tests tests/unit/band5/test_band5_role.py; oracle-context.md:418 live-wired |
| `removereactrole` | command | domain/role | KEEP | golden parity/goldens/role/sweep_removereactrole.json; oracle-context.md:419 live-wired |
| `listreactroles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_listreactroles.json; tests tests/unit/band5/test_band5_role.py + test_band5_seams.py |
| `temprole` | command | domain/role | KEEP | golden parity/goldens/role/sweep_temprole.json; tests tests/unit/band5/test_band5_role.py; oracle-context.md:421 live-wired |
| `temproles` | command | domain/role | KEEP | golden parity/goldens/role/sweep_temproles.json; tests tests/unit/band5/test_band5_role.py; oracle-context.md:422 live-wired |
| `role.hub` | panel | domain/role | KEEP | spec sb/domain/role/panels.py:96-150 (renderer role.render_hub); tests tests/unit/band5/test_band5_seams.py + tests/unit/invariants/test_composition_parity.py. Ports the LIVE RoleHubPanelView; the oracle-dead orphan is oracle-side only (views/roles/main_panel.py RoleHubView, oracle-context.md:564-567) |
| `role.hub.role_create` | button | domain/role | REWORK | handler:role.create_pending -> operator_spine pending terminal (the only pending item in domain/role); the typed lane handler:role.createrole is live + kernel-audited (parity/goldens/kernel/kernel_audited_prefix_command.json) |
| `role.hub.role_manage` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:126 manage_view (real) |
| `role.hub.role_time` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:42 time_roles_view (real) |
| `role.hub.role_xp` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:56 xp_roles_view (real) |
| `role.hub.role_reaction` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:70 reaction_view (real; same handler golden-covered via listreactroles sweep_listreactroles.json) |
| `role.hub.role_diagnostics` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:102 diagnostics_view (real) |
| `role.hub.role_exemptions` | button | domain/role | KEEP | handler sb/domain/role/handlers.py:88 exemptions_view (real) |
| `role.info_card` | panel | domain/role | KEEP | spec sb/domain/role/panels.py:180-197 (renderer role.render_info_card); rendered by roleinfo, golden parity/goldens/role/sweep_roleinfo.json |

### domain/rps_tournament (30 — KEEP 29 · REWORK 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `rps` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rps.json + tests/unit/band6/test_band6_deathmatch_casino.py |
| `rpsregister` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/rps_tournament_foreign_active_refusal.json + tests/unit/band6/test_band6_rps_tournament.py |
| `rpsstart` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rpsstart.json + tests/unit/band6/test_band6_rps_tournament.py |
| `rpsbot` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rpsbot.json + tests/unit/band6/test_band6_rps_tournament.py |
| `rpsmatchup` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rpsmatchup.json + tests/unit/band6/test_band6_rps_tournament.py |
| `rpshelp` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rpshelp.json |
| `rpssettings` | command | domain/rps_tournament | KEEP | golden parity/goldens/rps_tournament/sweep_rpssettings.json + tests/unit/band6/test_band6_rps_tournament.py |
| `rps_tournament.hub` | panel | domain/rps_tournament | KEEP | spec sb/domain/rps/panels.py:121-139; opened via games.hub nav (tests/unit/band6/test_band6_games_panels.py::test_hub_render_matches_the_golden_bytes) |
| `rps_tournament.hub.rps_rules` | button | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_blackjack_rps.py |
| `rps_tournament.hub.rps_settings_view` | button | domain/rps_tournament | KEEP | shares handler:rps.settings_view with !rpssettings golden parity/goldens/rps_tournament/sweep_rpssettings.json + test_band6_rps_tournament.py::test_rpssettings_bare_shows_the_read_view |
| `rps_tournament.hub.rps_quick_move` | select | domain/rps_tournament | KEEP | shares workflow:rps.solo_play with quickplay buttons, end-to-end tested tests/unit/band6/test_band6_rps_quickplay.py::test_walking_skeleton_rps_quickplay_end_to_end (spec sb/domain/rps/panels.py:128-134) |
| `rps_tournament.quickplay` | panel | domain/rps_tournament | REWORK — with sibling lane: tournament-flow goldens lane (docs/decisions.md:542) | render + free-play flow tested tests/unit/band6/test_band6_rps_quickplay.py::test_walking_skeleton_rps_quickplay_end_to_end and money lanes test_band6_blackjack_rps.py::test_rps_solo_win_and_free_play/test_rps_solo_loss_floors, but the coin-bet click path has no golden (sweep_rps.json is the bare open) |
| `rps_tournament.quickplay.rock` | button | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_blackjack_rps.py |
| `rps_tournament.quickplay.paper` | button | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_blackjack_rps.py |
| `rps_tournament.quickplay.scissors` | button | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_blackjack_rps.py |
| `rps_tournament.pvp` | panel | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_rps_pvp.py |
| `rps_tournament.registration` | panel | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_rps_tournament.py::test_registration_render_pins_the_golden_bytes + golden parity/goldens/rps_tournament/rps_tournament_foreign_active_refusal.json |
| `rps_tournament.registration.join` | button | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_duplicate_registration_refusal_is_oracle_verbatim (handler:rps.tournament_join) |
| `rps_tournament.match` | panel | domain/rps_tournament | KEEP | tests/unit/band6/test_band6_rps_tournament.py::test_match_render_open_stage_keeps_shipped_lines + test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_rock` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_paper` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_scissors` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_lizard` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_spock` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_pawn` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_knight` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_queen` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_fire` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_water` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |
| `rps_tournament.match.move_grass` | button | domain/rps_tournament | KEEP | handler:rps.tournament_move exercised end-to-end tests/unit/band6/test_band6_rps_tournament.py::test_walking_skeleton_rps_tournament_end_to_end + test_record_move_locks; extended-mode render test_match_render_mode_subset_lizard_spock |

### domain/security (3 — KEEP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `security` | command | domain/security | KEEP | golden parity/goldens/security/sweep_security.json; tests: tests/unit/band2/test_band2_slice2.py (+1) |
| `security.hub` | panel | domain/security | KEEP | spec sb/domain/operator_spine.py:94 hub_spec; tests: tests/unit/band6/test_band6_settings_panels.py |
| `security.status` | panel | domain/security | KEEP | spec sb/domain/security/panels.py:37; open pinned by goldens/security/sweep_security.json |

### domain/server_management (13 — KEEP 9 · REWORK 4)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `servermanagement` | command | domain/server_management | KEEP | golden parity/goldens/server_management/sweep_servermanagement.json; tests: tests/unit/band6/test_band6_server_management_hub.py |
| `server-management` | command | domain/server_management | REWORK | golden servermanagement/sweep_slash_server-management.json; slash twin of `servermanagement` (both → panel:server_management.hub); oracle ships the pair verbatim (server_management_cog.py prefix + slash) |
| `server_management.hub` | panel | domain/server_management | KEEP | spec sb/domain/server_management/panels.py:148; open pinned by goldens/server_management/sweep_servermanagement.json + servermanagement/sweep_slash_server-management.json; tests: tests/unit/band6/test_band6_server_management_hub.py |
| `server_management.hub.moderation` | button | domain/server_management | REWORK | sb/domain/server_management/panels.py:163 `_pending('moderation', ...)` while moderation.hub is LIVE (sb/domain/moderation/panels.py:117); the sibling Channels button at :164-170 shows the exact nav pattern (handler=PanelRef('channel.hub')) |
| `server_management.hub.channels` | button | domain/server_management | KEEP | declared in sb/domain/server_management/panels.py:148 (server_management.hub spec); panel open pinned by goldens/server_management/sweep_servermanagement.json + servermanagement/sweep_slash_server-management.json; nav -> panel:channel.hub |
| `server_management.hub.roles` | button | domain/server_management | REWORK | sb/domain/server_management/panels.py:171 `_pending('roles', ...)` while role.hub is LIVE (domain/role 25/26 real; only role.hub.role_create is pending) |
| `server_management.hub.cleanup` | button | domain/server_management | REWORK | sb/domain/server_management/panels.py:173 `_pending('cleanup', ...)` while cleanup.hub is LIVE (sb/domain/cleanup/panels.py:148, golden cleanup/sweep_cleanup.json) |
| `server_management.hub.setup` | button | domain/server_management | KEEP | declared in sb/domain/server_management/panels.py:148 (server_management.hub spec); panel open pinned by goldens/server_management/sweep_servermanagement.json + servermanagement/sweep_slash_server-management.json; nav -> panel:setup.hub |
| `server_management.hub.access_map` | button | domain/server_management | KEEP | deliberate pending terminal — own manager slice (sb/domain/server_management/panels.py:181-182 + docstring under-port note :61-64); the natural nav target settings.access is itself still pending-armed (settings.access.* rows pending) |
| `server_management.hub.help_preview` | button | domain/server_management | KEEP | deliberate pending terminal — help-manager slice (sb/domain/server_management/panels.py:183-184; docstring :61-64) |
| `server_management.hub.help_editor` | button | domain/server_management | KEEP | deliberate pending terminal — help-manager slice (sb/domain/server_management/panels.py:185-186; docstring :61-64) |
| `server_management.hub.sm_refresh` | button | domain/server_management | KEEP | declared in sb/domain/server_management/panels.py:148 (server_management.hub spec); panel open pinned by goldens/server_management/sweep_servermanagement.json + servermanagement/sweep_slash_server-management.json; nav -> panel:server_management.hub |
| `server_management.hub.help_back` | button | domain/server_management | KEEP | declared in sb/domain/server_management/panels.py:148 (server_management.hub spec); panel open pinned by goldens/server_management/sweep_servermanagement.json + servermanagement/sweep_slash_server-management.json; nav -> panel:help.home |

### domain/settings (16 — KEEP 5 · REWORK 11)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `settings` | command | domain/settings | KEEP | goldens parity/goldens/settings/settings_hub_open.json + sweep_settings.json + sweep_slash_settings.json; tests tests/unit/settings_band/test_band1_settings.py; audit row OK at docs/review/admin-surface-audit-2026-07-12.md:61 |
| `settings.access` | command | domain/settings | KEEP | golden parity/goldens/settings/sweep_settings_access.json; handler settings.access_view (sb/domain/settings/handlers.py, registered real); oracle-context.md:434 live-wired |
| `settings.hub` | panel | domain/settings | KEEP | renderer sb/domain/settings/panels.py:315 (settings.render_hub); golden parity/goldens/settings/settings_hub_open.json; tests tests/unit/band6/test_band6_settings_panels.py |
| `settings.hub.needs_setup` | button | domain/settings | REWORK — with sibling lane: settings-mutation slice (audit PARK, docs/review/admin-surface-audit-2026-07-12.md) | handler:settings.needs_setup_pending pending terminal, sb/domain/settings/handlers.py:36-37; audit docs/review/admin-surface-audit-2026-07-12.md:182-193 (deliberate pending-terminal shell) |
| `settings.hub.invalid` | button | domain/settings | REWORK — with sibling lane: settings-mutation slice (audit PARK, docs/review/admin-surface-audit-2026-07-12.md) | handler:settings.invalid_pending pending terminal, sb/domain/settings/handlers.py:38-39; audit docs/review/admin-surface-audit-2026-07-12.md:62 PARK |
| `settings.hub.missing_bindings` | button | domain/settings | REWORK — with sibling lane: settings-mutation slice (audit PARK, docs/review/admin-surface-audit-2026-07-12.md) | handler:settings.missing_bindings_pending pending terminal, sb/domain/settings/handlers.py:40-41; audit docs/review/admin-surface-audit-2026-07-12.md:62 PARK |
| `settings.hub.audit` | button | domain/settings | REWORK — with sibling lane: settings-mutation slice (audit PARK, docs/review/admin-surface-audit-2026-07-12.md) | handler:settings.audit_pending pending terminal, sb/domain/settings/handlers.py:42-43; the K7 audit trail it should read is live (docs/review/admin-surface-audit-2026-07-12.md:63 K7 mutation lane OK) |
| `settings.hub.command_access` | button | domain/settings | REWORK — with sibling lane: settings-mutation slice (audit PARK, docs/review/admin-surface-audit-2026-07-12.md) | handler:settings.command_access_pending pending terminal, sb/domain/settings/handlers.py:44-45; audit docs/review/admin-surface-audit-2026-07-12.md:62 PARK |
| `settings.hub.subsystem_select` | select | domain/settings | KEEP | handler settings.open_group real (sb/domain/settings/handlers.py:65+) — the landed control/claims/operator-hubs-interactive.md slice (group select navigates to read-only operator hubs, rest to pending terminal); tests tests/unit/app/test_component_feed.py |
| `settings.access` | panel | domain/settings | KEEP | renderer sb/domain/settings/panels.py:406 (settings.render_access); golden parity/goldens/settings/sweep_settings_access.json |
| `settings.access.explain` | button | domain/settings | REWORK | handler:settings.access_explain_pending pending terminal, sb/domain/settings/handlers.py:53-55 ('ports with the governance-diagnostic slice (governance.resolve_subsystem_state)') |
| `settings.access.reset` | button | domain/settings | REWORK | handler:settings.access_reset_pending pending terminal, sb/domain/settings/handlers.py:56-58 |
| `settings.access.access_prev` | button | domain/settings | REWORK | handler:settings.access_page_pending pending terminal, sb/domain/settings/handlers.py:59-61 |
| `settings.access.access_next` | button | domain/settings | REWORK | handler:settings.access_page_pending pending terminal, sb/domain/settings/handlers.py:59-61 |
| `settings.access.subsystem` | select | domain/settings | REWORK | handler:settings.access_subsystem_pending pending terminal, sb/domain/settings/handlers.py:46-48 |
| `settings.access.select_scope` | select | domain/settings | REWORK | handler:settings.access_scope_pending pending terminal, sb/domain/settings/handlers.py:49-51 |

### domain/setup (25 — KEEP 13 · REWORK 11 · DROP 1)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `setup` | command | domain/setup | KEEP | goldens parity/goldens/setup/sweep_setup.json + quicksetup/sweep_slash_setup.json; tests tests/unit/setup_band/test_band1_setup.py; oracle-context.md:404-405 live-wired essential setup |
| `setup-hub` | command | domain/setup | DROP | oracle-context.md:440 — setup-hub marked legacy-duplicate (oracle-marked): 'Open the legacy section-list hub (compat)'; canonical surface is the !setup / /setup spine (oracle-context.md:582) |
| `setup-advanced` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-advanced.json; oracle-context.md:437 live-wired; slash/prefix twin of setupadvanced (fold candidate, inventory.md:248) — shipped-surface mirror, keep both |
| `setupadvanced` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_setupadvanced.json; oracle-context.md:436 live-wired prefix twin (same handler setup.advanced_open) |
| `setup-describe` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-describe.json; oracle-context.md:439 live-wired |
| `setupdescribe` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_setupdescribe.json; oracle-context.md:438 live-wired prefix twin (same handler setup.describe_entry) |
| `setup-status` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-status.json; oracle-context.md:447 live-wired |
| `setup-reset` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-reset.json; oracle-context.md:444 live-wired |
| `setup-skip` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-skip.json; oracle-context.md:442 live-wired |
| `setup-unskip` | command | domain/setup | KEEP | golden parity/goldens/setup/sweep_slash_setup-unskip.json; oracle-context.md:443 live-wired |
| `setup.hub` | panel | domain/setup | KEEP | spec sb/domain/setup/panels.py:162-186 (renderer setup.depth_render); tests tests/unit/setup_band/test_band1_setup.py; opened by setup-hub golden sweep_slash_setup-hub.json |
| `setup.hub.depth_quick` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 (docs/decisions.md:223 posture, wizard-lifecycle slice); docs/review/admin-surface-audit-2026-07-12.md:182-193 |
| `setup.hub.depth_standard` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.hub.depth_advanced` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.essential_card` | panel | domain/setup | KEEP | spec sb/domain/setup/panels.py:204-229 (renderer setup.essential_render); rendered live by !setup (handler setup.essential_open), golden parity/goldens/setup/sweep_setup.json |
| `setup.essential_card.essential_save` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.essential_card.essential_skip` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.essential_card.essential_kind` | select | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | on_select handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 (options provider setup.essential_kind_options is real) |
| `setup.status_card` | panel | domain/setup | KEEP | renderer setup.status_render (sb/domain/setup/panels.py); rendered by setup-status, golden parity/goldens/setup/sweep_slash_setup-status.json |
| `setup.suggestions_card` | panel | domain/setup | KEEP | spec sb/domain/setup/panels.py:267-302 (renderer setup.suggestions_render; :120-122 ports views/setup/ai_review/main_panel.py literals verbatim) — the LIVE oracle /setup-describe review panel, NOT the retired oracle-dead 'suggestions' wizard section; next's 10 sections (sb/domain/setup/sections.py:45-71) exclude all 7 retired slugs (oracle-context.md:568-571) |
| `setup.suggestions_card.accept_high_confidence` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.suggestions_card.review_one_by_one` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.suggestions_card.reject_ai_suggestions` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.suggestions_card.rerun_deterministic` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |
| `setup.suggestions_card.stage_final_review` | button | domain/setup | REWORK — with sibling lane: wizard-lifecycle slice (tonight's completeness-sweep sibling) | handler:setup.wizard_pending terminal, sb/domain/setup/panels.py:128-135 |

### domain/starboard (12 — KEEP 12)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `starboard` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard.json; handler sb/domain/starboard/handlers.py |
| `starboard.ignore` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard_ignore.json; handler sb/domain/starboard/handlers.py |
| `starboard.unignore` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard_unignore.json; handler sb/domain/starboard/handlers.py |
| `starboard.off` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard_off.json; handler sb/domain/starboard/handlers.py; test tests/unit/band6/test_live_channel_adapters.py |
| `starboard.selfstar` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard_selfstar.json; handler sb/domain/starboard/handlers.py |
| `starboard.panel` | command | domain/starboard | KEEP | golden parity/goldens/starboard/sweep_starboard_panel.json; test tests/unit/app/test_runtime_smoke.py |
| `starboard.config` | panel | domain/starboard | KEEP | register_panel spec sb/domain/starboard/panels.py |
| `starboard.config.starboard_threshold` | button | domain/starboard | KEEP | handler sb/domain/starboard/panels.py |
| `starboard.config.starboard_selfstar` | button | domain/starboard | KEEP | handler sb/domain/starboard/panels.py |
| `starboard.config.starboard_disable` | button | domain/starboard | KEEP | handler sb/domain/starboard/panels.py |
| `starboard.config.starboard_pick_channel` | select | domain/starboard | KEEP | handler sb/domain/starboard/panels.py |
| `starboard.config.starboard_toggle_ignore` | select | domain/starboard | KEEP | handler sb/domain/starboard/panels.py |

### domain/ticket (26 — KEEP 21 · REWORK 5)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `ticket` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket.json; test tests/unit/app/test_main_wiring.py |
| `ticket.new` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket_new.json; handler sb/domain/ticket/handlers.py; test tests/unit/app/test_main_wiring.py |
| `ticket.add` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket_add.json; handler sb/domain/ticket/handlers.py; test tests/unit/app/test_cut1_surfaces.py |
| `ticket.remove` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket_remove.json; handler sb/domain/ticket/handlers.py |
| `ticket.claim` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket_claim.json; handler sb/domain/ticket/handlers.py |
| `ticket.close` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticket_close.json; handler sb/domain/ticket/handlers.py; test tests/unit/namespace/test_validate.py |
| `ticketpanel` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketpanel.json |
| `ticketsetup` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketsetup.json |
| `ticketlimit` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketlimit.json; handler sb/domain/ticket/handlers.py |
| `ticketblacklist` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketblacklist.json; handler sb/domain/ticket/handlers.py; test tests/unit/band8/test_band8_ticket.py |
| `ticketblacklist.add` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketblacklist_add.json; handler sb/domain/ticket/handlers.py; test tests/unit/app/test_cut1_surfaces.py |
| `ticketblacklist.remove` | command | domain/ticket | KEEP | golden parity/goldens/ticket/sweep_ticketblacklist_remove.json; handler sb/domain/ticket/handlers.py |
| `ticket.hub` | panel | domain/ticket | KEEP | register_panel spec sb/domain/ticket/handlers.py |
| `ticket.hub.open_ticket` | button | domain/ticket | KEEP | handler sb/domain/ticket/handlers.py |
| `ticket.hub.open_ticket.ticket.open_form` | modal | domain/ticket | KEEP | inventory notes: 1 fields; on_submit=null; submit rides the opening action's handler (h |
| `ticket.hub.my_tickets` | button | domain/ticket | KEEP | handler sb/domain/ticket/handlers.py |
| `ticket.hub.post_panel` | button | domain/ticket | KEEP | handler sb/domain/ticket/handlers.py |
| `ticket.launcher` | panel | domain/ticket | KEEP | register_panel spec sb/domain/ticket/handlers.py |
| `ticket.launcher.launcher_open` | button | domain/ticket | KEEP | handler sb/domain/ticket/handlers.py |
| `ticket.launcher.launcher_open.ticket.launcher_open_form` | modal | domain/ticket | KEEP | inventory notes: 1 fields; on_submit=null; submit rides the opening action's handler (h |
| `ticket.setup` | panel | domain/ticket | KEEP | register_panel spec sb/domain/ticket/handlers.py |
| `ticket.setup.setup_autocreate_log` | button | domain/ticket | REWORK | inventory: custom pending fn sb.domain.ticket.handlers._register.<locals>.ticket_setup_pending (sb/domain/ticket/handlers.py); oracle-context.md:461 ticketsetup live-wired (ticket_cog.py) |
| `ticket.setup.setup_enable` | button | domain/ticket | REWORK | inventory: custom pending fn sb.domain.ticket.handlers._register.<locals>.ticket_setup_pending (sb/domain/ticket/handlers.py); oracle-context.md:461 ticketsetup live-wired (ticket_cog.py) |
| `ticket.setup.setup_post_panel` | button | domain/ticket | REWORK | inventory: custom pending fn sb.domain.ticket.handlers._register.<locals>.ticket_setup_pending (sb/domain/ticket/handlers.py); oracle-context.md:461 ticketsetup live-wired (ticket_cog.py) |
| `ticket.setup.setup_staff_role` | select | domain/ticket | REWORK | inventory: custom pending fn sb.domain.ticket.handlers._register.<locals>.ticket_setup_pending (sb/domain/ticket/handlers.py); oracle-context.md:461 ticketsetup live-wired (ticket_cog.py) |
| `ticket.setup.setup_log_channel` | select | domain/ticket | REWORK | inventory: custom pending fn sb.domain.ticket.handlers._register.<locals>.ticket_setup_pending (sb/domain/ticket/handlers.py); oracle-context.md:461 ticketsetup live-wired (ticket_cog.py) |

### domain/treasury (7 — KEEP 7)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `treasury` | command | domain/treasury | KEEP | golden parity/goldens/treasury/sweep_treasury.json; test tests/unit/spec/test_events.py |
| `treasury.contribute` | command | domain/treasury | KEEP | golden parity/goldens/treasury/sweep_treasury_contribute.json; handler sb/domain/treasury/ops.py; test tests/unit/band3/test_band3_panel_actions.py |
| `treasury.grant` | command | domain/treasury | KEEP | no golden (capture-skipped: treasury TTL cache, inventory.md:268); route workflow:treasury.disburse sb/domain/treasury/ops.py; tests: tests/unit/band3/test_band3_treasury_inventory.py, tests/unit/band6/test_live_channel_adapters.py |
| `treasury.hub` | panel | domain/treasury | KEEP | register_panel spec sb/domain/treasury/panels.py |
| `treasury.hub.contribute` | button | domain/treasury | KEEP | handler sb/domain/treasury/ops.py |
| `treasury.hub.contribute.treasury.contribute_form` | modal | domain/treasury | KEEP | handler sb/domain/treasury/ops.py |
| `treasury.hub.refresh` | button | domain/treasury | KEEP | test tests/unit/band2/test_band2_slice2.py |

### domain/utility (33 — KEEP 27 · REWORK 3 · DROP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `utilitymenu` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_utilitymenu.json; handler utility.menu_view (prefix twin of /utility — deliberate shipped pair, fold candidate noted) |
| `utility` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_slash_utility.json; handler utility.menu_view (slash) |
| `ping` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_ping.json; handler utility.ping_view |
| `avatar` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_avatar.json; handler utility.avatar_view (oracle: hidden-classified but distinct function + registry entry_point) |
| `serverinfo` | command | domain/utility | DROP | oracle-context: 'serverinfo — Alias for !info server' — legacy-duplicate (oracle-marked), hidden=True (utility_cog.py); next handler utility.server_info_view duplicated by !info + utility.panel.server_info button |
| `myprofile` | command | domain/utility | KEEP | 2 goldens utility/sweep_myprofile.json + sweep_slash_myprofile.json; handler utility.myprofile_view |
| `botinfo` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_botinfo.json; handler utility.botinfo_view |
| `info` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_info.json; handler utility.info_view (sb/domain/utility/handlers.py:330); tests/unit/band2/test_band2_slice1.py |
| `userinfo` | command | domain/utility | DROP | oracle-context: 'userinfo — Alias for !info user [@member]' — legacy-duplicate (oracle-marked), hidden=True; next has THREE overlapping surfaces (info_view, userinfo_view, user_info_view button) |
| `membercount` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_membercount.json; handler utility.membercount_view |
| `poll` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_poll.json; handler utility.poll_view (sb/domain/utility/handlers.py:354) |
| `remind` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_remind.json; handler utility.remind_view (handlers.py:375) |
| `invite` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_invite.json; handler utility.invite_view (handlers.py:400); tests/unit/parity_adapter/test_utility_capture.py PASS |
| `clear` | command | domain/utility | KEEP | golden parity/goldens/utility/sweep_clear.json; handler utility.clear_view |
| `utility.panel` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:114 (utility_panel_spec); tests/unit/parity_adapter/test_utility_capture.py PASS |
| `utility.panel.server_info` | button | domain/utility | KEEP | sb/domain/utility/panels.py:126; handler utility.server_info_view (real, handlers.py:163) |
| `utility.panel.user_info` | button | domain/utility | KEEP | sb/domain/utility/panels.py:131; handler utility.user_info_view (real, handlers.py:169) |
| `utility.panel.avatar` | button | domain/utility | KEEP | sb/domain/utility/panels.py:136; handler utility.avatar_view; tests/unit/parity_adapter/test_utility_capture.py PASS |
| `utility.panel.poll` | button | domain/utility | REWORK | sb/domain/utility/panels.py:145; handler utility.poll_pending while !poll (utility.poll_view, handlers.py:354) is live + golden-backed |
| `utility.panel.remind` | button | domain/utility | REWORK | sb/domain/utility/panels.py:149; handler utility.remind_pending while !remind (utility.remind_view, handlers.py:375) is live + golden-backed |
| `utility.panel.invite` | button | domain/utility | REWORK | sb/domain/utility/panels.py:153; handler utility.invite_pending while !invite (utility.invite_view, handlers.py:400) is live, golden-backed and ARGLESS |
| `utility.panel.utility_overview` | button | domain/utility | KEEP | sb/domain/utility/panels.py:158; nav -> panel:utility.panel |
| `utility.panel.open_general` | button | domain/utility | KEEP | sb/domain/utility/panels.py:179 layout row; nav -> panel:general.menu (real) |
| `utility.panel.open_four_twenty` | button | domain/utility | DROP | sb/domain/utility/panels.py:179 layout row; handler utility.four_twenty_pending — a pending terminal while panel:four_twenty.overview is fully real (5/5 components, golden four_twenty/sweep_420.json) |
| `utility.pong` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:205 (pong_spec); render terminal of golden-backed !ping |
| `utility.avatar_card` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:209; render terminal of golden-backed !avatar |
| `utility.server_info` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:213; render terminal for server_info_view (button + !info server) |
| `utility.user_info` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:217; render terminal for user_info_view |
| `utility.profile_card` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:221; tests/unit/parity_adapter/test_utility_capture.py PASS |
| `utility.bot_info` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:225; render terminal of golden-backed !botinfo |
| `utility.member_census` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:231; render terminal of golden-backed !membercount |
| `utility.user_card` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:237; render terminal of golden-backed !userinfo/!info user |
| `utility.error_card` | panel | domain/utility | KEEP | spec sb/domain/utility/panels.py:246; tests/unit/parity_adapter/test_utility_capture.py PASS |

### domain/ux_lab (11 — DROP 11)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `uxlab` | command | domain/ux_lab | DROP | golden parity/goldens/ux_lab/sweep_uxlab.json; oracle-context.md:484-485 uxlab admin-gated lab |
| `ux_lab.home` | panel | domain/ux_lab | DROP | register_panel spec sb/domain/ux_lab/ (renderer handler:ux_lab.render_home); oracle-context.md:484-485 uxlab admin-gated lab |
| `ux_lab.home.buttons` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.selects` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.modals` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.embeds` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.components_v2` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.pil_cards` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.mock_studio` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.probe_bench` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |
| `ux_lab.home.compare` | button | domain/ux_lab | DROP | inventory: handler ux_lab.*_wing -> operator_spine pending terminal; oracle-context.md:484 uxlab = admin-only interface lab |

### domain/welcome (3 — KEEP 3)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `welcome` | command | domain/welcome | KEEP | golden parity/goldens/welcome/sweep_welcome.json; tests tests/unit/band2/test_band2_slice2.py; oracle-context.md:486 primary entrypoint |
| `welcome.hub` | panel | domain/welcome | KEEP | ensure_hub('welcome') sb/manifest/welcome.py:18 -> sb/domain/operator_spine.py:96 hub_spec; nav target of the landed settings-hub group select (control/claims/operator-hubs-interactive.md); tests tests/unit/band6/test_band6_settings_panels.py |
| `welcome.status` | panel | domain/welcome | KEEP | renderer sb/domain/welcome/panels.py:43 (welcome.status_render); byte-pinned via parity/goldens/welcome/sweep_welcome.json (welcome routes panel:welcome.status) |

### domain/xp (20 — KEEP 16 · REWORK 4)

| id | kind | subsystem | verdict | evidence |
|---|---|---|---|---|
| `xpmenu` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_xpmenu.json |
| `rank` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_rank.json; +1 more golden(s); test tests/unit/app/test_cut1_surfaces.py |
| `givexp` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_givexp.json; test tests/unit/band4/test_band4_xp.py |
| `resetxp` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_resetxp.json; test tests/unit/band4/test_band4_xp.py |
| `xpconfig` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_xpconfig.json |
| `xpimport` | command | domain/xp | KEEP | golden parity/goldens/xp/sweep_xpimport.json |
| `xp.hub` | panel | domain/xp | KEEP | panel spec sb/manifest/xp.py:129 |
| `xp.hub.rank` | button | domain/xp | KEEP | test tests/unit/ai/test_k10_orchestration.py; component spec/handler sb/manifest/xp.py:133 |
| `xp.hub.config` | button | domain/xp | KEEP | test tests/unit/rollback/test_s14_rollback.py; component spec/handler sb/domain/xp/panels.py:189 |
| `xp.hub.givexp` | button | domain/xp | KEEP | test tests/unit/band4/test_band4_xp.py; component spec/handler sb/manifest/xp.py:137 |
| `xp.hub.givexp.xp.givexp_form` | modal | domain/xp | KEEP | test tests/unit/band4/test_band4_community.py; modal spec sb/domain/xp/panels.py:56 |
| `xp.hub.resetxp` | button | domain/xp | KEEP | test tests/unit/band4/test_band4_xp.py; component spec/handler sb/manifest/xp.py:141 |
| `xp.hub.resetxp.xp.resetxp_form` | modal | domain/xp | KEEP | test tests/unit/band4/test_band4_community.py; modal spec sb/domain/xp/panels.py:69 |
| `xp.rank_card` | panel | domain/xp | KEEP | panel spec sb/domain/xp/panels.py:334 |
| `xp.config` | panel | domain/xp | KEEP | panel spec sb/domain/xp/panels.py:243 |
| `xp.config.xp_range` | button | domain/xp | REWORK | pending terminal (label='XP Range'; handler handler:xp.config_range_pending -> pending_handler ter); spec sb/domain/xp/panels.py:256; oracle xpconfig leg live-wired (oracle-context.md xp_cog) |
| `xp.config.xp_cooldown` | button | domain/xp | REWORK | pending terminal (label='Cooldown'; handler handler:xp.config_cooldown_pending -> pending_handler ); spec sb/manifest/xp.py:92; oracle xpconfig leg live-wired (oracle-context.md xp_cog) |
| `xp.config.xp_levelup_channel` | button | domain/xp | REWORK | pending terminal (label='Level-up Channel'; handler handler:xp.config_channel_pending -> pending_h); spec sb/domain/xp/panels.py:266; oracle xpconfig leg live-wired (oracle-context.md xp_cog) |
| `xp.config.xp_import` | button | domain/xp | REWORK | pending terminal (label='📥 Import from another bot'; handler handler:xp.import_setup_pending -> pe); spec sb/domain/xp/panels.py:271; oracle xpconfig leg live-wired (oracle-context.md xp_cog) |
| `xp.import_scan` | panel | domain/xp | KEEP | panel spec sb/domain/xp/panels.py:307 |

## DROP — proposed retirements (report-only; nothing deleted)

**60 items.** Every DROP here is a *proposal*: this report
deletes nothing, and per the audit discipline the golden-corpus changes these
folds imply are owner-ratifiable. Grouped where the rationale is shared.

### btd6 flat legacy alias tree (33)

- `btd6ref`, `btd6ref.tower`, `btd6ref.hero`, `btd6ref.round`, `btd6ref.income`, `btd6ref.rbe`, `btd6ref.relic`, `btd6ref.ct` — Flat compat alias twin of the canonical dotted `btd6 ref <sub>` tree; oracle self-classifies the btd6ref cog legacy_duplicate + hidden — redundant surface, fold into the dotted tree (report-only)
- `btd6strat`, `btd6strat.browse`, `btd6strat.mine`, `btd6strat.strategy`, `btd6strat.strategy-audit`, `btd6strat.submit`, `btd6strat.pending`, `btd6strat.strategies`, `btd6strat.why-no-response` — Flat compat alias twin of the canonical dotted `btd6 strat <sub>` tree; oracle self-classifies the btd6strat cog legacy_duplicate + hidden — redundant surface, fold into the dotted tree (report-only)
- `btd6events`, `btd6events.live`, `btd6events.event`, `btd6events.leaderboard`, `btd6events.sources`, `btd6events.source-health`, `btd6events.latest-data`, `btd6events.refresh-source`, `btd6events.grounding` — Flat compat alias twin of the canonical dotted `btd6 events <sub>` tree; oracle self-classifies the btd6events cog legacy_duplicate + hidden — redundant surface, fold into the dotted tree (report-only)
- `btd6ops`, `btd6ops.readiness`, `btd6ops.runs`, `btd6ops.source_enable`, `btd6ops.source_disable`, `btd6ops.seed-data`, `btd6ops.announcechannel` — Flat compat alias twin of the canonical dotted `btd6 ops <sub>` tree; oracle self-classifies the btd6ops cog legacy_duplicate + hidden — redundant surface, fold into the dotted tree (report-only)

### ux_lab — entire surface parked (11)

- `uxlab`, `ux_lab.home` — Opener of a dead gallery — all 9 wings land on pending terminals; internal admin lab, not member-facing — park entire surface, revive a wing only when a concrete UX experiment needs it (report-only)
- `ux_lab.home.buttons`, `ux_lab.home.selects`, `ux_lab.home.modals`, `ux_lab.home.embeds`, `ux_lab.home.components_v2`, `ux_lab.home.pil_cards`, `ux_lab.home.mock_studio`, `ux_lab.home.probe_bench`, `ux_lab.home.compare` — Wing button is a pending terminal (9/9 wings pending); internal admin lab surface with no member-facing value — park with the lab (report-only)

### deploy-ops terminals (admin cogmgr/reload_all; ruled at docs/decisions.md:223) (7)

- `admin.hub.reload_all` — deploy-op pending terminal whose command class is ruled unported (docs/decisions.md:223: subsystems are compiled manifests, not runtime-loadable cogs) — the button can never arm
- `admin.cogmgr.cogmgr_load`, `admin.cogmgr.cogmgr_unload`, `admin.cogmgr.cogmgr_reload` — deploy-op ruled unported (docs/decisions.md:223) — no compiled-architecture analog; pending terminal can never arm
- `admin.cogmgr.cogmgr_prev`, `admin.cogmgr.cogmgr_next` — pager windows the deploy-ops select; falls with the deploy-ops drop (docs/decisions.md:223) (returns only if the manifest-registry re-home needs >1 page)
- `admin.cogmgr.cogmgr_select` — exists only to arm the deploy-ops-dropped trio (docs/decisions.md:223); falls with it (a registry re-home may re-purpose it — see admin.cogmgr rework)

### redundant prefix menu twins of BOTH-kind commands (2)

- `adminmenu` — redundant prefix twin of `admin` (BOTH already covers !admin + /admin); fold to aliases=('adminmenu',) on the admin spec so the name stays callable and the golden re-points — oracle keeps adminmenu only as its registry entry_point (oracle-context: adminmenu = registry entry_point)
- `modmenu` — redundant prefix twin of `moderation` (BOTH covers !moderation + /moderation); fold to alias so !modmenu stays callable — sb/domain/help/categories.py:69 cites '!modmenu' as the hub_command and the golden pins its bytes, so alias-fold not deletion

### oracle-marked legacy_duplicate command aliases (3)

- `mineinv` — oracle-marked legacy_duplicate of !inventory; handler is a pure pass-through — fold mineinv/mineinventory into aliases of the inventory command and retire the duplicate declaration + sweep_mineinv golden (report-only)
- `serverinfo` — oracle-marked legacy_duplicate of !info server; fold name to an alias of !info and retire the duplicate command declaration (handler stays for the panel button); report-only. NOTE oracle inconsistency: serverinfo is still a registry entry_point — flag to owner
- `userinfo` — oracle-marked legacy_duplicate of !info user; fold to alias of !info, retire duplicate declaration + unify userinfo_view/user_info_view handlers; report-only

### role legacy compat surfaces (2)

- `rolemenu` — Redundant 4th surface onto panel:role.hub; oracle self-classifies it legacy_duplicate+hidden. roles (canonical) + rolesettings (live alias) remain. Report-only; note the oracle inconsistency that rolemenu is still the oracle role-subsystem registry entry_point (oracle-context.md:583-584) — owner call before pruning the golden sweep_rolemenu.json.
- `rolecreator` — Redundant 4th surface onto panel:role.hub; oracle self-classifies it legacy_duplicate+hidden with no entry_point role. Report-only; golden sweep_rolecreator.json is the only artifact keeping it.

### setup legacy compat opener (1)

- `setup-hub` — Oracle self-classifies setup-hub as the legacy compat section-list opener; next ports it verbatim (handler setup.hub_open) purely for parity. Report-only; golden parity/goldens/setup/sweep_slash_setup-hub.json is the retained artifact — pruning is owner-ratifiable corpus change per docs/review/admin-surface-audit-2026-07-12.md §8 discipline.

### pending duplicate of a fully-real panel (1)

- `utility.panel.open_four_twenty` — known lead confirmed: duplicates the real four_twenty subsystem behind a pending refusal; drop the pending handler — if the nav is wanted, it is a one-line nav -> panel:four_twenty.overview, not a port (report-only)

## REWORK — consolidated fix list

**110 rows, three tiers.**

### (a) Shipping tonight — curation-rework PRs

Contained wiring fixes with the target already live in-tree; each bundle is
one PR (branch + PR number below).

1. **nav-wiring bundle** — branch `claude/curation-rework-nav-wiring`,
   PR #332: `server_management.hub.moderation` / `.roles` / `.cleanup` →
   nav to the live moderation/role/cleanup hubs (Channels-button pattern,
   sb/domain/server_management/panels.py:163-173); `mining.workshop.ws_back`
   → nav to panel:mining.hub (one-liner, sb/domain/mining/panels.py:759);
   `utility.panel.invite` → point at the live argless utility.invite_view
   handler (one-liner, sb/domain/utility/panels.py:153).
2. **cleanup-words bundle** — branch `claude/curation-rework-cleanup-words`,
   PR #333: `cleanup.words.word_add` / `.word_remove` → button→modal→
   live workflow twins (moderation warn precedent,
   sb/domain/moderation/panels.py:132-138); `cleanup.words.scan_history` →
   handler:cleanup.history_scan; `cleanup.words.word_refresh` →
   REFRESH_PANEL one-liner; `cleanup.hub.logging` → nav PanelRef
   logging.hub (subsystem landed).
3. **btd6-paragon bundle** — branch `claude/curation-rework-btd6-paragon`,
   PR #336: wire `btd6.paragon.calc` / `.requirements` / `.stats` +
   the 4 selectors (`paragon`/`players`/`difficulty`/`tier5`) to the
   already-ported math (sb/domain/btd6/paragon_math.py +
   paragon_degrees.py), replacing paragon_pending refs in
   sb/domain/btd6/panels.py:348-403 (named successor per docs/decisions.md:347).

### (b) With sibling lane — coordinate, do not double-land

Each row is marked in the main table with its lane; the lanes:

- **fishing-port lane** (claim control/claims/fishing-port-remaining.md,
  slices 2-4): 13 pending fishing commands (rod, bait, craftbait, craftcharm,
  craftrod, rodrecipes, craftpearl, curios, craftcurio, tidepool, dock,
  boathouse, fishery) + 4 fishing.hub buttons (rod/bait/structures/rules).
- **mining-write-parity WP-2 (PR #312):** stash, unstash, vaultupgrade
  write goldens; vault va_deposit/va_withdraw ingress lands after its
  stash_write golden freezes the contract.
- **mining-write-parity WP-3 folds WP-4 (PR #317):** descend, ascend,
  mineworld, repair, quickcraft write goldens.
- **mining-write-parity WP-5 (planned, claimed):** skill allocate/respec +
  the 5 mining.skills buttons.
- **mining-write-parity WP-6 (planned, claimed):** build / forge fo_build /
  home ho_build / workshop ws_craft (shared atomic craft implementation).
- **energy lane (PR #320,** docs/scoping/energy-system-scope.md**):** cook,
  use — BLOCKED terminals verified at sb/domain/mining/service.py:895 and
  :912; later energy slices wire them.
- **settings-mutation slice** (PARKed by
  docs/review/admin-surface-audit-2026-07-12.md): the 5 settings.hub
  diagnostics buttons (needs_setup, invalid, missing_bindings, audit,
  command_access).
- **wizard-lifecycle slice** (tonight's completeness-sweep sibling): the 11
  setup wizard interactions (3 depth buttons, essential-card save/skip/kind,
  5 suggestions-card actions) — all one setup.wizard_pending terminal,
  sb/domain/setup/panels.py:128-135.
- **operator_spine stub sweep** (core/admin/setup completeness sibling): the
  5 channel.hub buttons (create/delete/move/restrict wire to already-real
  golden-backed typed handlers; visibility has no typed twin).
- **completeness-sweep sibling (core/admin/setup stubs):** diagnostic hub
  diag_status/diag_sysinfo/diag_errors (arm as live process-state reads),
  diagnostic.command_list cmdlist_prev/cmdlist_next pager, admin.cogmgr
  panel re-home onto the manifest registry read.
- **Gap finding (not an inventory row): `/setup-depth`** — golden
  `setup/sweep_slash_setup-depth.json` exists, oracle /setup-depth is
  live-wired, but next declares no such command. REWORK, with sibling
  (wizard-lifecycle / completeness sweep): declare the slash CommandSpec in
  sb/manifest/setup.py or park the golden under `_unmapped` with a skip
  ruling. (Per C4+C6; oracle also live-wires /setup-delegate and
  /setup-undelegate, same family.)

### (c) Backlog — one line each

- **`pay`** — mint the funded !pay transfer golden via parity/cases/curated.py + capture (only manifest command with neither golden nor skip ruling); sibling-flagged on the parity corpus count-pin — land after mining WP PRs #312/#317.
- **farm goldens** — click-golden batch (mint procedure per docs/decisions.md:542) for farm_collect / farm_buy_hen / farm_upgrade_coop money paths — rows reconciled KEEP on the split-verdict rule, the golden gap stays a real backlog item.
- **`rps_tournament.quickplay`** — mint the bet-settle interaction golden (!rps 10 → move → escrow settle), extends the tournament-flow goldens lane (procedure per docs/decisions.md:542).
- **`leaderboard`** — report-only alias fold: trim the oracle-marked legacy_duplicate 11-alias tuple (sb/manifest/leaderboard.py:27-30); command itself KEEP.
- **xp.config ×4** — port the xp config mutation legs (xp_range / xp_cooldown / xp_levelup_channel / xp_import) in sb/domain/xp — oracle xpconfig legs are live-wired; one contained slice.
- **ticket.setup ×5** — implement the ticket setup panel actions (enable, staff-role, log-channel, autocreate-log, post-panel) in sb/domain/ticket/handlers.py replacing ticket_setup_pending; oracle ticketsetup is live-wired.
- **`role.hub.role_create`** — wire the Create button to the existing live createrole lane (modal → handler:role.createrole).
- **`counterpreset`** — port the preset-apply branch (the one `partial` row in the inventory) with the channel-ops slice, replacing counters.preset_pending.
- **settings.access ×6 (access-map explorer)** — governance-diagnostic slice named by the pending copy itself (sb/domain/settings/handlers.py:46-61): explain/reset/prev/next buttons + subsystem/scope selects.
- **`server-management`** — name-pair regularization with `server_management` (fold to one CommandSpec if the grammar grows a slash-name field, else ledger as deliberate) + unify the split golden directories.
- **`mine` + `mining.hub.mi_mine`** — port the grid Mine navigator (deep-systems successor lane per docs/decisions.md:326, NOT yet claimed); !mine currently returns the capture-pinned BLOCKED byte (sb/domain/mining/service.py:198); interim !fastmine carries the swing.
- **`mining.hub.mi_how_to`** — static how-to copy port from the oracle mining hub (no DB, no golden dependency).
- **utility.panel poll/remind ×2** — modal ingress collecting args, then delegate to the live utility.poll_view / utility.remind_view ops.
- **`btd6.ctteam.set_team`** — modal feeding the existing typed ctteam set leg (sb/domain/btd6/oracle_surface.py cmd_ctteam).

## Honest nulls

**No NOT-MEASURED rows.** Every one of the 1088 inventory rows received
an evidenced verdict; the chunk-assignment reconciliation found zero
coverage gaps. (Rows whose goldens are capture-skipped by ruling — e.g.
`catch` unseeded RNG, `treasury.grant` TTL cache, /ai diagnostics
settle-budget race — are KEEP on test/source evidence and annotated as
such in the table, not nulled.)

