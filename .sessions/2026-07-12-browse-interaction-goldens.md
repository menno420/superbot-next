# 2026-07-12 — mint the browse-interaction goldens (D-0034 capstone)

> **Status:** `in-progress`

- **📊 Model:** Claude Opus 4.8 · high · feature build (D-0034 / D-0073 — interaction goldens)

## Scope

The interaction-golden CAPSTONE of the UI-restoration lane, STACKED on
slice 3 (`dex-browse`, PR #288 → slice 2 `browse-surfaces-convert` #279 →
the engine #270, all unmerged). Slices 1–3 ARMED the shared BrowserView
engine and two browse surfaces (inventory detail sort/filter/page + the
dex element filter) but deliberately shipped ZERO golden churn — no golden
CLICKED a browse control. That left the corpus's real interaction blind
spot open: ~470 goldens, all single-step but ONE (the blackjack Hit
button), and the sort/filter SELECTS had no coverage at all. This session
mints the multi-step click/select→re-render goldens that close it, using
the D-0073 sanctioned mint procedure (capture_case + kernel-spine strip).

## Plan

- Restore local Postgres (prior workers wrongly reported asyncpg
  unavailable — the cluster is wiped on container restart, not absent).
- Grow the replay CLICK vocabulary to carry a select's chosen `values`
  (the D-0073 modal-`fields` twin on the click kind) so the SELECT goldens
  self-document what was picked.
- Add curated typed cases (the blackjack-click precedent: session hub
  buttons need `component_index`; the inventory seed needs `fixture_sql`)
  that open the panel → drive a `nav:browse:*` sort/filter/page click or
  the dex element-filter select → capture the RE-RENDERED panel.
- Mint the goldens via `capture_case` + `apply_dispositions` (kernel-spine
  stripped, matching D-0073); update the corpus count pins.
- Gate green including the new goldens; land READY, base `dex-browse`.

## ⟲ Previous-session review

(pending — filled at close-out)

## ⚑ Flags

(pending — filled at close-out)
