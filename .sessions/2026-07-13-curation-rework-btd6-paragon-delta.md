# 2026-07-13 — btd6 paragon arbitration delta (stats degree view onto #339)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · arbitration delta lane · mandate: first
  claim wins — #339 (claim 01:16:21Z) is senior over #336 (01:45:05Z) on
  the btd6 paragon surface; #336's REAL deltas port here, onto #339's head

## Scope

Port onto `claude/btd6-paragon-calculator` (PR #339's head, 28f608e) the
deltas its junior duplicate PR #336 carried and it lacks:

1. the 📊 Stats per-degree drill-down #339 explicitly deferred (its module
   doc, ledgered-deviation bullet 3): the `btd6.paragon_stats` panel —
   milestone degree select + 🔢 Enter-degree modal
   (`btd6.paragon_degree_form`) + ↩ Calculator — over the PORTED
   `stats.paragon_stats_at_degree` + `paragon_degrees` formulas (power /
   boss-multiplier / elite-multiplier headline, per-attack scaled cells),
   with #336's oracle pins (Degree 1: power 0, ×1.0, ×2; Degree 100:
   power 200,000, ×2.25, ×4.5; footer `BTD6 stats v55.1`);
2. the reverse-solver least-tiers / least-pops axis-minimisation pins
   (#339 pins least-cash only) + the `least_cash == 0` mid-degree pin.

Definition of done: implemented + tested green on `python3 -m pytest
tests/ -q` + snapshot/compat pins regenerated in the same PR. Base PR =
#339's branch; #336 closes citing this lane. CI parked (Actions dropping
check runs ~03:40Z — no kicks, no merges).
