# 2026-07-13 — game sections slice 2: settings surface (ORDER 017 item 4)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · NIGHT-RUN lane · mandate: ORDER 017 item 4, slice b of D-0082

## Scope

Slice 2 of `docs/design/game-sections.md` (D-0082 §5): the settings
surface — a real `games.sections` panel (per-section **Enable all** +
pick-a-few multi-select over the slice-1 registry), wired into the
settings hub as the `games` group, every mutation through the existing
governance K7 `SET_VISIBILITY` op (`set_subsystem_visibility`) — no new
store, no migration. Stacked on `claude/minigame-sections-1` (PR #334,
head 2c5781a, unmerged at branch time). Covered by the existing lane
claim `control/claims/minigame-sections.md`. Excludes slice c (games hub
provider filtering) and the peer fishing / mining-WP / energy lanes.

## What shipped

(close-out pending)

## 💡 Session idea

(close-out pending)

## ⟲ Previous-session review

Newest card (`2026-07-13-minigame-sections-1.md`) is a complete, honest
close-out: its shipped list matches the branch head diff (spec leaf +
manifest inventory + read seam + 13 tests), its post-flip CI-red section
names the exact root cause (field-role registration ⇒ snapshot recompile
+ A-2 ledger entries) and mints a usable guard recipe — adopted here as
a pre-push gate (`manifest_compile.py` + `check_schema_growth.py` before
every push). Its PL-001 flag that the settings panel must read the
REGISTRY (not `enabled_games`, which drops fully-disabled sections) is
exactly the read shape this slice implements. Its 💡 (`enabled_map`
batch read) belongs to slice c's provider work — left for that lane.
