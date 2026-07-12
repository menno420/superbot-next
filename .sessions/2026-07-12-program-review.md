# 2026-07-12 — program review (owner's 7 questions: architecture, parity honesty, production readiness, AI, foundations, web edits)

> **Status:** `complete`

- **📊 Model:** Fable · high · docs/audit (Q-0194)

## Scope

Whole-program review answering the owner's seven questions about
superbot-next vs the old bot (menno420/superbot): construction quality,
honest gaps, golden-parity honesty, production readiness, AI
integration, foundational sections, and web-based-edit compatibility.
Method: six parallel read-only audit areas (architecture, parity,
production/foundations, AI, web, sim-lab/backlog) over main at the
audited HEAD `c792079` (#254), synthesized into one plain-language
deliverable for the owner:

- `docs/review/program-review-2026-07-12.md` (badge `audit`) — the
  review document, every load-bearing claim cited to file:line /
  commit / PR / CI run ID.
- `docs/review/README.md` (badge `reference`) — index so the doc is
  reachable under the check_docs --strict BFS roots.
- One link line added to `docs/retro/README.md` for discoverability.

Docs-only PR — no code, no parity data, no control/ writes. Note:
main moved to `edfeca8` (#255, utility re-homes, gate 396→404,
`_unmapped` 74→66) during assembly; the review cites the audited HEAD
and flags the movement where headline counts appear.

## 💡 Session idea

The review's consolidated "Top 10 gaps" list is effectively a gen-2
program backlog seeded from evidence rather than memory — a successor
session could turn it into inbox ORDERs nearly mechanically, since
each item already carries its file/PR/run citations.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-parity-flips-wave8.md`, the most recent
completed card at branch time.) Its end-state map held: the program
was complete at 50/50 with `_unmapped` as the one remaining pool, and
its 💡 idea (dedicated re-home waves toward a green report job) is
exactly what wave 9 (#248–#255) has been executing since — gate
365→404 across seven re-home PRs. Its trap-37 lesson (re-derive park
claims at pick-up, never honor on faith) was applied here: every
audit claim in the review was re-measured at HEAD rather than
replayed from status.md memory, which is how the review caught the
stale bits it reports (current-state.md counts, COVERAGE.md frozen at
import, README-first.md's pre-flip framing).

## Close-out

Delivered in one docs-only PR on this branch: the review doc
(`docs/review/program-review-2026-07-12.md`, ~500 lines, seven verdicts
+ sim-lab/backlog synthesis + Top-10 next moves + explicit
"not measured" footer), its README index, the one-line retro link, this
card, and the telemetry row. `python3 bootstrap.py check --strict` run
locally: the eleven [stamp] findings the first draft introduced
(decision IDs re-cited outside their home docs) were resolved by citing
`docs/decisions.md` line anchors instead of restamping the IDs; after
the fix the only red was the designed born-red card hold, cleared by
this flip. No code, parity data, or control/ files touched.
