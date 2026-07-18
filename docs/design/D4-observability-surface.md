# D4 — Observability surface (metrics / readiness / structured logs)

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the D1–D6 lanes into fuller
> design docs (`docs/status/completeness-table-2026-07-18.md`). This is a PLAN,
> not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line`
> at HEAD `88f3c38` unless noted.

## TL;DR

superbot-next already ships a rich observability **grammar** — a 46-family
Prometheus metric spec, a DB-aware readiness state table, a secret-redaction
scrubber, an operator-alert sink spec, and an in-memory findings ring — but the
grammar is **declared ahead of where it is wired**. The production-readiness gap
is not "build observability from scrat"; it is **arm and close the loop** on what
exists: register the outbox metric families that are silently dark, thread a
correlation ID from adapter to effect into a structured log stream, extend the
already-good `/ready` gate to cover outbox backpressure, and put redaction on the
primary log stream (not just the alert/finding egress). Each is a small, landable
slice.

## Problem

Four concrete production-readiness gaps, each grounded in the current code.

### P1 — Declared metrics are partially dark (outbox families never registered)

The metric grammar is real and rich: `sb/spec/observability.py` declares 46
metric families (`METRICS`, ported verbatim from the shipped bot), each with a
bounded-cardinality `LabelSpec` (`sb/spec/observability.py:24-48`) so
`tools/check_metric_cardinality.py` can bound series count. The outbox subsystem
declares 4 more families in its own tuple —
`outbox_pending_age_seconds` (gauge), `outbox_delivered_total`,
`outbox_dead_letter_total`, `outbox_claims_total`
(`sb/kernel/outbox/metrics.py:19-45`) — and that module's own docstring names
`outbox_pending_age_seconds` growing while `outbox_delivered_total` stays flat as
"the relay-health alert shape" (`sb/kernel/outbox/metrics.py:8-11`).

But the composition root instantiates only the **default** tuple:

- `build_registry()` defaults to `specs=METRICS` (`sb/kernel/observability/metrics.py:79`).
- The boot call passes no argument — `build_registry()` at `sb/app/main.py:269` —
  so `OUTBOX_METRICS` is never added to the registry.
- Only `tools/check_metric_cardinality.py:23` unions the two tuples
  (`ALL_METRICS = METRICS + OUTBOX_METRICS`) for the CI cardinality check — the
  live registry never sees them.

The consequence is silent. The relay bumps its counters through a guarded helper
that swallows the resulting lookup miss: `_inc()` calls
`registry.counter(metric_name).inc(n)` inside a bare `except Exception: pass`
(`sb/kernel/outbox/relay.py:50-59`), and `MetricRegistry._get` raises
`KeyError` for a family that was never registered
(`sb/kernel/observability/metrics.py:60-64`). So `outbox_delivered_total`,
`outbox_dead_letter_total`, and `outbox_claims_total` are emitted into a
try/except that discards them, and `outbox_pending_age_seconds` — the one gauge
whose whole reason to exist is the backpressure alert — has **no emitter at all**
anywhere in the tree (grep for it finds only the spec and the docstring). The
outbox is the durability spine (spec 08); its health is currently unobservable on
`/metrics`.

Secondary: when `prometheus_client` is not importable, every handle is the silent
`_NoOp` and `render()` returns an **empty body**
(`sb/kernel/observability/metrics.py:28-29,88-89,122-123`). Whether `/metrics`
carries anything at all in the production image therefore depends on
`prometheus_client` being in the hash-pinned runtime lock — this needs an explicit
end-to-end confirmation, not an assumption (see Open Questions).

### P2 — No documented end-to-end scrape path

`/metrics` is mounted and serves the full Prometheus exposition with the correct
content type (`sb/adapters/http/health.py:174-179,185`), and it is deliberately
independent of lifecycle phase so a draining replica still exposes metrics
(`sb/adapters/http/health.py:20-22`). What is missing is the **other half of the
loop**: there is no scrape configuration, no `ServiceMonitor`/`PodMonitor`, no
documented scrape target + interval, and no statement of where the endpoint lives
relative to the deploy (Railway private network vs public). The endpoint exists;
nothing is declared to consume it, so in production the metrics are exposed but
un-scraped. (The health server binds `cfg.HEALTH_HOST` default `::` /
`cfg.HEALTH_PORT` default 8080 — `sb/adapters/http/health.py:148-149,190`.)

### P3 — Readiness is DB+gateway-aware but blind to outbox backpressure

The readiness surface is genuinely good and should be credited: `readiness_decision`
is a PURE state table (`sb/adapters/http/health.py:67-96`) that returns 503 for
`gateway_not_ready`, `still_starting`, `draining`, `failed_startup`, and 503
`db_unavailable` when RUNNING but the DB probe fails — the DB probe is a bounded
`SELECT 1` via `checked_acquire()`, `wait_for` 2s, cached ~1s
(`sb/adapters/http/health.py:99-117`). The route is `/ready` (not the k8s-idiomatic
`/readyz`) and it is wired at boot with the live gateway probe
(`sb/app/main.py:276-284`).

The gap: readiness does not consider **outbox depth**. A replica whose relay is
wedged (claims taken, nothing delivered, `outbox_pending_age_seconds` climbing —
exactly the P1 alert shape) still answers `/ready` = 200 and keeps receiving
traffic, because the state table only knows gateway + phase + DB. For a bot whose
effects are delivered through the outbox spine, a backed-up outbox is a real
"not ready to be trusted with more work" signal that the current gate cannot
express. There is also no `/readyz` alias, so an orchestrator using the k8s
convention finds nothing.

### P4 — Logs are unstructured, un-correlated, and un-redacted at the stream

Logging is configured once at the entrypoint with a plain-text formatter:
`logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")`
(`sb/app/main.py:835-837`). Three gaps follow:

