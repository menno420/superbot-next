# Game sections — design + 3 slices lane claim — `minigame-sections`

> **CLAIM (2026-07-13)** — game-sections lane (SuperBot World night run,
> ORDER 017 item 4, minigame/casino panel consolidation). This lane claims
> the DESIGN PR (`docs/design/game-sections.md` + D-0082) and the 3
> implementation slices that follow so a concurrent fleet does not
> duplicate any slice.

**EXCLUDED — peer lanes.** The fishing port (`fishing-port-remaining`,
PR #313 lineage), the mining write-parity WP lane
(`mining-write-parity-lane`, PRs #312/#317), and the energy lane (#320)
are peer-claimed; this lane touches game SECTIONS (grouping + enablement
+ panels), never those subsystems' internals.

- `minigame-sections` · **ORDER-017 item 4 game-sections lane — design + 3 slices (registry/enablement seam, settings surface, panel subscription)** — `GameSectionSpec` spec leaf + registry, per-guild enablement riding governance `subsystem_visibility`, settings-hub `games` group, games-hub provider subscription; EXCLUDES fishing / mining-WP / energy lanes (peer-claimed) · docs/, sb/spec/sections.py, sb/manifest/games.py, sb/domain/games/, sb/domain/settings/ · 2026-07-13
