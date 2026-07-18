# 2026-07-18 — arm the dark outbox metric families (D4 observability, P1)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · small · kernel slice

## Scope

Build the D4 observability design's P1 item: arm the four outbox metric
families that are declared in code but never registered on the live registry
(so their emits land in a swallowing try/except), and add the missing emitter
for the one gauge that has no emitter anywhere in the tree.

Two concrete gaps closed:

1. The composition root built the registry with the default `METRICS` tuple
   only, so `OUTBOX_METRICS` (`outbox_pending_age_seconds`,
   `outbox_delivered_total`, `outbox_dead_letter_total`, `outbox_claims_total`)
   was never instantiated — the relay's guarded counter bumps hit a `KeyError`
   the guard discards. The outbox is the durability spine; its health was
   unobservable on `/metrics`.
2. `outbox_pending_age_seconds` (the backpressure gauge) had no emitter at all.

Pure wiring of declared families: no new metric semantics, no backend/auth/
threshold decisions (those remain owner questions in the D4 doc's Open
Questions and land with the later slices).

## What landed

- **Register the union at the composition root** — `build_registry(METRICS +
  OUTBOX_METRICS)` (`sb/app/main.py`), the same union
  `tools/check_metric_cardinality` already validates (now 51 families).
- **Emit the gauge** — a guarded `_set` twin of the relay's `_inc`
  (`sb/kernel/outbox/relay.py`), fed by a bounded
  `OutboxStore.pending_age_seconds` read (`MIN(available_at)` over pending
  rows, clamped at 0), emitted on each relay tick. Both the store read and the
  emit sit behind a guard — observability never blocks delivery.
- **Tests** — a prometheus-independent spy registry proves all four families
  emit at the seam (claims/delivered/dead-letter counters + the age gauge); a
  prometheus-gated `/metrics` render smoke proves the end-to-end exposition;
  the age query's none/clamp semantics are covered directly.

Flag (decide-and-flag): the gauge reads `MIN(available_at)` per the D4 doc's
explicit P1 hint (a backing-off row's future `available_at` clamps to 0 = not
yet due, so the gauge measures *due-but-undelivered* backpressure) rather than
`created_at`; the declared spec docstring ("oldest PENDING row, 0 when none")
holds under both readings.

P1 secondary confirmed: `prometheus-client==0.25.0` is in the hash-pinned
`requirements.lock` (fail-closed vs degrade-silently is an owner question — not
changed here).

## Verification

- `python3 -m pytest -q --ignore=examples` → **3490 passed, 29 skipped**.
- Layer + metric guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`, `check_metric_cardinality` (51
  families), `check_runtime_smoke`, `manifest_compile` — no new guard fires.

## 💡 Session idea

Fold the metric union into one canonical `ALL_METRICS` seam that both the
composition root and `check_metric_cardinality` import, so a future third
metric tuple can't drift live-vs-checked (the doc's cleaner alternative). And
`OutboxStore.pending_age_seconds` is exactly the bounded probe D4.3's
`/readyz` outbox-depth gate needs — reuse it there rather than re-deriving.

## ⟲ Previous-session review

The recent cards (verify-C2/C3-backlog, tournament-open TOCTOU, test-depth
sweeps) were born-red, gate-only, and landed clean; none touched the
observability surface, so no D4 sibling contention to reconcile. The
verify-C2/C3 card's convention — cite the standing class-killer test as the
durable proof — is echoed here by the `test_default_registry_leaves_outbox_
families_dark` regression guard that keeps the dark-family class unwritable.
