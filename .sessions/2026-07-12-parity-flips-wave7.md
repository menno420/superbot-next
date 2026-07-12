# 2026-07-12 — parity flips wave 7 (the money-race-family flips: farm · fishing · mining — the last three real pending rows)

> **Status:** `complete`

- **📊 Model:** Fable · high · feature build (Q-0194 / ORDER 012)

## Scope

The parity-flips lane's wave 7: the three games-family rows the wave-6
card named as "the remaining flip map's three real rows" — farm,
fishing, mining — each flipped pending→ported in its own
squash-merged-on-green PR on the 6-check ruleset (`report`
red-by-design, non-required). All three rows sit downstream of the
#217 money-race locking fixes, so every diff was audited against the
F-001/F-002 legs it must NOT disturb. Main moved around this lane as
usual (#232/#234/#235/#237/#238/#239 from the band-7 successor lane
landed interleaved); every count below is re-verified at the current
HEAD `553ff2b` (#240's merge, main HEAD at wrap-up), not replayed from
mid-wave memory. This wrap-up card + its telemetry row + the status
fold ride the wrap-up PR (control fast lane, docs-only — trap 25: no
Postgres ladder in the wrap-up seat; counts are CI-LOG-VERIFIED
instead).

## The three PRs (each merge sha verified against `git log origin/main` at `553ff2b`)

1. **#233** `c3e8ad0` — farm pending→ported (1/1 goldens,
   sweep_farm). `farm.hub` reshaped to the shipped `FarmMenuView`
   (Collect/Shop/Refresh, purple embed, live fields + balance footer
   via renderer_override, session_lifecycle) and the `FarmShopView`
   sub-panel ported (sb/domain/farm/panels.py — both views anchored to
   disbot/views/farm/menu.py). ONE depth exemption
   `table:chicken_farm` under the EXISTING time-driven class (rows
   land only on the passive timer; none of the three K7 money lanes
   ever ran in capture). The #217 locking paths were untouched by
   construction: a render-only diff — farm's store.py/ops.py are not
   in the diff at all (manifest.snapshot.json / parity.yml /
   sb/domain/farm/panels.py / sb/manifest/farm.py, 4 files).
   Ladder discipline note ledgered in-PR: `pytest tests/unit
   tests/integration` in ONE invocation fails 4 money-race cases on
   PRISTINE main — pre-existing cross-suite pollution, not this diff;
   the canonical ladder runs the suites separately.
2. **#236** `c1f56cd` — fishing pending→ported (2/2 goldens,
   sweep_fish + sweep_fishlog). `!fish` reshaped to the shipped
   begin_cast lane (sb/domain/fishing/service.py — fishing_energy
   store + migration 0035, energy math + daily sha256 weather
   verbatim, the waiting-for-a-bite cast_panel session panel via
   renderer_override); `!fishlog` the shipped 32-species fishdex
   embed. THE DATE-SEED FINDING: the capture harness never patched
   `datetime.now` — the golden's weather byte is the CAPTURE DAY's
   sha256 draw, so replay seeds the capture-date value per case via
   the new `CAPTURE_WORLD_WEATHER` runner map
   (sb/adapters/parity/runner.py:133, `"sweep.fish": "rain"` —
   the #163/#167 reseed lane extended to the shipped unpatched
   wall-clock read). Migration-number collision handled forward:
   the branch's 0034 collided with #234's `0034_btd6_data_blobs` on
   forward-merge — renumbered to `0035_fishing_energy.sql` with
   checksums.json keeping BOTH rows. ONE depth exemption
   `table:fishing_catch_log` under the EXISTING time-driven class
   (rows land only at bite resolution inside the interactive cast
   session — the rps_players precedent). #217 locking untouched: no
   FOR UPDATE / advisory / txn-boundary edits, games wager/store not
   in the diff. Ratchet fishing {events: 1, tables: 3, settings: 0}.