1. **Not structured.** Plain text, not JSON/logfmt — a log drain (Railway ships
   stdout to its drain) cannot index fields, only full-text search.
2. **No correlation thread.** A correlation ID already exists and is carried
   through the *data* spine end-to-end: `WorkflowContext.correlation_id`
   (`sb/spec/draft.py:127`), the `audit_log.correlation_id` and
   `event_outbox.correlation_id` columns (`migrations/0003_audit_spine.sql:26`,
   `migrations/0002_event_outbox.sql:21`), the findings seam's `correlation_id`
   parameter (`sb/kernel/observability/findings.py:49-56`), and the relay even
   forwards `_outbox_correlation_id` on emit
   (`sb/kernel/outbox/relay.py:99-101`). But it is **never threaded into the log
   records** — there is no `logging.Filter`/adapter that stamps `correlation_id`
   onto a `LogRecord`, so a log line for an interaction cannot be joined to its
   audit row or its outbox delivery. The correlation exists everywhere except the
   place an operator reads first.
3. **Redaction covers egress sinks but not the log stream.** `redact_text` /
   `redact_payload` are real and conservative
   (`sb/kernel/observability/redaction.py:69-116`) and are applied at the
   operator-alert choke point (`prepare_alert`, `sb/kernel/observability/alerts.py:73-96`)
   and when recording findings (`sb/kernel/observability/findings.py:63-64`). But a
   raw `logger.info(...)` / `logger.exception(...)` — and exception strings embed
   DSNs, which is exactly why findings scrub them — flows to stdout **unredacted**.
   The scrubber exists; it is just not on the highest-volume path.

## Proposed design

Four slices, each respecting the layer rules in `.claude/CLAUDE.md` (kernel work
stays in `sb/kernel/*`, adapter surfaces in `sb/adapters/http`, composition in
`sb/app/*`; no kernel→domain edge). Ordered cheapest-highest-signal first.

### D4.1 — Close the declared-vs-wired metric gap (arm the outbox families)

- **Register the outbox families.** Pass the union at the composition root:
  `build_registry(METRICS + OUTBOX_METRICS)` at `sb/app/main.py:269` (import
  `OUTBOX_METRICS` from `sb.kernel.outbox.metrics`). This is the same union
  `tools/check_metric_cardinality.py:23` already validates, so the cardinality
  gate stays honest. Alternatively (cleaner, avoids a future third tuple drifting):
  fold the union into a single `ALL_METRICS` seam that both the root and the
  checker import — a small kernel/spec-level refactor.
- **Emit `outbox_pending_age_seconds`.** Add the gauge set on each relay/reaper
  tick from a bounded `MIN(available_at)` age query the store already has the
  shape for (`sb/kernel/outbox/store.py:104` selects PENDING rows by
  `available_at`). The emit stays in `sb/kernel/outbox/relay.py` behind the
  existing guarded `_inc`/a `_set` twin — observability never blocks delivery.
