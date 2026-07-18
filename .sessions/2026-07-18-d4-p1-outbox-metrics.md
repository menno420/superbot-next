# 2026-07-18 — arm the dark outbox metric families (D4 observability, P1)

> **Status:** `in-progress`

- **📊 Model:** _pending_

## Scope

Build the D4 observability design's P1 item: arm the four outbox metric
families that are declared in code but never registered on the live registry
(so their emits land in a swallowing try/except), and add the missing emitter
for the one gauge that has no emitter anywhere in the tree.

Two concrete gaps closed:

1. The composition root builds the registry with the default `METRICS` tuple
   only, so `OUTBOX_METRICS` (`outbox_pending_age_seconds`,
   `outbox_delivered_total`, `outbox_dead_letter_total`, `outbox_claims_total`)
   is never instantiated — the relay's guarded counter bumps hit a `KeyError`
   that the guard discards. The outbox is the durability spine; its health is
   unobservable on `/metrics`.
2. `outbox_pending_age_seconds` (the backpressure gauge) has no emitter at all.

Pure wiring of declared families: no new metric semantics, no backend/auth/
threshold decisions (those remain owner questions in the D4 doc's Open
Questions and land with the later slices).

## Plan

- Register the union at the composition root (`build_registry(METRICS +
  OUTBOX_METRICS)`), the same union the cardinality gate already validates.
- Add a guarded gauge `_set` twin next to the relay's guarded counter `_inc`,
  a bounded `pending_age_seconds` read on the store, and emit the gauge on the
  relay tick.
- Unit tests proving the four families now emit at the outbox seam, plus a
  render smoke asserting a non-empty `/metrics` body carrying an outbox family.

## 💡 Session idea

_pending_

## ⟲ Previous-session review

_pending_
