# R — Resilience: outbox→Discord delivery + DB pool flap-tolerance

> **Status:** `plan`
>
> A production-readiness design proposal, **beyond the D1–D6 planning lanes** —
> the first entry in the "Beyond D1–D6 — production-readiness tracks" section of
> the design index. This is a PLAN, not built work — the owner reacts and
> prioritizes; the code and `docs/decisions.md` win once slices land. Evidence
> citations are `file:line` at HEAD `cae15f8` unless noted.

## TL;DR

The two durability spines — the **outbox→Discord delivery lane** and the **DB
pool** — are already built with more resilience than a greenfield read assumes,
and in both cases the production gap is **one layer deeper than "add retry"**:

- **Outbox.** Bounded exponential backoff, a `DEAD` dead-letter status with 90d
  retention, an operator finding on exhaustion, and dead-letter metrics all
  exist (`sb/kernel/outbox/relay.py:36-43,103-146`, `store.py:37-41,179-203`).
  But the `try/except` those retries hang off wraps **`bus.emit`**, and the bus
  gives per-handler isolation — "publish-accepted, not delivered"
  (`sb/kernel/events_bus.py:7-8,38-50`) — while the effectful Discord subscriber
  **swallows its own `HTTPException`** (`sb/adapters/discord/message_feed.py:210`).
  So the retry boundary sits on the wrong side of an isolation seam: a transient
  gateway blip or a 429 inside egress is dropped, and the relay marks the row
  `delivered`. The fix is **move the retry boundary to the Discord ack**, so the
  existing backoff/dead-letter machinery finally covers the failure it was built
  for (plus jitter + a dead-letter replay path).
- **DB pool.** The seam already fails-closed with one typed signal
  (`DBUnavailable`, `sb/kernel/db/pool.py:69-78`) and revalidates a connection
  once on checkout (`checked_acquire`, `pool.py:161-192`). The gap is that
  "refuse" is **slow and unbounded**: no circuit breaker to make refusal fast and
  cheap during an outage, no backoff between the two acquire attempts, and no
  boot retry (a flap during deploy crashes the process). Add
  **reconnect-with-backoff + a circuit breaker + a fast fail-closed path**,
  anchored on the idempotency ledger (`sb/kernel/db/idempotency.py`) so a refused
  write leaves no half-applied state and replays cleanly.

Each is a small-to-medium, landable slice. Outbox delivery-reach lands first —
it is the highest user-facing value (it closes a **silent** dropped-effect).

## Problem

Two resilience gaps, each grounded in the current code.

### P1 — Outbox retry/dead-letter stops at publish-accept, not at the Discord ack

The outbox delivery lane is genuinely well built and should be credited. The
relay claims rows atomically (`SKIP LOCKED` + lease), and on failure runs a real
retry-or-dead decision:

- **Bounded exponential backoff** — `backoff(n) = min(5 · 2^(n-1), 300)` seconds
  (`sb/kernel/outbox/relay.py:39-43`), applied on each retry via
  `mark_retry_or_dead`, which bumps `available_at` by the backoff and flips the
  row back to `pending` (`sb/kernel/outbox/store.py:198-202`).
- **A dead-letter store** — `OutboxStatus.DEAD` is a terminal status
  (`store.py:40`); after `MAX_ATTEMPTS = 12` bus-level failures
  (`relay.py:36`) the row goes `dead`, is retained 90d
  (`store.py:96`, `retention="delivered:7d;dead:90d"`), an `outbox_dead_letter_total`
  counter is bumped, and an operator finding is recorded
  (`relay.py:113-146`).
- **The two-counter design** deliberately separates `claims` (leases taken —
  crash-loop signal) from `delivery_attempts` (bus-level failures — gates DEAD),
  so a crash-looping relay can never dead-letter a healthy event
  (`store.py:44-51`, "finding 6").

So retry, backoff, and dead-letter **exist**. The gap is **what they measure a
failure against**. The relay's `try` wraps exactly one call — the bus emit:

```
await self._bus.emit(row.event_name, **dict(row.payload), _outbox_dedup_key=…)
```
(`sb/kernel/outbox/relay.py:95-102`). On the clean path it immediately calls
`mark_delivered` (`relay.py:116-119`). But `EventBus.emit` is deliberately
**publish-accepted, not delivered**: it loops subscribers with per-handler
isolation, logs-and-swallows any subscriber exception, and returns the *count*
of handlers that completed — "one failing subscriber never blocks the others or
the emitter … `event_emitted=True` means publish-accepted, not delivered (§2.8
honesty)" (`sb/kernel/events_bus.py:6-8,38-50`). Two consequences compound:

