# 2026-07-13 — game sections slice 1: registry + enablement seam (ORDER 017 item 4)

> **Status:** `complete`

- **📊 Model:** `fable-5` · NIGHT-RUN lane · mandate: ORDER 017 item 4, slice a of D-0082

## Scope

Slice 1 of `docs/design/game-sections.md` (D-0082): the `GameSectionSpec`
spec leaf + registry (`sb/spec/sections.py`), the DEFAULT section
inventory declared in `sb/manifest/games.py` (SBW replacement slot per
§7), and the per-guild enablement read seam
(`sb/domain/games/sections.py::enabled_games`) riding governance
`subsystem_enabled`. Unit tests incl. the drift-guard (sections ↔ hub
roster) idea from the design session's card. Covered by the existing
lane claim `control/claims/minigame-sections.md` — no new claim.
Excludes fishing / mining-WP / energy lanes (peer-claimed) and slices
b/c (settings surface, provider subscription).

## What shipped

- `sb/spec/sections.py` — `GameEntry`/`GameSectionSpec` frozen stdlib-only
  leaf + collision-fenced idempotent registry (`register_section` /
  `get_section` / `all_sections`), field roles registered; fence mirrors
  `sb/kernel/panels/registry.py::register_panel` via the spec-leaf
  `EventRedefined` shape.
- `sb/manifest/games.py` — `GAME_SECTIONS` DEFAULT inventory
  (`competitive` 🏆 / `activities` 🎲, roster-verbatim from
  `sb/domain/games/panels.py` GAMES_COMPETITIVE/GAMES_ACTIVITIES),
  comment-marked as the single SBW-spec replacement slot (design §7);
  registered at manifest import + in `ENSURE_REFS` like the manifest's
  other registrations.
- `sb/domain/games/sections.py` — `enabled_games(guild_id) ->
  tuple[GameSectionView, ...]` over lazy `governance.subsystem_enabled`
  (the `guild_teardown.py:78` seam shape); fail-open for unknown keys;
  fully-disabled sections dropped.
- Tests (13): `tests/unit/spec/test_sections.py` (frozenness, idempotence
  + collision, order) + `tests/unit/band6/test_band6_game_sections.py`
  (drift-guard sections ↔ hub roster — the design card's 💡 landed;
  seam filtering over stubbed AND real governance reads).
- Gates: pytest 2069 passed / 13 skipped; `bootstrap.py check --strict`
  exit 0 (known claims-format advisory on mining-write-parity-lane.md).
- Flag (PL-001): a section whose games are ALL disabled is dropped from
  `enabled_games` (nothing to render); slice b's settings panel reads
  the registry directly, so it still sees every section.
- Flag (PL-001): drift-guard test lives at
  `tests/unit/band6/test_band6_game_sections.py` (band home of the games
  hub tests), not the card-suggested `tests/spec/` path (no such dir).

## 💡 Session idea

`enabled_games` calls `subsystem_enabled` once per game key — each call
re-fetches the guild's whole visibility chain. A
`enabled_map(guild_id) -> dict[str, bool]` batch read in governance
service (one `fetch_visibility_for_chain` + one dependency-rules pass)
would make slice c's hub provider one-read cheap; land it when slice c
wires the provider.

## ⟲ Previous-session review

Newest card (`2026-07-13-minigame-sections-design.md`) is a clean
docs-only close-out: every seam it cites carries file:line anchors
verified at HEAD 291361d, its PL-001 flags (lazy domain→governance
import; D-0082 single-stamp) are exactly the decisions this slice now
consumes, and its 💡 drift-guard test idea is specific enough to land
here verbatim — this session adopts it. Adopting also its inherited
guard recipe: restore `.substrate/guard-fires.jsonl` before every
commit after local `bootstrap.py check --strict` runs.
