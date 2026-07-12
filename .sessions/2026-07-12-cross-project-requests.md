# 2026-07-12 — cross-project requests: sim-lab simulation asks + IDEA-project expansion asks

> **Status:** `complete`

- **📊 Model:** fable-5 · high · docs/requests (owner directive 2026-07-12)

## Scope

Owner directive (2026-07-12): file (a) requests for things that could be
SIMULATED, addressed to the sibling sim-lab project, and (b) requests to
the IDEA project to expand existing features or propose new ones — both
as docs in one branch, READY PR, merged on green. Deliverables:

- `docs/requests/README.md` — index + routing convention (new
  directory; no prior cross-project outbox convention existed in this
  repo — verified by repo-wide search, `control/` is inbound-only with
  the manager as its one writer).
- `docs/requests/sim-lab-requests-2026-07-12.md` — six simulation
  requests, each grounded in a counted/verified repo fact.
- `docs/requests/idea-project-requests-2026-07-12.md` — six feature
  areas plus an explicit net-new invitation, each with cited current
  state and constraints.

Evidence base: `docs/review/program-review-2026-07-12.md` re-verified
against main at `764a393` (#260/#261 — post-review movement folded in:
corpus 468, `_unmapped` 56, deathmatch row 51 born, sim baseline 802
pins).

## Numbers re-counted at HEAD (where they moved since the review)

- Sim-gate baseline: **802** layout assignments, **802/802 `exempt`**,
  zero sim-backed, `sim/records/` empty — the review's 788 was true at
  `c792079`; 802 is the count at `764a393`.
- Golden corpus: **468** case files; steps histogram `{1: 461, 2: 4,
  3: 3}`; input kinds `{command: 408, slash: 66, modal: 3, click: 1}` —
  exactly 1 click + 3 modal submits corpus-wide.
- Live ladder: rows 8 (Games, band 6) and 9 (Knowledge + AI, band 7)
  both `pending` at `docs/status/testing-report-2026-07-09.md:37-38`.

## 💡 Session idea

The stamp-discipline check (one decision-id citation home outside the
ledger) quietly shapes how request docs must cite decisions — by
`docs/decisions.md:LINE` anchor, never by bare ID. Worth one line in the
doc-authoring guidance (`docs/requests/README.md` or the collaboration
model) so future outbound docs don't burn a draft cycle rediscovering it
the way the program-review session did.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-kit-upgrade-v1.14.0.md`, the most recent
completed card at branch time.) A clean distribution-only session: its
verify recipe (`python3 bootstrap.py check --strict` exit 0 + full
pytest) was reused verbatim here and its lane-owed follow-ups list
(diverged docs awaiting manual merge) was left untouched by this
docs-only round — nothing in `docs/requests/` collides with the four
diverged kit templates it names. Its counts (1729 passed / 13 skipped)
moved to 1733/13 here via the sibling merges, consistent with the
#261 deathmatch birth landing between the two sessions.

## Close-out

Delivered in one docs-only READY PR on this branch: the two request docs
+ their README index (reachable both as a `docs/**/README.md` BFS root
and via the added link from `docs/review/README.md`), this card, and the
telemetry row (Q-0194 convention). Verify at the branch head:
`python3 bootstrap.py check --strict` — zero doc findings (badge, link,
reachability, stamp all clean; only the designed born-red card hold,
cleared by this flip) and `python3 -m pytest -q` — **1733 passed / 13
skipped** (after `bash scripts/env-setup.sh` + editable install of
`examples/superbot-plugin-hello`, which bare collection needs). No code,
no parity data, no control/ writes; `control/inbox.md` ORDERs 014/015
were verified already-executed on main (#257, #259) before branching.