1. **The relay discards `emit`'s return value.** `emit` returns the delivered
   handler count (`events_bus.py:50`), but the relay `await`s it and marks the
   row `delivered` regardless (`relay.py:95,117`) — even when **zero** subscribers
   succeeded. There is no signal path from "the subscriber raised" back to
   "retry this row".
2. **The effectful egress subscriber swallows its own transient failures.** The
   Discord-facing consumers catch and log rather than raise — e.g. the passive
   feed stages "never break the event loop" (`message_feed.py:198-199,229-231`)
   and the shipped stage's documented behavior is to swallow Discord failures:
   "the shipped stage swallowed Discord failures (`except discord.HTTPException`)"
   (`message_feed.py:210`). (Discord's own transient family — `HTTPException`,
   `RateLimited`, `DiscordServerError` — is recognized as transient elsewhere, on
   the *interaction* path: `sb/kernel/interaction/errors.py:59`. The outbox egress
   has no equivalent hook.)

Net: the retry boundary (relay `try`) and the real failure point (Discord send
in a subscriber) sit on opposite sides of the bus's isolation seam. A transient
gateway blip or a **429** during a queued user-facing effect is caught by the
subscriber, logged, and dropped — while the outbox row is marked `delivered` and
the 12-attempt backoff/dead-letter machinery **never engages**. The one failure
mode the outbox spine was built to survive is the one it currently cannot see.

Two smaller sub-gaps ride along:

- **No jitter.** `backoff` is a deterministic `min(base · 2^(n-1), cap)`
  (`relay.py:39-43`). If many rows enter backoff in the same failure window (a
  gateway-wide blip), they all become claimable again at the same instant — a
  thundering-herd re-hit against a still-recovering Discord.
- **No dead-letter replay.** `DEAD` is terminal (`store.py:40`); the reaper only
  *prunes* it at 90d (`store.py:205-218`). There is no operator path to requeue a
  dead-lettered effect after the underlying cause clears — the 90d window is
  retention for forensics, not a replay affordance.
- **The dead-letter metric is currently dark.** `outbox_dead_letter_total` (and
  the sibling outbox families) are declared but not registered on the live
  registry until D4.1 lands — see `docs/design/D4-observability-surface.md` §P1.
  Alerting on dead-letter growth (Open Questions) depends on that wiring.

### P2 — DB pool fails-closed but has no reconnect-backoff, breaker, or boot retry

The DB seam is also better than a greenfield read assumes, and the credit is
specific. It already centralizes **fail-closed / refuse-with-notice**: every raw
asyncpg connection/pool error is converted to one typed `DBUnavailable`
(`sb/kernel/db/pool.py:69-78,90-103`), which subclasses `ConnectionError` on
purpose so the resolver classifies it transient / retryable / `DISCORD_FAILED`
through an existing row — "no domain ever fails-open with empty/stale rows"
(`pool.py:16-18,220-223`). It also revalidates a possibly-dead connection on
checkout: `checked_acquire()` pings `SELECT 1` if the connection has been idle
past 30s and, on failure, releases-and-reacquires **once** before raising
(`pool.py:161-192`). The transaction seam commits-or-rolls-back atomically and
surfaces connection failures as `DBUnavailable` after the rollback
(`pool.py:195-216`).

So "the pool assumes a live connection and crashes on a drop" is **not** the
actual state — the fail-closed posture exists. The real gap is that the refuse
path is **slow, unbounded, and boot-fragile**:

1. **No reconnect-with-backoff.** `checked_acquire` reacquires exactly once, with
   **no delay** between attempts (`pool.py:183-187`); a second failure raises
   immediately. During a managed-Postgres failover or maintenance window (seconds
   to ~a minute of unavailability), there is no bounded reconnect loop that waits
   and retries — the seam gives up after two back-to-back attempts.
2. **No circuit breaker.** During an outage, **every** request independently walks
   into the pool and pays the full `command_timeout` (`DB_COMMAND_TIMEOUT_S`
   default 30s, `pool.py:131`, `sb/spec/config.py:209`) before failing. There is
   no breaker to fast-fail once the DB is known-down, no half-open probe to test
   recovery, and no load-shedding — so a flap turns into a pile-up of 30s-blocked
   coroutines all hammering a recovering database. The refusal is *correct* but
   *expensive*: users wait the full timeout to be told "try later," and the
   recovering DB is stampeded.
