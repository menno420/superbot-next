# 2026-07-18 — reconcile the 07-18 completeness table (C1 done, doc-fix done, group_pending re-scoped)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · medium · docs-only

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

- Two rows MOVED from the "GENUINELY OPEN" table into "DONE / NOT-A-GAP":
  **C1** (evidence: #516 `7ceedee` / #519 `eb2f146` / #526 `0cac02d` / #538
  `bfff394`; `git log bfff394..HEAD -- sb/domain/setup/` empty) and the
  **setup docstring** doc-fix (#526; `grep "skipped until"
  sb/domain/setup/wizard.py` empty). Each row reformatted to the DONE table's
  3 columns (Item | Verdict | Evidence).
- **settings.group_pending** rewritten IN PLACE in the OPEN table: verdict kept
  OPEN, "Mintable?" flipped NOT-mintable → "MULTI-SLICE EPIC (not a single
  mint)"; body now enumerates page frame S0 + 7 edit widgets, records "large
  but buildable, not blocked" (write ops `settings.set_scalar`/`clear_scalar`
  + modal/windowed-select machinery already exist), and routes the group-routing
  product decision to `docs/question-router.md`. Oracle ref `f87fa50`.
- DECIDE-AND-FLAG (PL-001): also made two MINIMAL consistency touch-ups the
  three flips entailed — the C5 row's dangling "(see OPEN/trivial)" cross-ref
  and the Conclusion's "C1 remaining / wizard.py docstring fix" prose both
  named items now DONE, so a reconciliation snapshot that left them would
  contradict itself. Kept each to the minimal phrase; no other rows touched.
- No decision-ID (`D-00NN`) token introduced into the table (verified by grep).
- Verify: `pytest -q --ignore=examples` → **3443 passed, 17 skipped** (docs-only
  change). The `examples/superbot-plugin-hello` collection error
  (`ModuleNotFoundError: superbot_plugin_hello`) is PRE-EXISTING and unrelated
  (plugin example not on the path) — hence the `--ignore=examples`.

## 💡 Session idea

Completeness-table snapshots are dated, hand-verified, and go stale the moment
a closing PR lands past their base — exactly the drift this session fixed by
hand (C1/doc-fix closed one/two PRs after base `782ca2d`). A cheap standing
guard would catch it: a checker that, for each row citing a `#NNNN`/SHA as its
DONE/OPEN evidence, flags when a LATER commit touched the same cited path
(`git log <base>..HEAD -- <path>`) — turning "is this verdict stale?" from a
manual oracle-vs-HEAD re-read into a mechanical diff. It would not judge
correctness (that still needs a human read), only surface the rows whose
underlying source moved since the snapshot's base — the precise signal that
sent three verdicts stale here.

## ⟲ Previous-session review

The 2026-07-18 rps-solo-edit-in-place session (`complete`, #552) was a tight,
single-item slice — item 2 of the rps-tournament remaining-surface idea doc —
that reused an existing presenter seam (`refresh_session_view`) rather than
inventing one, and named its precedent (the blackjack `table_click` lane)
explicitly. Same discipline this slice aimed for: do ONE contained thing, lean
on what already exists, and cite the exact evidence. The contrast worth noting
is scope-shape — that session shipped runtime behaviour behind a golden; this
one is pure docs reconciliation, so its "verification" is git-log/grep evidence
re-confirmed at HEAD, not a minted golden.
