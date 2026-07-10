# 2026-07-10 — band-5 compensator fixes (effect-leg compensation gaps)

> **Status:** `complete`

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

## What shipped

1. **PR #105** (merge `2c222e1`) — the PR-B plan above, delivered in full:
   `moderation.compensate_timeout` + `proof_channel` unlock compensator (both
   with blocked-path tests), the class-killer invariant
   `tests/unit/workflow/test_compensator_invariant.py` (97 registered ops
   scanned; only the two fixed ops violated it; allowlist empty), and the
   ORDER-009 flag-13 dispositions applied to the parity machinery
   (`sb/adapters/parity/dispositions.py`, the `parity/parity.yml`
   `dispositions:` block,
   decision record `docs/parity/flag-13-disposition-2026-07-10.md`). The @codex
   review question rode its final head per ORDER 010.
2. **PR A** (this repo's session-close PR) — this log's flip + enders, the
   #99/#101 ender catch-up, the ORDER 010 rule encoded in
   `docs/collaboration-model.md`, and the heartbeat overwrite (ORDER 008
   trigger record included; OWNER-ACTION 1 cleared per ORDER 009).

## 💡 Session idea

The compensator invariant test turns a runtime-review defect class into a
fence: a `"reversible"` EFFECT leg without a compensator is now unwritable at
authoring time instead of discoverable at review time. Generalize the move —
each external-review finding that survives verification should leave behind
one structural invariant (registry scan / spec lint), not just its point fix;
the ledger of such fences is what makes the next review cheaper.

## ⟲ Previous-session review

The #101 session seeded the exact design this session shipped — instances,
fix shape, even the invariant's test-pattern precedent — which made this the
cheapest fix session of the band. But it left no session log at all (its
catch-up ender was written by the close-out session), so the seed's quality
was invisible to the ritual that is supposed to surface it. Good seams, no
wake: the capture discipline is ahead of the close-out discipline.
