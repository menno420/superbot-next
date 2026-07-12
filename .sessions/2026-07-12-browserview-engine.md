# 2026-07-12 — the shared BrowserView engine (flag 41 / D-0034, slice 1)

> **Status:** `in-progress`

- **📊 Model:** Claude Opus 4.8 · high · feature build (flag 41 / D-0034)

## Scope

Slice 1 of the UI-restoration lane: build the GENERIC, kernel-level
BrowserView engine (§2.3; D-0034 deviation (2)) that renders interactive
sort / filter / paging controls for any Table/List block whose ListSpec /
TableSpec declares `sort_options` / `filter_options` / a page size, and
routes their clicks back through the ALREADY-live component adapter →
`resolve()` seam (D-0053) to re-render the panel with the new state.

DELIBERATELY WITHOUT the surface conversions — inventory detail,
leaderboards, dex, fishlog, recipe browsers stay static (their declared
sort/filter options are honest data today, armed in slice 2). The engine is
built + wired behind the existing declarations + exercised by contract
tests; the default render path (`browse=None`) is byte-identical to the
pre-engine renderer, so no golden churns.

## Delivered

- `sb/kernel/panels/browserview.py` (new) — the pure engine: the
  deterministic filter→sort→paginate algebra (`browse_page`, stable sort
  with a `-key` descending marker, bounds-clamped `paginate`), the state
  codec (`encode`/`decode` over the `nav:browse:<control>:<panel_id>:<block>:
  <sort_idx>:<filter_idx>:<page>` grammar), `apply_delta` (the click's state
  transition — selects carry their new value in the interaction's `values`,
  buttons step the page), and `browse_controls` (the sort/filter selects +
  prev/next/page-indicator RenderedComponents, disabled at the paging
  bounds). Stdlib-only; the sole sibling import is the render model.
- `sb/kernel/panels/render.py` — `render_panel(..., browse=None)`: when a
  `BrowseState` is supplied the named block is filtered/sorted/paged and the
  controls are injected outside the layout search space (the page-turn nav's
  richer sibling). Every browse addition is guarded by `browse is not None`,
  so the default render is unchanged.
- `sb/kernel/panels/registry.py` — `NAV_BROWSE_ID_PREFIX` constant (the
  browse control family joins the `nav:*` namespace).
- `sb/kernel/panels/router.py` — `route()` recognizes the `nav:browse:`
  family and returns `NavBinding(kind="browse")`. Combinatorial state ⇒
  parsed at click time (never pre-minted into the static table), but it
  dispatches through the SAME NavBinding → panel-engine seam as page-turn;
  `nav` is not a scheme-version token, so no dynamic id is shadowed.
- `sb/kernel/panels/engine.py` — `handle_nav` grows a `browse` branch →
  `_handle_browse`: decode against the panel spec, apply the delta, re-render
  with the new state (data re-resolved fresh at click time, §2.4). A
  malformed/stale id degrades to the §3.4 polite-expiry terminal, never a
  crash.
- `sb/kernel/interaction/adapters/component.py` — the NavBinding dispatch
  threads the interaction's `values` into the nav request so browse
  sort/filter selects round-trip their selection (harmless for the
  value-less nav kinds).
- Tests: `tests/unit/panels/test_browserview.py` (37 — sort per declared key
  + stability, filter per option + "all", paging first/middle/last/single/
  empty + bounds, encode/decode round-trip, custom_id grammar, apply_delta,
  control bounds-disable) + `tests/unit/panels/test_browserview_contract.py`
  (8 — the engine honors ListSpec declarations, a click re-resolves to the
  expected page/sort/filter through the SAME `dispatch_component` seam other
  components use, the default render emits no controls).

## Evidence

- `python3 -m pytest tests/ -q` → 1772 passed, 8 skipped (the skips are the
  real-Postgres integration tests, run in CI's golden-parity job).
- `python3 bootstrap.py check --strict` → all checks passed (1 pre-existing
  owner-action advisory on control/status.md, untouched by this PR).
- Architecture + manifest + compat gates all green locally
  (symbol_shadowing / no_skip / config_usage / metric_cardinality / egress /
  money_race / manifest_compile / namespace / escape_hatches / schema_growth
  / amendments / compat_frozen / sim_gate / parity_depth).
- `run_golden_parity.py --gate` needs Postgres + asyncpg (unavailable in this
  container — reports RED-no-binding, exit 0); the required leg runs in CI.
  Because every browse addition is behind `browse=None`, the default render
  is byte-identical → no golden is expected to churn.

## 💡 Session idea

Slice 2's cheapest first arm is the inventory category detail panel (D-0034
deviation (2) names it by hand): its `ListSpec` already declares
`sort_options=("rarity","quantity","name")` / `filter_options=<types>` /
`default_sort="rarity"`. The only real work is (a) making the detail
provider emit ROW DICTS (name/type/quantity/rarity) instead of the
pre-rendered lines it emits today, plus a `sort_of` that returns the rarity
RANK so "rarity" reads rarest-first (the oracle's `service.sort_items`
semantics — the engine sorts ascending, so declare `-rarity` or feed a rank),
and (b) opening the detail panel through `render_panel(browse=default_state)`
instead of the static path. The golden for the detail panel WILL then change
(it gains the controls) — that is the surface-conversion churn slice 2 owns,
and it needs a golden re-cut + owner presentation sign-off on the control
copy (Sort/Filter/All labels + the page-indicator format are engine defaults
I chose faithful-to-oracle-intent, not oracle-pinned — flagged for the owner).

## Guard recipe

The engine's non-churn guarantee lives in ONE place: every browse branch in
`sb/kernel/panels/render.py` is gated by `browse is not None` (search the
file for `armed = browse is not None`). If a future edit renders browse
controls on the default path, `run_golden_parity.py --gate` will churn every
list/table golden — the guard is `render_panel(spec, ctx)` (no browse kwarg)
must equal the pre-engine output; the regression test is
`tests/unit/panels/test_browserview_contract.py::test_render_no_browse_is_unchanged_static_view`.

## ⟲ previous-session review

The channel-ops enabler card (#242) set the pattern this slice mirrors: an
ENGINE/ENABLER slice that ships the machinery and PARKS the flip
(surface conversion) for a named later PR, keeping parity/goldens frozen by
construction. That card's discipline — "build the port, park the blocked
declaration, name the successor precisely" — made the slice-1/slice-2 cut
here a lookup rather than a judgement call. What the surrounding records
under-specified: the exact seam a browse click rides. D-0053's component-feed
card documents the click→`dispatch_component`→`resolve()` path but not that
NavBinding dispatch DROPS the interaction's `values` (args={}) — a browse
select would have silently lost its selection. A one-line "nav dispatch
carries no select values" note in the component-feed card would have saved a
grep pass; this card records it (the `component.py` NavBinding branch now
threads `values`).
