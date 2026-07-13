# Games finalization review — mining · fishing · idle (farm) — 2026-07-13

> **Status:** `audit` — ORDER 031 phase 1: end-to-end per-game reviews
> (oracle vs port) for the three finalization targets, consolidated from
> three parallel review seats. **Report-only: nothing was changed, claimed,
> or armed by this document.** Reviewed against oracle @ scratchpad clone
> (`menno420/superbot` cdb26804/9776401 per port headers) and next @ main
> `605db5a`/`1eab517` (review sweeps), landed at main `9634e81`. Companion
> spec: [`../specs/casino-section-spec.md`](../specs/casino-section-spec.md)
> (game inventory + section taxonomy, same order).

## Headline verdicts

| Game | Verdict |
|---|---|
| **Mining** | **Command-surface complete and parity-green** (all 37 oracle commands declared, `parity/parity.yml:263` `mining: ported`, 46 goldens) but the **interactive layer is roughly half-ported**: grid Mine navigator, 3 sub-hubs, ~12 panel-write buttons + workshop craft selector, 3 argful writes pending — and nearly every remaining write face is claimed by the in-flight WP stack (#312/#317/#335/#344) or the energy lane. Safely workable now: render/read-side slices only. |
| **Fishing** | **The most complete game port in the repo**: all 20 oracle commands live and golden-pinned (24 goldens incl. 3 row-bearing Reel writes); the cast leg already runs the FULL oracle knob compound — ORDER 019 item 4's premise is STALE (retired by #373 + #394). The one real behavioral residue is the D-0043 minigame TIMING rung (instant Reel commit ⇒ deepwater strictly dominant); secondary: populated `!fishtop`/`!trophies` body copy deviates. |
| **Idle (farm)** | **Faithful, essentially complete port**: accrual core verbatim, 3 coin lanes as audited K7 ops with a *stronger-than-oracle* concurrency fence, panels byte-identical to the oracle golden. Residue is small and mostly ledgered: idle-summary/in-place-edit redraw lane under-ported, no row-bearing `chicken_farm` golden yet, two tiny unpinned byte drifts (leaderboard provider strings, `top_farmers` SQL filter). ORDER 019 item 6 (idle plugin pin) already executed. |

---

## 1. MINING

Oracle: `disbot/cogs/mining_cog.py` (37 commands, :43-771), `services/mining_workflow.py`, `views/mining/` (16 modules), `views/explore/`. Next: `sb/domain/mining/` (17 modules) + `sb/manifest/mining.py:52-132` (all 37 declared verbatim).

### What's ported

- **Live command surface**: hub (`!minemenu`, byte-pinned `sweep_minemenu`), fastmine/chop/explore, inventory/stats/gear/character views, buildlist/buildable, market + sell/sellall/buy (FOR-UPDATE fenced K7 legs), descend/ascend/mineworld, stash/unstash/vaultupgrade, equip/unequip/loadouts (WP-1 write goldens, PR #306), repair/quickcraft, cook/use (energy-lane slice 2 goldens), reset_inventory (admin). The deep-system PENDING roster is **empty** (`sb/domain/mining/service.py:1055-1091` — "all 26 original deep-system commands are ported").
- **Partial**: `!minestats` (Deepest field wrong — G1 below), `!build`/`!craft` argful (WP-6 pending terminal), `!skill <branch>` argful (WP-5 pending terminal), `!mine` (absent-by-parity: golden `sweep_mine` pins the capture-world generic-error byte; grid system is D-0043).
- **Panels**: 8 PanelSpecs render live; pending writes = vault 📥/📤 modals, forge 🔥/home 🏠 Build, 4 skill spends + ♻ Respec, workshop craft selector, grid, how-to (panels.py:143-157, 297-332, 432-451, 699-715, 860-873). Sub-hub navigation (Character/Workshop/Gear interactive) is flattened to result cards / direct opens — deviation ledgered (panels.py:41-43).

### Parity state

- `parity/parity.yml:263` **`mining: ported`**; 46 goldens (37 sweeps + 9 row-bearing writes: WP-1 ×5, energy slice-2 ×4); ratchet `mining: {events: 3, tables: 10}` (parity.yml:1173).
- Open guard-only-capture exemptions (parity.yml:867-955): `mining_gear_wear`, `mining_world`, `mining_vault`, `mining_structures`, + the depth face of `mining_player_state` — retirements are the WP lane's deliverable (WP-2 #312, WP-3 #317, WP-4, WP-5 #335, WP-6 #344).
- Completeness-table row 88 slightly lags the tree: cook/use argful are LIVE (slice-2 goldens in-tree) though the row still lists them pending.

### Gaps vs oracle (behavioral)

- **G1 — `!minestats` "Deepest" wrong after energy slice 2**: service.py:381 renders current depth; oracle reads `get_max_depth` (mining_cog.py:157,181). The docstring excuse (service.py:347-349) is stale — descend is live and records max_depth (ops.py:428-433). Golden-neutral fix (fresh-player golden has depth=0=max).
- **G2 — grid Mine navigator absent** (seed-deterministic x/y/z world, dig-as-locomotion, fog-of-war, energy dig brake).
- **G3 — ~12 panel write buttons pending** (9 handlers).
- **G4 — workshop craft selector + argful `!build`/`!craft`** (WP-6 #344).
- **G5 — skill spend + respec** (WP-5 #335).
- **G6 — title-equip Select absent** (windowed-select grammar successor + WP-5's park-honest-pending flag).
- **G7 — sub-hub navigation flattened** (ledgered).
- **G8 — market/recipe interactive panels absent** (need windowed select).
- **G9 — fastmine/grid dig energy gating absent** — deliberate (oracle gates only grid `dig()`; energy slice 3 is owner-gated).
- **G10 — hub live-overview under-render** (Tool/Light "—", partial Wealth; ledgered, panels.py:32-43).

### World-hub integration

Wired **both directions**: games hub `ga_mining` → `PanelRef("mining.hub")` (sb/domain/games/panels.py:140-141), world hub `world_mine` with enablement predicate (games/panels.py:373-378), mining hub 🗺️ → `games.world` (mining/panels.py:186-190); `sweep_world`/`sweep_worldcard` pin bytes. **Gap**: the oracle's dynamically attached "↩ Mining Hub" back button on the world hub (oracle main_panel.py:257-274) is unported — panel-engine route-origin limitation, same as the ledgered role row.

### Ranked extend/improve

| # | Item | Effort | Collision |
|---|---|---|---|
| 1 | **`!minestats` Deepest → max_depth fix (G1)** — read `store.get_max_depth` in `stats_view` (service.py:381) per oracle mining_cog.py:157; golden-neutral | **S** | **NONE — UNBLOCKED, TOP PICK 1** |
| 2 | **How-to panel port (G3)** — flip `mining.how_to_pending` to the one-screen guide card (oracle how_to_panel.py, 76 lines); exact fishing `howtofish` precedent (#410) | **S** | **NONE — UNBLOCKED, TOP PICK 2** |
| 3 | Character sub-hub port (G7) — render-only PanelSpec routing to already-live surfaces | M | LOW |
| 4 | Workshop sub-hub port (G7) — reverses the 2026-07-13 curation repoint of `↩ Workshop`; coordinate first | S/M | LOW |
| 5 | ORDER 019 item 3 — `check_money_race` mis-classification | S/M | **LANDED since review sweep — PR #425 @ `9634e81`** (see dispositions below) |
| 6 | ORDER 019 item 7 — windowed-select grammar successor (unlocks G6, G8, setup's 43-cog picker) | M/L | **PARTIAL** — grammar core + a non-mining consumer unclaimed; the mining title-equip consumer collides with WP-5 (#335) — build grammar-only |
| 7 | Vault deposit/withdraw modals (G3) | M | **BLOCKED-ADJACENT** — WP-2 (#312) re-freezing mining_vault; sequence after |
| 8 | Grid Mine navigator (G2) | L | **BLOCKED** — WP-3 (#317) + energy slice 3 (owner-gated) |
| 9 | Hub live-overview enrichment (G10) | M | MEDIUM — `sweep_minemenu` re-mint discipline |

**BLOCKED-BY-CLAIM (not ours):** WP-2/WP-3 write goldens (#312/#317 — row 88 says "hands off"); WP-5 skill spend + title equip (#335); WP-6 argful build/craft + structures (#344); cook/use + fastmine gating (energy-lane claim, slice 2 active, slice 3 owner-gated).

---

## 2. FISHING

Oracle: `disbot/cogs/fishing_cog.py` (20 commands, L75–418), `services/fishing_workflow.py`, `utils/fishing/` (12 modules), `views/fishing/` (11 views). Next: `sb/domain/fishing/` (16 modules, 5803 ln) + `sb/manifest/fishing.py` (20 CommandSpecs, 13 PanelSpecs).

### What's ported

All 20 commands **PORTED** (18 fully; `!fishtop`/`!trophies` PARTIAL — populated-body copy deviates). `cast_open` (service.py:131–356) is a line-mapped port of oracle `begin_cast` (fishing_workflow.py:384–518): Boathouse regen, energy settle/gate, rod, **venue profile** (deepwater pool + coral live, pinned by the deepwater-reel golden), weather, bait resolve, gear stats, structure mults, the verbatim compound `effective_pull = rod × bait × weather × gear × tide_pool`, energy spend post-roll, bait consume via the #394 `consume_bait_charge` fence (store.py:310). Hub 7-button parity exact; how-to-fish rules card (#410); structures sub-hub; all five craft lanes; `_PENDING_CASTS` token-fenced registry closes an oracle TOCTOU (codex #373 P1) — **PORTED+**, deviation ledgered.

**ABSENT**: the cast minigame timing layer (oracle cast_view.py:142–543) and the `_FishingDoneView` Cast-again continuation (:545–583).

### Parity state

- `parity/parity.yml:252` **`fishing: ported`**; coverage `{events: 3, tables: 10}` (:1161). The `fishing_catch_log` and `fishing_bait` exemptions were **RETIRED 2026-07-13** by the cast-depth Reel-write goldens (:712–725); the ONE surviving exemption is `table:fishing_rod` guard-only-capture (:730–741).
- 24 goldens: 20 sweeps + 3 curated Reel **writes** (`fishing_cast_reel_write`, `fishing_cast_deepwater_reel_write`, `fishing_cast_bait_spend_write`; parity/cases/curated.py:713–754) + `fishing_howtofish_rules_card`.
- **Completeness table :76 is stale**: its residue sentence "the cast leg still runs the starter shore profile" contradicts the PENDING-roster note it cites (service.py:1036–1044) — the true-up commit #412 (21:28Z) post-dates #373 (12:54Z) but didn't absorb it.

### Gaps vs oracle

- **Real residue #1 — the minigame timing rung** (the only big gap; ledgered at ops.py:26–37 + service.py:1036–1044). Reel commits instantly, so bite-delay/fake-out (`effective_bite_speed` computed then discarded, service.py:335), reaction window/too-early spook/premature grace, trophy reel-fight + escape rolls, and the unprompted got-away edit do not exist ⇒ rod `window_bonus`/`premature_grace`/`escape_resist` and bait/Dock/weather bite-speed are outcome-inert, and **deepwater is strictly dominant in next** (rarer fish + coral, zero extra risk; oracle balanced by difficulty, venue.py:69–82). The pure math is already ported with no runtime caller (sb/domain/fishing/minigame.py:12–22) — the rung is wiring + kernel real-time timing support (D-0043).
- **Real residue #2 — populated `!fishtop`/`!trophies` bodies**: oracle medals 🥇🥈🥉 + resolved display names + species count (fishing_cog.py:154–192) vs next's raw `1. <@id> — N fish` (service.py:994–996, 1015–1018). Self-ledgered under-port; `_member_display_name` seam already exists (panels.py:916) — cheap to close.
- Checked and NOT gaps: weather (wired into roll + surfaces), curios/crafting (all five lanes), gear effects (pull live; bite-speed half inert per residue #1), venue unlocks (oracle has none by design), structures, fishlog dex verbatim, energy incl. Boathouse-adjusted settle.

### World-hub integration

**Complete; next exceeds oracle.** Oracle's world-hub Fish button showed a static entry card ("fishing is hub-less", world_hub.py:77–97); next routes it to the **live fishing hub** (`explore:open:fishing`, sections-enablement gated, sb/domain/games/panels.py:382–384), plus games-hub roster entry, sections seam (sb/manifest/games.py:94 → `enabled_games()`), leaderboard provider (`fishlb`/`anglerlb`), and `↩ Games` nav.

### Ranked extend/improve

| # | Item | Effort | Flags |
|---|---|---|---|
| 1 | **ORDER 019 item 4 disposition + completeness-row true-up** — item 4 is ALREADY DONE (#373+#394); fix the stale "starter shore profile" sentence at completeness-table :76 to name the actual residue (timing rung) | **S** | mild collision: `completeness-remainders` claim lists the table (its fishing slice landed #410) — **UNBLOCKED in practice**, note in PR |
| 2 | **fishtop/trophies populated-body fidelity** — port medals/display-names/species-count/weight copy into `top_view`/`trophies_view` (service.py:979–1019) | **S** | service.py file-level overlap with the bait-race claim but disjoint functions — **UNBLOCKED** |
| 3 | Cast-again continuation on the result card | M | needs a RESULT_CARD-with-actions seam — check precedent |
| 4 | D-0043 minigame timing rung (restores deepwater risk balance) | **L** | needs kernel real-time panel-edit support; oracle truth = cast_view.py:202–382 |
| 5 | Retire the stale `fishing-bait-race-fence` claim file | S | **BLOCKED-BY-CLAIM by definition** — claim owner/coordinator retires it, not a worker |
| 6 | First row-bearing `fishing_rod` golden (retires the last fishing exemption, parity.yml:730–741) | M | parity-harness lane; check parity-hygiene claim first |
| 7 | Anything on the bait-consume leg (service.py:295–315 / store.py:310–378) | — | **BLOCKED-BY-CLAIM** (`fishing-bait-race-fence`) — and already shipped #394 |

---

## 3. IDLE (chicken farm)

Oracle: `disbot/cogs/farm_cog.py`, `services/farm_workflow.py`, `utils/farm/farm.py`, `utils/db/games/farm.py`, `views/farm/menu.py`. Next: `sb/domain/farm/` (core, ops, panels, store) + `sb/manifest/farm.py`.

### What's ported

- Pure accrual/pricing core **verbatim** (core.py:28-117 — same constants LAY_INTERVAL_SECONDS=300 / EGG_VALUE=2 / caps 100/10 / prices 40×1.55 / 100×1.8 / capacity 20+15/lvl, same settle remainder carry, same zero-timestamp normalization).
- The three coin lanes as audited K7 ops (ops.py:48-155) incl. the buy-settles-at-OLD-flock-size subtlety, with a **stronger-than-oracle fence**: `pg_advisory_xact_lock` + row FOR UPDATE (store.py:40-83; MONEY-RACE ruling #217/2026-07-12) — closes the oracle's double-collect mint and no-row first-buy race. Race tests: tests/integration/test_farm_mining_money_race.py:144, :197.
- Both panels byte-verbatim (panels.py:123-218); GDPR erasure lane is a next-side addition (ops.py:158-163).
- **PARTIAL/ABSENT (documented under-ports, panels.py:36-43)**: in-place-edit + flash-line redraw lane; "while you were away" idle-summary blurb (no `get_status` twin); inline level-up note on collect (event emits, ops.py:171-178, but the result card drops `award.note`, ops.py:74-76).

### Parity state

- `parity.yml:251` **`farm: ported`**; `{events: 1, tables: 2}` (:1160). One exemption: `table:chicken_farm` session-resolution (:690-711) — the READ surface is pinned; "first row-bearing golden lands with a button-driving capture" (the fishing sibling exemption directly below was retired 2026-07-13 by exactly such a capture — precedent exists).
- `parity/goldens/farm/sweep_farm.json` is **byte-identical to the oracle's** (canonical-JSON diff: none). Trap-24 drift check: no drift (corpus sha `7f7628e1`).
- Completeness table :75 `| farm | ✅ hub + 3 K7 money lanes | ✅ | ✅ |` — accurate.

### Gaps vs oracle

Accrual math: **none**. Remaining: (1) idle-summary blurb absent; (2) in-place edit + flash line; (3) inline level-up note; (4) `top_farmers` drops oracle's `AND chickens > 0` (store.py:98-101 vs utils/db/games/farm.py:90-91 — near-unreachable, but byte drift in a NAME_STABLE store read); (5) leaderboard provider strings drift (next "🐔 Farm Leaderboard"/no `card_theme="harvest"` vs oracle rank_providers.py:332-337; unpinned); (6) no row-bearing golden. Prestige/upgrade-tree: **no gap** — the oracle farm has none (prestige lives only in the separate idle-plugin engine).

### Idle-plugin boundary (host side)

- `plugins.lock.json` idle pin **already executed** — commit `0cae0e1` (PR #370, 2026-07-13), generated by `tools/plugin_pin.py --write`. Host-side pin alone is safe: pinned-but-not-installed = skip-with-warning, never fatal (plugin_host.py:244-259); installed-but-drifted hash reds boot deliberately.
- Remaining there is owner-gated live driving (docs/operations/plugin-proof-live-drive.md §6 — "agent sessions must not attempt") and the idle seat's own lane, not superbot-next code. The idle plugin is a SEPARATE game from the farm; docking a plugin game into `GAME_SECTIONS` is unaddressed by the v1 contract (named follow-up).

### World-hub integration

At parity: `world_farm` third in the world row with the oracle description VERBATIM (sb/domain/games/panels.py:273-275, 386-390), games-hub roster + `GAME_SECTIONS` activities entry (sb/manifest/games.py:96-97), enablement-gated per D-0082; nav-home pins `nav:hub:games`. The sections seam is a next-side improvement over the oracle's flat registry.

### Ranked extend/improve

| # | Item | Effort | Collision |
|---|---|---|---|
| 1 | **Farm leaderboard provider parity trim** (oracle `display_title`/`empty_hint`/`card_theme="harvest"`, providers.py:98-101) | **S** | none — **TOP UNBLOCKED** |
| 2 | **`top_farmers` `chickens > 0` filter** (store.py:98-101; rides the same PR as #1) | **S** | none — **TOP UNBLOCKED** |
| 3 | Inline level-up note on collect (surface `award.note`, ops.py:74-76) | M | games result-card lane — check other seats first |
| 4 | Button-driving capture golden for `chicken_farm` (retire parity.yml:697; fishing precedent) | M | capture-harness lane — verify no overlap |
| 5 | "While you were away" + in-place-edit redraw lane | L | cross-domain panel-grammar decision — route, don't build solo |
| 6 | ORDER 019 item 6 — **ALREADY DONE** (0cae0e1/#370); residue = mark inbox item done (coordinator-owned) | S | **COLLISION: control files coordinator-owned — report only** |
| 7 | Idle-plugin sections docking → name in docs/game-plugin-contract.md successors | S | contract doc shared with plugin lane |
| 8 | De-vendor `examples/superbot-idle-plugin/` once the split repo installs | M | cross-repo timing — idle seat decides |

---

## ORDER 019 dispositions (games-touching items)

| Item | Disposition |
|---|---|
| **Item 4 — fishing cast-leg wiring** | **ALREADY DONE** — retired by PR #373 (`d7b18b2`, 2026-07-13 12:54Z) + the #394 bait-race fence; the item was cut from a pre-#373 sweep. `cast_open` runs the full oracle knob compound today (service.py:209–284). Needs a DONE ack + doc true-up, **not a build**: the completeness-table :76 residue sentence is stale (see stale artifacts). |
| **Item 6 — idle plugin `plugins.lock.json` pin** | **ALREADY LANDED** — commit `0cae0e1` / PR #370 (2026-07-13), the only commit ever touching the idle row; generated by `tools/plugin_pin.py --write`. Residue = owner-gated live drive + marking the inbox item done (coordinator-owned file). |
| **Item 3 — `check_money_race` mis-classification** | At review-sweep time (main `605db5a`) this was an unclaimed tooling fix; **it has since LANDED** — PR #425 merged as `9634e81` (this doc's landing HEAD; night lane, claim `night-money-race-and-doctrine-doc`, card `.sessions/2026-07-13-night-money-race-checker-fix.md`). No remaining action. |
| **Item 7 — windowed-select grammar successor** | **OPEN, split disposition**: the grammar core (25-option-cap windowing vocabulary) + a non-mining consumer is **unclaimed and safe**; the mining title-equip consumer **collides with WP-5** (#335, park-honest-pending bullet) — build grammar-only if picked up. Unlocks mining G6/G8 and setup's 43-cog picker. |

## Stale artifacts found (for the coordinator, not fixed here)

1. **`control/claims/fishing-bait-race-fence.md` lingers post-merge** — its deliverable shipped as PR #394 (`d51e38c`, 16:30Z: `consume_bait_charge` store.py:310, wired service.py:310–315) but the claim file is still present at `9634e81`, nominally blocking the lane. Claim owner/coordinator should retire it.
2. **Completeness-table fishing residue sentence stale** (docs/status/completeness-table-2026-07-13.md:76): "the cast leg still runs the starter shore profile" was retired by #373; the true-up #412 post-dates it but didn't absorb it. Mining row 88 also slightly lags (cook/use argful now LIVE).
