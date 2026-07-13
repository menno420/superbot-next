# Curation rework — BTD6 paragon delta port — `curation-rework-btd6-paragon-delta`

> **CLAIM (2026-07-13)** — arbitration delta lane. PR #339
> (`claude/btd6-paragon-calculator`, claim committed 01:16:21Z) holds the
> SENIOR claim on the btd6 paragon surface; PR #336
> (`claude/curation-rework-btd6-paragon`, claim stamped 01:45:05Z) is the
> junior duplicate and closes. This lane ports ONLY the real deltas #336
> carried that #339 lacks, onto #339's head (base PR = #339's branch):
> the 📊 Stats per-degree drill-down (`btd6.paragon_stats` panel — degree
> milestone select + 🔢 Enter-degree modal — over the ported
> `stats.paragon_stats_at_degree` / `paragon_degrees` formulas, the view
> #339 explicitly deferred) and the least-tiers/least-pops reverse-solver
> axis pins.

**Scope.** `sb/domain/btd6/paragon_panel.py`, `sb/domain/btd6/panels.py`
(stats spec + degree modal), `sb/manifest/btd6.py`, `manifest.snapshot.json`,
`compat/compat-frozen.json` (one modal root), `tests/unit/band7/`. No
migrations, no stores, no goldens re-minted (the stats click route is
golden-unpinned, #151's class).

- `curation-rework-btd6-paragon-delta` · **arbitration delta — port #336's paragon stats degree view + solver axis pins onto #339's head** — `btd6.paragon_stats` panel (milestone select + degree modal) over the ported per-degree formulas; least-tiers/least-pops oracle pins · sb/domain/btd6/, sb/manifest/btd6.py, manifest.snapshot.json, compat/, tests/unit/band7/ · 2026-07-13
