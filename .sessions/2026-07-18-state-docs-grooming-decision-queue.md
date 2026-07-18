# 2026-07-18 — state-docs grooming + consolidated owner-decision queue

> **Status:** `in-progress`
>
> Born-red: this card is the FIRST commit alone (holds the `substrate-gate`
> HOLD red) so the docs land in a later commit and this card flips to
> `complete` as the deliberate LAST commit.

- **📊 Model:** (fill at flip)

## Goal

Land ONE docs-only grooming slice: refresh the state docs to reflect tonight's
2026-07-18 landed work, and surface the consolidated owner-decision queue in
one discoverable place.

1. `docs/current-state.md` — update "what is true right now" for tonight's
   merges: the D1 render band exists (kernel leaf, no consumer yet), Pillow
   `>=12.3.0` is a hard runtime dep (security bump, NOT the originally-scoped
   `<12`), the dark outbox metric families are armed at the composition root,
   the settings group-routing decision is made (option A) with an epic plan
   queued, and the clean-mint port surface is exhausted. Refresh the stale test
   count.
2. `docs/NEXT-TASKS.md` — item 1 shifts from "finish the port to full parity"
   to the current phase: the clean-mint surface is exhausted, so the work is
   now (a) owner-gated forward proposals and (b) small self-initiated
   improvements. Item 2 (already complete, #555) untouched unless inconsistent.
3. Surface the OWNER-DECISION QUEUE — make the already-consolidated agenda
   (`docs/design/OWNER-DECISIONS-2026-07-18.md`, 31 prioritized rows gathering
   every open design-doc question + standing gates) DISCOVERABLE from the state
   docs, and index question-router's own residual open owner items
   (CL-5b custody, K10 API-keys / test-guild) beside it. Do not duplicate the
   agenda; do not invent questions.

## Scope

Docs-only. `docs/current-state.md`, `docs/NEXT-TASKS.md`, `docs/question-router.md`
(+ this card). No `sb/` code touched. No decision-ID (`D-00NN`) token minted
(stamp-gate: no `D-00NN` in 2+ non-ledger docs).

## Verification

(fill at flip: pytest tail + `bootstrap.py check` docs-gate + stamp-gate grep)

## Trail

(fill at flip)

## 💡 Session idea

(fill at flip)

## ⟲ Previous-session review

(fill at flip)
