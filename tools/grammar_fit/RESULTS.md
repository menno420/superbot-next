# grammar_fit RESULTS (V-2 cumulative ledger)

Cumulative fit: **45.45%** tier-1/2 over 11 units (spike line: 85.26% / 95 units).

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

Per band:
- band 1: 45.45% (5/11)
