# Session — domain policy/derivation coercion sweep (wholesale)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit: the first
> commit was this card alone (born-red, held the substrate-gate); the tests
> landed in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · high · test writing

## Order

Deliberate systematic sweep to close a category wholesale: untested
defensive-coercion / fallback branches in `sb/domain/*` policy + store
derivation modules — code that coerces malformed / off-type stored values
(`int()`/`bool()`/`str(... or default)` coercion, `x or DEFAULT`,
`except (TypeError, ValueError)` swallows reverting to shipped defaults, JSON
`_decode` tolerance). Removing any such branch silently ships a WRONG answer no
test catches. Rounds 1–8 already covered mining/rewards, karma/policy,
spec/refs, http/health, btd6/difficulty_costs, egress/allowed_mentions_for;
scopes fishing/role/casino/server_management/xp are claimed elsewhere.

## Scope

Test-only. Zero `sb/` source edited; no dependency change (pip-audit n/a). Pins
the EXISTING read-model coercion behavior of the enumerated modules —
behavior-preserving, no claimed semantics touched.

## Enumeration (the completeness proof)

Untested real-hazard coercion branches (removal → silent wrong answer):

- `welcome/service.py::_as_bool` — present unrecognized string → `False`
  (fallback ignored for present values); `_as_int` — non-numeric/float string →
  fallback; `load_policy` `str(... or DEFAULT_*)` empty-string revert. Loader
  had NO test (0 test files referenced `welcome.service`).
- `automod/engine.py::_as_bool` — unrecognized token → fallback `d`; `_as_int` —
  non-int → `d`; `_ids` — mixed/`<@&…>`/`;`-separated tokens parsed, junk/None →
  subset/empty. `load_policy` never called by a test (only `AutomodPolicy`
  constructed directly).
- `moderation/service.py::_as_int` / `_as_bool` — present off-type value →
  fallback. Existing test pins only the all-default (`None`) path; the
  present-malformed leg is unpinned.
- `counters/service.py::_as_bool` — present unrecognized → `False`;
  `load_policy._template` empty/None stored template → `DEFAULT_TEMPLATES[kind]`;
  `CounterPolicy.template_for` empty template → `DEFAULT_TEMPLATES` fallback.
  Loader untested (only `render_counters` + presets pinned).
- `counting/store.py::_decode` — malformed JSON / non-dict / `None` → `{}`
  (silent state loss). Existing counting tests monkeypatch `get_state`, so
  `_decode` is never exercised.
- `automation/store.py::_decode` — malformed JSON / non-dict / list / int /
  bytes → `{}` or decoded dict (silent config loss on
  `get_rule_by_name`/`list_rules_for_guild`). 0 test files referenced
  `automation.store`.

Count: **13 untested real-hazard coercion branches across 6 modules.**

## What the tests pin

20 tests across three new files (each assertion verified against a live probe of
the real function before commit):

1. **`tests/unit/band2/test_policy_coercion_sweep.py` (9)** — welcome / automod /
   moderation / counters `load_policy` driven end-to-end through the K7 `resolve`
   seam (`install_settings_reader` + `register_setting`). Pins the honest
   per-module `_as_bool` divergence: welcome/counters return `False` for a
   *present* unrecognized token (fallback is the `None`-only leg), while
   automod/moderation return the fallback `d`. Pins `_as_int` reverting a
   non-numeric / float / list value to the shipped default (it is
   `int(str(value))`, so `3.9` does NOT truncate to 3 — it raises and reverts),
   `str(... or DEFAULT)` empty reverts (welcome messages, moderation
   escalation-action, counters templates → `DEFAULT_TEMPLATES[kind]`),
   `automod._ids` mixed-token parsing (`<@&1>,2 ; 3` → `{1,2,3}`; junk/None →
   empty), and `CounterPolicy.template_for` read-time blank revert.
2. **`tests/unit/band6/test_counting_store_decode.py` (5)** —
   `counting/store.py::_decode`: `None`→`{}`, live-dict passthrough, JSON-string
   decode, malformed/empty string swallowed to `{}`, non-dict/non-str (int) →
   `{}`. Existing counting tests monkeypatch `get_state`, so this swallow was
   never exercised.
3. **`tests/unit/scheduler/test_automation_store_decode.py` (6)** —
   `automation/store.py::_decode`: dict passthrough, JSON object str + bytes
   decode, malformed str → `{}`, JSON *list* (valid JSON, not a config map) →
   `{}`, bare int → `{}`. No test referenced `automation.store` before.

## Verification

- `python3 -m pytest -q tests/unit/band2/test_policy_coercion_sweep.py
  tests/unit/band6/test_counting_store_decode.py
  tests/unit/scheduler/test_automation_store_decode.py` → **20 passed**.
- Full `python3 -m pytest -q --ignore=examples` (Postgres started; discord
  present) → **3702 passed, 2 skipped, 1 warning** in ~100s. The +20 delta over
  the previous `origin/main` baseline (3682, #597) is exactly this slice; no
  other test moved. The 2 skips are pre-existing/unrelated; the 1 warning is the
  pre-existing `discord/player.py` `audioop` DeprecationWarning (stdlib).
- Guards clean: `check_symbol_shadowing`, `check_namespace`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

The four `load_policy` readers each carry a *private* `_as_bool` / `_as_int`
coercion helper, and they disagree on the unrecognized-present-token contract:
welcome (`sb/domain/welcome/service.py`) and counters
(`sb/domain/counters/service.py`) return a hard `False`, while automod
(`sb/domain/automod/engine.py`) and moderation
(`sb/domain/moderation/service.py`) return the caller's fallback `d`. For a
bool whose shipped default is `True` (welcome `join_enabled`), a corrupt stored
token silently flips the feature OFF rather than honoring the default — a
different failure posture than the sibling subsystems. Worth a one-line posture
decision: either the divergence is intentional (bool rows are opt-in-only, so
any non-truthy token means off) or these four helpers should share ONE coercion
utility with a single agreed fallback contract. These tests pin TODAY's
per-module behavior, so whichever way it lands, the diff to this test is the
signal. Guard recipe: anchor on the `_as_bool` defs in the four service/engine
modules + `test_welcome_load_policy_coerces_malformed_stored_values` /
`test_automod_as_bool_unrecognized_returns_fallback`; a consolidation would
collapse the two divergent assertions into one.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-karma-policy-coercion.md` (`complete`, same
`opus-4.8 · high · test writing` class, round 8). That card's convention carried
here verbatim: a read-only HUNT proving the exact gap is uncovered before
writing (confirmed welcome/automod/counters `load_policy` are untouched by any
test and moderation pins only the all-`None` default path — the present-malformed
legs are unexercised), a born-red card as the sole first commit holding the
substrate-gate, tests in a second commit, and a verification section re-running
the exact commands with tails/counts. The heeded honesty seam: assert only what
the shipped code truly produces — `_as_int(3.9)` is pinned as *reverts to
fallback* (not `int(float)`-truncates), and the read-model helpers' divergent
fallback contract is routed to the 💡 idea as a posture question rather than
"fixed" or falsely unified in a test. Where this slice diverges from the single
-module karma round: it is a deliberate WHOLESALE sweep — the enumeration above
is the completeness evidence (13 branches / 6 modules), and it spans two hazard
shapes (policy-loader `_as_*` coercion AND store `_decode` JSON tolerance)
rather than one module's ladder, closing the domain-coercion category the
prior rounds were chipping at one at a time.
