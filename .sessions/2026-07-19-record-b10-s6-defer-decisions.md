# 2026-07-19 — record B10 route-origin + S6 role-select DEFER decisions

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · docs-only

## Scope

DOCS-ONLY slice. Record two coordinator decisions (both DEFER, decide-and-flag,
PL-001) into the decisions ledger and flip their routed question-router blocks
from OPEN → ANSWERED (DEFER):

1. **B10 route-origin seam = DEFER.** Adds new kernel surface (a session-scoped
   route-origin signal + a `BACK_TO_ORIGIN` nav mode) for a single cosmetic
   back-button label with no second consumer today; reversible — revisit when a
   second route-origin consumer appears organically.
2. **S6 role-select widget = DEFER.** No reachable role-typed setting exists in
   any non-hub group, so there is no honest golden target to build against;
   build the widget when such a setting exists organically.

Deliverables:
- `docs/decisions.md`: append TWO decision entries (D-0098 B10, D-0099 S6) —
  status decided / date 2026-07-19 / verdict + why + provenance — matching the
  file's existing entry format.
- `docs/question-router.md`: flip the B10 and S6 Open blocks → ANSWERED (DEFER,
  2026-07-19) with the answer + a one-line rationale, move them into the
  Answered section, and bump the open-blocks header count (three → one; only the
  D2 real-time minigame-framework block stays open). STAMP-GATE: the new D-NN
  tokens live ONLY in the ledger — the router refers to each decision in prose
  ("recorded in the decisions ledger 2026-07-19"), never the token, so each new
  id lands in zero non-ledger docs.
- xp negative-level guard question stays OPEN — untouched (genuine product fork,
  stays routed).
- NO code, goldens, or manifests touched.

Provenance: both decided by the coordinator under decide-and-flag; relayed via
the coordinator session 2026-07-19. Pure reversible DEFERs.

This card is born red (`in-progress`) and holds the substrate-gate until the
work lands; it flips to `complete` as the last commit.
