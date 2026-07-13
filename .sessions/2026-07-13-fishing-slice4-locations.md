# 2026-07-13 — fishing depth slice 4 port: curios / craftcurio / tidepool / dock / boathouse / fishery (locations slice — FINAL)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · feature build

## Scope

The faithful port of fishing depth slice 4 — the FINAL rung of the
fishing gear port (D-0043 named successor scope; lane claim
`control/claims/fishing-port-remaining.md`, built directly atop slice 3 =
PR #342 / `3e4a77d`). The last six shipped commands moved from honest
D-0043 pending terminals to real surfaces: `!curios` · `!craftcurio` ·
`!tidepool` · `!dock` · `!boathouse` · `!fishery` — the fishing PENDING
roster is now EMPTY (20/20 commands live) and `parity/goldens/_unmapped/`
carries ZERO sweeps (row + directory retired).

Shipped shape (the #313/#330/#342 slice recipe — NO migration this
slice; the fishing structures ride the EXISTING generic
`mining_structures` table as additive rows, curios/pearls/coral ride
`mining_inventory` via the sanctioned lazy-import mining.store seam):

- **Domain** (`sb/domain/fishing/curios.py`, NEW): the shipped
  `utils/fishing/curios.py` ported verbatim — the four-entry
  CURIO_CATALOG (Carved Coral Shell 🐚 2 / Coral Seahorse 🌊 4 /
  Coral Idol 🗿 8 / Coral Leviathan 🐉 16 coral), `cost_text`,
  `collection_progress`, `curio_by_key`; the shipped
  `craftable_key_for` lands as `curio_craftable_key_for` (bait.py
  already exports the package's `craftable_key_for` —
  check_symbol_shadowing rule 2, the slice-3 precedent predicted this
  exact collision; bytes identical).
- **Domain** (`sb/domain/mining/structures.py`, EXTENDED): the four
  fishing structures verbatim from the oracle module that owns them —
  TIDE_POOL/DOCK/BOATHOUSE/FISHERY keys, level names (Reef Pool /
  Tidal Basin / Grand Reef · Fishing Dock / Deepwater Pier · Boathouse
  / Grand Boathouse · Fishery / Grand Fishery), build ladders
  (1500/3🪸 · 4000/6 · 9000/10 — 1200/2🪸+15🪵 · 3500/5+30 —
  2000/3🪸+20🪵 · 5000/6+40 — 2500/4🪸+25🪵 · 6000/8+45) and the four
  mult/bonus fns (pull 0.04 · bite 0.06 · regen 0.12 · bonus 0.05).
- **Ops**: `fishing.craft_curio` (coral −cost, +1 curio item, one txn —
  the oracle craft_curio inventory-only conversion, fenced by the new
  `fishing.store.lock_coral_slot` — SHARED with the build leg, see
  below) and `fishing.build_structure` (the
  decide-and-flag fork, resolved PORT THE WRITE: the oracle
  `mining_workflow.build_structure` L705 one-txn coin debit + material
  consume + level raise; #217 advisory-fenced locking read via the new
  `mining.store.lock_structure_build_slot`; balance event after commit;
  the shipped `mining:{structure}_build` reason via the ported
  `market.structure_build_reason` — BUG-0031's generic derivation;
  mining_structures written ONLY through
  `mining.store.set_structure_level`, the sole-writer seam).
- **Handlers/panels**: `fishing.curios_view` (the 🪸 Coral Curios blue
  card, cog-inline embed verbatim), `fishing.craftcurio_route`, the
  four structure panels (Build + ↩ Structures buttons, teal/dark-teal
  embeds — `dark_teal` joined STYLE_TOKEN_COLORS as the goldens pin the
  byte; the shipped HubView children carry the standard nav row, unlike
  the author-locked rod/bait BaseViews) + the live structures sub-hub
  (oracle structures_hub.py; GAME_COLOR purple, four live status
  fields). The fishing hub 🏗 Structures button repointed from
  `fishing.structures_pending` to the live sub-hub (byte-neutral vs
  goldens/fishing/sweep_fishing — label/emoji/style unchanged); the
  structures_pending terminal retired. The four structure commands
  route straight to their PanelSpecs (the `!fishing`/`!fishlog`
  precedent).
- **Parity**: the FINAL 6 `_unmapped` sweeps re-homed into the gated
  `fishing` row (#193 law: `git mv` + the one sanctioned `subsystem`
  flip; rename similarity 98-99%, 2-line diffs) → `_unmapped` EMPTY —
  its `parity.yml` subsystems row, `verification/verified_live.yml`
  roster row and the directory itself retired (R1/V4 pair rows with
  non-empty golden dirs both ways). NO new tables → NO new exemption
  rows; mining_structures / mining_inventory coverage already rides
  mining's rows/exemptions (A-16 note updated in structures.py).
- **Sim-gate**: the structures sub-hub is the one above-floor panel
  (5 declared actions > the ≤4 floor) → 3 `legacy-seed` exempt overlay
  rows in `manifest/layout/fishing.lock.json` + baseline regen (the
  fishing.hub precedent); the four structure panels sit at 2 actions
  each (below-floor auto-exempt).

## Verification (local, real Postgres 16, pristine parity_replay DB)

- **golden-parity GATE GREEN — `gate: GREEN — all 484 golden(s) across
  51 ported subsystem(s) replay clean`** (the +6 re-home takes fishing
  16 → 22, `_unmapped` 6 → 0; all six re-homed sweeps replayed
  byte-identical on first mint — the curios card fields/footer, the
  craftcurio guard content, and every structure panel byte: embeds,
  emoji-in-label Build buttons, nav rows, teal/dark-teal colors).
- **check_parity_depth: OK — 50 subsystems (50 ported), kernel ported,
  484 goldens** (the `_unmapped` row retired). `--write-ratchet`
  regenerated the block UNCHANGED (guard-only sweeps move no db_delta
  table — the slice-2/3 doctrine held again; floor stays
  `fishing: {events: 1, tables: 4}`).
- **pytest tests/: 2127 passed, 2 skipped, 1 warning in 264.79s** —
  includes the new `tests/unit/band6/test_band6_fishing_structures.py`
  (14 tests: curio catalog + structure defs/ladders/mults verbatim,
  the craftcurio/build guard bytes vs the goldens, the curios-card
  embed bytes, panel spec component trees incl. the sub-hub, ops/reason
  registration, manifest + hub flips + the emptied PENDING roster).
- **pytest tests/integration -q: 11 passed in 9.27s.**
- **check_migrations: clean (50 migration(s))** — no migration this
  slice, by design.
- **manifest_compile: green (sha256:9b77d755047a133aa1651bc7352ff8ff
  83706bf8fab60e0c0d387abd6fc0221e, 48 manifest(s))** (snapshot
  recompiled — 6 route flips + 5 new panels).
- **check_compat_frozen: OK** (no new command names/aliases — all six
  were already declared; only their routes went live).
- **check_sim_gate: OK — 1378 [A] assignment(s), 558 auto-exempt
  below-floor** (after the 3 sub-hub overlay rows + baseline regen).
- **check_money_race: OK — 0 violations under sb/domain (2 allowlisted
  site(s), 0 ledgered known-risk site(s))** — the build leg takes BOTH
  fences BEFORE the level/inventory reads (lock_structure_build_slot
  then the shared lock_coral_slot — a stable order, the carve leg holds
  only the coral key) → debit → consume → raise; the curio leg fences
  on the SAME lock_coral_slot before the coral read (materials-only) —
  the shared key serializes a racing carve × Build over one
  floor-at-zero coral row (PR #350 codex P1, fixed in-flight).
- **check_verified_live: OK — 51 subsystems (0 verified), 0 records**
  (roster re-mirrored after the `_unmapped` retirement).
- **check_namespace / check_symbol_shadowing / check_escape_hatches /
  check_schema_growth / check_amendments / check_runtime_smoke /
  check_no_skip / check_config_usage / check_metric_cardinality /
  check_egress: clean.**
- `python3 bootstrap.py check --strict` pre-flip → only the designed
  born-red HOLD + the pre-existing mining-write-parity-lane
  claims-format advisory (never exit-affecting).

### 6 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_curios, sweep_craftcurio, sweep_tidepool, sweep_dock,
sweep_boathouse, sweep_fishery — only the `"subsystem"` line changed
(`_unmapped` → `fishing`); calls/events/db_delta bytes untouched (#193
law). All six pin write-free guard/read bytes (fresh-player renders),
so no coverage/exemption movement; `_unmapped` is empty and retired.

## 💡 Session idea

The `_unmapped` end-state was undocumented: every recipe doc describes
re-homing sweeps OUT of `_unmapped`, but nothing said what happens when
the LAST sweep leaves — this slice discovered at gate time (R1 red,
then the verified_live V4 test red) that TWO rosters pair rows with
non-empty golden dirs and both needed same-commit retirement (row +
comment + the directory itself). Worth one line in the port recipe /
parity.yml header: "a subsystem dir emptied by re-homes retires its
`subsystems:` row AND its `verified_live.yml` mirror row in the same
commit" — the next band that empties a shared dir (e.g. a future
`_pending` roster) hits this exact two-registry trap, and the second
registry is only discoverable by running the FULL suite, not the named
gates.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-fishing-slice3-bait.md@3e4a77d`.)
Its 💡 idea was directly load-bearing here: it predicted this slice's
`craftable_key_for` collision by name, so the rename-with-provenance
happened at write time instead of at gate time — zero shadowing reds
this session. That is the session-chain working exactly as designed
(a forward-looking idea consumed by its successor). Its recipe also
transferred wholesale (born-red sequencing, #193 re-home mechanics,
guard-as-pure-read handlers, fence-then-re-read ops, band6 skeleton,
ratchet doctrine). One gap, now closed by this session's idea: neither
slice-2 nor slice-3 anticipated registry rows that must RETIRE when a
roster empties — their cards only ever grew coverage. Nothing else to
improve: the four-slice ladder landed 20/20 commands with every gate
green on first local run each time.
