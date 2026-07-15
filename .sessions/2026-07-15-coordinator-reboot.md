# 2026-07-15 — Coordinator reboot: ORDER 023 ack + revival heartbeat

> **Status:** `complete`

- **📊 Model:** Fable-class (Claude 5 family) · coordinator reboot session

## Scope

Coordinator seat reboot on the owner's v3.6 per-seat go:

1. **HARD-SYNC** — session booted on origin/main HEAD
   `ad75bbcfca001fefcb39e677e4b5ecddb3c80af3` (the ORDER 023
   EAP-extension note, #489).
2. **Routine re-arm + exhaustive trigger audit** — failsafe cron
   re-armed, pacemaker send_later chain live, full list_triggers sweep
   for wedges and stale predecessor chains.
3. **ORDER 023 ack** — acked via the revival heartbeat
   (`control/status.md` overwrite): EAP extended through 2026-07-21;
   routines re-armed on the owner's v3.6 per-seat go, which ORDER 023
   names as the re-arm gate.
4. **Next-slice dispatch** — extension feature tests (overview panel +
   add_repo now; Artifact tool + coordinator-comms when live) and
   superbot hub upkeep (Q-0166: unconsumed superbot ORDERs 003 + 005,
   hub heartbeat re-stamp).

Claim: `control/claims/coordinator-reboot-2026-07-15.md` (control +
.sessions only, no product code). This card is the branch's born-red
first commit; it holds the PR red until the end-of-session flip.

## Verification

- Close-out shipped list below (## Shipped); heartbeat deltas landed in
  `control/status.md` in the same commit (control + .sessions only).

## 💡 Session idea

- The auto-merge-enabler should skip re-arming PRs that carry the
  do-not-automerge label — today the carve-out demands a manual disable
  after every push to a parked PR (bit #392's reconcile push on
  2026-07-15).

## ⟲ Previous-session review

- The 2026-07-14 dormancy heartbeat was an exemplary baton — routine
  specs exact enough to recreate verbatim; its one rot ('No ORDER ≥
  023') went stale within hours, re-confirming that position lines rot
  and HEAD re-verification before acting is mandatory.

## Shipped

- ORDER 023 acked+done
- ORDER 001 closed per testing ledger
- feature tests add_repo/Artifact recorded
- 5 terminal claims swept
- #392/#476 reconciled
- superbot #2110 landed (ORDERs 003+005)
- #490 landed by owner 2026-07-15