3. **#240** `553ff2b` — mining pending→ported (6/6 goldens — the 2
   mining sweeps + 4 strays re-homed `_unmapped`→mining:
   sweep_fastmine / sweep_chop / sweep_explore /
   sweep_reset_inventory). Shipped core-loop bytes verbatim
   (!fastmine swing, !chop, !explore, the !mine capture-artifact
   copy, !reset_inventory admin wipe) plus the ANCHORED MiningHubView
   (sb/domain/mining/panels.py — 7 persistent `mining:*`
   `custom_id_override` ids, dark_grey token, live-overview fields
   via renderer_override; the golden pins the panel_anchors row —
   goldens/mining/sweep_minemenu.json — so anchored semantics, NOT
   session_lifecycle). The re-home retired wave-6's promissory notes:
   the #230 game_xp covered-elsewhere citations re-pathed
   `_unmapped`→mining AND upgraded to PORTED-row coverage
   (parity/parity.yml table:game_xp / event:game_xp.awarded /
   event:game_xp.level_up now cite goldens/mining/* replaying green
   through the ported row). game_xp substrate moved to shipped
   shapes (migration 0036_game_xp_shipped_types.sql + the corpus
   event payload). RNG determinism: mining ops moved to the
   module-global random stream the runner reseeds per case, with
   seed-42 trajectories verified BEFORE the build. ONE depth
   exemption `table:mining_player_state` under the EXISTING
   guard-only-capture class (D-0069 — the captured !descend/!ascend
   sweeps pin the shipped GUARD bytes with no row; the geared descent
   exists in no imported golden). #217 locking untouched: no FOR
   UPDATE / advisory / txn-boundary edits — games store/ops edits are
   ADDITIVE game_xp accessors only — and check_money_race green in
   the same CI. Ratchet mining {events: 2, tables: 5, settings: 0}.
   Side repair ledgered in-PR: the shared dev Postgres ledger was
   healed (0034's DDL applied, its checksum row corrected).

## End counts (wave-7 END state, CI-LOG-VERIFIED at main `553ff2b`, #240's merge)

- gate **GREEN 355/355 across 48 ported** (47 subsystem rows + the
  kernel coverage home) — main-push golden-parity run 29182868238
  gate job 86623673864: "gate: GREEN — all 355 golden(s) across 48
  ported subsystem(s) replay clean" + "golden-parity gate: 48 ported /
  3 pending" with the pending table _unmapped [107 goldens] /
  quicksetup [1 goldens] / setup [8 goldens] + "check_parity_depth:
  OK — 50 subsystems (47 ported), kernel ported, 471 goldens" (same
  job); integration 11 passed same job (the F-001/F-002 real-Postgres
  concurrency regressions INCLUDED — the locking-untouched claim is
  CI-proven, not asserted).
- report **361/471 green, 471/471 replayable** — report job
  86623673865 same run: "green: 361/471 replayed cases match their
  golden" + "replayable: 471/471" + "ported: 48/51 subsystems" with
  farm 1/1 · fishing 2/2 · mining 6/6 green [ported] in the
  per-subsystem table; "report: RED — 110 golden(s) not yet at parity
  (EXPECTED until the last subsystem flips ported)" (red-by-design,
  non-required).
- units **1713 passed / 8 skipped in CI** (ci run 29182868237 tests
  job 86623673877 — the deps-free CI shape; local canonical ladders
  with deps differ by the standing guarded-import skip delta).
- corpus **471 = 465 imported + 6 minted** (unchanged this wave — all
  three flips rode imported/re-homed goldens, zero mints);
  `_unmapped` **111→107** at HEAD (wave movement: sweep_fastmine +
  sweep_chop + sweep_explore + sweep_reset_inventory → mining at
  #240; hand-verified 107 files in parity/goldens/_unmapped at HEAD).
- parity **47/50 subsystem rows ported** + kernel home ported =
  **48/50 program rows**. Remaining pending (verified in parity.yml
  AND the gate job's pending table at HEAD): **setup** (8 goldens,
  PARKED at the create-channel wall, trap 17), **quicksetup** (1,
  BLOCKED D-0030), plus the `_unmapped` re-home pool (107). NOTHING
  ELSE IS PENDING — every real subsystem row is ported; both
  remaining walls are owner-shaped.

## Traps confirmed / new intel

- **Date-seeded daily surfaces**: when the shipped surface derives
  from the calendar date (fishing's daily sha256 weather) and the
  capture harness never patched `datetime.now`, replay must seed the
  CAPTURE-DATE value per case — the `CAPTURE_WORLD_*` runner-map
  lane, never a datetime monkeypatch in domain code (#236).
- **Money-race domains flip cleanly** when the diff never touches the
  store/ops locking legs: panels/manifest reshapes + ADDITIVE store
  fns only; check_money_race + the CI F-001/F-002 integration leg
  are the proof, cited per-PR (#233 render-only / #236 no-store-diff
  / #240 additive-only + checker green).
- **Forward-merge migration-number collisions**: renumber the
  branch's migration to the next free slot and keep BOTH checksum
  rows — never rewrite the landed sibling's row (#236, 0034→0035).
- **Anchored hubs vs session hubs**: when the golden pins a
  panel_anchors row, the hub rides persistent `custom_id_override`
  ids — NOT the session-lifecycle default that most wave-6 hubs took
  (#240 vs the #233 farm hub in the SAME wave; read the golden's
  anchor block before choosing the lifecycle).
- **Loot/RNG determinism**: port loot ops onto the module-global
  random stream the runner reseeds per case and verify the seed-42
  trajectories BEFORE building panels on top (#240; the four_twenty
  #227 precedent generalized).
- **One-invocation suite pollution**: `pytest tests/unit
  tests/integration` in a single invocation fails 4 money-race cases
  on PRISTINE main — pre-existing cross-suite pollution, run the
  suites separately (#233 ledger; not fixed this wave, follow-up
  candidate).
- Trap 25 honored: wrap-up seat ran no Postgres ladder; every count
  above is CI-log-verified at the merge sha.

## Verification

Merge shas verified against `git log origin/main` at `553ff2b` (farm
`c3e8ad0a5d71f3d86cd75810edd1f67bab78091f`, fishing
`c1f56cd769ef3348b52b581d32c2e689734ffdfe`, mining
`553ff2b9ff50ba13a7a48c3ea0724dc350eca049`); end counts
CI-LOG-VERIFIED at that sha (run/job ids per claim above);
parity.yml statuses re-read at HEAD (47 ported / 3 pending
hand-counted; kernel: ported); `_unmapped` 107 / setup 8 /
quicksetup 1 hand-counted on disk at HEAD; source anchors for every
wave fact re-verified at HEAD (FarmMenuView/FarmShopView in
sb/domain/farm/panels.py, begin_cast in sb/domain/fishing/service.py,
CAPTURE_WORLD_WEATHER at sb/adapters/parity/runner.py:133,
`mining:*` custom_id_override in sb/domain/mining/panels.py, the
chicken_farm/fishing_catch_log/mining_player_state exemption rows and
the re-pathed game_xp citations in parity/parity.yml, migrations
0035/0036 on disk); `python3 bootstrap.py check --strict` green at
the wrap-up head.

## 💡 Session idea

The parity program's agent-shaped work is now ONE lane: the residual
`_unmapped` re-home sweep (107 goldens). The wave-5 histogram minus
everything since says the bulk is btd6-family sweeps over the PORTED
btd6 row (~62 — pure flip-sized re-homes per the #193 law, no port
work) plus small stray families; a single re-home wave could plausibly
take `_unmapped` under 40 and turn the report job's biggest red block
green. Setup (trap 17) and quicksetup (D-0030) stay owner-shaped —
the honest end-state short of owner action is `_unmapped` ≈ the
setup-family strays only. Sequencing note: run the re-home wave AFTER
the band-7 successor lane's btd6 slices settle, since both touch the
btd6 goldens dir.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-parity-flips-wave6.md`, this lane's
direct predecessor.) Its 💡 idea was this wave's exact map and priced
it right: fishing + mining DID flip together naturally with their
`_unmapped` game sweeps re-homing WITH the flips, and the #230 game_xp
covered-elsewhere citations WERE converted to direct coverage in the
same motion — the exemption rows' own text had named the successor,
and the successor executed it (#240). Farm rode the same band as
predicted. Its doctrine entries held without friction: exemption-class
honesty priced all three of this wave's exemptions into EXISTING
classes (time-driven twice, guard-only-capture once — zero vocabulary
growth for the second wave running), and the static-id-hub rule
(custom_id_override, no `_mint_ephemeral`) was exercised again by the
mining hub. What it under-called: it filed the wave as "three real
rows + two walls" as if the three were uniform, but the three differed
sharply in mechanism — farm was a render-only afternoon, fishing
forced a NEW replay-vocabulary seam (the capture-date weather map),
mining carried substrate work (game_xp shapes, migration 0036, RNG
stream discipline). The flip-count metric hides port-depth variance;
the wave-8 planner should price by golden count TIMES substrate
distance. One thing it could not have foreseen: the #217 money-race
fixes turned out to be an asset, not a hazard — the CI F-001/F-002
integration leg gave every flip PR a free locking-regression proof.
