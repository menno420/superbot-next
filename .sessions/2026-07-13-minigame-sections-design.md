# 2026-07-13 — game sections design (ORDER 017 item 4)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · NIGHT-RUN lane · mandate: ORDER 017 item 4

## Scope

Design PR for minigame/casino "game sections" consolidation: lane claim
(`control/claims/minigame-sections.md`), decision record D-0082, and
`docs/design/game-sections.md` — section model (`GameSectionSpec` spec
leaf + registry, declared in `sb/manifest/games.py`), per-guild
enablement riding the existing governance `subsystem_visibility` store
(no new store), settings-hub `games` group, panel update contract, SBW
spec plug-in slot (SIM-REQUEST 2026-07-13T00:55Z, PR #325, unanswered),
and the 3-slice implementation plan. Docs-only; no code changes.
Excludes fishing / mining-WP / energy lanes (peer-claimed).

## What shipped

_(to be filled at close-out)_

## 💡 Session idea

The design's DEFAULT section inventory is hand-derived from
`sb/domain/games/panels.py` hub rows — a tiny drift-guard test
(assert every game key in the sections constant is a registered
manifest subsystem key, and vice versa for hub rows) would keep the
manifest declaration honest against the hub roster for free; land it
with slice (a) as `tests/spec/test_sections_registry.py`.

## ⟲ Previous-session review

Newest card (`2026-07-13-completeness-table.md`, PR #326) is a model
close-out: born-red held the gate as designed, the sweep evidence
("zero unregistered refs") is cited not asserted, and its guard recipe
about dirty `.substrate/guard-fires.jsonl` after local
`bootstrap.py check --strict` is directly actionable — this session
will restore that file before every commit per its recipe. Its 💡 idea
(mechanical `tools/check_completeness.py --table`) remains unclaimed
and worth a future slice.
