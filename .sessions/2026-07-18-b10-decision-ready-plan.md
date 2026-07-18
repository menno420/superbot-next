# 2026-07-18 — B10 route-origin: turn the proposal into a decision-ready package

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the three docs landed in the
> second commit; this flip is the last.

- **📊 Model:** opus-4.8 · medium · docs-only

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
the go/no-go routes through the router's native `### Q:` block convention (its
internal design-detail defaults are labelled `D2`–`D6`, mapped to B10's own
Q2–Q6, and live only in the plan doc — no cross-doc stamp bleed).

## Verification (re-confirmed at HEAD this session)

- **Proposal citations re-read against live code (HEAD `5776b12`):**
  `NavigationSpec` is static-only (`sb/spec/panels.py:172-183`); `resolve_home_hub`
  handles `FOLLOW_PARENT` (`sb/kernel/panels/registry.py:161-166`); the render
  nav-row is origin-blind (`sb/kernel/panels/render.py:606-627`); `PanelSession`
  stores no route origin (`sb/kernel/panels/engine.py:254-271` — **the seam the
  signal is built onto**); `role.hub` is statically `home_hub="community"`
  (`sb/domain/role/panels.py:172-173`); the `nav:browse:`/`nav:selwin:`
  click-time-parsed nav-id precedent exists (`sb/kernel/panels/registry.py:36-47`)
  and back-ids are otherwise registration-minted (`:132-137`). All B10 citations
  verify.
- **Question triage:** B10 Q1 ("is it worth it?") is the single load-bearing
  owner cost/benefit call → routed to `question-router.md`. B10 Q2–Q6 (scope,
  depth, golden strategy, back-id minting, label source) are mechanical → resolved
  as flagged decide-and-flag defaults (D2–D6) in the plan doc.
- **pytest:** `python3 -m pytest -q --ignore=examples` → **3490 passed, 29
  skipped, 1 warning** in 84.91s (docs-only; `examples/` excluded per the standing
  plugin-example import gap).
- **docs-gate:** `python3 bootstrap.py check` → **exit 0**; no unreachable/badge
  finding for `docs/design/B10-route-origin-implementation-plan.md` (carries the
  `plan` badge in its first ~12 lines, reachable from `design/README.md`'s
  planning-series table). Pre-existing advisory warnings only (owner-action /
  claims / seat-digest / automerge-drift / model-line-class on OTHER cards) —
  none mine, none exit-affecting.

## Trail

- **B10-route-origin-implementation-plan.md:** new `plan` doc — TL;DR, the one
  gate it waits on (Q1), a Verification section re-reading every B10 citation, a
  "where session state lives" note pinning the `PanelSession` seam, the 2-slice
  build (slice 1 = engine capability, zero golden churn, unit-tested against a
  synthetic 2-panel open graph; slice 2 = role.hub opt-in where the origin golden
  churn lands), layer/seam safety (kernel imports spec only, no domain edge), a
  decide-and-flag defaults table (D2–D6), rough size/order, and the golden
  determinism risk.
- **question-router.md:** appended ONE OPEN `### Q:` block in Open questions — the
  B10 route-origin go/no-go with options (GO / NO-GO / DEFER) and a recommended
  default ("(c) DEFER, leaning (a)-when-a-second-need-appears" — a kernel grammar
  add earns its keep at ≥2 consumers; slice 1 ships zero churn so it's cheap when
  a second need appears). Maintainer answer + routing result left `(pending)`.
  Rewrote the Open-questions header note from "No unanswered blocks" to "One
  unanswered block". No other blocks touched (append-only respected).
- **design/README.md:** added the plan doc's row to the planning-series table
  (reachability wire).
- No `sb/` code touched — this is a PLAN (decide-and-flag), not built code; it
  makes B10 executable-pending-one-owner-decision.

## 💡 Session idea

The plan doc labels its internal design-detail defaults `D2`–`D6` (mapped to
B10's Q2–Q6) — a lightweight local numbering that reads cleanly IN the doc but
collides namespace-wise with the repo's `D1`–`D6` planning-lane doc series
(`docs/design/D1..D6-*.md`). A future reader grepping "D4" gets both the
observability-surface design doc AND this plan's golden-strategy default. Cheap
guard: when a plan doc mints local decision labels, prefix them with the doc's
own slug (e.g. `B10-D4`) so no bare `D<n>` token overloads the series namespace.
Guard recipe: a `tools/` check that flags a bare `D[1-6]` token minted as a
`### `/table-row label inside a `docs/design/*.md` that is NOT one of the
`D<n>-*.md` series files — the smell is a local label shadowing a series id.

## ⟲ Previous-session review

The 2026-07-18 settings-epic-plan-option-a session (`complete`, #562-class) set
the exact template this slice followed: a docs-only planning slice that answers
one owner call into `question-router.md` and routes it into a paired executable
plan doc, with a `design/README.md` reachability row and a born-red-then-flip
card. Reusing its shape (verification section re-reading citations, a
decide-and-flag defaults table, explicit "no D-token minted" scope note) kept
this slice fast and audit-clean — a good example of a prior card's structure
being reusable machinery, not just a log.
