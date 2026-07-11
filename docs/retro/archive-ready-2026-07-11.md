# Archive-ready note — 2026-07-11 close-out

> **Status:** `reference` — written by the close-out session, every load-bearing claim
> re-verified against source/CI at main `0e7cacd` (Q-0120). This is the single
> resume-here document for whoever un-archives the project.

## Current true state (one paragraph)

Parity stands at **37/49 subsystems ported** (hand-counted in `parity/parity.yml` at
main `0e7cacd`; CI agrees: `check_parity_depth: OK — 49 subsystems (37 ported), 467
goldens`). The golden-parity **gate is GREEN — 258/258 goldens across the 37 ported
subsystems** at main HEAD `0e7cacd`, CI-log-verified in the main-push golden-parity
run 29165331776 (gate job 86577356262:
https://github.com/menno420/superbot-next/actions/runs/29165331776). The **report leg
stays red-by-design** (non-required, red until full parity): 295/467 replayed cases
green, 467/467 replayable, same run (report job 86577356263). **Bands closed: 5**
(live-bug fix lane done via #111, live-drive leg #109), **6** (games — both games
playable solo + PvP + tournament, ALL game-family goldens green, lane SESSION
COMPLETE), and **7-deterministic** (all three golden-pinned rows ported — btd6 #144,
project_moon/projectmoon #148, ai #151 — plus the chooser/modal/policy/orchestration
slices through #204 and the btd6 resolver slice #208). **What remains:** the
games-family pending rows (per the gate job's own pending table: casino 2, creature 5,
farm 1, fishing 2, four_twenty 1, games 2, inventory 1, mining 2, treasury 2 goldens);
the setup wall (8 goldens, PARKED — playbook trap 17) and quicksetup (1 golden,
BLOCKED at the create-channel wall — decision ledger, docs/decisions.md); the band-7 **live-NL leg, owner-key-gated**
(OWNER-ACTION 5 — ANTHROPIC_API_KEY + AI_ENABLED absent; code shipped deterministic);
the remaining **`_unmapped` re-homes (182 goldens** per the same gate log — each
family is flip-sized port work, the #193 law); the **parked codex risk-review PRs
#196/#206** (money-race + gate-false-green findings — anchors spot-verified real at
close-out, conclusions unverified; see the sweep below); and the smaller ledgered
follow-ups (kernel-band golden mint — the #194 named follow-up; CommandSpec modal
facet; review-channel poster, parks with NL arming; testing-report rows 8/9 —
band-6/7 live-testing passes per the 9-step ladder).

## ⚑ Owner-actions (all live items, click-level — six-field blocks in control/status.md)

1. **OWNER-ACTION 2** — create the empty repo `superbot-plugin-hello` at
   https://github.com/new (unblocks ORDER 002; agent repo-create is 403-walled).
2. **OWNER-ACTION 3** — repo Settings → Rulesets: enable merge queue or drop
   require-up-to-date for `docs/**` + `control/**` (kills the update-branch dance;
   agent ruleset-edit is admin-walled — now also in docs/CAPABILITIES.md).
3. **OWNER-ACTION 5** — put a real `ANTHROPIC_API_KEY` + `AI_ENABLED=true` in the
   agents' session env (gates band-7 live-NL EVIDENCE only; deterministic surface
   shipped).
4. **OWNER-ACTION 6** (new at close-out) — re-arm the sibling lanes' failsafe
   routines killed by the 2026-07-11T16:31Z platform env-teardown
   (`auto_disabled_env_deleted`); this lane's loop was deliberately disarmed and
   needs nothing until un-archived. Record:
   docs/retro/q0265-routine-loop-2026-07-11.md.
5. FYI (no action): codex line-anchored findings are repeatedly real; its top-level
   "I committed X / opened PR Y" claims were phantom in every observed instance —
   calibration now durable in docs/collaboration-model.md § Standing @codex review.

## Open-PR / branch / claims sweep (nothing unclassified)

- **PR #196** (codex docs-only review findings F-001..F-003) — **PARKED** open:
  anchors spot-verified real (plain-SELECT checkpoint loads, NATURAL_KEY/no-dedup
  money ops, FOR UPDATE only in `lock_rows_for_settlement`), conclusions unverified;
  next step recorded in `control/claims/codex-risk-review-prs-196-206.md`.
- **PR #206** (codex follow-up cutover-risk review + README-first pointer) —
  **PARKED** open, same claim file, same next step (verify test-first, fix real ones
  as slices, then merge or supersede-and-close both docs PRs).
- **Branch `codex/review-correctness-bugs-in-superbot`** — head of parked #196.
- **Branch `codex/verify-and-address-f-001-to-f-003-issues`** — head of parked #206.
- **Branch `status/heartbeat-2026-07-09-band1`** — **CLOSED** leftover: head of PR
  #60, closed 2026-07-09 per ORDER 003 (superseded by #73). Branch deletion is a
  verified agent wall (docs/CAPABILITIES.md) — owner deletes it by hand or enables
  "Automatically delete head branches".
- **`control/claims/`** — was empty at close-out; now carries exactly one file, the
  deliberate park record above.
- Everything else merged: all other work landed on main via squash-merged-on-green
  PRs (#111 → #209; per-PR trail in control/status.md's lane records — #209 is the
  band-7 lane's own archive-prep wrap-up, merged while this close-out was in flight;
  its heartbeat fold was forward-merged into this branch).

## What a fresh session needs to resume

1. **Boot ritual**: `git pull`, read `control/README.md` (protocol) →
   `control/inbox.md` at HEAD (orders; claim before executing) →
   `control/status.md` (state; the lane records + LANE END maps name every
   remaining work item per lane) → `docs/AGENT_ORIENTATION.md` +
   `docs/status/README-first.md` (orientation + live-truth pointers).
2. **Ship mechanics**: READY PRs merged on green under the 6-check ruleset (`report`
   red-by-design, not required); land your own PRs; forward-only git; direct pushes
   to main are ruleset-blocked; @codex question on every substantive PR's final head
   (docs/collaboration-model.md), merge without waiting (Q-0258); Q-0120-verify every
   external claim.
3. **Playbook + ops notes** (team memory, survives sessions):
   `superbot-next-parity-flip-playbook`, `superbot-next-band7-ops-notes`,
   `superbot-next-quicksetup-parity-wall` under
   `/tmp/claude/memory/team/project/project/f3463adc-…/`; per-session cards in
   `.sessions/` (newest-first, guard recipes inside).
4. **Routine re-arm** (Q-0265 continuous mode): one-shot chain links ~16 min apart +
   2-hourly failsafe cron, both `create_trigger` with `persistent_session_id` —
   exact recipe in docs/collaboration-model.md § Continuous mode and
   docs/retro/q0265-routine-loop-2026-07-11.md (the loop was DISARMED at close-out;
   nothing fires until re-armed).
5. **First work candidates**: verify-and-fix the #196/#206 findings (claim file
   above); games-family parity rows; `_unmapped` re-home families; the kernel-band
   golden mint.

## Nothing important remains chat-only — confirmation

The close-out captured the last chat-only knowledge into durable homes: the Q-0265
loop run/teardown/disarm record (docs/retro/q0265-routine-loop-2026-07-11.md + the
ORDER 008 record in control/status.md), the re-arm recipe
(docs/collaboration-model.md), the codex calibration (docs/collaboration-model.md;
already in team memory), the fleet-failsafe owner flag (OWNER-ACTION 6), and the
ORDER-013 self-review's durable copy (docs/retro/self-review-2026-07-11.md). The
standing owner-actions 2/3/5 were re-verified complete in six-field form in
control/status.md. To this session's knowledge, no decision, blocker, recipe, or
owner-ask exists only in a chat transcript.
