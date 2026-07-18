# 2026-07-18 — fishing test-depth: catch/loot math (weight/pearl/roll_catch/band-cap) + populated leaderboard rendering

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`) — releases the born-red HOLD so the server-side
> lander can merge PR #546 on green.

- **📊 Model:** Opus 4 family · high · test-depth
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

- `python3 -m pytest tests/unit -q` → `3409 passed, 2 skipped, 1 warning in 64.02s` (full unit suite, per the ref-table lesson)
- `python3 tools/check_namespace.py` → `check_namespace: clean`
- `python3 tools/check_no_skip.py` → `check_no_skip: clean (every surface funnels through resolve())`

## Deviation ledger

- **Gap-6 (roll_coral_drop / roll_bonus_catch) — SKIPPED, already covered.**
  Confirmed in `test_band6_fishing_cast_wiring.py::test_reward_rolls_clamp_and_coral_gating`:
  the `[0,1]` bonus clamp AND the load-bearing no-draw-on-shore coral
  property are both pinned there. Not re-covered — no real uncovered
  branch found, so it was not padded.
- **Timing / reel-boundaries / refusal gates — deliberately untouched.**
  Thoroughly dry in `test_band6_fishing_{minigame_timing,cast_wiring}.py`
  (bite-delay floor, fake-out, reel-window bounds, trophy fight, the
  BLOCKED/quiet-venue/duplicate-guard/stale-token/expired-cast paths).
  There are NO admin permission gates in this domain by design — the
  ops are `authority_ref="user"` invoker-locks — so no gate-ladder gap.
- **Two gap-list anchors were stated with drifted constants; corrected
  against HEAD.** (a) Pearl CAP: the gap said "rank 21 → capped", but
  `pearl_drop_chance(21) == 0.02 + 0.004·20 == 0.10` (uncapped); the
  `0.15` cap first bites at **rank 34** (rank 33 == 0.148 is still
  under). The test pins the true boundary. (b) Leaderboard species
  denominator: the gap said `S/21`, but `top_view` prints
  `len(catalog.SPECIES) == 32` (shore 21 + deepwater 11); the test
  asserts `/{total}` against the live catalog. (c) Band cap: `7·3 == 21`
  already equals the shore cap, so the `min()` only visibly BITES past
  level 7 (band 24 → 21) — the test uses level 8 for the true cap
  boundary plus level 7 for the band==cap equality.
- **No gaps padded.** All five math/render gap clusters covered in 9
  cases; gap-6 skipped as already-covered per the task's own scout note.

## 💡 Session idea

`top_view` and `trophies_view` each independently rebuild the medal
ladder (`["🥇","🥈","🥉"]` → `**{rank+1}.**`) and the `_angler_name`
resolve loop inline — two copies of one "ranked-rows → prefixed lines"
projection that already drifted once (the species-count denominator).
A single `_leaderboard_lines(rows, guild_id, fmt)` helper taking a
per-row formatter would collapse the medal/prefix/name-resolve seam to
one place and let the populated bodies be pinned without a golden —
low-cost, and it removes the only spot where a future rank-emoji change
could silently diverge between the two boards.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-test-depth-xp.md` (xp test-depth, #542) —
the most recent OTHER card and the closest sibling: an additive,
born-red, DB-free characterization slice one band over (band-4 vs this
band-6). Its posture is sound and this fishing slice mirrors its
discipline exactly — full-local `tests/unit` sweep per the ref-table
lesson (it ran 3358 green; this one 3409), both guards clean, born-red
+ flip-last, claim-before-build. Its strongest transferable move is the
**"reframe a drifted gap-list anchor rather than force or drop it"**
habit (its Q-0120 dead negative-level guard finding) — I applied the
same here to three gap-list constants that had drifted off HEAD (pearl
cap rank, the `/32` species denominator, the band-cap boundary level),
pinning the TRUE numbers instead of the stated ones. One caution its
own ledger flags — DB-backed `store.py` SQL stays out of reach DB-free —
holds identically here: `top_fishers`/`top_trophies` and `record_catch`
remain caller-stubbed, their SQL left for a DB-harnessed slice. Confirms
band-4 xp and band-6 fishing loot/render are the current test-depth
frontier.

## Close-out

PR **#546** (menno420/superbot-next) — `tests/unit/band6/test_band6_fishing_loot_math.py`,
**9 DB-free cases**, additive only. Full unit suite (3409 passed) + both
guards green; server-side lander on green. Branch `claude/test-depth-fishing`.
