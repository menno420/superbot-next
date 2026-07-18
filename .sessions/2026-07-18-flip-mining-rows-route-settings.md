# 2026-07-18 — flip B2/B3 mining rows DONE, route the settings per-group edit-page owner decision

> **Status:** `in-progress`

- **📊 Model:** _pending_

## Goal

Land one contained docs-only slice that fixes two stale artifacts the prior
07-18 reconcile (#556) missed:

1. `docs/status/completeness-table-2026-07-18.md` still lists **B2** (mining
   skill-panel spend) and **B3** (mining workshop craft selector) as OPEN /
   MINTABLE, but BOTH already landed on main — #556 flipped C1 + the wizard
   doc-fix but left these two mining rows stale.
2. `docs/question-router.md` has no entry for the `settings.group_pending`
   per-group scalar-edit-page owner decision, even though #556's report
   CLAIMED to route it there — the routing never actually landed.

## Scope

Docs-only. Two files:
- `docs/status/completeness-table-2026-07-18.md` — flip B2 + B3 OPEN → DONE,
  move them into the DONE / NOT-A-GAP section (same shape as #556's C1 flip),
  citing PR #527 (B2) and PR #532 (B3). No other rows touched.
- `docs/question-router.md` — append ONE properly-formatted owner-intent entry
  for the per-group edit-page group-routing decision. No decision-ID token.

Plus this card. No `sb/` code touched.

## Verification (re-confirmed at HEAD this session)

- _pending_

## Trail

- _pending_

## 💡 Session idea

- _pending_

## ⟲ Previous-session review

- _pending_
