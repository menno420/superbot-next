# 2026-07-12 — arm the browse surfaces on the shared engine (D-0034, slice 2)

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · feature build (flag 41 / D-0034)

## Scope

Slice 2 of the UI-restoration lane, STACKED on slice 1 (the shared
BrowserView engine, PR #270 / `browserview-engine-k8`, not yet merged).
Convert the declared-but-static browse surfaces so their in-panel
sort / filter / page controls are LIVE through the slice-1 engine —
using `render_panel(browse=…)` as the arming hook, wiring each surface's
DECLARED `sort_options` / `filter_options` (never inventing options).

Only **inventory detail** qualifies: it is the SOLE surface in the whole
`sb/domain/` tree that declares a `ListSpec` / `TableSpec` browse algebra.
The other named targets (leaderboards, dex/creature, fishlog, recipe
browsers) declare NO `ListBlock` / `TableBlock` at all — arming them would
require inventing sort/filter options, which the slice forbids. They are
flagged as out-of-scope-by-construction, not skipped-by-failure.

## Delivered

- `sb/domain/inventory/service.py` — `inventory_row(item_key, qty, meta)`:
  the browse ROW the detail provider emits, carrying exactly the declared
  sort/filter keys — `name` (item key), `quantity` (int), `rarity` (the
  `RARITY_ORDER` RANK so an ASCENDING sort is rarest-first — a raw rarity
  STRING would sort alphabetically, not by tier), `type` (the filter value),
  and `_line` (the shipped `item_line` + the rarity tag the oracle's flat
  sort modes append). The rank lives in the ROW, not a custom `sort_of`,
  because the engine sorts each block with its DEFAULT field accessor.
- `sb/domain/inventory/panels.py` — the detail surface armed:
  - `render_line` renders a browse row via its `_line` key (a bare string
    still renders verbatim — the pre-engine fallback);
  - the detail provider emits ROWS (pre-sorted alpha by item key, so the
    engine's STABLE sort breaks every tie alpha — the shipped "alpha within
    a tier" / "alpha within a quantity" order);
  - the `ListSpec` arms the shipped algebra: `page_size=8` (the shipped
    `_PER_PAGE` detail slice — the engine paginates flat rows, so no header
    budget is needed), `sort_options=("rarity", "-quantity", "name")` (the
    `-quantity` descending marker = the shipped highest-first quantity sort;
    the option LABEL and SET stay rarity / quantity / name), `default_sort`
    and `filter_options` unchanged.
- `sb/kernel/panels/browserview.py` — `default_browse_state(spec)`: the
  BrowseState a fresh OPEN arms — the first block that DECLARES an algebra
  opens on its `default_sort`, no filter, page 0. A spec with no browsable
  block returns None (the byte-identical static render). Arming is by
  DECLARATION — no schema field grown.
- `sb/kernel/panels/engine.py` — `_render_and_present` auto-arms
  `default_browse_state(spec)` on a fresh OPEN / nav-back (browse is None);
  a control click still carries its own explicit BrowseState via
  `_handle_browse`. Non-browsable panels yield None → unchanged static
  render. Only the `render_panel` branch is touched; `renderer_override`
  (the inventory HUB) is untouched, so the hub golden does not churn.
- `manifest.snapshot.json` — regenerated (`manifest_compile --write`): the
  scoped diff is `page_size 12→8` + `quantity → -quantity` on the 8 detail
  panels + the stable_hash. No frozen compat field changed
  (`check_compat_frozen` green).
- Tests: `tests/unit/band3/test_band3_treasury_inventory.py`
  (`inventory_row` shape + rank + `_line`; the provider emits rows sorted by
  key), `tests/unit/panels/test_browserview.py` (`default_browse_state` arms
  the declared block / returns None without one), and the two band-3
  panel-action contract tests re-pointed to the armed shape (the sanctioned
  conversion churn).

## Evidence (local; golden replay is CI-only — no local Postgres)

- `pytest tests/ -q` → **1776 passed, 8 skipped**.
- `bootstrap.py check --strict` → **all checks passed** (the sole warning is
  a pre-existing owner-action advisory on `control/status.md`, untouched).
- `check_compat_frozen` → **OK — compat artifacts match the pin**.
- `check_parity_depth` → **OK — 51 subsystems (50 ported), kernel ported,
  468 goldens**.
- `check_money_race` → **OK — 0 violations**; `check_sim_gate` → **OK**.
- `run_golden_parity --gate` → RED **only** on the local binding failure
  (`Postgres unavailable: asyncpg is not installed`); it runs in CI. **No
  golden file changed** — the sole inventory golden (`sweep_inventory.json`)
  exercises the EMPTY hub, never the detail panel, so nothing re-mints.

## ⚑ Flags (owner hand-pass)

- **Presentation deviation (owner sign-off):** the generic engine renders a
  FLAT sorted list with SELECT sort/filter controls + a page indicator; the
  oracle's bespoke view used a cycling sort BUTTON (`🔀 Sort: X`), per-tier
  grouped headers when rarity-sorted, `"Filter by type…"` / `"All types"`
  chrome, and `"◀ Prev"` / `"Next ▶"` labels. That chrome is slice-1
  engine-owned (generic); the surface ships faithful-to-oracle DATA
  (row lines, sort semantics, filter set, empty-state, page size) — the
  control CHROME is an owner presentation hand-pass, not a data change.
- **`quantity → -quantity`:** the descending marker corrects the sort
  DIRECTION to the shipped highest-first semantic using slice-1's documented
  `-key` mechanism; the visible option label/set is unchanged. Flagged as a
  direction correction, not a new option.
- **Surfaces #2–#5 out of scope:** leaderboards / dex / fishlog / recipe
  browsers declare no `ListSpec`/`TableSpec` — not "declared-but-static", so
  arming them faithfully needs a prior declarative-panel build (a successor
  slice), never invented options here.

## 💡 Session idea

The auto-arm-by-declaration policy (`default_browse_state`) means the next
surface's conversion is pure DECLARATION: give it a `ListBlock` + a row
provider and it arms itself. The cheapest genuine second surface is whichever
domain gets a declarative list panel FIRST — the engine wiring is now done,
so slice 3 is a domain-panel build, not a kernel change.
