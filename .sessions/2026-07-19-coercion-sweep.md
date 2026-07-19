# Session — domain policy/derivation coercion sweep (wholesale)

> **Status:** `in-progress`
>
> Born-red: this card is the session's FIRST commit (holds the substrate-gate);
> the tests land next; the Status flip to `complete` is the deliberate LAST
> commit once the close-out is written.

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

[[fill: per-file summary after tests land]]

## Verification

[[fill: pytest tails/counts, guards, bootstrap check]]

## 💡 Session idea

[[fill]]

## ⟲ Review

### previous-session review

[[fill]]