- **Confirm the exposition end to end** (P1 secondary): assert `prometheus_client`
  is in the hash-pinned runtime lock and add a headless smoke that boots,
  `build_registry()`s, hits `render()`, and asserts a non-empty body containing an
  outbox family — closing the "`_NoOp` silently serves empty" trapdoor.
- **Seams changed:** `sb/app/main.py` (composition), `sb/kernel/outbox/relay.py`
  (+ possibly `store.py` for the age query), optionally a small `ALL_METRICS`
  fold in `sb/kernel/observability/metrics.py` or `sb/spec/observability.py`.

### D4.2 — Document + wire the Prometheus scrape path

- Declare the scrape target: a `ServiceMonitor`/`PodMonitor` (or the Railway/
  Grafana-Agent equivalent — see Open Questions) pointed at
  `HEALTH_HOST:HEALTH_PORT/metrics`, with an interval and a cardinality budget
  reference (the per-family budgets already computed in
  `sb/spec/observability.py:70-83`). Decide auth posture (P2 / Open Questions).
- This slice is mostly **ops config + docs**, not `sb/` code: an operations
  runbook under `docs/operations/` plus whatever manifest the deploy platform
  needs. No layer-rule surface.

### D4.3 — `/readyz` that also gates on outbox depth

- Extend the PURE `readiness_decision` (`sb/adapters/http/health.py:67-96`) with an
  outbox-depth input: add an `outbox_pending_age_s: float` (or `outbox_backpressure:
  bool`) parameter and a row that returns 503 `outbox_backpressure` when RUNNING +
  DB up but the oldest PENDING age exceeds a configured threshold. Keeping it a
  pure parameter preserves the fully-tested no-aiohttp core (the module's stated
  design, `sb/adapters/http/health.py:23-27`).
- Feed it from the same bounded, cached probe pattern as `db_ready()`
  (`sb/adapters/http/health.py:99-117`) — a `checked_acquire()` `MIN(available_at)`
  read, cached ~1s, timeout-bounded, failing "not backed up" on error so the probe
  never wedges readiness.
- Add a `/readyz` route alias next to `/ready`
  (`sb/adapters/http/health.py:182-185`) for the k8s convention; keep `/ready` for
  the existing orchestrator consumer.
- Threshold is a declared `ConfigSpec` (like `HEALTH_HOST`/`HEALTH_PORT`), no raw
  env read (`check_config_usage` applies) — value is an Open Question.
- **Seams changed:** `sb/adapters/http/health.py` only (adapter band); a new
  `ConfigSpec` in `sb/spec/config.py`.

### D4.4 — Structured logs + correlation thread + stream redaction

- **Structured formatter.** Replace the plain `basicConfig` format
  (`sb/app/main.py:835-837`) with a JSON/logfmt formatter living in the kernel
  observability band (a new `sb/kernel/observability/logging.py` leaf — importable
  by every layer, like the rest of the K0 observability leaf). Fields: timestamp,
  level, logger, message, and `correlation_id` when present.
- **Correlation thread.** Introduce a `contextvars`-based correlation context in
  the kernel observability band and a `logging.Filter` that stamps the current
  `correlation_id` onto each `LogRecord`. Set the context at the two entry seams
  where a correlation id is born or received — the interaction/adapter ingress
  (`sb/adapters/*`) and the workflow/effect boundary
  (`WorkflowContext.correlation_id`, `sb/spec/draft.py:127`) — so a log line from
  adapter→effect carries the same id already written to `audit_log` /
  `event_outbox`. No kernel→domain edge: the contextvar + filter live in kernel;
  adapters set it; domain code inherits it ambiently.
- **Stream redaction.** Route the formatter's rendered message through
  `redact_text` (`sb/kernel/observability/redaction.py:69`) — the same scrubber the
  alert and finding sinks use — so a stray DSN in an exception string never reaches
  the log drain. This makes redaction a property of the stream, not of each call
  site remembering to scrub.
- **Seams changed:** new `sb/kernel/observability/logging.py`; `sb/app/main.py`
  (install the formatter/filter at `cli()`); light touches at the adapter ingress
  seams to set the correlation context. No `sb/domain/*` edits.

## Affected surfaces

