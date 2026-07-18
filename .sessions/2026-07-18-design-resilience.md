# 2026-07-18 — Resilience design doc (outbox delivery + DB pool)

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · docs · resilience design doc — outbox retry/dead-letter reach + DB reconnect/fail-closed (born-red, holds substrate-gate)

## Scope

A NEW production-readiness design track, beyond the D1–D6 planning-mode lanes:
**resilience of the two durability spines** — outbox→Discord delivery and the
DB pool. It turns two operational risks into a grounded design doc the owner
reacts to and prioritizes: (1) the outbox retry/backoff/dead-letter machinery
is real but its retry boundary stops at the **bus publish-accept**, not at the
**Discord ack**, so a transient gateway/HTTP 429 in the effectful subscriber is
silently dropped as "delivered"; (2) the DB seam already fails-closed with a
typed `DBUnavailable`, but has **no reconnect-with-backoff, no circuit breaker,
and no boot retry**, so a managed-Postgres failover/maintenance flap makes every
request pay the full command timeout twice before refusing, and can crash the
process at boot.

Docs-only planning artifact — no `sb/` code changes. Grounded evidence-first in
the ACTUAL outbox + db kernel read this session
(`sb/kernel/outbox/{relay,store,enqueue,metrics}.py`,
`sb/kernel/db/{pool,idempotency}.py`, `sb/kernel/events_bus.py`, the Discord
egress swallow in `sb/adapters/discord/message_feed.py`), with `file:line`
citations at HEAD `cae15f8`.

## Deliver

- `docs/design/R-resilience-delivery-and-db.md` — the fuller design doc: TL;DR,
  Problem (two grounded gaps — outbox retry reach + DB flap resilience), Proposed
  design (outbox: retry-to-Discord-ack via a delivery-status return + jitter +
  dead-letter replay; DB: reconnect-with-backoff + circuit breaker + fast
  fail-closed anchored on the idempotency ledger), Affected surfaces, Rough size
  (S/M/L per component + slicing: outbox reach first — highest user-facing
  value; DB reconnect second), and Open questions for the owner (backoff bounds,
  dead-letter retention/replay, breaker thresholds, refuse-vs-queue UX,
  dead-letter-growth alerting). `> **Status:** \`plan\`` badge (a valid docs-gate
  token).
- `docs/design/README.md` — a NEW `## Beyond D1–D6 — production-readiness tracks`
  section AFTER the existing D-series table, with a `[Resilience](R-resilience-delivery-and-db.md)`
  row; every existing D-series row is preserved untouched (sibling design-doc PRs
  edit the same file).

## Verification

- `python3 bootstrap.py check --strict` → 0 exit-affecting findings (badges valid
  + the new doc reachable from the design index); the only red in CI is this
  card's own designed born-red hold on the substrate-gate until the card flips
  complete.
- No `sb/` or test code touched — docs-only; the functional CI gates ride green,
  substrate-gate is the expected sole hold.

## 💡 Session idea

The load-bearing finding is that both spines are **more built than the topic
assumed, and the gap is one layer deeper than "add retry".** The outbox already
has bounded exponential backoff (`relay.py:39-43`), a DEAD dead-letter status
(`store.py:40`), 90d retention, and an operator finding on exhaustion — but the
`try/except` it retries on wraps `bus.emit` (`relay.py:95-102`), and the bus
gives **per-handler isolation** (`events_bus.py:38-50`, "publish-accepted, not
delivered — §2.8 honesty") while the effectful Discord subscriber **swallows its
own `HTTPException`** (`message_feed.py:198-199,210,229-231`). So the retry
boundary and the failure point are on opposite sides of an isolation seam: the
relay marks the row DELIVERED even when zero subscribers succeeded (it discards
`emit`'s returned delivered-count). The fix is not "add a dead-letter store" —
it exists — it is **move the retry boundary to the Discord ack** by having the
egress report delivery status back, so the outbox's existing backoff/dead-letter
machinery finally covers the failure it was built for. Symmetrically the DB seam
already fails-closed (`pool.py:16-18,220-223`, `DBUnavailable`) and revalidates
once on checkout (`checked_acquire`, `pool.py:161-192`) — the gap is that
"refuse" is **slow and unbounded**: no breaker to make refusal fast/cheap, no
backoff between the two acquire attempts, no boot retry. The idempotency ledger
(`idempotency.py`, `once()`/`record_outcome` atomic in one txn) is the anchor
that makes a *fast* fail-closed safe: refusing before the txn opens leaves no
half-applied state, so a breaker can shed load during a flap and the write
replays cleanly later.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-design-b10-route-origin.md` (#531) and, through it,
the planning-mode design-doc series it carries forward from D4 (#528): read the
subsystem in source, cite `file:line`, verdict only on verified ground, and open
the doc as a born-red card holding only the substrate-gate. This card extends the
same method to a NEW track beyond D1–D6 — every gap named (the outbox's
publish-accept-vs-Discord-ack boundary, the bus isolation seam, the DB seam's
slow unbounded refuse) is grounded in a real citation from the outbox/db/bus
code, not inferred from the topic prompt — and it reuses the exact born-red /
card-flips-complete landing doctrine D4 and B10 proved out. Distinct from B10
(panel nav grammar) and D4 (observability wiring): this is the first
**resilience** track, and it deliberately corrects the topic's "no retry/no
reconnect" framing against what the code actually already ships.
