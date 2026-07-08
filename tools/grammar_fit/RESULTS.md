# grammar_fit RESULTS (V-2 cumulative ledger)

Cumulative fit: **96.13%** tier-1/2 over 181 units (spike line: 85.26% / 95 units).

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

Per band:
- band 1: 45.45% (5/11)
- band 2: 99.41% (169/170)
