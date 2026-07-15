# 2026-07-14 — games hub: casino/minigame section swap (ORDER 022 (a)2)

> **Status:** `complete`

- **📊 Model:** fable-5

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

Build landed: PR #477 (`GAME_SECTIONS` 2→3 sections, rosters regrouped,
band6 drift-guard rewritten, both hub goldens re-minted via
`tools/mint_golden.py --write --force`).

- `python3 -m pytest tests/ -q` → 3113 passed, 15 skipped.
- `python3 tools/manifest_compile.py` → green (49 manifests).
- `python3 bootstrap.py check --strict` → green up to the DESIGNED
  born-red hold on this PR's own session card + the 4 pre-existing
  claims advisories (never exit-affecting, present on main).
- `python3 tools/check_parity_depth.py` → OK — 49 subsystems
  (49 ported), kernel ported, 498 goldens.
- `tools/run_golden_parity.py --gate` (local Postgres, per
  docs/CAPABILITIES.md) → `gate: GREEN — all 498 golden(s) across
  50 ported subsystem(s) replay clean`.
- Golden counts (498), `parity/parity.yml`, and both count-pin tests
  stayed untouched by design — the swap re-mints two existing hub
  goldens in place, it does not mint new ones.
- `manifest.snapshot.json` moved by construction (the sections panel's
  handler/provider/action/selector ids are registry-derived off
  `GAME_SECTIONS`), and `sim/sim-gate-baseline.json` was re-pinned via
  `check_sim_gate --write-baseline` after the 2→3 section below-floor
  shape crossed the exempt threshold.

Landed via the merge-queue reconciliation session (2026-07-15): synced
main in (post-WP-stack + #466 fishing cast-again), no conflicts against
this branch's games-only diff, label removed, card flipped here.

## 💡 Session idea

`check_sim_gate --write-baseline` is a manual step the author has to
remember to run whenever a registry-driven panel's declared-component
count crosses the below-floor threshold (here: `GAME_SECTIONS` 2→3
sections = 6 declared components) — nothing fails loudly if a future
PR changes `GAME_SECTIONS` again and forgets the re-pin, since the
baseline file just goes stale silently until some other unrelated PR's
CI run trips over the drift. `tools/check_sim_gate.py` could detect the
specific case of "a registry the baseline derives from changed shape
but the baseline file's own git blob is untouched in this diff" and
print a pointed suggestion, the same class of self-diagnosing check
this repo already builds elsewhere (e.g. `check_parity_depth`'s ratchet
guidance).

## ⟲ Previous-session review

(Covers `.sessions/2026-07-14-title-equip-write.md`, the sibling ORDER
022 slice landed the same day.) That session's guard recipe — audit
`ValidatorError(` call sites in `sb/domain/mining/ops.py` for the
one-arg sentence form before a golden freezes the wrong byte — is
still unbuilt and cheap; worth a few minutes in a future mining-adjacent
session. Its close-out doc discipline (Verification / idea / review all
filled with real specifics, not placeholders) is the shape this section
swap's own card followed once picked back up here — a card left with
"(filled at close-out)" placeholders past its actual landing is exactly
the kind of drift the reconciliation pass exists to catch and fix, not
just flip the Status badge on.
