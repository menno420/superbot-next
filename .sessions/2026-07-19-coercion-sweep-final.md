# Session — coercion sweep FINAL slice (category floor)

> **Status:** `in-progress`
>
> Born-red: this card is the sole FIRST commit (holds the substrate-gate). The
> tests land in the second commit; the `in-progress` → `complete` flip is the
> deliberate LAST commit. No close-out until the tests are green.

- **📊 Model:** opus-4.8 · high · test writing

## Order

FINAL slice of the domain-coercion coverage sweep — cover the last enumerated
untested real-hazard coercion branches so the category is EXHAUSTED (this
landing is the floor). Prior rounds (#593–#598) chipped the category one module
at a time; this closes the remainder.

## Scope

Test-only. Zero `sb/` source edited; no dependency change (pip-audit n/a). Pins
the EXISTING read-model coercion behavior of the enumerated branches —
behavior-preserving, no claimed semantics touched.

## Enumeration (the completeness proof)

Remaining untested real-hazard coercion branches (removal → silent wrong
answer):

- `sb/domain/server_logging/service.py::load_config` — its only test
  (`test_logging_config_defaults_and_degrade`) pins the all-UNSET/default path.
  Three present-value legs unpinned:
  - `_as_bool` (~L186) — present-token recognition: truthy
    `("1","true","yes","on")`→`True`, falsy `("0","false","no","off")`→`False`
    (only the UNSET→fallback line was hit). Removal → silently flips the wrong
    category toggle.
  - `_as_id_tuple` (~L197) — mention-token parse for
    `ignored_channels`/`ignored_users`: strips `<#@&` wrappers, `;`→`,`,
    `.isdigit()` filter (only empty/UNSET tested). Removal → wrong ignored set.
  - present-invalid-routing degrade (~L222-223) — a stored `routing` not in
    `VALID_ROUTING` degrades to `ROUTING_COMBINED` ("degrade, never disable");
    only the UNSET `... or ROUTING_COMBINED` leg was reached. Removal →
    wrong/absent routing.
- `sb/domain/ai/policy_store.py::get_generation` (~L302-313) — DB-backed.
  `int(str(row["value"]) or 0)` with `except ValueError: return 0` reverts a
  malformed stored generation value → `0`; the malformed leg was untested (the
  `str(... or 0)` empty leg rides alongside). Removal → a corrupt counter row
  raises instead of folding to the shipped `0`.

Count: **4 untested real-hazard coercion branches across 2 modules.**

## What the tests pin

_(filled at completion)_

## Verification

_(filled at completion)_

## 💡 Session idea

_(filled at completion)_

## ⟲ Review

### previous-session review

_(filled at completion)_
