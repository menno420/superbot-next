# 2026-07-12 — slice 5 port: skills / skill / titles (skill tree · earned titles)

> **Status:** `in-progress`

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

_Pending the born-red first push; filled on the flip-to-complete commit._
