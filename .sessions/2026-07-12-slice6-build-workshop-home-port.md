# 2026-07-12 — slice 6 (FINAL) port: build / buildlist / buildable / workshop / home

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 6 — the **structures / workshop / home**
rung, and the FINAL rung of the deep-mining ladder. Five shipped commands move
from honest D-0043 pending terminals to real surfaces, stacked on slice 5
(PR #299, itself on #296 on #292 on #289 on #286): `!build` · `!buildlist` ·
`!buildable` · `!workshop` · `!home`. After this slice the mining deep-system
`PENDING` dict is EMPTY (all original 26 keys ported).

Planned delivery:

- **Domain** (`sb/domain/mining/structures.py`): add the **Home** structure —
  `HOME` key, the `_HOME_LEVEL_NAMES` `("(not built)", "Cozy Cabin", "Stone
  Keep", "Grand Hall")` ladder + `_HOME_BUILD_LADDER` (2000🪙/wood30·stone20 →
  5000🪙/stone50·iron15 → 12000🪙/gold15·diamond3) + `MAX_HOME_LEVEL`, registered
  in `_DEFS`. Home rides the EXISTING generic `mining_structures` table (0046,
  slice 4) — no new table. `workshop.py`: add `gear_recipes` / `craftable_gear`
  (the equippable-recipe subset annotated with craftable-now), ported verbatim.
  `recipes.py` (the 44-row shipped catalogue) already landed slice 4.
- **Handlers** (`service.py` `_register()`): `build_route` (bare `!build` →
  the "Available Structures" recipe embed, the same bytes as `!buildlist`;
  argful `!build <item>` craft write deferred D-0043), `buildlist_route` (the
  recipe embed), `buildable_view` (fresh player → "You currently don't have
  enough resources to build anything." PLAIN). build/buildlist/buildable/home/
  workshop removed from `PENDING` + `ensure_handler_refs` → **PENDING empty**.
- **Panels** (`panels.py`): the session `mining.workshop` PanelSpec (the shipped
  `views/mining/workshop_panel.py` `MiningWorkshopView` — a provider-fed 25-option
  craft select + 🔁 Quick-craft (disabled with no last-broken) + ↩ Workshop + nav,
  its 🔧 Workshop embed via renderer override; goldens/mining/sweep_workshop pins
  every byte) and the session `mining.home` PanelSpec (🏠 Build + ↩ Mining Hub +
  nav, its 🏠 Home embed via renderer override; goldens/mining/sweep_home pins the
  not-built card). The hub 🔨 Workshop button + forge ↩ Workshop button repoint
  from `mining.workshop_pending` to the now-live `mining.workshop` panel (byte-
  neutral: those pins carry only the label + anchored/minted id).
- **Deferred (D-0043 pending terminals, no golden drives them)**: the argful
  `!build <item>` / craft-select write, the 🏠 Build structure write (coin +
  material sink), and the ↩ Workshop sub-hub — all ride the deferred
  successor/panel port, exactly like slice-4's forge Build and the argful
  cook/use lanes. The panel RENDERS + guard/read bytes are the only parity surface.
- **A-16 depth floor**: NO new declared table surface — Home rides the already-
  declared + `guard-only-capture`-exempt `mining_structures` (slice 4); the
  deferred build/craft writes register no store. No new exemption row, ratchet
  unchanged.
- **sim-gate**: the `mining.workshop` panel declares 2 actions + 1 selector = 3,
  and `mining.home` 2 actions — BOTH below the 4-action auto-exempt floor → no
  overlay, no baseline change (the forge/titles precedent).
- **Golden re-home** (#193 law): the 5 `_unmapped` sweeps
  (sweep_build/buildlist/buildable/workshop/home) re-home into the gated `mining`
  row (gate 447 → 452) by `git mv` + the one sanctioned `subsystem` flip.

## Verification (local, real Postgres, pristine parity_replay DB)

- **golden-parity GATE GREEN — all 452 golden(s) across 51 ported subsystem(s)
  replay clean** (was 447; the +5 re-home takes mining 32 → 37, `_unmapped`
  21 → 16). Each of the 5 verified byte-identical against the REAL handlers by a
  targeted `replay_case` pass BEFORE the `git mv` (all GREEN — the Available
  Structures green recipe embed for build+buildlist, the plain "not enough
  resources" buildable guard, the 🔧 Workshop panel's 25-option craft select +
  disabled Quick-craft + "All 39 gear recipes" field + "Balance: 0 🪙" footer,
  and the 🏠 Home not-built card's "(not built) (0/3)" + "Next: Cozy Cabin"
  "20× stone, 30× wood + 2000 🪙"), then again in the full gate after.
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported, 468
  goldens** — NO new declared table surface: Home rides the already-declared +
  `guard-only-capture`-exempt `mining_structures` (slice 4); the build/craft/
  structure-build writes are deferred, registering no store. No new exemption
  row; ratchet unchanged (`mining {events: 2, tables: 5, settings: 0}`).
- **check_migrations: clean (47)** — NO new migration (Home rides 0046).
  **manifest_compile: green** (snapshot recompiled, 48 manifests).
- **check_money_race: OK — 0 violations** — the argful build/craft write and the
  🏠 Build structure write are DEFERRED (D-0043 pending terminals), so NO new
  money-bearing op is introduced; the checker has nothing new to advisory-fence
  (the slice-5 respec/spend deferral precedent).
- **check_sim_gate: OK — 1339 [A] assignment(s), 529 auto-exempt below-floor** —
  the `mining.workshop` panel declares 2 actions + 1 selector = 3 and
  `mining.home` 2 actions, BOTH ≤ the 4-action floor → auto-exempt, NO overlay
  and NO baseline change (the forge/titles precedent; the +6 auto-exempt keys are
  the two new panels' arrangement rows).
- **pytest tests/unit: 1748 passed, 5 skipped** on a pristine DB, run SERIALLY
  (`-p no:randomly`). `test_composition_parity.py` green — the 5 now-removed
  `*_pending` refs (build/buildlist/buildable/home/workshop) pruned from the
  burn-down; the new home-build / workshop-craft / workshop-hub pending terminals
  register at import (panels.py `_register_refs`), so they stay import-visible.
- `bootstrap.py check --strict`: the only red was the by-design born-red HOLD
  while this card declared `in-progress` — flipped `complete` in this final
  commit; nothing else.

### 5 re-homed goldens (git mv `_unmapped → mining`, subsystem flip only)
sweep_build, sweep_buildlist, sweep_buildable, sweep_workshop, sweep_home — only
the `"subsystem"` line changed (`_unmapped` → `mining`); asserted calls/events/
db_delta bytes untouched (#193 law). sweep_workshop is the fifth component-bearing
mining golden (after vault / forge / skills / titles); sweep_home the sixth.

## Deferred (honest-pending write-terminals across the finished ladder)

The row-bearing writes that no imported golden drives remain deferred (D-0043):
equip / unequip / loadout-save·apply·delete / geared-descend·ascend / world
reseed / vault deposit·withdraw / vaultupgrade·stash / repair / quickcraft /
cook / use / skill spend / respec / title equip / **structure build (forge +
home)** / **craft**. The one capture run after the ladder completes seeds the
personas that exercise these lanes and mints the row-bearing goldens.

## 💡 Session idea

Slice 6 closes the deep-mining ladder: all 26 deep-system commands are ported and
the mining `PENDING` dict is empty — yet the port is a **render/guard shell over a
deferred write core**. Every rung landed the same shape: each imported sweep drove
only the bare fresh-player invocation, so the row-bearing writes — equip / loadout
apply / geared descend / world reseed / vault deposit / repair / quickcraft / cook
/ use / skill spend / respec / title equip / **structure build (forge + home) /
craft** — live in NO golden and stay honest D-0043 pending terminals. The single
highest-leverage follow-up is now unblocked: ONE capture run against the oracle,
seeding a persona with resources, equipped+worn gear, a broken tool, allocated
skills, a deep `max_depth`, a chosen title, and built structures, driving one of
each write (a `!build stone hut`, a `!workshop` craft pick, a `!home` 🏠 Build, a
funded `!repair`, a `!quickcraft` with a real last-broken, etc.). That one run
mints the row-bearing goldens across the whole ladder AND lets the
`depth.exemptions.mining` `guard-only-capture` rows (mining_equipment /
mining_loadout_presets / mining_gear_wear / player_skills / mining_world /
mining_vault / mining_structures / mining_player_state columns) be DELETED
together — the D-0069 class exit that converts the ladder from "declared + exempt"
to "declared + covered". Until then the deferred write terminals are the honest
ledger of what the corpus never exercised.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-slice5-skills-titles-port.md`.) Its headline —
PUSHED + PR GREEN, stacked on #296 — landed the skill-tree + earned-title stack
clean. Two lessons carried into slice 6. First, the sim-gate floor arithmetic:
slice 5's 7-action skills panel needed the vault overlay recipe, while its
1-action titles panel auto-exempted; slice 6's workshop (3 declared) and home
(2 declared) both sit below the 4-action floor, so — like the forge panel — NO
overlay/baseline change is required. Second, the deferral discipline: slice 5
deferred both write lanes (respec + spend) so no new money-bearing op existed to
fence; slice 6 defers the structure-build + craft writes identically, so
check_money_race stays clean with nothing new to advisory-lock. The
session-PanelSpec + renderer-override recipe (proven slices 2–5) renders the
workshop's provider-fed craft select and the home not-built card.
