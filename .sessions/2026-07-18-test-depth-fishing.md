# 2026-07-18 — fishing test-depth: catch/loot math (weight/pearl/roll_catch/band-cap) + populated leaderboard rendering

> **Status:** `in-progress`
>
> Born-red HOLD (per `.sessions/README.md`): this in-progress card is the
> FIRST commit and holds `substrate-gate` red until the deliberate LAST
> commit flips it `complete` — releasing the server-side lander to merge
> on green.

- **📊 Model:** `[[fill: Opus 4 family · high · test-depth]]`
- **Born:** 2026-07-18 (born-red first commit)

## Scope

Test-depth coverage for `sb/domain/fishing` loot MATH + populated
leaderboard rendering — the real thin spots the imported sweeps left
surviving only via mocks/parity goldens:

- `catalog.nominal_weight` / `roll_weight` — the `0.18·rank^1.65` curve,
  the `uniform(0.65, 1.55)` spread band ends, and the `max(0.01, …)`
  weight floor.
- `ops.pearl_drop_chance` / `roll_pearl_drop` — the `0.02 + 0.004/rank`
  linear curve, the `0.15` saturation cap, and both sides of the draw
  threshold.
- `ops.roll_catch` — the `1/rank^(1/pull)` inverse-size weighting, the
  `max(1.0, rarity_pull)` clamp, the big-end flattening, and the
  empty-pool `None` branch.
- `catalog.max_size_rank_for_level` — the `max(1, level)·3` band under
  the `min(band, venue_size_cap)` cap, and the level floor.
- `fishing.top_view` / `fishing.trophies_view` populated bodies — medals
  → `**N.**`, the `caught (S/T species)` line, the 🐟 emoji fallback for
  a species missing from the catalog, and `_angler_name` degrading to
  `User {id}`.

Additive tests ONLY — no product code, no golden, DB-free (injected
`ScriptRng` + monkeypatched `store.*` / `guild_directory`). New file
`tests/unit/band6/test_band6_fishing_loot_math.py`. The bite/reel TIMING
state machine, reel-boundaries, and refusal/BLOCKED gates are ALREADY
thoroughly covered (test_band6_fishing_minigame_timing.py,
test_band6_fishing_cast_wiring.py) — this PR deliberately does not touch
them. Born-red card, tests second, flip-last; server-side lander on green.

## Verification

- `python3 -m pytest tests/unit -q` → `[[fill: tail]]`
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface funnels through resolve())`

## Deviation ledger

`[[fill: skipped/already-covered gaps]]`

## 💡 Session idea

`[[fill]]`

## ⟲ Previous-session review

`[[fill]]`

## Close-out

`[[fill: PR # + test count]]`
