# 2026-07-18 — design-series README status-index reconciliation (docs-only)

> **Status:** `in-progress`
>
> Born-red as the session's FIRST commit (card alone), holding the
> `substrate-gate` red while the reconciliation lands in a later commit. Flip to
> `complete` is the deliberate LAST step once the close-out is written.

## Goal

`docs/design/README.md`'s planning-mode status table (lines ~20-29) drifted:
D4/D1/D3/D6 rows read `**this PR**` and D5/D2/B8 read `planned`, but all 8 core
design docs (D1–D6 + B8/B10) are committed and landed, each carrying a `plan`
Status badge. Decisions D-0093..D-0096 settled several staged questions
(D1 render-band fonts/Pillow; D3 audit-retention + access-granularity; D6
removal deferral). Reconcile the stale status tokens and add a settled-questions
column, decisions-in-prose only.

## Scope

Docs-only. One file (`docs/design/README.md`) + this card. No `sb/` code
touched. **Stamp-gate:** D-0093 already homes in `D1-themed-card-renderer.md`,
D-0094/D-0095 in `D3-access-audit-model.md`, D-0096 in
`D6-autonomy-apparatus-removal.md` (all non-ledger). Every token already has a
sole non-ledger home, so README references them in PROSE only — no `D-00NN`
token minted here.

## Plan

1. Status column: all 8 planning-mode rows → `plan` (mirroring each doc's own
   badge, matching the file's production-readiness table style). Reflect landed
   per-doc progress inline: D1 Slice 1 render band landed (#560/#561); D4 P1
   outbox metric families armed (#562).
2. Add a "Staged questions settled" column citing (in prose, no tokens) the
   render-band Pillow decision (NOTE Pillow shipped `>=12.3.0` per #561, not
   `<12`), the D3 audit-retention + M1 access-granularity decisions, and the D6
   removal-deferral decision.
3. Keep the table format; don't rewrite prose beyond the status/decisions
   reconciliation. The settings epic plan (#563) already has its own
   production-readiness row — no action there.
