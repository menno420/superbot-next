# 2026-07-13 — anchor-refresh sweep: proposed design record (docs-only)

> **Status:** `complete`

- **📊 Model:** `fable-5` · docs lane · mandate: convert the parked #341
  scoping finding (the anchor-refresh sweep needs four unmade design
  calls) into an owner-reviewable PROPOSED design record

## Scope

Docs-only. The game-sections slice-3 lane (#341) parked the promised
"anchor sweep" as a successor because scoping it surfaced four design
calls no agent should make alone: session-hub anchorability vs the
pinned no-anchor goldens, panel-id provenance missing from
`panel_anchors`, the absent anchor-editor adapter port, and the
subsystem→hub fan-out / rate-limit posture. This session verifies the
parked citations at HEAD, writes `docs/design/anchor-refresh-sweep.md`
as a PROPOSED (not decided) design record laying out each call with
options / recommendation / cost, links it from `docs/design/README.md`,
and claims the branch. No code, no migration, no golden, no D-number —
`docs/decisions.md`'s grammar is closed to `decided|superseded|retired`,
so the D-entry mints only when the owner decides.

## Close-out

- `docs/design/anchor-refresh-sweep.md` (badge `ideas` — the badge
  vocabulary is CLOSED: archive/audit/binding/historical/ideas/
  living-ledger/owner-guidance/plan/reference, no `proposed`; `ideas`
  is the closest honest token and the doc's prose carries PROPOSED),
  linked from `docs/design/README.md`. No D-number minted; next free
  is D-0083.
- Citation drift found and corrected against the parked finding:
  `blackjack.hub` (`sb/domain/blackjack/panels.py:109`) is NOT
  session-lifecycle — the parked `:276,307` lines were its
  tournament-table/results session views; immaterial (that hub renders
  no enablement state). All other citations re-verified at `de3824b`
  (engine skip `:105-110`/`:323-326`, nine-column `0025`, presenter
  `panel_view.py:209-219`, emitter precedent `egress.py:46-50`, bot
  born `main.py:384`, resolver `render.py:246/:249/:544`).
- Stamp discipline forced D-0082 out of the new doc entirely —
  `check_stamp_discipline` wants each D-id at ONE doc home
  (`game-sections.md` keeps it); the new doc cites the lane by design
  doc, not by ledger id.
- Gates: pytest 2133 passed / 13 skipped · `check_doc_cites` OK
  (758 checked, 0 missing) · `manifest_compile` green (48 manifests,
  hash unchanged — docs-only) · `bootstrap.py check --strict` clean to
  the designed born-red hold + the known pre-existing mining-lane
  claims advisory. `.substrate/guard-fires.jsonl` check-run appends
  restored, not committed (majority precedent: 3 commits ever).

## 💡 Session idea

The badge vocabulary and the decisions.md status grammar both lack a
pre-decision token, so every owner-reviewable proposal will squat on
`ideas` and carry its real status in prose — fine once, drift-prone at
scale. If proposals become a recurring lane, add a `proposed` badge to
the kit vocabulary (one enum entry + the data-lifecycle class call:
proposals probably want an expiry nudge like plans' 60-day window)
instead of letting each doc improvise.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-minigame-sections-2.md` @ de3824b — the
newest card at boot.) A complete close-out whose shipped list matches
the #337 merge diff (settings panel + hub group + routing + 14 tests +
the flagged settings-golden re-cut). Two things transferred directly:
its PL-001 flag pattern (name the convention that could NOT carry the
work — `f"{group}.hub"` vs the player hub — then state the honest
route) is the exact posture this doc uses for the decisions.md-status
question, and its layout-budget note ("adding a disable-all would cross
the sim-gate floor — deliberately not added") is the model for this
doc's cost lines: name the gate a choice trips, not just the choice.
One friction: the card cites design §5/§6 by number while the design
doc's section numbers shifted during review — this doc pins citations
to file:line at a named HEAD instead.
