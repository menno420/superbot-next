# Session — interaction dispatch-trace seam: close the zero-coverage gap

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · test writing

## Order

Self-initiated engineering: land ONE genuinely-valuable, contained, reversible
improvement. HUNT found that `sb/kernel/interaction/trace.py` — the
`command.dispatched` dispatch-trace seam (spec 02 §3.5, the RC-2/RC-5
owner-override transparency signal carrier) — has **zero direct test coverage**
(grep of `tests/` for `interaction.trace` / `emit_dispatch_trace` /
`install_trace_bus` returns nothing). Every other kernel band probed (config,
observability redaction/alerts/findings, authority transparency, scheduler
misfire, outbox relay/enqueue, credentials cadence, versioning resolve, db
idempotency) is densely covered; this seam is the one live gap.

## Scope

Add `tests/unit/interaction/test_dispatch_trace.py` locking three real contracts
of `emit_dispatch_trace` / the registered `COMMAND_DISPATCHED_SPEC`:

1. **payload/schema drift guard** — the hand-built payload dict's keys EXACTLY
   match `COMMAND_DISPATCHED_SPEC.payload_schema` field names (the schema
   evolves additive-only; a hand-built payload that drifts from it is a silent
   observability bug), and every `required` schema field is present.
2. **never-breaks-dispatch robustness** — `emit_dispatch_trace` is fire-and-forget
   observability: a raising bus, and a no-running-loop `RuntimeError`, are both
   swallowed and never propagate out (a regression here would break every command
   dispatch).
3. **correct derivation + registration** — enums rendered to `.value`
   (surface/lane/reason), actor/guild/orchestration threaded from the request,
   and the EventSpec registered `observability_only=True` under the reserved
   `kernel` owner_subsystem.

Test-only: zero `sb/` source edited; no deps touched.

## Verification

Pending — flip to `complete` records the pytest tail + guard results.
