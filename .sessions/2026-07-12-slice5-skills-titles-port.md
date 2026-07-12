# 2026-07-12 — slice 5 port: skills / skill / titles (skill tree · earned titles)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 5 — the **skill tree + earned titles**
identity rung. Three shipped commands move from honest D-0043 pending terminals
to real surfaces, stacked on slice 4 (PR #296, itself on #292 on #289 on #286):
`!skills` · `!skill` · `!titles`.

Planned delivery:

- **Domain** (`sb/domain/mining/titles.py`, new): the earned-title model ported
  VERBATIM from the oracle (`disbot/utils/mining/titles.py`) — `Title`,
  `TitleContext`, the 9-row `_RULES` catalogue (mastery → depth → level:
  the Deep One / Ironclad / Lucky / Master Smith / Spelunker / Deepdelver /
  Coreborn / Veteran / Legend), `get_title`, `is_earned`, `earned_titles`,
  `display`. The skill-tree model (`skills.py`) already landed slice 1 and is
  wired into `EffectiveStats` via `character.character_stats`; slice 5 adds the
  `respec_cost` helper (200 + 50·level) for the panel footer.
- **Store + migration**: an `equipped_title` column on `mining_player_state`
  (the only persisted title state — earned titles are DERIVED on read), migration
  `0047_mining_equipped_title.sql` (ALTER, + checksums) + `get_equipped_title` /
  `get_max_depth` reads. `player_skills` already exists (0041, slice 1).
- **Panels** (`panels.py`): the shipped `views/mining/skills_panel.py`
  (`MiningSkillsView` + `build_skills_embed`) as a session `mining.skills`
  PanelSpec — the four branch buttons + ♻ Respec · 🏆 Titles · ↩ Mining Hub +
  the standard nav row, its live 🌳 Skill Tree embed built by a renderer override
  (goldens/mining/sweep_skills pins every byte: title, MINING_COLOR, the Points
  field + the four branch fields, footer). And `views/mining/titles_panel.py`
  (`MiningTitlesView` + `build_titles_embed`) as a session `mining.titles`
  PanelSpec — ↩ Mining Hub + nav row, its live 🏆 Titles embed (Equipped +
  🔒 Locked (9) fields) built by a renderer override (goldens/mining/sweep_titles).
- **Handlers** (`service.py` `_register()`): the `skill_route` — bare `!skill`
  answers the branch-picker guard PLAIN (goldens/mining/sweep_skill pins the
  byte), an argful `!skill <branch>` spend is deferred; `skills`/`skill`/`titles`
  removed from `PENDING` + `ensure_handler_refs`.
- **Deferred (D-0043 pending terminals, no golden drives them)**: the argful
  `!skill <branch>` point spend, the skills-panel branch/respec button clicks
  (respec is the coin-bearing lane), and the titles select-menu equip — all ride
  the deferred panel/successor port, exactly like slice-4's forge Build button
  and the argful cook/use lanes. The panel RENDERS (read-only) are the only
  parity surface.
- **A-16 depth floor**: no NEW declared table surface — `player_skills` is
  already declared + `guard-only-capture`-exempt (slice 1); `equipped_title`
  rides `mining_player_state` (a column, no new table, already exempt). No new
  exemption row.
- **sim-gate**: the new 7-action `mining.skills` panel exceeds the 4-action
  auto-exempt floor → legacy-seed Exempt overlay (`manifest/layout/mining.lock`)
  + regenerated baseline (the slice-3 vault precedent). The 1-action
  `mining.titles` panel sits below the floor → auto-exempt, no overlay.
- **Golden re-home** (#193 law): the 3 `_unmapped` sweeps
  (sweep_skill/skills/titles) re-homed into the gated `mining` row
  (gate 444 → 447) by `git mv` + the one sanctioned `subsystem` flip.

## Verification (local, real Postgres, pristine DB)

- **golden-parity GATE GREEN — all 447 golden(s) across 51 ported
  subsystem(s) replay clean** (was 444; the +3 re-home takes mining 29 → 32,
  `_unmapped` 24 → 21), incl. sweep_skill / sweep_skills / sweep_titles. Each
  verified byte-identical against the REAL handlers by a targeted `replay_case`
  pass BEFORE the `git mv` (all three GREEN — the 🌳 Skill Tree card's
  MINING_COLOR frame / Points "**0** available · 0 spent" / "Game level **0**
  (points cap at **20** …)" / four "—" branch fields / "♻ Respec refunds all
  for 200 🪙" footer / the 4-branch + respec·titles·hub button rows + nav row;
  the 🏆 Titles card's Equipped "— none —" + 🔒 Locked (9) fields + earn-guidance
  footer + ↩ Mining Hub button + nav; and the plain `!skill` branch-picker
  guard), then again in the full gate after.
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  468 goldens** — NO new declared table surface: `player_skills` is already
  declared + `guard-only-capture`-exempt (slice 1), and `equipped_title` rides
  `mining_player_state` (a column, no new table, already exempt). No new
  exemption row; R3 ratchet unchanged.
- **check_migrations: clean (47)** — 0047_mining_equipped_title.sql appended to
  `checksums.json`. **manifest_compile: green** (snapshot recompiled, 48
  manifests).
- **check_money_race: OK — 0 violations** — the coin-bearing ♻ Respec lane and
  the point spend are DEFERRED (D-0043 pending terminals), so NO new
  money-bearing op is introduced; the checker (which flags only functions that
  transitively call the coin primitives) has nothing new to fence. The point
  spend is not coin-bearing (it draws the derived level pool, not coins), so the
  oracle's own self-service allocate carried no fence either.
- **check_sim_gate: OK — 1333 [A] assignment(s), 523 auto-exempt below-floor**
  — the new 7-action `mining.skills` panel exceeds the 4-action floor → three
  legacy-seed Exempt overlay rows added to `manifest/layout/mining.lock.json`
  (AMEND additively) + `--write-baseline` regenerated `sim/sim-gate-baseline.json`
  (the slice-3 vault precedent). The 1-action `mining.titles` panel sits below
  the floor → auto-exempt, NO overlay.
- **pytest tests/unit: 1748 passed, 5 skipped** on a pristine DB, run SERIALLY
  (`-p no:randomly`). `tests/unit/invariants/test_composition_parity.py` green
  (the 3 now-removed `*_pending` refs — skill/skills/titles — pruned from the
  burn-down; the skills-panel spend/respec pending terminals register at import
  so they stay import-visible).
- `bootstrap.py check --strict`: the only red was the by-design born-red HOLD
  while this card declared `in-progress` — flipped `complete` in this final
  commit; nothing else.

### 3 re-homed goldens (git mv `_unmapped → mining`, subsystem flip only)
sweep_skill, sweep_skills, sweep_titles — only the `"subsystem"` line changed
(`_unmapped` → `mining`); asserted calls/events/db_delta bytes untouched
(#193 law). sweep_skills is the third component-bearing mining golden (after the
vault and forge cards); sweep_titles is the fourth. The argful `!skill <branch>`
spend, the skills-panel branch/respec button clicks, and the titles select-menu
equip stay deferred (D-0043 pending terminals), the write-free render/guard
paths being the only parity surface.

## 💡 Session idea

Slice 5 declares the identity read surface (`player_skills` reads feed the skill
panel + the title earn-checks; `equipped_title` is added but only ever read `NULL`
this slice) yet — like every rung before it — every imported sweep drove only the
bare invocation: `!skills` and `!titles` render the fresh-player card, `!skill`
pins the branch-picker guard. So the row-bearing skill spend (`!skill mining`),
the coin-scaled respec, and the equipped-title write land in NO golden. They
join the growing `guard-only-capture` ledger (equip / loadout / wear / skill /
geared-descend / world-reseed / vault / structures). The one capture run after
the ladder completes should seed a persona with allocated skill points (a branch
at 10/10 → an EARNED title), a deep `max_depth`, and a chosen `equipped_title`,
drive one `!skill <branch>` spend, one `!skills` panel with non-zero allocation,
and one `!titles` with an earned+equipped title (exercising the Earned field and
the select-menu equip), mint the row-bearing goldens, and DELETE the
`player_skills` + `mining_player_state` exemptions at once (the D-0069 class exit).

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-slice4-forge-repair-craft-port.md`, the slice-4
forge/repair/quickcraft/cook/use port.) Its headline — PUSHED + PR GREEN,
stacked on #296 — landed the workshop/campfire/consumable stack clean and
CI-green first push. Two lessons carried directly into slice 5. First, its
sim-gate note: the 2-action forge panel auto-exempted below the 4-action floor
(no overlay), whereas slice-3's 5-action vault needed legacy-seed overlays + a
regenerated baseline — slice 5's skills panel has SEVEN actions, so the vault
recipe (three `mining.lock` overlay rows for `LayoutSpec.pages` / `PageSpec.rows`
/ `PanelSpec.layout` + `--write-baseline`) was applied from minute one, while the
1-action titles panel followed the forge path (auto-exempt). Second, its
money-race discipline: every slice-4 write was advisory-fenced against the
read-then-settle coin/material race; slice 5 instead DEFERS both write lanes
(the coin-bearing respec and the point spend), so — confirmed by the checker —
no new money-bearing function exists to fence, and the port stays as small as the
three golden-pinned bare surfaces allow. The session-PanelSpec + renderer-override
recipe proven across slices 2–4 is reused verbatim for both the skills and titles
cards.
