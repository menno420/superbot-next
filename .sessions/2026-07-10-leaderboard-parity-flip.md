# 2026-07-10 — leaderboard parity flip (pending→ported through the A-16 door)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `leaderboard` row in `parity.yml` pending→ported as its own
deliberate slice — the follow-up the groundwork session (#118) withheld.
No behavior change: the golden already replayed byte-green at HEAD; this
PR is the disposition flip + the A-16 ratchet row + this card.

## What shipped

1. **The flip**: `parity.yml` `leaderboard: ported` — the third ported
   subsystem (after help and rps_tournament).
2. **A-16 ratchet row minted**:
   `leaderboard: {events: 1, tables: 2, settings: 0}` (via
   `check_parity_depth.py --write-ratchet`, re-applied by hand to keep
   the file's comment header; counts identical). R2 is vacuous for
   leaderboard (no declared surfaces in `manifest.snapshot.json`), so the
   floor is the ratchet row; zero exemptions added.

The single golden (`parity/goldens/leaderboard/sweep_leaderboard.json`,
case `sweep.leaderboard`) replays GREEN against real Postgres. Parity
dashboard moves 2 → 3 ported (of 49), 17 → 18 gate-enforced green
goldens replayed by the gate leg.

## Enablers (why the flip is mechanical now)

- **#118** (leaderboard groundwork): board panel opens with shipped
  bytes, canonical provider order, the 3 games-lane strings granted
  cross-lane, `_record_anchor` skipping session-lifecycle panels.
- **#117** (`_mint_ephemeral`, sb/kernel/panels/engine.py): session-
  lifecycle panels mint run-minted 32-hex custom_ids the Normalizer
  symbolizes as `<cid:N>` — cleared the last residual diff class.

## 💡 Session idea

`--write-ratchet` regenerates the whole file and drops every comment —
the tool even warns about it. For a file that doubles as the owner's
dashboard and carries its contract in comments, the regenerator should
splice only the `depth.ratchet` mapping in place (ruamel or a targeted
text edit) so a flip PR's diff is exactly the two lines reviewers need
to see.

## ⟲ Previous-session review

The groundwork card's "flip is unblocked, belongs to a follow-up slice"
handoff was exactly right — this slice needed zero code, and its
residual-diff accounting (3 granted strings + the `<cid:N>` class via
#117) matched what the replay showed at this HEAD. What it
under-delivered: it did not mention that `--write-ratchet` is
destructive to the file's comments, so the mechanical-looking "mint the
ratchet row" step still required a restore-and-hand-edit pass that a
future flip could trip over.
