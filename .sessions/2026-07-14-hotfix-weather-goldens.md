# 2026-07-14 — hotfix: make the four fishing cast/howtofish goldens date-independent

> **Status:** in-progress

- **📊 Model:** Claude Fable 5 · fleet-unblocking golden-parity hotfix

## Scope

Fleet-wide golden-parity gates went red at 2026-07-14T00:00Z: the four
2026-07-13-minted fishing goldens (`fishing_cast_reel_write`,
`fishing_cast_deepwater_reel_write`, `fishing_cast_bait_spend_write`,
`fishing_howtofish_rules_card`) were captured date-live — the capture
run never armed the `seed_weather_for_replay` seam, so each golden
embeds 07-13's date-derived forecast (⛈️ Storm,
`sb/domain/fishing/weather.py` derives weather from the UTC calendar
date). Any replay on a different day derives that day's condition
(07-14 → 🌧️ Rain) and the four cases diff red on the forecast embed
field. Fix: extend `CAPTURE_WORLD_WEATHER` in
`sb/adapters/parity/runner.py` (the exact mechanism that keeps
`sweep.fish` / `sweep.fishing` / `sweep.forecast` green) with the four
case ids pinned to `"storm"` — the capture day's condition — so both
capture (`tools/mint_golden.py` → `capture_case`) and replay
(`replay_case` → `capture_case`) seed the same weather on any date;
then re-mint the four goldens via `tools/mint_golden.py --write
--force`. No production behavior change in `weather.py`; no other
golden touched. Claim lands in-PR (`control/claims/
hotfix-weather-goldens.md`) rather than on main first — deliberate for
the fleet-unblocking hotfix, noted in the PR body.
