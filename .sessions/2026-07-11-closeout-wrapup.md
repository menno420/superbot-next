# 2026-07-11 — close-out wrap-up + archive prep

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · close-out/docs (Q-0194 — telemetry row rides
  this PR; tokens_out not measured)

## Scope

Owner-directed WRAP-UP + ARCHIVE-PREP: no new feature work. Capture the remaining
chat-only knowledge into durable homes, sweep every open PR/branch/claim to a
terminal classification, write the archive-ready note, and ship it all as one
merged-on-green docs PR.

## What shipped

1. **Q-0265 routine-loop record** — docs/retro/q0265-routine-loop-2026-07-11.md:
   the ~40-link one-shot chain (2026-07-10T19:48Z → 2026-07-11T19:40Z), the
   2026-07-11T16:31Z platform ENV-TEARDOWN incident (fleet-wide
   `auto_disabled_env_deleted`; this lane self-healed, siblings could not be), and
   the close-out DISARM (both triggers deleted ~19:30Z, verbatim facts) + the re-arm
   recipe. Status routine section (ORDER 008 record) carries the fold.
2. **OWNER-ACTION 6** (control/status.md, six-field): sibling-lane failsafes may
   still be dead from the teardown — owner/manager re-arm.
3. **Codex calibration made durable** — docs/collaboration-model.md § Standing
   @codex review: line-anchored findings repeatedly real; top-level committed/PR
   claims phantom in every observed instance (#144/#160/#178 comment citations).
4. **Re-arm recipe durable** — docs/collaboration-model.md § Continuous mode grew
   the exact `create_trigger`/`persistent_session_id` mechanics + the disarmed-state
   pointer.
5. **PR/branch/claims sweep** — #196/#206 PARKED with anchors spot-verified and the
   next step in control/claims/codex-risk-review-prs-196-206.md;
   `status/heartbeat-2026-07-09-band1` classified as the closed-#60 leftover
   (deletion = owner click, verified wall); claims dir otherwise empty. Nothing
   unclassified.
6. **Docs audit** — `bootstrap check --strict` run; its one advisory
   (`owner-ask-wall-unrecorded`, the OWNER-ACTION 3 ruleset wall) fixed by the
   dated append-log entry in docs/CAPABILITIES.md. Grooming: the stale ux-lab-card
   housekeeping flag in status.md marked RESOLVED (backfilled by #159, verified).
7. **ORDER-013 self-review durable copy** — docs/retro/self-review-2026-07-11.md
   (verified byte-identical on main from #171 `569b967` through `0e7cacd` before
   copying; no other self-review/lessons section was ever overwritten — checked all
   35 status.md revisions).
8. **Archive-ready note** — docs/retro/archive-ready-2026-07-11.md: true state
   (37/49 ported; gate GREEN 258/258 at `0e7cacd`, CI run 29165331776 gate job
   86577356262; report 295/467 red-by-design same run), every ⚑ owner-action, the
   sweep, and the fresh-session resume map.

## Verification

- Gate/report/parity counts read from the main-push golden-parity run's own job logs
  at `0e7cacd` (run 29165331776), and the 37-ported count hand-counted in
  parity/parity.yml at the same sha (Q-0120 — no stale status text trusted).
- The #196/#206 anchors spot-checked against sb/domain/games/store.py and
  sb/domain/blackjack/ops.py before writing the park note.
- `bootstrap check --strict` green after the CAPABILITIES fix.

## 💡 Session idea

Make the golden-parity gate **fail closed on the replay denominator**: `run_gate()`
should compare replayed-case count to golden-file count per ported subsystem and red
on any mismatch (the #196 F-003 class — an unreconstructable ported golden currently
drops out silently and only `CURATED_CASES` coverage saves it today). Small,
test-first, and it hardens the single number the whole program's green claims rest
on; natural first slice for the next builder session alongside the #196/#206
verification.

## ⟲ Previous-session review

Reviewed: the btd6 resolver maps/modes session (#208, merge `0e7cacd`,
`.sessions/2026-07-11-btd6-resolver-maps-modes.md`). Clean shape: it took a ledgered
parked item (the #144 resolver line) rather than inventing work, retired the ledger
line in the same PR, and merged on green with the gate unchanged — exactly the
Q-0265 continuous-mode contract. One nit for future close-outs: its telemetry-row
outcome fields were all null; citable fields (merged_pr at minimum) would make the
Q-0194 ledger analyzable without a git archaeology pass.
