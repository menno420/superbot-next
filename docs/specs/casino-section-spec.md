# Casino / minigame section spec — inventory, taxonomy, enablement (game-sections §7)

> **Status:** `plan` — ORDER 031 phase 1 publication of the
> inventory+consolidation spec that
> [`../design/game-sections.md`](../design/game-sections.md) §7 declares as
> its **single replacement point**. The SBW SIM-REQUEST for this spec
> (outbox 2026-07-13T00:55Z, PR #325, ⚑5) never received an answer — the
> SBW seat is dark — so superbot-next publishes it first-party under
> decide-and-flag (PL-001): **this document IS the arrival §7 waits on.**
> Structured in exactly the four §7 fields + expansion slots. Evidence
> base: oracle @ corpus sha `7f7628e1`, next @ main `605db5a` (verified
> refs), landed at `9634e81`. **The casino SECTION BUILD itself stays a
> separate order** — this is spec only; nothing here changes code.

## 0. Ground truth — the machinery is already built

`docs/design/game-sections.md` still reads `plan`, but all three of its
design slices (§8 a/b/c) are live at HEAD:

- **slice a — spec leaf + registry**: `sb/spec/sections.py:36-58`
  (`GameEntry` / `GameSectionSpec`), collision-fenced `register_section`
  (sections.py:69-79); DEFAULT inventory at `sb/manifest/games.py:78-102`
  (`GAME_SECTIONS`), registered pre-manifest (games.py:105-113); read seam
  `sb/domain/games/sections.py:45-60` (`enabled_games(guild_id)`).
- **slice b — settings surface**: `sb/domain/games/sections_panel.py`
  (338 lines), routed from the settings hub
  (`sb/domain/settings/handlers.py:38` — `"games": "games.sections"`).
- **slice c — provider-driven hubs**: `sb/domain/games/panels.py:209-236`
  (`games.hub_fields` renders from `all_sections()` filtered through
  `enabled_games`), per-game `visible_when` predicates
  (panels.py:244-256, 308-310), world-hub line filtering (panels.py:280-295).

Delivery mechanism is therefore exactly what §7 promised: **replace the
`GAME_SECTIONS` tuple** (`sb/manifest/games.py:78-102` — flagged in-code as
"the SINGLE SBW-spec REPLACEMENT SLOT", games.py:73-77) and update the two
pinned agreements that hang off it (§5). No engine changes, no store changes.

## 1. §7 field 1 — Inventory (game keys + labels)

**10 shipped playable games** (oracle roster of record:
`disbot/utils/subsystem_registry.py`, `parent_hub: "games"` members, split
`competitive`/`activities`) **+ 1 planned (roulette) + 1 backlog candidate
(multiplayer blackjack table) + 3 game-adjacent non-games excluded (§6).**

| # | Game (subsystem key) | Oracle entry points | Wager / XP integration | Mode |
|---|---|---|---|---|
| 1 | **Casino — Texas Hold'em poker** (`casino`) | `!casino` hub, `!poker`/`!holdem` (casino_cog.py:40-63); hub "New Poker Table" button; per-player ephemeral live hands | **Play-chips only** — v1 deliberately off-economy; N-party escrow via `game_wager_workflow` is a named money-safety follow-up (`utils/poker/engine.py:11`). No game_xp. | Multiplayer 2–8, shared table |
| 2 | **Blackjack** (`blackjack`) | `!blackjack`/`!bj [bet]` solo, `!bj @player [bet]` PvP (blackjack_cog.py:434-470); `!bjtournament`/`!bjstart`/`!bjstatus` | **Real-economy wagers**: balance check + `game_wager_workflow` escrow/tournament entry; crash-safe via `game_state_service` | Solo + PvP + tournament |
| 3 | **Rock Paper Scissors** (`rps_tournament`) | `!rps` quickplay, `!rpsregister`/`!rpsstart`/`!rpsbot`/`!rpsmatchup`/`!rpshelp`/`!rpssettings` | **Real-economy wagers**: `game_wager_workflow` escrow + tournament entry/payout; checkpoints via `game_state_service` | PvP + bot matches + tournament |
| 4 | **Deathmatch** (`deathmatch`) | `!dm_challenge` (aliases `deathmatch`/`challenge`/`dm`), `!dm_help`; Fight Bot / Challenge Player panel | **None** — no economy/wager/XP hooks (grep: zero hits) | PvP duel + vs-bot |
| 5 | **Counting** (`counting`) | `!countingmenu`/`!cm`, `!start_match`, `!end_match`, `!reset_count`, `!toggle_turns`, `!count_info`, `!counttop`, `!count_rules`, … (10 cmds) | **None** | Channel-wide collaborative + timed matches |
| 6 | **Word Chain** (`chain`) | `!chainmenu` + managed chain channels | **None** | Channel-wide collaborative |
| 7 | **Mining** (`mining`) | `!minemenu` + 37-command ladder (mining_cog.py:43-771) | **game_xp** (`mining_workflow`); own economy loops | Solo idle/progression |
| 8 | **Fishing** (`fishing`) | `!fishing` + 20 commands (forecast/sail/fishdex/shops/crafting/venues) | **game_xp** (`fishing_workflow`) | Solo progression |
| 9 | **Creatures** (`creature`, incl. PvP battles) | `!hunt`, `!creatures`/`!pets`, `!dex`, `!dextop`; `!cbattle @opponent`, `!cbrecord`, `!cbattletop` (battles are the same subsystem — creature_battle_cog.py docstring 14-17) | **game_xp** (`creature_workflow` + `creature_battle_service`); no wagers | Solo catch/collection + PvP |
| 10 | **Chicken Farm** (`farm`) | `!farm`/`!chickenfarm`/`!coop` | **game_xp** (`farm_workflow`) | Solo idle |

Shared plumbing (oracle `disbot/services/`): `game_state_service`
(crash-safe checkpoints — blackjack, rps), `game_wager_workflow` (coin
escrow / tournament entry+payout — blackjack, rps, tournaments),
`game_xp_service` (shared cross-game XP pool — mining/fishing/creature/farm
+ world card).

### Per-game readiness in superbot-next

Sources: `parity/parity.yml:234-282`, `sb/domain/<key>/` at `605db5a`,
`docs/status/completeness-table-2026-07-13.md`.

| Game | parity.yml | sb/domain | Completeness row | Verdict |
|---|---|---|---|---|
| casino | `ported` (:239) | 9 modules | :63 ⚑ roulette-disabled is the SHIPPED parity byte (`sb/domain/casino/service.py:95-97`); per-player ephemeral hands = owner-armed live step | **ready-for-section** |
| blackjack | `ported` (:237) | 6 | :61 ✅ solo + tournament, paid-pot conservation golden | **ready-for-section** |
| rps_tournament | `ported` (:270) | 8 | :94 ✅ zero pending routes | **ready-for-section** |
| deathmatch | `ported` (:248) | 6 | :72 ✅ (duel-resolution stats = time-driven exemption parity.yml:561) | **ready-for-section** |
| counting | `ported` (:246) | 9 | :70 ✅ | **ready-for-section** |
| chain | `ported` (:240) | 6 | :64 ✅ | **ready-for-section** |
| creature | `ported` (:247) | 9 | :71 ✅ | **ready-for-section** |
| farm | `ported` (:251) | 5 | :75 ✅ | **ready-for-section** |
| fishing | `ported` (:252) | 16 | :76 ✅ (residue sentence stale — see [games-finalization review](../review/games-finalization-2026-07-13.md)) | **ready-for-section** |
| mining | `ported` (:263) | 18 | :88 ⚑ write faces pending; WP-2 #312 / WP-3 #317 in flight — hands off | **partial** (section-listable: enablement gating works today) |
| games (hub + substrate) | `ported` (:254) | 11 | :78 ✅ | this IS the section machinery — live |
| roulette | n/a (never shipped) | coming-soon byte only | (inside casino row) | **not-ported — expansion slot** |

**Summary: 10/10 shipped games ported with live domain subsystems; 9
ready-for-section outright, mining partial (membership still safe); nothing
playable is not-ported.**

Mining is included despite partial readiness: section membership is an
*enablement* concern and mining's dispatch gating already works; readiness
is tracked above, not encoded in the section.

## 2. §7 field 2 — Section grouping (taxonomy)

Owner's words (product intent): card games + minigames consolidated "into
one minigame/casino section", expanded options ("any kind of minigame they
can add should be there"), enable-all-or-pick-a-few, dynamically updating
panels. Two viable taxonomies; per PL-001 this is a decision with rationale,
not a blocker:

**Recommendation: three sections — 🎰 `casino` / 🕹️ `arcade` / 🌍 `world`.**

```python
# drop-in replacement for GAME_SECTIONS (sb/manifest/games.py:78-102)
GAME_SECTIONS: tuple[GameSectionSpec, ...] = (
    GameSectionSpec(
        key="casino", title="Casino", emoji="🎰",
        games=(
            GameEntry("blackjack", "Blackjack", "🃏", PanelRef("blackjack.hub")),
            GameEntry("casino", "Casino", "🎰", PanelRef("casino.hub")),
            # expansion slot: roulette / multiplayer blackjack table dock
            # INSIDE the casino subsystem (see §6 granularity note)
        )),
    GameSectionSpec(
        key="arcade", title="Arcade", emoji="🕹️",
        games=(
            GameEntry("deathmatch", "Deathmatch", "⚔️", PanelRef("deathmatch.hub")),
            GameEntry("rps_tournament", "Rock Paper Scissors", "✂️",
                      PanelRef("rps_tournament.hub")),
            GameEntry("counting", "Counting", "🔢", PanelRef("counting.hub")),
            GameEntry("chain", "Word Chain", "🔗", PanelRef("chain.hub")),
        )),
    GameSectionSpec(
        key="world", title="World", emoji="🌍",
        games=(
            GameEntry("mining", "Mining", "⛏️", PanelRef("mining.hub")),
            GameEntry("fishing", "Fishing", "🎣", PanelRef("fishing.hub")),
            GameEntry("creature", "Creatures", "🐾", PanelRef("creature.hub")),
            GameEntry("farm", "Chicken Farm", "🐔", PanelRef("farm.hub")),
        )),
)
```

Why three, why these:

1. **Casino gets its own section** — the owner's framing is literally
   "minigame/casino"; the shipped `competitive` group mixes real-wager card
   games with skill duels. A casino section is the natural home for the
   documented expansion pipeline (roulette + multiplayer blackjack table,
   oracle `docs/planning/casino-poker-design-2026-06-22.md:30-31,96-97`)
   and for the wager/money-safety doctrine that applies to this family only
   (blackjack/rps ride `game_wager_workflow`; poker is play-chips pending
   escrow — `utils/poker/engine.py:11`).
2. **Arcade = quick-session minigames** (duels + channel games): no
   persistent progression, join-and-play — where "any kind of minigame they
   can add" lands by default.
3. **World = persistent-progression games** — exactly the family the
   shipped `!world` spine federates (mine/fish/farm + shared `game_xp`;
   `sb/domain/games/panels.py:15-19,267-276`); creature joins as the same
   catch/progress/game_xp shape.
4. **Three fits the built budget exactly**: the sections settings panel has
   headroom to 3 sections before the roster needs paging
   (`sb/domain/games/sections_panel.py:29-32`). Four would force a paging
   redesign.

**Fallback (zero golden churn):** keep the shipped 2-section
`competitive`/`activities` grouping (games.py:78-102 as-is) and ship only
§1's membership confirmation + §6's expansion slots. Named so the build
order can choose consciously; the recommendation stands on the owner's
casino framing.

## 3. §7 field 3 — Enable-all-or-pick-a-few semantics

Adopted verbatim from the built slice-b behavior — this spec RATIFIES it,
no change requested:

- **One truth**: per-guild enablement is the governance
  `subsystem_visibility` row per game key (`GameEntry.key` IS the subsystem
  key, `sb/spec/sections.py:40`); disabling via sections and via the
  governance explorer is the SAME row (sections.py module docstring 5-7).
- **Enable-all** per section = write `enabled=None` per game (override
  DELETED back to registry default-enabled) — sections_panel.py docstring
  7-11.
- **Pick-a-few** = per-section multi-select, options = the section's games,
  `default` = currently enabled; submit DIFFS the selection (newly selected
  → `enabled=None`, newly deselected → `enabled=False`) —
  sections_panel.py:9-12.
- Every write rides the audited governance K7 `SET_VISIBILITY` op with the
  actor's WorkflowContext (sections_panel.py:14-19); no section-side store.
- **Fail-open posture**: unknown keys are ENABLED
  (`sb/domain/games/sections.py:7-9`); a broken enablement read renders the
  full roster (`sb/domain/games/panels.py:172-178,181-195`). A game added
  to `GAME_SECTIONS` before its subsystem ships is harmless-by-default.

## 4. §7 field 4 — Panel update contract (dynamic panels)

Adopted from the built slice-c behavior, stated as the normative contract:

1. **Next-interaction consistency** — every hub open / nav click / refresh
   re-resolves and re-renders the enabled set fresh
   (`sb/kernel/panels/engine.py:382`; provider `games.hub_fields`,
   panels.py:209-236). A section whose games are all disabled DROPS from
   the hub (sections.py:46-48).
2. **Stale-click denial** — every game button carries a `visible_when`
   enablement predicate (`games.enabled_<key>`, panels.py:244-256,308-310):
   disabled games drop at render AND a stale click is denied at dispatch;
   direct commands are independently denied by the resolve.py governance
   gate (design §4).
3. **In-place refresh after a settings write** — best-effort
   `refresh_session_view` (sections_panel.py:26-29).
4. **Anchored-panel sweep = named successor** — the anchor store is
   record-only today (game-sections.md:104-106,113-117;
   `docs/design/anchor-refresh-sweep.md`); this spec does NOT pull it
   forward.

## 5. Migration mechanics — honest blast radius of the §2 recommendation

What the constant swap actually touches (found by reading, not assumed —
this is what a build order must budget):

1. **Drift-guard test rewrite**:
   `tests/unit/band6/test_band6_game_sections.py:56-70` pins sections ↔ hub
   roster both directions over `(("competitive", GAMES_COMPETITIVE),
   ("activities", GAMES_ACTIVITIES))` — rewrite the pin table to the three
   new sections (the guard's purpose survives).
2. **Hub-golden re-pin**: `games.hub_fields` renders one field per section
   (panels.py:233-236), so `parity/goldens/games/sweep_games.json` +
   `sweep_slash_games.json` need re-pinning to the three-field render.
3. **`_STATIC_HUB_FIELDS` regroup** (panels.py:175-178) in the same commit
   so the degraded fail-open render matches.
4. **Button styles/rows are separate constants** (panels.py:327-332,
   350-356) — custom ids (`games:open:<key>`) and predicates survive
   unchanged; re-deriving the primary/success style split from the new
   sections is purely cosmetic — decide at build time.
5. **Settings panel needs nothing** (registry-driven, sections_panel.py:5-7;
   3 sections is inside its layout budget).
6. **Governance rows need nothing** — keys unchanged; existing per-guild
   overrides keep working (enablement never referenced section keys).

## 6. Expansion slots and exclusions

**Expansion slots:**

- **New standalone minigame** ("any kind of minigame" path): ship its
  subsystem as usual, then add one `GameEntry(key, label, emoji,
  PanelRef("<key>.hub"))` to the fitting section. Default: `arcade` unless
  persistent progression (`world`) or real wagers/cards (`casino`).
  Everything else — enablement rows, settings option, hub field,
  visible_when predicate — derives automatically (§§3-4).
- **Roulette + multiplayer blackjack table**: dock INSIDE the `casino`
  subsystem per the oracle charter
  (casino-poker-design-2026-06-22.md:13 — "a casino under games, so it can
  also include other games like roulette"; candidates ranked at :30-31).
  Roulette's disabled tile is today's shipped parity byte
  (`sb/domain/casino/service.py:95-97`). **Granularity flag (PL-001):**
  section enablement is per SUBSYSTEM key, so poker vs roulette are not
  individually toggleable via governance rows. **Recommendation: accept
  subsystem granularity** — it is the one-truth invariant game-sections.md §4 bought;
  per-table-game toggles, if ever wanted, are a casino-subsystem setting,
  not a section concern.
- **A fourth section**: allowed by the leaf but crosses the settings
  panel's 3-section layout budget (sections_panel.py:29-32) ⇒ requires the
  paging successor first. Named, not scheduled.
- **`GameSectionSpec` field extensions**: §7 permits extending the leaf if
  the spec adds fields (game-sections.md:126). This spec adds NONE —
  descriptions stay in the panels roster (`_GAME_DESCRIPTIONS`,
  panels.py:164-170).

**Exclusions (flagged, PL-001) — game-adjacent, not minigames:**

- `btd6` — strategy/reference assistant for an external game with its own
  top-level hub (oracle registry has no `parent_hub`,
  subsystem_registry.py:774-807); no play loop, no wager/XP.
- `four_twenty` — observe-only delight panel, oracle
  `parent_hub: "utility"` (registry:1048); "Nothing here writes to the DB
  or mutates economy/XP" (cog docstring :29).
- `project_moon` — knowledge-base lookup for an external game; no
  parent_hub, no game loop.

Keeping them out matches the oracle's own hub roster, so the shipped
`!games` goldens stay honest.

## 7. Slice fit (game-sections.md §8 continuation)

Design slices a-c are shipped; this spec lands as the §7 replacement in one
further slice: swap `GAME_SECTIONS` (§2 code block) + regroup
`_STATIC_HUB_FIELDS` + re-pin the two hub goldens + rewrite the drift-guard
pin table + (optional, cosmetic) re-derive button styles. One PR, unit
tests per the §8 convention. **That build remains a separate order** — this
document is the phase-1 spec publication only, and is the ORDER 031
heartbeat/outbox reference hook for the spec deliverable.
