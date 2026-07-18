# claim: arm the dark outbox metric families (D4 observability, P1)

- **branch:** `claude/d4-p1-outbox-metrics`
- **scope:** Register the already-declared `OUTBOX_METRICS` family tuple at the
  composition root so the four outbox families are live on `/metrics`, and add
  the missing emitter for the `outbox_pending_age_seconds` gauge on the relay
  tick. Pure wiring of declared families — no new metric semantics, no backend/
  auth/threshold choices (those stay owner questions in the D4 doc). Unit tests
  proving the families now emit at the outbox seam.
- **date:** 2026-07-18
