# 2026-07-13 — game sections slice 2: settings surface (ORDER 017 item 4)

> **Status:** `complete`

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

- `sb/domain/games/sections_panel.py` — the `games.sections` settings
  panel, registry-driven over `sb.spec.sections`: per section one
  **Enable all** button (`enabled=None` per game — override deleted back
  to registry default-enabled, design §5 verbatim) + one pick-a-few
  multi-select (`min_values=0`, options `default` = currently enabled;
  submit DIFFS the selection — newly selected → `None`, newly deselected
  → `False`, unchanged → no write, no spurious audit rows). Writes ride
  governance `set_subsystem_visibility` (K7 `SET_VISIBILITY`) with the
  actor's WorkflowContext via `ctx_from_request`; reads use
  `subsystem_enabled` per key DIRECTLY (the slice-1 card flag —
  `enabled_games` drops fully-disabled sections). Post-write in-place
  refresh mirrors `ai/settings_widgets._refresh_settings_page`
  (best-effort `refresh_session_view`). All components
  `audience_tier="administrator"` (the settings-hub gate).
- `sb/manifest/games.py` — `_register_sections()` moved ABOVE the
  MANIFEST construction (the panel install is registry-driven);
  `games.sections` joins the panels facet + `ENSURE_REFS`.
- `sb/domain/settings/panels.py` — the `("games", "Games", "🎮", …)`
  group APPENDED to `_HUB_GROUPS` (after the 19 shipped groups — their
  golden option order survives).
- `sb/domain/settings/handlers.py` — `settings.open_group` routes via
  the new `_GROUP_PANELS` mapping (`games` → `games.sections`) BEFORE
  the operator-spine check. **Flag (PL-001):** the `f"{group}.hub"`
  convention cannot carry this group — `games.hub` is the PLAYER games
  hub (band-6 parity flip) — so a dedicated-panel mapping is the honest
  route; next dedicated group page reuses the dict.
- **Golden re-cut (flagged):** the three settings goldens
  (`settings_hub_open`, `sweep_settings`, `sweep_slash_settings`) carry
  the 20th `subsystem_select` option — settings is `ported`, the
  n-parity gate replays these bytes; the option payload mirrors
  `sb/adapters/parity/transport.py::_option_payload` exactly. The hub's
  golden-pinned "`groups`: 19" Inventory literal is left as shipped
  (under-port literal per the module doc) — flagged, not drifted.
- Tests (14 new): `tests/unit/band6/test_band6_game_sections_panel.py`
  (spec shape/fences/manifest install; providers over stubbed reads;
  enable-all N×None writes + guild guard + failed-write honesty; pick
  diff/no-op/empty-selection/guard/failure; hub roster + routing);
  `test_band6_settings_panels.py` roster expectation grows `games`.
- Gates: pytest 2084 passed / 13 skipped; `manifest_compile.py` green
  post `--write` (new panel, NO new field roles — `check_schema_growth`
  clean, ledger untouched); full checker fleet green (`check_sim_gate`
  auto-exempts the panel: 4 declared actions+selectors = below floor);
  `bootstrap.py check --strict` red ONLY on this card's designed
  born-red hold + the known mining-lane claims advisory.
- Layout budget: 2 selects + 1 shared button row + nav = 4 rows /
  5 components; headroom to 3 sections before paging is needed. Adding
  a disable-all (the design doc does NOT name one) would cross the
  sim-gate below-floor threshold (>4 components) — deliberately not
  added.

## 💡 Session idea

The enable-all/pick handlers read-then-write per game with no fence —
two racing operators can interleave diffs (last-write-wins per row;
harmless for idempotent None/False writes but the ack counts can lie).
When the governance `enabled_map` batch read lands (slice-1 card idea,
slice c), thread it here too: one read per submit instead of N, and the
diff becomes atomic against one snapshot.

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
