# 2026-07-13 — command/component curation report (ORDER 017 item 2, KEEP/REWORK/DROP)

> **Status:** `complete`

- **📊 Model:** fable-5 · night-run curation review (ORDER 017 item 2)

## Scope

The night-run curation report — ORDER 017 item 2. An evidenced
KEEP / REWORK / DROP verdict for every command and interactive component
across `sb/manifest` + `sb/domain` + the panels surface, compiled into the
deliverable `docs/review/curation-report-2026-07-13.md` on this branch
(`claude/curation-report`). This first commit is the claim
(`control/claims/curation-report.md`) + this born-red card; the report
follows on the same branch. Contained reworks do NOT ride here — each ships
on its own `claude/curation-rework-<slug>` branch with its own claim.

## What shipped

- `docs/review/curation-report-2026-07-13.md` — the full curation report:
  **1088 items** (407 commands, 681 components), each with exactly one
  verdict and a one-line evidence citation. Verdicts: **KEEP 918 ·
  REWORK 110 · DROP 60 · NOT-MEASURED 0**. Report-only — nothing deleted,
  renamed, or rewired by the document itself; DROP calls are
  owner-ratifiable proposals.
- Three contained curation-rework PRs spun off the report's
  "shipping tonight" tier, retiring its 17 pending-terminal rows:
  **PR #332** (`claude/curation-rework-nav-wiring`), **PR #333**
  (`claude/curation-rework-cleanup-words`), **PR #336**
  (`claude/curation-rework-btd6-paragon`). This close-out commit
  backfills their PR numbers into the report's §REWORK(a) bundle list.

## Verification

- `python3 bootstrap.py check --strict` — exit 0 (the pre-existing
  advisory claims-format warning on `mining-write-parity-lane.md` is
  known-acceptable and not introduced by this branch).
- `python3 -m pytest tests/ -q` — green, no failures.

## 💡 Session idea

The report cites lane/PR anchors inline (`PR #312`, `PR #317`, the three
rework bundles) and this session had to hand-backfill numbers that were
"pending" at write time. A tiny doc-drift checker that extracts `PR #NNN`
citations from `docs/review/*.md` and compares each against live GitHub
state (open/merged/closed, branch still exists) would catch dangling
"pending" placeholders and citations of long-merged PRs the same way the
stamp checker catches decision-token drift — review docs stay load-bearing
instead of quietly rotting.

## ⟲ Previous-session review

Previous card `2026-07-13-install-auto-merge-enabler.md` installed the
auto-merge enabler (PR #321) and its watch item — "the enabler proves
itself on the next real agent PR" — is being cashed out by exactly this
session's PRs (#327, #332, #333, #336). One interaction the card didn't
call out: its in-progress/drafted session-card SKIP guard means a
born-red-card branch like this one *cannot arm until the card flip is the
final commit* — the flip is not just bookkeeping, it is the arm
precondition. Worth a line in that card's guard recipe; otherwise the
card is a model close-out: exact failure surface named (repo
"Allow auto-merge" toggle, `::warning::` in the arm step) so verification
is a single Checks-tab read.
