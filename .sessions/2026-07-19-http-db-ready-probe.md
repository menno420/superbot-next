# Session — K5 health: cover the db_ready() probe-cache/timeout/failure surface

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`): the first commit was this card alone (born-red, held
> the substrate-gate); the test landed in the second commit; this flip is the
> last.

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

- `python3 -m pytest -q tests/unit/adapters/test_health_db_ready.py` →
  **5 passed** in 0.26s.
- Full `python3 -m pytest -q --ignore=examples` (Postgres up + discord present)
  → **3679 passed, 2 skipped, 1 warning** in 108s. Baseline was 3674 passed (the
  #595 close card); the **+5 delta is exactly this file** — no other test moved.
  The 2 skips are pre-existing/unrelated; the 1 warning is the pre-existing
  `discord/player.py` `audioop` DeprecationWarning (stdlib, unrelated).
- Guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

`db_ready()`'s ~1s cache is a single module-global `_probe_cache` tuple with no
lock. Under the real `/ready` server, aiohttp handlers run on one event loop, so
concurrent `_ready` requests that arrive on a cold cache each `await` their own
`checked_acquire()` before either writes the cache — the "one physical probe
serves both readers" invariant this session pins holds only for *sequential*
awaits (as tested), not for a burst that races past the cache check together.
That is almost certainly fine (the probe is cheap and bounded, and a small burst
of duplicate `SELECT 1`s on a cold cache is harmless), so this is a note, not a
bug — but if a future change makes the probe expensive, an in-flight
single-flight (store an `asyncio.Future` the first prober creates and later
readers `await`) would restore the strict anti-storm guarantee. Guard recipe:
anchor on `_probe_cache` + `db_ready` in `sb/adapters/http/health.py`; a
behavioral pin would launch N concurrent `db_ready()` coroutines on a cold cache
and assert `checked_acquire` was invoked exactly once — that test would fail
TODAY (documenting the sequential-only guarantee), so it is the signal a
single-flight is wanted.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-spec-namespaced-predicate-parsers.md`
(`complete`, same `opus-4.8 · high · test writing` class). That card's
conventions carried here verbatim: a read-only HUNT to prove the exact gap is
genuinely uncovered before writing (confirmed `db_ready` appears in no test —
the one `db_ready` hit in `tests/unit/parity_adapter/test_replay_adapter.py` is
an unrelated `harness.db_ready` attribute, not this function); a born-red card as
the sole first commit holding the substrate-gate; the test in a second commit;
and a Verification section that re-runs the exact commands and records
tails/counts with the delta reconciled against the predecessor's baseline. The
concrete carry heeded is that card's *honesty seam* — do NOT assert behavior the
shipped code does not produce. Applied here by running a scratch harness against
the real `db_ready()` and reproducing all five results (success/cache-hit,
expiry, down/cached, uninitialised, timeout-at-bound) BEFORE writing a single
assertion; the anti-storm "invoked exactly once" claim in particular was
confirmed as `calls == 1`, not assumed. Where this slice diverges: the
predecessor pinned a pure stdlib grammar leaf (`sb/spec/refs.py`, no I/O); this
pins an async I/O wrapper with a mutable module-global cache and a real timeout —
so the discipline shifted from tie-break/empty-value edges to seam-patching
(`monkeypatch.setattr(pool, "checked_acquire", …)`) and clock/bound control, and
the residual concurrency subtlety (sequential-only anti-storm) is routed to the
💡 idea rather than silently over-claimed by the tests.
