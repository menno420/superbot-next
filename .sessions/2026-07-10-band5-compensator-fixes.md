# 2026-07-10 — band-5 compensator fixes (effect-leg compensation gaps)

> **Status:** `in-progress`

- **📊 Model:** Claude Fable 5

## Scope

Two-PR session plan; claimed orders 009, 010 (and 008-record) per the
control/README.md claiming convention.

**PR B (this branch, `claude/band5-compensator-fixes`):** the seeded quick-win
lane from `docs/ideas/effect-leg-compensation-gaps-2026-07-10.md` —

1. `proof_channel.end_access`: compensator for the uncompensated
   `apply_unlock` EFFECT leg (mirror `GRANT_PRIZE`'s `compensate_lock`).
2. `moderation.timeout`: `moderation.compensate_timeout` for the
   uncompensated `apply_timeout` EFFECT leg (mirror the WARN pattern).
3. Class-killer unit invariant: scan all registered `CompoundOpSpec`s and
   reject any non-optional EFFECT leg after a DB leg that is `"reversible"`
   without a compensator.
4. ORDER 009 (flag-13 disposition, accepted exactly as proposed): apply the
   three corpus-red classes to the parity machinery + short decision doc.

**PR A (follow-up):** session-log enders (Session idea + Previous-session
review), status flip to `complete`, ORDER 010 doctrine acknowledgement, and
the control/status.md heartbeat.
