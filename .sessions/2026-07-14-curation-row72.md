# 2026-07-14 — parity: curation row 72 + farm goldens (ORDER 022 (a)4)

> **Status:** `complete`

- **📊 Model:** fable-5

## Scope

Claimed lane (`control/claims/order-022-titleequip-row72.md`, PR #471;
branch `claude/curation-row72`, stacked on `mining-write-parity-wp7` @
`cd65819` per ORDER 017 rule 2 / ORDER 022 (a)4): curation backlog
row 72 + its farm goldens — the last curation-rework night bundle
(bundle 3 of `control/claims/curation-rework-night-bundle.md`), taken
over via the branch-from-#371-head path.

- **Row 72** (`docs/review/curation-report-2026-07-13.md:1177` —
  `rps_tournament.quickplay` REWORK): mint the bet-settle interaction
  golden (`!rps 10` → move click → the audited `rps.solo_play` bet
  settle) — the coin-bet click path has no golden (sweep_rps.json is
  the bare open).
- **Farm goldens ×3** (same report § "(c) Backlog", the reconciled
  split-verdict rows): click-golden batch for the farm money paths —
  `farm_collect` / `farm_buy_hen` / `farm_upgrade_coop` — via
  `tools/mint_golden.py` (D-0073 procedure, canonical stripped
  flavor).
- Count pins re-summed FROM DISK by the mint tool
  (parity/parity.yml, test_replay_adapter.py,
  test_check_parity_depth.py); CAPTURE_WORLD_WEATHER registration
  BEFORE any mint per the post-07-13 date-live-outage doctrine.

Decide-and-flag deviations (PL-001, each one-line-rationale'd in the
PR body):

- `sb/domain/rps/ops`' module-private solo-play RNG is now runner-armed
  at every case head (`sb/adapters/parity/runner.py`, the fishing
  cast-RNG posture) — without it the bot's move differs between capture
  and every replay.
- The three farm K7 legs now speak their success copy through
  `LegOutcome.user_message` (`sb/domain/farm/ops.py`, the
  rps.record_solo_play precedent): the copy sat dead in
  `after["message"]`, which no surface reads — a Collect click
  committed money SILENTLY; minting that would enshrine the silent
  click as corpus truth.
- The parity transport mints a click-targetable message id for
  component-bearing panel FOLLOWUPS (`sb/adapters/parity/transport.py`)
  — the hub → Shop hop presents the shop as a followup, and a real
  `Webhook.send` returns the created message; component-less followups
  stay id-less (zero effect on the existing corpus).
- Exemption retirements + ratchet climbs (farm `table:chicken_farm`,
  rps `table:rps_players`; farm/rps_tournament ratchet rows) per the
  fishing_catch_log retirement precedent — both rows' own text promised
  retirement at the first row-bearing capture. The `cleanup` ratchet
  under-pin `--write-ratchet` also surfaced was REVERTED (not this
  lane's coverage).

## Previous-session review

`2026-07-14-fishing-minigame-timing.md` (PR #460) — the closest mint
prior art: CAPTURE_WORLD_WEATHER entries registered before the mint,
curated cases with click steps + fixture_sql, and the D-0073 tool run
end-to-end. Its trap notes (runner-armed private RNG streams; pins
re-summed from disk, never hand-computed) are exactly the hazards
this lane inherits — the rps solo-play module RNG needs the same
runner arm the fishing cast RNG got, or the bot's move is
capture/replay nondeterministic.

## 💡 Session idea

`tools/mint_golden.py` could grow a `--require-weather-entry` flag
(default on) that refuses to mint any case whose id is missing from
`CAPTURE_WORLD_WEATHER` unless the case's import graph provably never
reaches `sb/domain/fishing/weather.py` — making the post-07-13
"register weather FIRST" doctrine mechanical instead of team memory.
