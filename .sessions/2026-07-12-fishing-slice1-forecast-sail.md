# 2026-07-12 — fishing depth slice 1 port: forecast / sail (weather + venue)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · high · feature build (Q-0194)

## Scope

The faithful port of fishing depth slice 1 — the first rung of the fishing
gear/venue ladder (the D-0043 named successor scope: "fishing gear/venue
systems"; the mining ladder #286→#300 is complete, creature battle and the
tournament orchestration have landed, so this lane is the first remaining
item in the successor list). Two shipped commands move from honest D-0043
pending terminals to real surfaces: `!forecast` · `!sail`.

Delivered:

- **Domain** (`sb/domain/fishing/venue.py`, NEW): the shipped
  `utils/fishing/venue.py` ported — `SHORE`/`DEEPWATER` keys,
  `VenueProfile` (identity + the minigame numbers, carried as data; the
  shore numbers inlined verbatim from the oracle minigame constants —
  2.5s window, 3.0/6.0/1.5 bite band, 0.06 escape — since the live
  timing layer rides the later rung), `SHORE_PROFILE`/`DEEPWATER_PROFILE`,
  `normalize`/`profile_for`/`toggle`.
- **Store + migration**: `fishing_venue` (per-(user, guild) current venue;
  no row reads as `shore` — the shipped migration-094 shape) as a
  MEMBER_ID registered store with the `fishing.erase_subject_venue`
  delete-erasure body; migration `0048_fishing_venue.sql` (+ checksums).
- **Handlers** (`service.py`): `fishing.forecast_view` (the shipped
  date-seeded forecast embed — title/blurb/effect/footer on the
  fishing.card lane; goldens pin the Rain bytes) and `fishing.sail_route`
  (the shipped `toggle_venue` — plain game-state upsert, no audit, the
  energy-spend posture; the deepwater message is golden-pinned, the dock
  message oracle-source-verbatim). `forecast` + `sail` left `PENDING`;
  their two `*_pending` refs pruned from the composition-parity burn-down
  (trap 12a).
- **Panels**: the hub's "Fishing from" field and the cast footer now read
  the LIVE stored venue profile (no-row → shore = the golden bytes; the
  shipped `build_fishing_menu_embed` / `cast_view` footer interpolate the
  profile); the hub ⛵ Set sail / Dock button repoints
  `fishing.sail_pending` → `fishing.sail_route` (byte-neutral: the golden
  pins label + minted id only).
- **Deferred (D-0043, honest)**: the cast LEG stays at the starter shore
  profile — the venue→cast wiring (deepwater species pool, coral drop,
  minigame difficulty) rides the rod/bait/minigame rung where the
  oracle's rolled knobs land together; no imported golden drives a
  deepwater cast (deviation note updated in ops.py).
- **Parity**: `CAPTURE_WORLD_WEATHER` gains `sweep.forecast: rain` (the
  golden pins the capture-day Rain condition — trap 36a); the 2
  `_unmapped` sweeps (sweep_forecast / sweep_sail) re-homed into the
  gated `fishing` row (#193 law: `git mv` + the one sanctioned
  `subsystem` flip). `fishing_venue` is a NEW declared table surface
  COVERED by sweep_sail's own db_delta row — no exemption; ratchet
  fishing `{tables: 3 → 4}` (`--write-ratchet`, splice-only).

## Verification (local, real Postgres, pristine parity_replay DB)

- **golden-parity GATE GREEN — all 463 golden(s) across 51 ported
  subsystem(s) replay clean** (the +2 re-home takes fishing 7 → 9,
  `_unmapped` 15 → 13).
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  476 goldens**; `fishing_venue` covered (no new exemption row).
- **check_migrations: clean (48)**; **manifest_compile: green** (snapshot
  recompiled).
- **check_money_race: OK — 0 violations** (venue is game state, never
  coins; no new money-bearing op).
- **check_sim_gate: OK — 1351 [A] assignment(s), 534 auto-exempt
  below-floor** — no new panels/actions; the sail-button repoint changes
  no arrangement row.
- **check_compat_frozen: OK** (no new command names/aliases/custom_ids —
  both commands were already declared; only their routes went live).
- **pytest tests/: 2050 passed, 13 skipped** (includes the new
  `tests/unit/band6/test_band6_fishing_venue.py` — venue module verbatim
  numbers, sail toggle both directions, forecast Rain embed bytes, store
  spec/erasure refs, manifest + hub route flips).
- `bootstrap.py check --strict`: the only red was the by-design born-red
  HOLD while this card declared `in-progress` — flipped `complete` in
  this final commit.

### 2 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_forecast, sweep_sail — only the `"subsystem"` line changed
(`_unmapped` → `fishing`); calls/events/db_delta bytes untouched (#193
law). sweep_sail is the first row-bearing `fishing_venue` golden — the
table is born covered, no guard-only exemption ever minted.

## 💡 Session idea

The fishing ladder inverts the mining ladder's coverage economics: mining
landed 8 `guard-only-capture` exemptions because every write lane sat
behind argful invocations the sweep never drove, but `!sail` is a BARE
command whose very first invocation IS the write — so its table lands
covered on day one. When slicing the remaining 13 fishing keys, front-load
the other bare-write toggles/opens (if any structure/bait surface writes
on bare invocation) for the same free coverage, and batch the argful craft
lanes (`craftrod`/`craftbait`/`craftpearl`/`craftcurio`) last so their
inevitable exemption rows land in one reviewed block rather than
dribbling in rung by rung.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-capabilities-oracle-path.md`.) Its headline
delivered exactly what this slice consumed: the ledgered worker-session
oracle path (list_repos → add_repo → local shallow clone) worked first
try — the clone was already attached at `/workspace/superbot` and this
session paid zero re-discovery, which is the ledger loop closing twice in
a row. Its pytest wall entry (`pip install pytest pytest-asyncio`, target
`tests/` never repo-root) also held verbatim. One gap it could not have
foreseen: the ledger records the oracle PATH but not the oracle's
trap-24 posture (default branch `97d281e` vs corpus sha `7f7628e1`) —
this slice pinned golden bytes over head-reconstruction where they
diverged in reach; a one-line "corpus sha wins" pointer in the same
CAPABILITIES entry would make the next porter's precedence explicit.
