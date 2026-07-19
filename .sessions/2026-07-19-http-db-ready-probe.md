# Session — K5 health: cover the db_ready() probe-cache/timeout/failure surface

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 7) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Fresh-territory hunt on
`sb/adapters/http` (not probed this session) found `db_ready()` in
`sb/adapters/http/health.py` — the bounded DB readiness probe behind `/ready` —
has NO test. `readiness_decision` (the pure §3.8 state table) is fully covered
by `tests/unit/kernel/test_health_readiness.py`, but the async probe wrapper
around it — the ~1s cache whose stated purpose is "probe storms don't hammer the
pool", the bounded `asyncio.wait_for` timeout, and the broad `except` that folds
down/timeout/uninitialised into "not up" — is unexercised. The
`reset_probe_cache_for_tests()` helper the module ships for exactly this has zero
consumers.

## Scope

Test-only. Added `tests/unit/adapters/test_health_db_ready.py`. Zero `sb/`
source edited; no dependency change (pip-audit n/a). No claimed domain touched —
this is a kernel-adjacent K5 adapter.

## What the tests pin

Behavior of `db_ready()`, each assertion verified against a live run of the real
function before being committed (scratch harness reproduced every result):

1. **Success + cache hit.** A probe that acquires a connection and runs
   `SELECT 1` cleanly returns `True`; a second call inside the cache window
   returns `True` **without re-probing** (the patched `checked_acquire` is
   invoked exactly once across the two calls). This is the anti-storm contract.
2. **Cache expiry re-probes.** With the cache window set to `0.0`, two calls
   invoke the probe **twice** — the `(now - cached_at) < _PROBE_CACHE_S` window
   check is load-bearing, not decorative.
3. **DB down → False, and the failure is cached.** A `checked_acquire` that
   raises `DBUnavailable` yields `False`; a second call inside the window stays
   `False` and does **not** re-probe (the negative result is cached the same way
   the positive one is — a storm of failing probes is also bounded).
4. **Uninitialised pool reads "not up".** With no pool initialised, `get()`
   raises `RuntimeError` inside the context entry; the broad `except` folds it to
   `False`. Real path, no mock — this is the "uninitialised" leg of the docstring
   contract.
5. **Bounded probe → timeout reads "not up".** With `_PROBE_TIMEOUT_S` set tiny
   and a probe that sleeps past it, `asyncio.wait_for` raises `TimeoutError`,
   caught → `False`, and the call returns at the bound (not the sleep). Pins that
   a wedged pool cannot hang `/ready`.

## Verification

- `python3 -m pytest -q tests/unit/adapters/test_health_db_ready.py` → (fill).
- Full `python3 -m pytest -q --ignore=examples` → (fill: tail + count).
- Guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta: (fill).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

(fill at close-out)

## ⟲ Review

### previous-session review

(fill at close-out)
