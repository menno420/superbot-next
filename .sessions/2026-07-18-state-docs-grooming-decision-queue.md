# 2026-07-18 — state-docs grooming + consolidated owner-decision queue

> **Status:** `complete`
>
> Born-red then flipped: the FIRST commit was this card alone (held the
> `substrate-gate` HOLD red); the docs landed in the second commit; this flip to
> `complete` is the deliberate LAST commit (per `.sessions/README.md`), releasing
> the HOLD.

- **📊 Model:** opus-4.8 · medium · docs-only

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

## Verification (docs-only)

- **pytest:** `python3 -m pytest -q --ignore=examples` → **3490 passed, 29
  skipped, 1 warning** in 75.11s (the `audioop` DeprecationWarning only). No
  `sb/` code touched, so unchanged by the doc edits — this is the count now cited
  in `current-state.md` (was 3,160).
- **docs-gate:** `python3 bootstrap.py check` → **exit 0**; all three edited docs
  reachable + badges intact (no `[unreachable]`/badge finding on
  current-state.md / NEXT-TASKS.md / question-router.md). Only advisory warnings
  (owner-action / claims-format / seat-digest / automerge-drift / model-line-class
  on OTHER cards) — none mine, none exit-affecting. The lone red before this flip
  was the born-red card's own `in-progress` status (the intended HOLD).
- **stamp-gate:** `grep -rnE 'D-009[0-9]' docs/ --include='*.md' | grep -v
  docs/decisions.md` shows `D-0090` only in `D2-realtime-minigame-framework.md`
  and `D-0091` only in `status/testing-report-2026-07-09.md` — **no token in 2+
  non-ledger docs**. My three edited docs mint **no new `D-00NN` token** (the sole
  `D-0024` in question-router `:288` pre-existed in the K10 answered block).

## Trail

- **current-state.md:** baseline test count 3,160 → 3,490 (with the render/metrics
  test provenance); "In flight" remaining-work line reframed from
  "port-to-full-parity + game-surface backlog" to the planning-led phase; added an
  **"Open owner decisions (one place)"** pointer to the consolidated agenda; a new
  top "Recently shipped" entry for the 2026-07-18 wave (D1 render band + Pillow
  security floor, D4 P1 outbox metrics + `ALL_METRICS` seam, settings option-A +
  epic plan).
- **NEXT-TASKS.md:** item 1 rewritten from "Finish the port to full parity" to
  "Planning phase — clean-mint surface exhausted", split into lane (a) owner-gated
  forward proposals and lane (b) small self-initiated improvements. Item 2 (#555,
  already complete) left intact.
- **question-router.md:** added an **"Open owner decisions — one-place index"**
  under Open questions — points to the consolidated agenda
  (`design/OWNER-DECISIONS-2026-07-18.md`, 31 rows) and indexes the router's own
  residual owner items (CL-5b custody; K10 API-keys / test-guild), with the
  settings decision noted answered (option A). No new Q-block minted (append-only
  invariant held); it is a digest/index, not history rewrite.
- No `sb/` code touched — pure state-docs grooming. `.substrate/guard-fires.jsonl`
  delta (checker telemetry) committed with the docs, not reverted.

## 💡 Session idea

The consolidated owner-decision agenda (`design/OWNER-DECISIONS-2026-07-18.md`) is
**date-stamped and point-in-time** — as rows get answered (settings already is)
and new design docs land, it silently drifts from the live open-question set, yet
`current-state.md` + `question-router.md` now hard-link it as "the one place." A
cheap guard: a `tools/check_decision_queue_fresh.py` that greps each
`docs/design/*.md` for an "§ Open questions" section and asserts every open one is
represented in the newest `OWNER-DECISIONS-*.md` (and that answered rows are struck),
warn-only — so the "one place" claim can't quietly rot the way the 07-13
completeness table did before its 07-18 reconciliation.

## ⟲ Previous-session review

The 2026-07-18 settings-epic-plan-option-a session (`complete`, #563) modeled the
discipline this slice leaned on: it recorded the owner's option-A ruling into
`question-router.md` **and** immediately routed it into an executable S0–S7 plan
doc, so tonight I could cite the decision as *answered-with-a-home* rather than
re-litigate it — a clean example of "a decision isn't done until its routing
target's bytes exist."
