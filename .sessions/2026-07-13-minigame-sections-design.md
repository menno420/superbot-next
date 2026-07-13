# 2026-07-13 — game sections design (ORDER 017 item 4)

> **Status:** `complete`

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

- `control/claims/minigame-sections.md` — lane claim (design + 3 slices),
  peer lanes (fishing / mining-WP / energy) explicitly excluded.
- `docs/decisions.md` [D-0082] — enablement REUSES governance
  `subsystem_visibility` + K7 `SET_VISIBILITY`; no new store/migration.
- `docs/design/game-sections.md` (+ new `docs/design/README.md` index,
  navigation-map row per its placement rule) — every cited seam verified
  at HEAD 291361d: hub roster `sb/domain/games/panels.py:104-131`,
  governance write/read `service.py:68`/`:243`, dispatch gate
  `resolve.py:310-314`, settings hub `_HUB_GROUPS` panels.py:119 +
  `open_group` handlers.py:67-90, engine render paths `engine.py:382`/
  `:340`, anchors record-only (a named-successor refresh sweep).
- Gates: pytest 2056 passed / 13 skipped; `bootstrap.py check --strict`
  green (known claims-format advisory on mining-write-parity-lane.md).
- Flag (PL-001): read seam uses a lazy domain→governance import, matching
  the established `platform/guild_teardown.py:78` shape, not a new port.
- Flag (PL-001): D-0082 stamped ONLY in the design doc — the stamp checker
  reds a second citation home (README/nav-map cite the doc, not the id).

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
