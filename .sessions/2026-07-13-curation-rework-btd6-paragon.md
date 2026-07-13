# 2026-07-13 — curation rework: btd6 paragon wiring (ORDER 017 item 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · NIGHT-RUN curation rework · mandate: ORDER 017
  item 2 (curation report PR #327, chunk 6)

## Scope

Wire the BTD6 Paragon calculator surface — `btd6.paragon` calc /
requirements / stats buttons plus their 4 selects — onto the ported
paragon math (`sb/domain/btd6/paragon_math.py`, `paragon_degrees.py`,
`stats.py`), retiring the `btd6.paragon_pending` terminals
(sb/domain/btd6/service.py:366, panels.py:348-403). This is D-0046's
named successor port ("the paragon power calculator (sacrifice
math/reverse solver)"). Oracle: disbot views/btd6/paragon_view.py +
paragon_modals.py + services/paragon_service.py — copy/fields matched
where the ported math exposes them; no invented numbers. No stores, no
migrations; goldens/btd6/sweep_paragon pins the initial open only and
must stay byte-identical.

## What shipped

- **Math** — `paragon_math.py` grows the oracle's forward power model
  (`compute_breakdown`, live-API-validated), the reverse solver
  (`solve_requirements`), typed models, `validate_inputs`, `base_price`
  over the ported difficulty util — `utils/btd6/paragon_math.py`
  @7f7628e1 verbatim; unit pins ported from the oracle's own
  `tests/unit/btd6/test_paragon_math.py` (incl. the 86,444-power /
  Degree-68 forward example and the solo-sub-d100 = 20-totems tip).
- **Surface** — new `sb/domain/btd6/paragon_surface.py` (9 handlers +
  shipped embed builders): selects fold picks into a state re-open (the
  ai policy widgets' `_open_page` posture); 🧮 Calculate = the shipped
  ParagonForwardModal twin (G-10) → local result card; 🎯 Requirements
  = new `btd6.paragon_requirements` config page → target form → reverse
  solve card; 📊 Stats = new `btd6.paragon_stats` degree view over the
  PORTED `stats.paragon_stats_at_degree`. `panels.py`: provider-fed
  selects (state-aware defaults + shipped extra-T5 rebound), 3 modal
  specs, 2 new session panels + renderers. `service.py`:
  `btd6.paragon_pending` RETIRED.
- **Honesty ledger** — no live API: the shipped `paragon_service`
  reconciliation stays a successor lane; every result carries the local-
  estimate label (gold accent + "estimate" footer, the shipped fallback
  branch, reworded "not armed in this build"). Extra-T5 select can't
  render *disabled* (no grammar facet) — shipped single option kept +
  server-side clamp. Stats page opens at Degree 1 (base infobox view =
  `degree_row`, still the deep-stats successor).
- **Gates** — golden parity gate GREEN (471/471; sweep_paragon initial
  open byte-identical with provider-fed selects), full suite 2099
  passed / 2 skipped, checker fleet clean, `manifest.snapshot.json`
  recompiled, compat pin amended (+`btd6.paragon_forward_form`).
- 32 new tests in `tests/unit/band7/test_band7_btd6_paragon.py`.

## 💡 Session idea

The panel-args state-re-open posture (select pick → `open_panel` with
folded args) is now used by three lanes (ai policy widgets, settings
widgets, this paragon surface) — worth extracting as a handler-kit
helper (`reopen_with_state(req, panel_id, **delta)` + a
`state_args(req)` strip of `values`/`session_action`) so the next
stateful session panel doesn't re-derive the strip-and-merge rules; the
tier5-clamp-on-render trick (state clamps in the renderer's decode, not
in every handler) belongs in the same note.

## ⟲ Previous-session review

Previous session (completeness table, PR #326) directly enabled this
slice: its btd6 row named `btd6.paragon_pending` as a top gap with a
"self-contained pure-compute port" disposition — accurate; the slice
needed zero stores/migrations, exactly as the table predicted. Friction
inherited and confirmed: its card's `.substrate/guard-fires.jsonl`
warning was reproduced verbatim here (bootstrap check dirties kit
state; `git checkout -- .substrate/…` before staging — guard recipe
still unlanded, a hook candidate). One stale row it leaves behind: the
completeness table's btd6 cell now overstates the gap it named — the
table is a dated snapshot, so this is noted for the NEXT table run, not
edited retroactively.
