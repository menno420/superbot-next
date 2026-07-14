# Claim — parity: capture-world weather seed for 4 fishing cast goldens

> Coordinator-authorized cross-lane hygiene fix (fishing lane closed for the
> night). Replicates onto main the seed already proven on PR #335
> (`mining-write-parity-wp5` @ `3220d17`). Runner-file-only; zero golden bytes.

- `fix/fishing-cast-weather-seed` · **hygiene** — pin the 2026-07-13 capture-day ⛈️ Storm condition into `CAPTURE_WORLD_WEATHER` for the four #387 write goldens (`fishing.cast_reel_write`, `fishing.cast_deepwater_reel_write`, `fishing.cast_bait_spend_write`, `fishing.howtofish_rules_card`) so replay stops reading the live wall clock via `current_weather()` and the required golden-parity `gate` stops flapping red daily on main + every open PR · area: sb/adapters/parity/runner.py · 2026-07-14
