# grammar_fit RESULTS (V-2 cumulative ledger)

Cumulative fit: **89.54%** tier-1/2 over 545 units (spike line: 85.26% / 95 units).

| band | subsystem | kind | unit | xN | tier | rationale |
|---|---|---|---|---|---|---|
| 1 | settings | command | settings | 1 | 1 | kernel resolve() + open-panel route (PanelRef settings.hub) — zero domain code |
| 1 | settings | panel | settings.hub | 1 | 1 | generated hub read-view over the K7 declaration registry (projections family) |
| 1 | settings | store | settings | 1 | 2 | StoreSpec data (NAME_STABLE, AGGREGATE) — schema derived, fences generated |
| 1 | settings | store | subsystem_bindings | 1 | 2 | StoreSpec data (RENAME via BindingSpec.legacy_settings_key_aliases) |
| 1 | settings | event | settings.changed | 1 | 2 | EventSpec data (shipped name verbatim, BEST_EFFORT advisory) |
| 1 | settings | handler | scalar/binding lane legs | 4 | 3 | thin conn-threaded DB legs behind K7 CompoundOpSpecs — domain seam by design |
| 1 | settings | provider | settings.hub_index | 1 | 3 | registered read-model provider (hub index) — thin, justified |
| 1 | settings | engine | settings.store | 1 | 3 | sole-writer EngineRef marker for the two tables — physical authority, by design |
| 2 | moderation | command | modmenu/moderation/warn/timeout/kick/ban/unban/clearwarnings/warnings/modlogs | 10 | 1 | CommandSpec verbatim; group field minted for K1 parent_group |
| 2 | moderation | op | warn/timeout/kick/ban/unban/clearwarnings | 6 | 1 | CompoundOpSpec DB+EFFECT legs fit; reversibility rollup honest |
| 2 | moderation | store | mod_logs/warnings | 2 | 2 | StoreSpec NAME_STABLE + MEMBER_ID erasure refs |
| 2 | moderation | event | moderation.action_taken | 1 | 2 | EventSpec BEST_EFFORT; payload schema declared |
| 2 | moderation | panel | moderation.hub | 1 | 2 | read-view hub over provider block |
| 2 | moderation | port | GuildModerationActions | 1 | 3 | domain-minted Discord state-mutation port (RC-21 sibling) |
| 2 | logging | command | logging (+7 group subcommands) | 8 | 1 | CommandSpec.group carries the shipped prefix group |
| 2 | logging | setting | 12 scalar keys + 6 channel bindings | 18 | 1 | SettingSpec/BindingSpec slices verbatim from keys.py |
| 2 | logging | handler | status/enable/disable/set/routes/test/create | 7 | 2 | thin HandlerRef routes over the settings K7 ops |
| 2 | logging | engine | moderation fan-out subscriber | 1 | 2 | bus-subscribed router through the RC-21 emitter |
| 2 | operator-eight | command | shipped surfaces declared verbatim (admin 7, channel 17, cleanup 7, +1 each x5) | 36 | 1 | CommandSpec + group/aliases carry every shipped name |
| 2 | operator-eight | setting | automod 15 / security 9+2 / welcome 10+2 / counters 4+3 / image_mod 8 / cleanup 1 | 54 | 1 | SettingSpec/BindingSpec slices verbatim; activations declared |
| 2 | operator-eight | panel | 9 generated hub read-views | 9 | 2 | one shared projection factory over the declaration registry |
| 2 | operator-eight | engine | automod rules / raid window / age gate / templates x2 | 5 | 1 | pure decision cores, injectable clock |
| 2 | operator-eight | op | cleanup word add/remove | 2 | 1 | NATURAL_KEY DB lanes |
| 2 | operator-eight | handler | admin kernel-truth reads + pending terminals | 9 | 2 | manifest-registry/lifecycle re-homes; declared-not-armed refusals |
| 3 | economy | command | economymenu/economy/daily/work/shop/balance/pay/setlogchannel/joblist | 9 | 1 | CommandSpec verbatim (aliases bal/wallet/transfer/jobs; G-4 cooldowns as data) |
| 3 | economy | op | daily/work/pay/buy | 4 | 1 | CompoundOpSpec NATURAL_KEY lanes; balance+ledger one txn (CRIT-9/INV-F) |
| 3 | economy | store | economy_balances/economy_audit_log/economy/job_progress/inventory | 5 | 2 | StoreSpec data (RENAME aggregate + NAME_STABLE ledger; MEMBER_ID erasure refs) |
| 3 | economy | event | economy.balance_changed | 1 | 2 | EventSpec BEST_EFFORT verbatim; pay emits two payload builders |
| 3 | economy | invariant | economy.balance_ledger_reconciliation | 1 | 2 | InvariantSpec RECONCILIATION QUARANTINE_ONLY (Q-D13) — declared data |
| 3 | economy | panel | economy.hub | 1 | 2 | read-view hub over provider block |
| 3 | economy | data | JOBS/SHOP_ITEMS/DAILY_TIERS/ITEM_CATALOGUE | 4 | 2 | pure data tables verbatim; the coupled item namespace + fence |
| 3 | economy | port | install_level_reader/install_xp_awarder | 2 | 3 | the band-4 XP boundary — honest waiting ports, never fabricated levels |
| 3 | economy | engine | reverse importers x2 + log fan-out | 3 | 3 | S14 ledger/aggregate importer bodies + bus->RC-21 emitter subscriber |
| 3 | treasury | command | treasury/contribute/grant (aliases bank/pool/donate/deposit/disburse/payout) | 3 | 1 | CommandSpec.group carries the shipped prefix group; staff tier = shipped manage_guild |
| 3 | treasury | op | contribute/disburse | 2 | 1 | CompoundOpSpec NATURAL_KEY; pool leg + economy ledger row one txn (RS02/Q-0071) |
| 3 | treasury | store | guild_treasury | 1 | 2 | StoreSpec NAME_STABLE AGGREGATE bears_value; S14 aggregate reverse importer |
| 3 | treasury | invariant | treasury.pool_ledger_reconciliation | 1 | 2 | InvariantSpec RECONCILIATION QUARANTINE_ONLY over pool x treasury:* ledger rows |
| 3 | treasury | panel | treasury.hub | 1 | 2 | read-view hub over provider block |
| 3 | inventory | command | inventory (inv) | 1 | 1 | CommandSpec verbatim; projection-first unified browser |
| 3 | inventory | panel | inventory.hub | 1 | 2 | read-view hub over the coupled item catalogue |
| 3 | inventory | engine | grouping/rarity/sort pure helpers | 3 | 2 | shipped display algebra verbatim as pure functions |
| 3 | inventory | port | install_extra_inventory_source | 1 | 3 | the band-6 mining/fishing merge seam — honest waiting port |
| 3 | economy | action | hub daily/work/shop/balance/inventory/jobs/treasury/overview | 8 | 1 | PanelActionSpec data — shipped custom_ids pinned verbatim; kernel-generated callbacks |
| 3 | economy | selector | jobcenter job_select + shop item_select | 2 | 1 | SelectorSpec over the audited economy.work/economy.buy ops; provider/static options |
| 3 | economy | panel | economy.jobcenter + economy.shop_panel | 2 | 2 | declared sub-panels (the shipped _WorkSubView/_ShopSubView) — nav serialized, closures gone |
| 3 | treasury | action | contribute (G-10 modal) + refresh | 2 | 1 | PanelActionSpec + ModalSpec data — the shipped one-field modal as declared form |
| 3 | inventory | action | hub open-category x7 | 7 | 1 | PanelActionSpec -> open-child PanelRefs over the static category population |
| 3 | inventory | panel | category detail panels x7 | 7 | 2 | ListBlock + declared sort/filter algebra; interactive re-sort waits on the BrowserView engine (D-0034) |
| 4 | xp | command | xpmenu/rank/givexp/resetxp/xpconfig/xpimport | 6 | 1 | CommandSpec verbatim; admin floor as tier data (shipped @admin_or_owner) |
| 4 | xp | op | award/reset/import_levels/repair_level_consistency | 4 | 1 | CompoundOpSpec NATURAL_KEY lanes (INV-G one audited seam; reset carries §2.7 confirm) |
| 4 | xp | store | xp | 1 | 2 | StoreSpec RENAME (the coins-split complement) bears_value; S14 aggregate importer |
| 4 | xp | event | xp.awarded/xp.level_up/xp.reset | 3 | 2 | EventSpec BEST_EFFORT verbatim; level_up CONDITIONAL via the D-0036 None-payload skip |
| 4 | xp | invariant | xp.level_consistency | 1 | 2 | InvariantSpec ROW_PREDICATE REPAIRABLE (level := level_progress(xp), deterministic) |
| 4 | xp | panel | xp.hub | 1 | 2 | provider-fed hub + Give/Reset G-10 modals over the audited ops |
| 4 | xp | engine | chat hot path + level-up fan-out + import parse core | 3 | 3 | cooldown+gate+rng -> K7 run; bus->RC-21 announce; announcer-format regex tables |
| 4 | xp | port | participation gate/role granter/history scanner + economy fills | 4 | 3 | the D-0031 waiting ports FILLED (level reader + xp awarder); 3 new honest waits |
| 4 | karma | command | thanks/karma/karma add//karma | 4 | 1 | CommandSpec verbatim (aliases rep/thank; group=karma; slash ephemeral) |
| 4 | karma | op | give | 1 | 1 | CompoundOpSpec NATURAL_KEY (INV-K: credit+given+audit ONE txn; ladder in-leg) |
| 4 | karma | store | karma/karma_audit_log | 2 | 2 | StoreSpec NAME_STABLE aggregate+ledger, both REVERSE_IMPORTABLE (mutation_id minted) |
| 4 | karma | event | karma.granted | 1 | 2 | EventSpec BEST_EFFORT verbatim payload keys |
| 4 | karma | invariant | karma.points_ledger_reconciliation | 1 | 2 | InvariantSpec RECONCILIATION QUARANTINE_ONLY (the D-0031 value posture) |
| 4 | karma | setting | enabled/cooldown_seconds/daily_cap/reaction_emoji | 4 | 2 | SettingSpec data — defaults pinned == policy constants (no-drift invariant) |
| 4 | karma | engine | react-to-thank core | 1 | 3 | policy fast-gate -> the SAME audited op; silent-on-block by design |
| 4 | community | command | community (prefix+slash) | 2 | 1 | router-only hub, shipped posture (zero business logic) |
| 4 | community | panel | community.hub | 1 | 2 | pure navigation actions (XP/Karma/Leaderboards/Spotlight) |
| 4 | leaderboard | command | leaderboard + 11 shipped aliases | 1 | 1 | CommandSpec verbatim (Q-A03 legacy_duplicate routes stay callable) |
| 4 | leaderboard | panel | leaderboard.board | 1 | 2 | PROVIDER-FED category selector — band-6 categories appear with zero edits |
| 4 | leaderboard | engine | rank provider registry (xp/coins/karma) | 3 | 3 | the shipped PR-G registry headless; register-a-provider extension seam |
| 4 | community_spotlight | command | spotlight (activity) | 1 | 1 | CommandSpec verbatim |
| 4 | community_spotlight | panel | community_spotlight.hub + games | 2 | 2 | provider-fed overview + the games selector's honest band-6 empty state |
| 4 | community_spotlight | engine | level-up feed subscriber | 1 | 3 | the xp.level_up -> spotlight DECLARED consumption; bounded deque verbatim |
| 5 | governance | setting | governance settings slice | 3 | 2 | SettingSpec x3 (governance_version + the two tier-grant role ids) |
| 5 | governance | store | governance stores | 5 | 2 | StoreSpec x5 (visibility/cleanup/audit/cap-overrides/templates) + 0016 |
| 5 | governance | event | governance.* events | 5 | 2 | EventSpec x5, compat-frozen names (events.py: Do NOT rename after v1) |
| 5 | governance | op | governance K7 lanes | 4 | 2 | CompoundOpSpec x4 — the shipped GovernanceMutationPipeline as lanes |
| 5 | governance | engine | scope-chain resolver + TTL override cache | 2 | 3 | resolve_visibility/resolve_execution verbatim; the chain walk and staleness bounds are runtime semantics no grammar expresses |
| 5 | governance | engine | subsystem registry data + tier taxonomy | 2 | 2 | SUBSYSTEM_META 43 rows + PermissionTier metadata = declared data |
| 5 | governance | engine | port fills (K6 override/role-binding, K8 visibility) | 3 | 3 | install_authority_ports — the S7/S9 waiting-port bodies |
| 5 | role | command | role commands + aliases | 17 | 1 | CommandSpec verbatim (roles/setrole/reactroles/temprole family) |
| 5 | role | panel | role.hub (7 shipped buttons, ids pinned) | 1 | 2 | PanelSpec + custom_id_override role:create…role:exemptions |
| 5 | role | setting | role settings slice | 4 | 2 | SettingSpec x4 (skip_roles + the two stack toggles + rr enable) |
| 5 | role | store | role stores | 8 | 2 | StoreSpec x8 (thresholds/reaction/modes/menus/options/grants/pickup/exemptions) + 0017 |
| 5 | role | op | role K7 lanes | 12 | 2 | CompoundOpSpec x12 incl. the grant EFFECT+compensator pair |
| 5 | role | task | role:grants_expiry | 1 | 2 | ManagedTaskSpec (A-8 consumer; shipped 5-min loop as Interval) |
| 5 | role | engine | time/XP planners + feasibility + apply | 4 | 3 | compute_assignments/plan_level_role_assignments/evaluate_role/classified apply — pure decision cores verbatim |
| 5 | role | engine | reaction runtime + xp-port fill | 2 | 3 | handle_reaction_add/remove modes; install_xp_ports fills the D-0031/D-0036 level-role granter |
| 5 | platform | store | command-access stores | 2 | 2 | StoreSpec x2 (old 050) + 0018 — the K8 admission DB truth |
| 5 | platform | op | platform K7 lanes | 2 | 2 | set_access_mode / set_access_channels |
| 5 | platform | engine | access reader fill + TTL cache | 1 | 3 | install_access_policy_reader — the S9 waiting-port body |
| 5 | platform | engine | guild-teardown registry | 1 | 3 | guild_lifecycle.py compiled: hook registry w/ shipped isolation |
| 5 | platform | engine | consistency report | 1 | 3 | severity contract + fail-isolated collector registry verbatim |
| 5 | platform | engine | introspection + guild snapshot | 2 | 3 | duck-typed pure reads verbatim; snapshot privacy tokens pinned |
| 5 | platform | engine | K10 claims | 3 | 2 | platform.explain_status/explain_consistency/code_context.explain byte-identical + fact gatherers |
| 5 | proof_channel | command | prize commands | 5 | 1 | CommandSpec verbatim (+prize/-prize/prizestatus/prizemenu/timedprize) |
| 5 | proof_channel | panel | proof_channel.hub | 1 | 2 | the _PrizeManagerView as declared grammar (G-10 modals) |
| 5 | proof_channel | store | proof_channel_locks | 1 | 2 | StoreSpec + 0018 (bug #8 durable deadlines) |
| 5 | proof_channel | op | proof K7 lanes | 3 | 2 | grant (record+EFFECT w/ compensator) / end / the sweep's unlock |
| 5 | proof_channel | task | proof:lock_reconcile | 1 | 2 | ManagedTaskSpec — the shipped per-lock timers + on_ready reconcile as ONE minute-granularity sweep |
| 6 | games | command | games/world/worldcard | 3 | 2 | CommandSpec rows (games kind=both) routing panels + a view |
| 6 | games | panel | games.hub + games.world | 2 | 2 | nav-only hub + world read panel, provider-fed overview |
| 6 | games | store | game_state + game_xp | 2 | 2 | SESSION checkpoint store + AGGREGATE shared track (reverse-importable, erasure bodies) |
| 6 | games | op | games.gc_sweep_row | 1 | 2 | the audited GC refund lane (shipped session_gc re-homed) |
| 6 | games | task | games:session_gc | 1 | 2 | ManagedTaskSpec Interval(3600) over the 24h TTL |
| 6 | games | engine | wager primitives + game-XP core | 2 | 3 | conn-threaded escrow/settle-once + soft-cap award policy — justified code under the K7 legs (P0-1 semantics) |
| 6 | games | engine | g1 session registry/dispatcher | 1 | 3 | the §3.4 dynamic-id seam: prefix claims + resolve() re-entry (kernel port fill, one justified module) |
| 6 | blackjack | command | blackjack/bjtournament/bjstart/bjstatus | 4 | 2 | CommandSpec rows, shipped names verbatim |
| 6 | blackjack | panel | blackjack.hub | 1 | 2 | 3 actions incl. G-10 bet modal |
| 6 | blackjack | op | solo/PvP/tournament lanes | 10 | 2 | K7 CompoundOpSpecs over the checkpoint store; settle table in one leg each |
| 6 | blackjack | engine | card/deck/dealer primitives | 1 | 3 | pure shipped math (engine.py) — justified code by design |
| 6 | blackjack | setting | default_entry_fee | 1 | 2 | SettingSpec, shipped persisted key |
| 6 | rps_tournament | command | rps family | 7 | 2 | CommandSpec rows, shipped names/aliases verbatim |
| 6 | rps_tournament | panel | rps_tournament.hub | 1 | 2 | move ENUM selector (values->op) + rules/settings views |
| 6 | rps_tournament | op | solo/PvP/tournament lanes | 7 | 2 | K7 CompoundOpSpecs; second throw settles in the same txn |
| 6 | rps_tournament | engine | rules tables | 1 | 2 | closed alias/win-condition data, shipped verbatim |
| 6 | rps_tournament | setting | entry fee/mode/best_of | 3 | 2 | SettingSpec rows (in-memory shipped settings made durable) |
| 6 | farm | command | farm | 1 | 2 | CommandSpec routing the farm hub (shipped single-command surface) |
| 6 | farm | panel | farm.hub | 1 | 2 | collect/buy-hen/upgrade-coop/refresh actions over the K7 lanes |
| 6 | farm | store | chicken_farm | 1 | 2 | StoreSpec, shipped shape (BIGINT epochs), MEMBER_ID erasure |
| 6 | farm | op | collect/buy_chicken/upgrade_coop | 3 | 2 | K7 money lanes w/ shipped copy + settle-at-old-flock subtlety |
| 6 | farm | engine | idle core (settle/pricing) | 1 | 3 | pure shipped math verbatim (core.py) — justified code by design |
| 6 | creature | command | creature family (7 shipped) | 7 | 2 | CommandSpec rows verbatim (catch/dex/dextop/cbrecord/… ) |
| 6 | creature | panel | creature.hub | 1 | 2 | catch/dex/top actions, RESULT_CARD views |
| 6 | creature | store | collection_log + battle_record | 2 | 2 | StoreSpec x2, shipped shapes, MEMBER_ID erasure |
| 6 | creature | op | catch + record_battle_result | 2 | 2 | K7 lanes (fled writes NOTHING; battle RECORD lane live) |
| 6 | creature | engine | catalog + catch roll | 1 | 3 | creatures.json byte-identical + injectable-rng roll — justified |
| 6 | mining | command | FULL 37-command shipped surface | 37 | 2 | CommandSpec rows verbatim; 27 deep-system commands = honest pending terminals riding the D-0043 successor port |
| 6 | mining | panel | mining.hub | 1 | 2 | mine/chop/explore/sell-all actions over the K7 lanes |
| 6 | mining | store | mining_inventory + player_state | 2 | 2 | StoreSpec x2 (TEXT user ids kept, +guild_id col) |
| 6 | mining | op | mine/harvest/explore/sell/sell_all/buy | 6 | 2 | K7 lanes; ledger rows + game-XP emits in one leg each |
| 6 | mining | engine | rewards + market tables | 2 | 3 | shipped reward math verbatim (legacy pickaxe path) + GEAR_SHOP/RESOURCE value data — justified code |
| 6 | mining | engine | extra-inventory-source fill | 1 | 3 | the D-0032 waiting-port body (mining_inventory -> !inventory) |
| 6 | fishing | command | FULL 20-command shipped surface | 20 | 2 | CommandSpec rows verbatim; 15 gear/venue/craft/structure commands = honest pending terminals (D-0043) |
| 6 | fishing | panel | fishing.hub | 1 | 2 | cast/log/trophies actions, RESULT_CARD views |
| 6 | fishing | store | fishing_catch_log | 1 | 2 | StoreSpec, shipped shape, MEMBER_ID erasure |
| 6 | fishing | op | fishing.cast | 1 | 2 | K7 lane — dex upsert + pearl + fish->mining_inventory + xp in ONE leg (starter profile) |
| 6 | fishing | engine | catalog + weight bands | 1 | 3 | fish.json (32 species = 21 shore + 11 deepwater) + weight roll — justified code |
| 6 | games | engine | band-6 rank providers | 6 | 3 | mining/creatures/fishing/farm/gamexp/crafting RankProviders w/ shipped alias rows (registry pattern, band-4 precedent) |

Per band:
- band 1: 45.45% (5/11)
- band 2: 99.41% (169/170)
- band 3: 91.67% (66/72)
- band 4: 75.51% (37/49)
- band 5: 83.33% (80/96)
- band 6: 89.12% (131/147)
