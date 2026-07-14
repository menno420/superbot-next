# 2026-07-14 — hotfix: make the four fishing cast/howtofish goldens date-independent

> **Status:** complete

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

**Mid-session collision (first-merged-wins):** parallel PR #448 landed
the identical `CAPTURE_WORLD_WEATHER` storm seed on main (7b0a661)
while this PR's CI was attaching — same mechanism, same four case ids,
same condition, but it kept the 07-13 golden bytes verbatim (spine
included) and left the ratchet untouched. Verified main green locally
on 07-14 (gate + depth). This PR was slimmed to the delta main lacks:
the canonical stripped D-0073 re-mint of the four goldens plus the
correlated fishing `depth.ratchet` correction, with `origin/main`
merged into the branch (no rebase of published history).

## Outcome

Local gate GREEN — `all 494 golden(s) across 50 ported subsystem(s)
replay clean`, run on 07-14 (a Rain day: the date-independence proof —
the same run was red on exactly the four cases before the fix). The
re-mint also normalized the four goldens to the canonical stripped
D-0073 flavor (the 07-13 mints carried the kernel spine that
`apply_dispositions` strips from non-kernel goldens and that replay
never diffed), so the fishing `depth.ratchet` row is deliberately
corrected 3/10 → 2/8 with narration beside the block in
`parity.yml` and its own section in the PR body. After the #448
collision the slimmed branch re-verified green on merged main: gate
GREEN 494/50, depth check OK 49/49/494, `pytest tests/ -q` 3025
passed / 2 skipped. Rot sweep of
`parity/goldens/`: no other live-date-derived value found (the three
`sweep_*` fishing goldens are already seam-armed; `Stormfang` is a
creature; remaining hits are static copy/notes prose). PR #449.

## 💡 Session idea

`mint_golden.py` could refuse (or loudly warn on) a fishing-subsystem
mint whose case id is absent from `CAPTURE_WORLD_WEATHER` — the tool
already knows the case and the seam registry, and a one-line preflight
("this capture reads the live UTC date; seed it or say --allow-live-
date") would have prevented this fleet-wide red at mint time instead
of at the next UTC midnight. Generalized: any module exposing a
`seed_*_for_replay` seam could register the case-id → seed map it
expects, and the mint tool cross-checks coverage.

## ⟲ Previous-session review

(2026-07-13-setup-wizard-5, the settings-write section flows)

Clean slice-on-spine work — three section flows registered without
touching the spine, and its 💡 idea (stage the LEVEL name, re-derive
columns at apply time) names a real staged-draft drift class; the card
would be stronger with the verification evidence inline (which gates
ran) rather than implied by the lane's conventions.
