# 2026-07-12 — creature PvP battle port (the cbattle Accept terminal comes alive)

> **Status:** `complete`

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

## Verification (local, DB-backed on Postgres 16)

- `python3 -m pytest` — **1761 passed / 13 skipped** (the +34 over the
  1727 baseline are the engine + service suites; the two parity
  corpus-count tests re-pinned 468→469).
- `python3 bootstrap.py check --strict` — **green** (the born-red HOLD
  released on this card's flip to `complete`).
- `python3 tools/run_golden_parity.py --gate` — **GREEN, all 413
  golden(s) across 51 ported subsystems replay clean** (was 412; the new
  creature_battle_accept golden joined).
- the 22-checker committed fleet — green; `manifest_compile` — green.

## What shipped

Three slices on `port/creature-battle`, committed in order:
1. `sb/domain/creature/battle.py` — the oracle combat engine, verbatim
   (byte-verified vs corpus sha 7f7628e1) + 26 unit cases.
2. `sb/domain/creature/battle_service.py` + `service.py`
   `creature.challenge_accept` + `panels.py` `resolved` stage — the
   auto-resolve-on-Accept flow on the deathmatch challenge-card seam,
   feeding the already-live `creature.record_battle_result` op + 6 unit
   cases.
3. `parity/goldens/creature/creature_battle_accept.json` (capture_case)
   + parity.yml (minted 6→7, exemption retired, ratchet up) + the
   [D-0078] ledger entry.

PR parked READY, never self-merged; all required gates green.

## 💡 Session idea

The event_outbox snapshot sort (parity/harness/dbsnap.py:94) sorts rows
by `json.dumps(row)` where `correlation_id` — a RAW uuid, not yet
normalized — is the first distinguishing column, so a case that mints 2+
event_outbox rows gets a NON-deterministic row order. It's invisible
today only because (a) this is the first case to mint two, and (b) the
kernel-surface-drift disposition strips event_outbox before the diff. If
a future kernel-band golden ever needs to PIN two outbox rows (they're
NOT stripped for `subsystem: kernel`), it will flake. Cheap durable fix:
normalize volatile ids BEFORE computing the sort key in `snapshot()`.

## ⟲ Previous-session review

No direct predecessor session in this lane — the creature row was flipped
`ported` (catch/collection/record read side) back in parity-flips wave-6
(#226, merge `f032e8a`) with the battle engine explicitly deferred as a
named successor (D-0043: "the interactive PvP battle engine … is a named
successor port — cbattle is an honest pending terminal"). This session
is that successor. The recon pass (scratchpad recon.md) mapped the seam
(the g1/deathmatch challenge-card pattern, the live record lane, the
oracle formulas); every load-bearing fact was re-verified at HEAD before
use — the oracle battle.py was re-fetched at the pinned sha and confirmed
byte-identical, and the `creature.record_battle_result` op was confirmed
live and dormant, exactly as recon reported.
