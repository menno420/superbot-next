# 2026-07-13 — completeness table morning true-up (post night-run)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · morning wrap-up lane · mandate: ORDER 017
  (PR #323) close-out — verify `docs/status/completeness-table-2026-07-13.md`
  against reality at HEAD after the night's fix slices landed

## Scope

Docs-only true-up of the completeness table, one small PR:

- **fishing row + Top-gap 1 + in-flight bullet** — the fishing lane landed
  ALL four slices overnight (#313 forecast/sail · #330 rod ladder ·
  #342 bait shelf · #350 locations/structures; claim closed #353); the
  deep-system `PENDING` roster is empty
  (`sb/domain/fishing/service.py:720`). The table still described fishing
  as the "largest pending block" with slice 1 in flight — corrected, with
  the honest residue named (starter shore profile cast wiring rides the
  minigame rung; `fishing.howtofish_pending` remains).
- **mining item 3 / in-flight bullets** — WP-5 (#335) and WP-6 (#344) are
  now open PRs; flagged with their numbers.
- **headline counts** — recounted at HEAD: 49 rows, core 43✅/6⚑ ·
  admin 44✅/5⚑ · setup 47✅/2⚑ (the original "50 rows" counted the
  header line; the per-slice flip annotations consolidated).

Out of scope: rows the night's own PRs already flipped (#326/#331/#339/
#340/#347/#349/#351/#356/#357/#358 each updated their row at merge);
peer-lane branches.

## 💡 Session idea

Each landing PR re-dirties every sibling PR through
`manifest.snapshot.json` (a compiled artifact both sides always touch) —
tonight that cost four re-merge round-trips. Marking the snapshot with a
merge driver that recompiles via `tools/manifest_compile.py --write`
(gitattributes `merge=manifest-recompile`) would make those merges
self-resolving and cut the serial-landing tax to zero.

## ⟲ Previous-session review

The night-run slices each updated their own table row at merge — that
discipline kept 10 of 12 rows honest with zero true-up cost; the only
drift came from lanes whose PRs did NOT carry table edits (fishing).
Workflow improvement: make "flip your own row (or say why not)" an
explicit PR-checklist line for lanes running while an audit table is
live, so the morning true-up shrinks to a recount.
