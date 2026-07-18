# 2026-07-18 — D2 real-time minigame framework: sharpen into a decision-ready package

> **Status:** `in-progress`
>
> Born red as the session's FIRST commit (card alone, holds the substrate-gate
> HOLD). The refinement lands in the second commit; this card flips to
> `complete` as the deliberate LAST commit once the close-out is written.

## Goal

Land ONE docs-only slice that makes D2
(`docs/design/D2-realtime-minigame-framework.md`) **decision-ready** — one owner
go/no-go away from executable:

1. Refine the D2 doc IN PLACE with a **Decision-ready refinement** section: a
   recommended reusable-primitive shape (grounded in the fishing code it lifts),
   the six shape sub-questions resolved as flagged decide-and-flag defaults (each
   owner-overridable), and a crisp cost/unblock statement.
2. `docs/question-router.md` — append ONE crisp OPEN owner go/no-go entry (the
   single load-bearing "build the framework now / defer / never" call) with a
   RECOMMENDED DEFAULT + one-line honest rationale, marked OPEN pending owner.

## Scope

Docs-only. Two docs (D2 in place + a router block) + this card. No `sb/` code
touched — D2 stays a PLAN. D-0090 is already homed in the D2 doc; NO `D-00NN`
token minted or spread — the go/no-go routes through the router's native
`### Q:` block convention and refers to the fishing determinism ruling in prose.
