# 2026-07-18 — B10 route-origin: turn the proposal into a decision-ready package

> **Status:** `in-progress`
>
> Born-red as the session's FIRST commit (per `.sessions/README.md`) so the
> in-flight docs slice is visible to parallel sessions; the born-red card holds
> the substrate-gate red until the deliberate LAST-commit flip to `complete`.

- **📊 Model:** [[fill:model-line]]

## Goal

Land ONE docs-only slice that makes B10 (`docs/design/B10-panel-route-origin.md`)
**executable-pending-one-decision**:

1. `docs/design/B10-route-origin-implementation-plan.md` — a NEW `plan` doc: the
   concrete implementation plan IF the owner approves — the session-scoped
   route-origin signal built onto the existing `PanelSession` per-message seam,
   the `BACK_TO_ORIGIN` nav-mode addition to `sb/spec/panels.py` + the engine
   resolver, the role-hub opt-in as first consumer, layer-safe (kernel imports
   spec only), plus the golden/tests each step needs. Mechanical design questions
   resolved as flagged decide-and-flag defaults. Reachable via a
   `docs/design/README.md` table row.
2. `docs/question-router.md` — append ONE crisp owner go/no-go entry (the single
   load-bearing cost/benefit call) with a RECOMMENDED DEFAULT + one-line
   rationale, marked OPEN pending owner. Routed, not decided.

## Scope

Docs-only. Two docs (+ a `design/README.md` reachability row) + this card. No
`sb/` code touched — B10 stays a PLAN. No decision-ID (`D-00NN`) token minted;
the go/no-go routes through the router's native `### Q:` block convention.

## Verification (to fill at close)

- **pytest:** [[fill:pytest-tail]]
- **docs-gate:** [[fill:docs-gate]]

## Trail

[[fill:trail]]

## 💡 Session idea

[[fill:idea]]

## ⟲ Previous-session review

[[fill:previous-session-review]]
