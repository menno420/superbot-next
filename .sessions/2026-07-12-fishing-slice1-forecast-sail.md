# 2026-07-12 — fishing depth slice 1 port: forecast / sail (weather + venue)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · high · feature build (Q-0194)

## Scope

The faithful port of fishing depth slice 1 — the first rung of the fishing
gear/venue ladder (the D-0043 named successor scope: "fishing gear/venue
systems"; the mining ladder #286→#300 is complete, so this lane is next in
the successor list). Two shipped commands move from honest D-0043 pending
terminals to real surfaces: `!forecast` · `!sail`.

Planned delivery:

- **Domain** (`sb/domain/fishing/venue.py`, NEW): the shipped
  `utils/fishing/venue.py` ported — `SHORE`/`DEEPWATER` keys,
  `VenueProfile` (identity + the minigame numbers, carried as data),
  `SHORE_PROFILE`/`DEEPWATER_PROFILE`, `normalize`/`profile_for`/`toggle`.
- **Store + migration**: `fishing_venue` (per-(user, guild) current venue;
  no row reads as `shore` — the shipped migration-094 shape) as a
  MEMBER_ID registered store with a delete-erasure body; migration
  `0048_fishing_venue.sql` (+ checksums).
- **Handlers** (`service.py`): `fishing.forecast_view` (the shipped
  date-seeded forecast embed — title/blurb/effect/footer,
  goldens pin the Rain bytes) and `fishing.sail_route` (the shipped
  `toggle_venue` — plain game-state write, no audit, the energy-spend
  posture; the deepwater message is golden-pinned). `forecast` + `sail`
  leave `PENDING`.
- **Panels**: the hub's "Fishing from" field and the cast footer read the
  LIVE stored venue profile (no-row → shore = the golden bytes); the hub
  ⛵ Set sail / Dock button repoints `fishing.sail_pending` →
  `fishing.sail_route` (byte-neutral: the golden pins label + minted id).
- **Deferred (D-0043, honest)**: the cast LEG stays at the starter shore
  profile — the venue→cast wiring (deepwater species pool, coral drop,
  minigame difficulty) rides the rod/bait/minigame rung with the rest of
  the gear knobs; no imported golden drives a deepwater cast.
- **Parity**: `CAPTURE_WORLD_WEATHER` gains `sweep.forecast: rain` (the
  golden pins the capture-day Rain condition — trap 36a); the 2
  `_unmapped` sweeps (sweep_forecast / sweep_sail) re-home into the gated
  `fishing` row (#193 law: `git mv` + the one sanctioned `subsystem`
  flip). `fishing_venue` is a NEW declared table surface COVERED by
  sweep_sail's own db_delta row — no exemption needed; ratchet
  regenerated upward (`--write-ratchet`).

## Verification (planned)

- golden-parity gate green over the re-homed corpus; `check_parity_depth`
  OK; `manifest_compile --write` snapshot; `check_sim_gate` unchanged (no
  new panels/actions); `check_money_race` clean (no money op);
  `pytest tests/` green; `bootstrap.py check --strict` green.

## 💡 Session idea

(minted at close)

## ⟲ Previous-session review

(minted at close)