3. **No boot retry.** `init()` calls `create_pool` once and lets a connection
   failure propagate as `DBUnavailable` (`pool.py:126-136`); there is no retry
   loop. A brief DB unavailability *at boot* (managed-DB maintenance overlapping a
   deploy) therefore crashes the process on startup rather than waiting the DB
   back.
4. **Half-apply risk is already contained — and that is the anchor to build on.**
   The idempotency ledger guards every double-fireable mutation inside one txn:
   `once()` + the effect + `record_outcome` share one connection and commit or
   roll back together (`sb/kernel/db/idempotency.py:10-20,114-151`). So a mid-flight
   drop does **not** half-apply — the txn rolls back whole (`pool.py:209-216`). This
   is precisely what makes a *fast* fail-closed safe: refusing **before** the txn
   opens leaves no partial state, and the same idempotency key lets the write
   replay cleanly once the breaker closes. The gap is that nothing today *uses*
   this property to refuse early — every caller still pays the full timeout.

Net: a Postgres flap does not crash the running process mid-effect (fail-closed +
atomic txn hold), but it *does* degrade badly — every request stalls for the full
command timeout, the recovering DB is stampeded, and a flap that overlaps boot is
fatal. The seam has the *posture* for graceful degradation but not the
*machinery* (backoff, breaker, boot retry) to make it fast and bounded.

## Proposed design

Two components, each respecting the layer rules in `.claude/CLAUDE.md` — all work
stays in `sb/kernel/*` (the outbox and db bands), with declared `ConfigSpec`
knobs in `sb/spec/config.py`; no `sb/domain/*` edit, no kernel→domain edge.
Ordered highest-user-facing-value first.

### R1 — Move the outbox retry boundary to the Discord ack

The machinery is already there; the design is to **feed it a real signal**.

- **Report delivery status back from egress.** Give the effectful outbox
  subscribers a way to signal transient failure back to the relay instead of
  swallowing it. Two shapes, owner's call (Open Questions):
  - *(a) Typed re-raise* — the egress subscriber for durable (`AT_LEAST_ONCE`)
    events re-raises Discord's transient family (`HTTPException` / `RateLimited` /
    `DiscordServerError`, the set already named at
    `sb/kernel/interaction/errors.py:59`) instead of swallowing it, and the relay
    switches from the fire-and-forget `bus.emit` to a **delivery call that
    propagates** that exception. The existing `except Exception` in the relay
    (`relay.py:103-115`) then drives the *already-built* `mark_retry_or_dead` path
    — no new retry code, the boundary just moves.
  - *(b) Delivery-result channel* — keep `emit`'s isolation for observability
    subscribers, but route durable effects through a dedicated
    `deliver(row) -> DeliveryOutcome` port whose `{ack, transient_fail,
    permanent_fail}` result the relay inspects (instead of discarding `emit`'s
    count, `relay.py:95,117`). `permanent_fail` (e.g. 403/404 — a deleted channel)
    dead-letters immediately without burning 12 attempts.
- **Honor the 429 `retry_after`.** When the transient failure is a 429 carrying a
  `retry_after`, pass it into the backoff so the row's `available_at` respects
  Discord's own cooldown rather than the generic exponential curve — a targeted
  extension of `backoff()` / `mark_retry_or_dead` (`relay.py:39-43`,
  `store.py:179-203`), not a rewrite.
- **Add jitter to backoff.** Change `backoff` to `min(base · 2^(n-1), cap)` **±
  full/decorrelated jitter** (`relay.py:39-43`) so rows that entered backoff
  together do not re-hit Discord in lockstep. Deterministic-seedable for the
  golden harness (Open Questions).
