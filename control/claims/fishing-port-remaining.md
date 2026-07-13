# Fishing port — remaining 13 commands lane claim — `fishing-port-remaining`

> **CLAIM (2026-07-13)** — fishing-port lane (SuperBot World night run, ORDER
> 017). This lane claims the port of the **13 remaining `_pending` fishing
> commands** so a concurrent fleet does not duplicate any slice. Supersedes the
> walled fishing session's unpushed local build; earlier-at-HEAD claim wins on
> any collision.

**Scope.** The 13 remaining `_pending` fishing commands — `rod`, `bait`,
`craftbait`, `craftcharm`, `craftrod`, `rodrecipes`, `craftpearl`, `curios`,
`craftcurio`, `tidepool`, `dock`, `boathouse`, `fishery` — plus their 13
`parity/goldens/_unmapped/sweep_*` goldens, `sb/manifest/fishing.py`, new
`sb/domain/fishing/*` modules, the `parity/parity.yml` fishing section, and
migrations **0049+**.

**EXCLUDED — forecast / sail.** `forecast` + `sail` + migration 0048 +
`sweep_forecast`/`sweep_sail` are owned by PR #313
(`claude/fishing-slice1-forecast-sail`, merged to main at this claim's HEAD);
we build atop it, not over it.

**Planned shape.** 3 stacked slices, each its own PR, born-red card + telemetry
row per PR. Branch prefix `claude/fishing-`.

- `fishing-port-remaining` · **fishing port — all 13 remaining `_pending` fishing commands (rod, bait, craftbait, craftcharm, craftrod, rodrecipes, craftpearl, curios, craftcurio, tidepool, dock, boathouse, fishery)** — port commands + retire their 13 `_unmapped` sweep goldens; EXCLUDES forecast/sail/migration 0048 (PR #313, merged; built atop) · sb/domain/fishing/, sb/manifest/fishing.py, parity/goldens/_unmapped/sweep_*, parity/parity.yml, migrations/0049+ · 2026-07-13
- `fishing-slice2-gear-reads` · **slice 2 — gear/reads: rod, bait, rodrecipes, curios** — read/guard surface + gear state · sb/domain/fishing/, parity/ · 2026-07-13
- `fishing-slice3-craft` · **slice 3 — craft: craftbait, craftcharm, craftrod, craftpearl, craftcurio** — crafting writes + recipes · sb/domain/fishing/, parity/, migrations/ · 2026-07-13
- `fishing-slice4-locations-structures` · **slice 4 — locations/structures: tidepool, dock, boathouse, fishery** — venue/structure surface · sb/domain/fishing/, parity/, migrations/ · 2026-07-13
