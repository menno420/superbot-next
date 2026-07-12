# Fishing depth ladder claim — lane `fishing-slice1-forecast-sail`

This lane claims fishing depth slice 1 (weather + venue: `!forecast` +
`!sail`) — the first rung of the D-0043 fishing gear/venue successor port
(the mining ladder #286→#300 is complete; the remaining 13 fishing
`PENDING` keys stay unclaimed for sibling lanes).

- `fishing-slice1-forecast-sail` · **fishing depth slice 1 — forecast/sail (weather + venue) [IN FLIGHT — this branch]** — `!forecast` live off the ported weather module + `!sail` venue toggle → new `sb/domain/fishing/venue.py` + `fishing_venue` store + migration 0048; re-home 2 `_unmapped` sweeps into the gated `fishing` row · area: sb/domain/fishing/, sb/manifest/fishing.py, migrations/, parity/, sb/adapters/parity/runner.py · 2026-07-12T22:13:18Z
