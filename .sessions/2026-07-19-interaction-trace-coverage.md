# Session — interaction dispatch-trace seam: close the zero-coverage gap

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`): first commit was this card alone (born-red, held the
> substrate-gate); the test landed in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · high · test writing

## Order

Self-initiated engineering: land ONE genuinely-valuable, contained, reversible
improvement. HUNT (read-only first) found that `sb/kernel/interaction/trace.py`
— the `command.dispatched` dispatch-trace seam (spec 02 §3.5, the RC-2/RC-5
owner-override transparency signal carrier) — had **zero direct test coverage**.
Every other kernel band probed was already densely covered (see the dry-line
survey below); this seam was the one live gap.

## Scope

Test-only. Added `tests/unit/interaction/test_dispatch_trace.py` (7 tests). Zero
`sb/` source edited; no dependency change (pip-audit n/a).

## What the tests pin

Three real contracts of `emit_dispatch_trace` / `COMMAND_DISPATCHED_SPEC`:

1. **payload/schema drift guard** — the emitted payload's keys are EXACTLY the
   `COMMAND_DISPATCHED_SPEC.payload_schema` field names (bidirectional set
   equality), and every `required` field is present. The schema evolves
   additive-only, and the payload dict is hand-built in `emit_dispatch_trace`;
   drift between them is a **silent** observability bug (best-effort trace,
   never fails loudly). This assertion catches an added-but-unpopulated schema
   field AND a payload key with no schema home.
2. **never-breaks-dispatch robustness** — `emit_dispatch_trace` is
   fire-and-forget: a bus whose `emit` raises is swallowed (generic `except`),
   and the no-running-loop path (`get_running_loop()` → `RuntimeError`) is
   swallowed while the always-on log line still stands. A regression here would
   break *every* command dispatch, not just the trace. The no-bus path is also
   covered (logs, returns, no emit attempt).
3. **correct derivation** — enums render to `.value` (surface / lane / reason),
   actor_id / guild_id / orchestration_id thread from the request (incl. the
   `provenance is None` → `orchestration_id=None` branch), and the RC-2/RC-5
   `override_applied` / `base_allowed` signal rides verbatim. The spec's own
   `observability_only=True` + reserved `kernel` owner_subsystem (the §2.8
   owner-rule carve-out) are asserted on the immutable spec object — NOT on
   `KNOWN_EVENTS` membership, which the shared `clear_event_registry()` test
   seam resets (an order-fragile assertion, corrected mid-session; see review).

## Verification

- `python3 -m pytest -q tests/unit/interaction/test_dispatch_trace.py` →
  **7 passed** in 0.07s.
- Full `python3 -m pytest -q --ignore=examples` (Postgres + discord present) →
  **3576 passed, 37 skipped, 1 warning**. The 1 warning is the pre-existing
  `discord/player.py` `audioop` DeprecationWarning (stdlib, unrelated). No
  Postgres provisioning needed — the trace seam has no DB dependency.
- Guards clean (**0 fires**, no `.substrate/guard-fires.jsonl` delta):
  `check_namespace`, `check_symbol_shadowing`, `check_config_usage`,
  `check_no_skip` — each `clean`, exit 0.
- `python3 bootstrap.py check` → exit 0; this card validates `complete` at HEAD
  (born-red hold cleared by this flip).
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## Dry-line survey (why this was the one real gap)

Read-only HUNT confirmed dense, thoughtful coverage on every kernel path
examined, so the honest field of candidates was small: `config` (parse_bool /
parse_dsn / coerce / intents / degradations all covered), `observability`
(redaction, alerts `prepare_alert`, findings, metrics), `authority`
(`build_transparency_audit`, owner predicate, bootstrap oracle), `scheduler`
(`apply_misfire` / `next_slot`, 7 tests), `outbox` (relay backoff / dead-letter
/ reaper, enqueue key-guard / to_jsonable / two-call protocol), `credentials`
(`rotation_due` / `horizon_epoch`), `versioning` (`resolve_versioned_load`),
`db` (`IdempotencyKey` render/parse roundtrip, once/record/read). The
interaction dispatch-trace seam was the standout zero-coverage kernel module
whose contract (never break dispatch + a silent payload-drift hazard) had real
failure consequences — hence the pick.

## 💡 Session idea

The payload/schema drift hazard here is a **recurring shape**: any hand-built
payload dict emitted against a declared `EventSpec.payload_schema` can silently
drift (best-effort events never fail-loud on a wrong key). This trace seam had
no guard until now; other best-effort emitters may have the same latent gap. A
cheap durable guard: a `tools/` lint (or one parametrized meta-test) that, for
each `observability_only` `EventSpec`, locates its single `bus.emit(NAME, ...)`
call site and asserts the literal payload-dict keys equal the schema field
names — turning the per-seam test written here into a corpus-wide invariant.
Guard recipe: anchor on `register_event_specs([...observability_only=True...])`
declarations; the emit call sites are `bus.emit(EVT_*, **payload)` with a
locally-built `payload` dict; the test target is a new
`tests/unit/observability/test_best_effort_payload_parity.py`.

## ⟲ Previous-session review

Predecessor convention carried from the night's test-writing thread (e.g.
`.sessions/2026-07-18-d5-1-e2e-modal.md`, `complete`, PR #573 — same
`opus-4.8 · high · test writing` class): born-red-card-then-flip, a verification
section that re-runs the exact commands and records tails/counts, and a scope
that adds ONE self-contained test file touching zero `sb/` source. One concrete
carry heeded: that thread's discipline of asserting against **real, immutable**
contract objects rather than mutable shared runtime state paid off here —
my first draft asserted `KNOWN_EVENTS[EVT_COMMAND_DISPATCHED]` membership, which
passed in isolation but FAILED under the full suite because another test's
`clear_event_registry()` seam had wiped the registry (module-level registration
does not re-run on cached re-import). Corrected to assert the frozen
`COMMAND_DISPATCHED_SPEC` attributes directly — order-independent and a truer
statement of the contract. The lesson (test the immutable spec, not the shared
registry) is the same "don't couple to resettable global state" caution the
predecessor's rebase-onto-`guard-fires.jsonl` note was making from the other
direction.
