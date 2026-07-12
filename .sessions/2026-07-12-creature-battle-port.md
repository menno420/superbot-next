# 2026-07-12 — creature PvP battle port (the cbattle Accept terminal comes alive)

> **Status:** `in-progress`

- **📊 Model:** Opus 4.8 · high · feature build (Q-0194)

## Scope

Port CREATURE BATTLES from the oracle (menno420/superbot @ 7f7628e1) into
superbot-next: the pending `cbattle` Accept terminal
(sb/domain/creature/service.py + panels.py) becomes a real
auto-resolve-on-accept battle. Three slices on one branch,
`port/creature-battle`:

1. **Deterministic battle engine** — `sb/domain/creature/battle.py`, the
   oracle `utils/creatures/battle.py` combat math ported VERBATIM (6-element
   type chart, rarity budget × archetype stat derivation, level scaling, the
   damage formula with the 0.85–1.0 jitter, SPD-ordered 6v6 lead-until-faint
   resolution). Pure + stdlib-only; the RNG is injectable so battles are
   deterministic + golden-replayable. NO EffectiveStats/equipment coupling.

2. **Battle flow on the g1/deathmatch challenge-card seam** — challenge →
   Accept → **auto-resolve** (the oracle has no turn buttons; the whole 6v6
   resolves in one shot on Accept) → write the `creature_battle_record` W/L
   pair + battle-win game-xp through the already-live
   `creature.record_battle_result` audited op, settle-once via the
   challenge-card session teardown. Decline stays as already ported.

3. **Replace the pending terminal + goldens** — the `creature.challenge_accept`
   pending handler becomes the real resolve-and-record path; a full-battle
   interaction golden (challenge → accept → resolve → record) minted via
   `capture_case`.

## Design ruling

`[D-0078]` — auto-resolve-on-accept battle port; the battle RNG is seeded
deterministically from the battle inputs (guild, challenger, opponent,
clock) so the resolution is replayable/goldenable, using the injectable-rng
seam the oracle already exposes.

## Landing

Born-red card (this file) + telemetry row on the FIRST commit; the card
flips `complete` on the LAST. READY PR, never self-merged; parked green on
the required gates (golden-parity included). `control/status.md` folded LAST
after re-reading the inbox at HEAD.

## Verification (local, DB-backed)

- `python3 -m pytest`
- `python3 bootstrap.py check --strict`
- `python3 tools/run_golden_parity.py --gate`

Results recorded on completion.
