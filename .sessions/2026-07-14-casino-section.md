# 2026-07-14 — games hub: casino/minigame section swap (ORDER 022 (a)2)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family)

## Scope

Claimed lane (`control/claims/order-022-casino-section.md`, branch
`claude/casino-section-1`): the casino/minigame section BUILD unlocked
by ORDER 022 (a)2 (control/inbox.md) — the spec §7 one-PR swap per
`docs/specs/casino-section-spec.md`. All D-0082 section machinery
(enable-all/pick-a-few, dynamic panels) is already live; this is the
taxonomy-only swap:

- `sb/manifest/games.py` `GAME_SECTIONS`: 2 sections
  (🏆 competitive / 🎲 activities) → the spec §2 drop-in 3-section
  block — 🎰 `casino` (blackjack, casino), 🕹️ `arcade` (deathmatch,
  rps_tournament, counting, chain), 🌍 `world` (mining, fishing,
  creature, farm). GAME_SECTIONS stays the single declaration site
  (SectionRedefined fence).
- `sb/domain/games/panels.py`: regroup the static fail-open hub
  fields to match the 3 sections. Custom ids (`games:open:<key>`)
  unchanged; spec §5.4 optional cosmetic button restyle SKIPPED by
  decision (noted in the PR body).
- `tests/unit/band6/test_band6_game_sections.py`: rewrite the
  2-section drift-guard pin table to the 3-section taxonomy, keeping
  both-direction roster agreement.
- Re-mint the two hub goldens `parity/goldens/games/sweep_games.json`
  + `sweep_slash_games.json` via `tools/mint_golden.py --write
  --force` (never hand-edited). Golden COUNTS do not move.

Untouched by design: parity/cases/curated.py, parity/parity.yml,
count-pin tests, mining write faces, control/status.md,
control/inbox.md, control/outbox.md, manifest.snapshot.json content.

## Verification

(in progress — filled at close-out)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out)
