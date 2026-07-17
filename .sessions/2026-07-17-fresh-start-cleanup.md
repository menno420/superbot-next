# 2026-07-17 — fresh-start cleanup: docs, instructions, next-tasks, apparatus wind-down

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only

## Scope

Owner-authorized fresh-start cleanup ahead of the Claude Code Projects EAP going
read-only Tue 2026-07-21 and the Project being recreated. Docs/instructions only —
**no `sb/` source and no workflow files touched** (branch
`claude/fresh-start-cleanup`):

1. **Claims** — verified `control/claims/` is already clean (only `README.md`;
   the terminal `conform-sweep-457.md` was retired by #505). No residual claim to
   delete.
2. **Current state** — `docs/current-state.md` + `control/status.md` corrected:
   EAP read-only date fixed to **2026-07-21** (not earlier); noted the fleet-wide
   PR backlog was cleared 2026-07-17 (#499 / #500 / #503 / #505 landed, WP stack
   merged); recorded the autonomous apparatus (self-wake, message bus) wind-down
   and Project recreation; refreshed the stability baseline to live ground truth
   (49 subsystems, 523/523 goldens, 49/49 ported, suite 3160 passed / 29 skipped).
3. **Instructions** — removed the "arm auto-merge / it lands itself" merge doctrine
   from `CONSTITUTION.md` (and the "silence = consent" landing rule) and the
   "auto-merge (squash) the moment green" framing from `docs/current-state.md`
   § Review rhythm; replaced with server-side-lander / owner-merge doctrine + the
   verbatim "no agent-side merges, classifier-denied since ~2026-07-15" note. Added
   a short Merging section to `.claude/CLAUDE.md`. Kept the architecture/layering
   rails and PL citations.
4. **Next tasks** — added `docs/NEXT-TASKS.md` (the six forward steps: finish the
   port to parity, the game-surface backlog, correctness gaps, live-production
   stand-up, the data safety net, and replacing the autonomy apparatus with an
   owner-directed flow).
5. **Scaffolding** — deprecation-bannered (not deleted): `control/README.md`,
   `control/outbox.md`, `control/status.md`, `docs/ROUTINES.md`,
   `docs/seat-digest.md`; and appended a retirement ORDER 024 to `control/inbox.md`
   (the append-only gate forbids a top banner, so the retirement notice ships as a
   well-formed appended ORDER). Deleted the inert self-marked-deletable probe
   `docs/_merge_verification_2026-07-15.md`. Left `.github/workflows/**` and `sb/`
   untouched per instruction.

## Verification

- `python3 bootstrap.py check --strict` — green ("all checks passed"); only
  pre-existing advisories.
- Added-card gate mirrored locally: `bootstrap.py check --strict --session-log
  .sessions/__born-red-card-added__.md --added-card <this card>` — green.
- Inbox append-only gate mirrored locally against the merge-base blob:
  `bootstrap.py check --strict --status-only --inbox-base <original inbox>` — green
  (pure-append + well-formed ORDER 024).
- `check_doc_cites`, `check_verified_live`, `check_intent_survival` and the
  committed-checker fleet — green (all cited paths resolve; the deleted probe had
  zero inbound references).

## 💡 Session idea

The inbox append-only gate makes a top-of-file deprecation banner impossible on
`control/inbox.md` without reddening `substrate-gate` — so a retirement notice has
to be smuggled in as an appended ORDER, which is the least-visible spot in a 36 KB
file. A cheap structural fix for the kit: teach the status/inbox checker to honor a
single well-formed **`> RETIRED`/`> DEPRECATED` blockquote inserted at the very top**
as an allowed non-append exception (the byte-prefix rule would apply to everything
*after* the banner). That lets an append-only bus be visibly tombstoned at its front
door instead of only at its tail. Anchors: `check_inbox_append` in `bootstrap.py`,
grammar in the kit's `src/engine/grammar.py`, gate step in
`.github/workflows/substrate-gate.yml` ("inbox append-only gate").

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-16-coordinator-close.md` (the coordinator close-out,
#503). It correctly parked the residual failsafe trigger removal as an owner ask
(deletion was platform-denied from that seat) — honest and well-cited. What it
could have done better is exactly what this session had to reconcile: it left the
`control/status.md` heartbeat asserting `#499/#500` as "gate-green DRAFTS awaiting
owner release" when those PRs merged the same day, so the live status doc read
wrong-by-a-day for anyone booting after it. The systemic improvement: a
close-out card that records "PR #N: draft, owner-lands" should carry a one-line
**post-merge reconcile hook** — a note (or a checker) that the *next* session must
re-verify and overwrite any "awaiting release" heartbeat against live PR state
before trusting it. This session's `docs/current-state.md` now absorbs that role by
retiring the second (heartbeat) ledger entirely — one source of truth, nothing to
drift.