| Band | Files | Slice |
|---|---|---|
| composition root | `sb/app/main.py:269` (registry union), `:835-837` (log config) | D4.1, D4.4 |
| kernel / observability | `sb/kernel/observability/metrics.py` (optional `ALL_METRICS` fold), new `sb/kernel/observability/logging.py` (formatter + correlation filter) | D4.1, D4.4 |
| kernel / outbox | `sb/kernel/outbox/relay.py` (emit `outbox_pending_age_seconds`), `sb/kernel/outbox/store.py` (age query) | D4.1 |
| adapter / http | `sb/adapters/http/health.py:67-96` (readiness input), `:182-185` (`/readyz` alias) | D4.3 |
| spec | `sb/spec/config.py` (backpressure threshold ConfigSpec), optionally `sb/spec/observability.py` (`ALL_METRICS`) | D4.1, D4.3 |
| adapters (ingress) | `sb/adapters/*` set correlation context at ingress | D4.4 |
| ops / docs | `docs/operations/*` scrape runbook + deploy manifest | D4.2 |

No `sb/domain/*` change in any slice — the whole surface sits at
kernel + adapter + composition, consistent with the layer map.

## Rough size + suggested PR slicing

- **D4.1 — arm outbox metrics** — **S**. One-line registry union + one gauge emit +
  one age query + a render smoke. Highest signal for the cost (turns the durability
  spine observable). Land first, standalone.
- **D4.2 — scrape path** — **S–M**, but mostly ops config/docs and partly
  owner-gated (depends on the backend + deploy decisions below). Can land as a docs
  runbook immediately and a manifest once the backend is chosen.
- **D4.3 — /readyz + outbox-depth readiness** — **M**. Pure-core extension + a
  cached probe + a route alias + a ConfigSpec + tests. Self-contained in the http
  adapter. Land after D4.1 (shares the age query).
- **D4.4 — structured logs + correlation + redaction** — **M–L**. The formatter is
  S; the correlation `contextvars` thread across adapter→effect ingress is the
  larger, more invasive piece and wants its own PR (touches every adapter ingress
  seam). Suggest splitting: **D4.4a** JSON formatter + stream redaction (S–M,
  composition + one kernel leaf), then **D4.4b** the correlation context + filter +
  ingress wiring (M).

Suggested landing order: **D4.1 → D4.3 → D4.4a → D4.4b → D4.2** (D4.2's manifest
waits on the owner's backend/auth calls; its runbook can land anytime).

## Open questions for the owner

1. **Metrics backend.** Prometheus + Grafana (self-hosted / Grafana Cloud), or the
   Railway-native metrics/Grafana-Agent path? This decides D4.2's manifest shape
   and whether the `text/plain; version=0.0.4` exposition
   (`sb/kernel/observability/metrics.py:16`) is scraped directly or via an agent.
2. **Where is `/metrics` exposed, and with what auth?** Today the health server
   binds `::`/8080 for Railway private networking
   (`sb/adapters/http/health.py:148-149`). Keep `/metrics` private-network-only
   (no auth, scraped from inside the deploy), or expose it publicly behind a bearer
   token / basic auth? Auth on the endpoint is currently none.
3. **Readiness thresholds.** What `outbox_pending_age_seconds` value should flip
   `/readyz` to 503 (D4.3)? A conservative default (e.g. 60s) with a `ConfigSpec`
   override, or a different number? Should backpressure be a *hard* 503 (stop
   routing) or a soft *degraded* signal that still serves 200?
4. **Cardinality budget.** The per-family budgets are computed
   (`sb/spec/observability.py:70-83`) but there is no fleet-wide series ceiling.
   Set an explicit total-series budget for the scrape (backend cost control), and
   should `tools/check_metric_cardinality.py` enforce it as a hard gate?
5. **`prometheus_client` in the runtime image.** Confirm it is in the hash-pinned
   runtime lock (S13) — if absent, `/metrics` serves an empty body by design
   (`sb/kernel/observability/metrics.py:122-123`) and the whole surface is dark.
   Should the boot smoke assert its presence (fail-closed) rather than degrade
   silently to `_NoOp`?
6. **Log format + drain.** JSON or logfmt for the structured stream (D4.4)? Which
   fields are mandatory beyond `correlation_id`? Is the Railway log drain the target,
   or a dedicated log backend (Loki, etc.) that changes the field contract?
7. **Alert delivery.** The operator-alert sink spec exists with a `LoggingAlertSink`
   default and a Discord `WebhookReporter` twin gated on `DISCORD_WEBHOOK_URL`
   (`sb/kernel/observability/alerts.py:14-19,99-108`). Should the relay-health
   alert shape (P1) fire through this sink, or through the metrics backend's
   alerting (Alertmanager/Grafana)? This decides whether P1's "alert" is a metric
   rule or an `OperatorAlert`.
