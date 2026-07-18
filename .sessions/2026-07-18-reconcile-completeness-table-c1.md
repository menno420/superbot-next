# 2026-07-18 — reconcile the 07-18 completeness table (C1 done, doc-fix done, group_pending re-scoped)

> **Status:** `in-progress`

## Goal

Verify-first reconciliation of `docs/status/completeness-table-2026-07-18.md`,
whose verdicts drifted after two closing PRs landed past its base snapshot
`782ca2d`. Three rows are stale against HEAD:

1. **C1** (setup-band except-density audit) lists `PARTIAL` but is DONE — the
   remaining `final_review.py` / `essential_steps.py` / `launcher.py` /
   `wizard.py` swallow sites were characterized by PRs #526 (`0cac02d`) and
   #538 (`bfff394` — "finish C1 audit"), completing the earlier #516/#519 legs.
2. **trivial doc-fix** (wizard.py stale docstring) lists `OPEN` but is DONE —
   PR #526 rewrote the "skipped until their seams exist" text to the resolved
   wording.
3. **settings.group_pending** is listed as a single non-mintable gap but is a
   scoped MULTI-SLICE EPIC (per-group scalar-edit panel surface: a page frame
   plus 7 edit-widget slices) that ALSO carries an unresolved owner-level
   group-routing product decision (does the per-group edit page replace
   group_pending for non-hub groups only, or also become reachable for the 5
   operator-spine hub groups?).

## Scope

Docs-only. Edits confined to `docs/status/completeness-table-2026-07-18.md`
(three rows) plus this card. No `sb/` code touched; existing table
format/columns preserved. Owner group-routing decision routed to
`docs/question-router.md` (the append-only owner-intent venue) rather than
decided here — genuine product intent, not a worker call.

## Verification (re-confirmed at HEAD this session)

- `git log -1 bfff394` → `test: pin setup launcher/wizard except boundaries
  (finish C1 audit) (#538)`; `git log -1 0cac02d` → `#526`. `#516`/`#519`
  present in log (`7ceedee`/`eb2f146`).
- `git log bfff394..HEAD -- sb/domain/setup/` is EMPTY — no new uncovered
  setup-band sites landed after the audit closed.
- `grep "skipped until" sb/domain/setup/wizard.py` → no match; the docstring
  at :106-113 now reads the resolved "lane is CLOSED" wording.
- group_pending scoped against oracle `menno420/superbot @ f87fa50` (the
  per-group edit page + 7 edit widgets) this session.

## Trail

(placeholder — filled at close-out)

## 💡 Session idea

(placeholder — filled at close-out)

## ⟲ Previous-session review

(placeholder — filled at close-out)
