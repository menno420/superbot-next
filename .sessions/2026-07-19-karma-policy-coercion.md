# Session — karma policy: cover load_policy's stored-value coercion + fallback

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`): the first commit was this card alone (born-red, held
> the substrate-gate); the test landed in the second commit; this flip is the
> last.

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 8) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Fresh-territory hunt on
unclaimed domain pure-derivation found `sb/domain/karma/policy.py::load_policy`:
its defensive coercion ladder (malformed stored `cooldown_seconds`/`daily_cap`
→ shipped default; `None` reaction_emoji → OFF; `bool()`/`int()` coercion of
string-typed KV rows; the per-key `_get` `LookupError` swallow) had NO test —
the only existing `load_policy` test feeds the all-`undeclared` (pure-default)
path.

## Scope

Test-only. Added three tests to `tests/unit/band4/test_band4_karma.py`
(karma file 14 → 17). Zero `sb/` source edited; no dependency change (pip-audit
n/a). No claimed domain semantics touched — this pins the existing read model's
coercion, behavior-preserving.

## What the tests pin

Each assertion verified against a live run of the real `load_policy` before
being committed (a scratch probe fed the crafted store through the actual
function; the printed `KarmaPolicy` matched every assertion below):

1. **`test_load_policy_coerces_malformed_stored_values` — the defensive swallow.**
   A stored `cooldown_seconds="not-an-int"` (`int()` `ValueError`) and
   `daily_cap=[1,2]` (`int()` `TypeError`) each revert to the shipped default
   (`DEFAULT_COOLDOWN_SECONDS=3600`, `DEFAULT_DAILY_CAP=10`) rather than leaking a
   non-int into `KarmaPolicy`; a stored `reaction_emoji=None` normalises to `""`
   (`str(emoji or "")` → feature OFF); a falsy `enabled=0` `bool()`-coerces to
   `False`. Remove the `try/except int()` and a malformed KV row would propagate a
   string/list into the frozen policy and break downstream cooldown/cap
   arithmetic silently — this test is the guard.
2. **`test_load_policy_coerces_string_typed_stored_values` — the coercion happy
   path.** String-typed rows (`cooldown_seconds="7200"`, `daily_cap="25"`) coerce
   to `int` `7200`/`25` (asserted with `isinstance(..., int)`, so a refactor
   dropping the `int()` and returning the raw string would fail); `reaction_emoji`
   `"✨"` is preserved; a truthy `enabled=1` → `True`.
3. **`test_load_policy_falls_back_per_missing_key` — the per-key `_get` swallow.**
   Declares `enabled`/`cooldown_seconds`/`daily_cap` (stored) but leaves
   `reaction_emoji` undeclared: the two stored keys resolve to their values while
   the undeclared key's `resolve` `LookupError` is swallowed per-field, reverting
   only that one to `DEFAULT_REACTION_EMOJI=""`. This is distinct from the
   pre-existing all-undeclared test — it pins that the fallback is granular, not
   all-or-nothing.

## Verification

- `python3 -m pytest -q tests/unit/band4/test_band4_karma.py` → **17 passed**
  in 0.17s (was 14 — the +3 delta is exactly this slice).
- Full `python3 -m pytest -q --ignore=examples` (Postgres started + discord
  present), branch rebased onto current `origin/main` (`bc8bcf5`, #596) →
  **3682 passed, 2 skipped, 1 warning** in 106s. The 2 skips are
  pre-existing/unrelated; the 1 warning is the pre-existing `discord/player.py`
  `audioop` DeprecationWarning (stdlib, unrelated). No other test moved.
- Guards clean: `check_symbol_shadowing`, `check_namespace`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

`load_policy` clamps neither `cooldown_seconds` nor `daily_cap` to the
`MIN_/MAX_` bounds it declares (`MIN_COOLDOWN_SECONDS=0`,
`MAX_COOLDOWN_SECONDS=604800`; `MIN_DAILY_CAP=1`, `MAX_DAILY_CAP=1000`) — those
constants exist and are exported in `__all__`, yet a stored `daily_cap=0` or
`cooldown_seconds=-5` (well-typed but out of range) sails through `int()` into
the frozen policy unbounded. Today the widgets that write these rows validate the
range upstream, so it's latent-safe; but the read model does not fail-closed to
the declared bounds the way it fail-closes on a *type* error. Worth a one-line
posture decision: either the `MIN_/MAX_` constants are write-side-only (then
`load_policy` needn't reference them and this is fine as-is), or the read model
should clamp defensively the same way it coerces. These tests pin TODAY's
behavior (type-coerce yes, range-clamp no), so whichever way the decision lands,
the change to this test is the signal. Guard recipe: anchor on the `int()`
try/except pair in `load_policy` and the `MIN_/MAX_` constants in
`sb/domain/karma/policy.py`; a behavioral pin would add a `daily_cap=0` case
asserting whichever clamp posture is chosen.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-http-db-ready-probe.md` (`complete`, same
`opus-4.8 · high · test writing` class, round 7). That card's convention carried
here verbatim: a read-only HUNT to prove the exact gap is genuinely uncovered
before writing (confirmed the only `load_policy` test feeds the all-undeclared
path — the stored-value coercion legs are unexercised), a born-red card as the
sole first commit holding the substrate-gate, the test in a second commit, and a
verification section that re-runs the exact commands and records tails/counts.
One concrete carry heeded: that card's honesty seam — assert only behavior the
shipped code actually produces (it routed the un-driven cache-eviction nuance to
its 💡 idea rather than over-claim in a test). Applied here to the range-clamp
gap: rather than assert `load_policy` clamps to `MIN_/MAX_` (it does not), the
tests pin only the coercion the code truly does, and the missing clamp is routed
to the 💡 idea as a posture question — not silently "fixed" nor falsely asserted.
Where this slice diverges: db_ready was a kernel health-probe cache/timeout
surface; this is a domain read model whose blast radius is every karma grant's
anti-farm gate (cooldown/cap), and the load-bearing assertion is the
type-coercion fallback — a malformed KV row silently reverting to the shipped
default rather than propagating a bad type into the frozen policy.