- **Dead-letter replay path.** Add an operator-driven requeue: flip a `DEAD` row
  back to `pending` with a reset `delivery_attempts` and a fresh `available_at`
  (a new `OutboxStore.replay(outbox_id)` sibling to `mark_retry_or_dead`,
  `store.py:179-203`), so a dead-lettered effect can be re-sent after the cause
  clears rather than only pruned at 90d. Surfaced as a bounded operator action,
  not an automatic loop (that would defeat the dead-letter's purpose).
- **Surface it in metrics.** The dead-letter counter exists
  (`outbox_dead_letter_total`, `sb/kernel/outbox/metrics.py:32-37`); add an
  `outbox_retry_total` (or reuse `delivery_attempts` as a gauge) so retries are
  visible before exhaustion, and depend on D4.1 registering the outbox families
  so any of this reaches `/metrics` (`docs/design/D4-observability-surface.md`
  §P1, §D4.1).
- **Seams changed:** `sb/kernel/outbox/relay.py` (delivery call + boundary),
  `sb/kernel/outbox/store.py` (`retry_after`-aware backoff, `replay()`),
  `sb/kernel/outbox/metrics.py` (retry metric), the egress subscriber(s) in
  `sb/adapters/discord/*` (report status instead of swallow — adapter band), and
  a jitter/attempt-bound `ConfigSpec` in `sb/spec/config.py`.

### R2 — DB reconnect-with-backoff + circuit breaker + fast fail-closed

Build the *machinery* under the seam's existing *posture* — the callers already
handle `DBUnavailable`, so this is invisible above the seam.

- **Reconnect-with-backoff in `checked_acquire`.** Replace the single no-delay
  reacquire (`pool.py:183-187`) with a bounded reconnect loop: a few attempts with
  short exponential backoff (+ jitter) before raising `DBUnavailable`, so a
  sub-minute failover is waited out rather than immediately refused. Bounds are
  declared `ConfigSpec`s, not magic numbers (like `DB_COMMAND_TIMEOUT_S`,
  `sb/spec/config.py:209`).
- **A circuit breaker in front of the pool.** Add a small breaker in the db band
  (a `sb/kernel/db/breaker.py` leaf, kernel-internal) that the CRUD primitives
  (`fetchone`/`fetchall`/`execute`, `pool.py:256-307`) and `checked_acquire`
  consult:
  - *Closed* — normal; consecutive `DBUnavailable`s increment a failure count.
  - *Open* — past a threshold, **fast-fail** every request with `DBUnavailable`
    immediately (no 30s timeout wait), shedding load off the recovering DB. This
    is the "refuse fast and cheap" the current slow-refuse lacks.
  - *Half-open* — after a cooldown, admit one probe (`SELECT 1`); success closes
    the breaker, failure re-opens it. Reuses the readiness probe pattern already
    proven at `checked_acquire`'s `SELECT 1` (`pool.py:177`).
  Because the breaker raises the **same** `DBUnavailable` the seam already emits
  (`pool.py:69-78`), every existing fail-closed caller and the readiness gate
  (`/ready` returns 503 `db_unavailable`, per `docs/design/D4-observability-surface.md`
  §P3) keep working unchanged — the breaker just makes the refusal *fast*.
- **Boot retry in `init()`.** Wrap `create_pool` (`pool.py:126-136`) in a bounded
  retry-with-backoff so a brief DB-unavailable window at boot waits the DB back
  instead of crashing the process. Bound and posture are owner-gated (fail after N
  attempts vs. wait indefinitely — Open Questions).
- **Anchor on the idempotency ledger for safe replay.** The breaker fast-fails
  **before** a txn opens, and the ledger's atomic `once()`+effect+`record_outcome`
  (`sb/kernel/db/idempotency.py:114-151`) guarantees a refused write left no
  partial state — so the same idempotency key replays the write cleanly once the
  breaker closes. The design's correctness rests on refusing at the seam boundary,
  never mid-txn (the txn seam already rolls back whole on a mid-flight drop,
  `pool.py:209-216`).
- **Seams changed:** `sb/kernel/db/pool.py` (reconnect loop, breaker consult,
  boot retry), new `sb/kernel/db/breaker.py` (breaker state machine), breaker/
  reconnect/boot `ConfigSpec`s in `sb/spec/config.py`. No caller or domain edit —
  the seam's contract (`DBUnavailable`) is unchanged.

## Affected surfaces

| Band | Files | Component |
|---|---|---|
| kernel / outbox | `sb/kernel/outbox/relay.py:36-146` (delivery call + boundary + jitter), `store.py:179-218` (`retry_after` backoff, `replay()`), `metrics.py:19-45` (retry metric) | R1 |
| adapter / discord | egress subscriber(s) in `sb/adapters/discord/*` — report delivery status instead of swallowing `HTTPException` (`message_feed.py:198-231`) | R1 |
| kernel / db | `sb/kernel/db/pool.py:118-192,256-307` (reconnect-backoff, breaker consult, boot retry), new `sb/kernel/db/breaker.py` (breaker state machine) | R2 |
| spec / config | `sb/spec/config.py:122-…` — new `ConfigSpec`s: outbox attempt bound + jitter; DB reconnect attempts/backoff, breaker threshold/cooldown, boot-retry bound | R1, R2 |
| observability (dependency) | outbox families reaching `/metrics` depends on `docs/design/D4-observability-surface.md` §D4.1; dead-letter-growth alert per D4 Open Q7 | R1 |

No `sb/domain/*` change in either component — the whole surface sits at
kernel + adapter + spec, consistent with the layer map. The DB work is
seam-internal (the `DBUnavailable` contract is unchanged), so it is invisible to
every caller.

## Rough size + suggested slicing

- **R1a — outbox delivery-reach (move the retry boundary to the Discord ack)** —
  **M**. The egress reports transient failure, the relay consumes a real delivery
  signal instead of discarding `emit`'s count, and the existing backoff/
  dead-letter path engages. Highest user-facing value (closes a *silent* dropped
  effect). Land first, standalone.
- **R1b — jitter + `retry_after` + dead-letter replay** — **S–M**. Backoff
  jitter and 429-`retry_after` honoring are small edits to `backoff()` /
  `mark_retry_or_dead`; the `replay()` operator path is S. Land after R1a (it
  needs the boundary in place to matter).
- **R2a — DB reconnect-with-backoff + boot retry** — **S–M**. A bounded loop in
  `checked_acquire` and `init`, plus `ConfigSpec`s. Self-contained in `pool.py`;
  no new module.
- **R2b — circuit breaker** — **M**. The breaker state machine (new `breaker.py`),
  the CRUD/`checked_acquire` consults, half-open probe, and tests. Larger, wants
  its own PR; land after R2a (shares the reconnect config).

Suggested landing order: **R1a → R1b → R2a → R2b**. R1a first because a silently
dropped user-facing effect is the sharpest production risk; the DB seam already
fails-closed, so R2 is a *quality-of-degradation* upgrade, not a
crash-prevention one.

## Open questions for the owner

1. **Outbox retry/attempt bounds.** `MAX_ATTEMPTS = 12` and `backoff` base 5s /
   cap 300s (`relay.py:36,39-43`) were sized against *bus-level* failures. Once
   the boundary moves to the Discord ack (a slower, rate-limited egress), are 12
   attempts over a ~300s-capped curve still right, or should durable effects get a
   longer tail before dead-lettering?
2. **Egress signal shape.** R1 option (a) typed re-raise vs. (b) a
   `deliver()->DeliveryOutcome` port — which fits the effectful-subscriber
   contract better? (b) cleanly distinguishes permanent (403/404 — deleted
   channel) from transient (429/5xx) so permanent failures dead-letter without
   burning 12 attempts; (a) is a smaller diff.
3. **Dead-letter retention + replay policy.** Keep the 90d `dead` retention
   (`store.py:96`)? Should `replay()` be operator-only (a bounded manual requeue),
   or is a capped auto-replay-after-cooldown acceptable for a subset of effects?
4. **Breaker thresholds.** Consecutive-failure count to *open*, cooldown before
   *half-open*, and probe cadence — conservative defaults (e.g. open after 5
   fails, 10s cooldown) with `ConfigSpec` overrides, or different numbers? Should
   the breaker be per-pool (global) or finer-grained?
5. **Refuse vs. queue-and-warn UX.** When the breaker is open, is "politely refuse
   the write" (the current fail-closed posture, `pool.py:16-18`) the right user
   experience, or should some writes be *queued* (durably) and a warning shown,
   with replay when the DB returns? Refuse is simpler and already the posture;
   queue-and-warn is a larger surface and only safe for writes that are
   idempotency-anchored.
6. **Boot-retry posture.** On a DB-unavailable boot, retry-with-backoff for a
   bounded window then crash (fail-fast for the orchestrator to restart), or wait
   indefinitely for the DB? The former plays nicer with a supervisor; the latter
   survives a long maintenance window without a restart storm.
7. **Alerting on dead-letter growth.** Once `outbox_dead_letter_total` is
   registered (depends on `docs/design/D4-observability-surface.md` §D4.1), should
   a rising dead-letter count fire through the operator-alert sink (D4 Open Q7) or
   the metrics backend's alerting? Same question for the breaker flipping *open*
   (a first-class "DB degraded" alert).
8. **Golden determinism for jitter.** Backoff jitter and the breaker's timing make
   retry scheduling non-deterministic. Seed the jitter and freeze the breaker clock
   in tests (the golden harness already pins seeded sequences), or keep jitter out
   of any golden-observed path?
