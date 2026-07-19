# Session — coercion sweep FINAL slice (category floor)

> **Status:** `complete`
>
> Born-red: this card was the sole FIRST commit (held the substrate-gate); the
> tests landed in the second commit; this `in-progress` → `complete` flip is the
> deliberate LAST commit.

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

5 tests across two files (each assertion verified against a live probe of the
real function before commit):

1. **`tests/unit/band2/test_policy_coercion_sweep.py` (+4)** — server_logging
   `load_config` (subsystem key `"logging"`) present-value legs, driven through
   the same K7 `resolve` seam (`install_settings_reader` + `register_setting`)
   the sibling loaders in this file use:
   - `test_logging_as_bool_recognizes_present_truthy_and_falsy_tokens` — the
     `_as_bool` truthy set `("1","true","yes","on")`→`True` and falsy set
     `("0","false","no","off")`→`False` win over ANY fallback (fallback is the
     unrecognized-only leg); a real `bool` passes through. The default test hit
     only the UNSET→fallback line.
   - `test_logging_as_id_tuple_parses_mention_tokens` — `_as_id_tuple` strips the
     `<#@&` mention wrappers, treats `;` as a separator, keeps only `.isdigit()`
     tokens in order; junk/`None`/empty → `()`.
   - `test_logging_load_config_coerces_present_stored_values` — the three legs
     end-to-end: present truthy/falsy category toggles, mention-token ignore
     lists, and — the key gap — a stored `routing` OUTSIDE `VALID_ROUTING`
     (`"bogus-routing"`) degrading to `ROUTING_COMBINED` ("degrade, never
     disable"). The default test reaches only the UNSET `... or ROUTING_COMBINED`
     leg.
   - `test_logging_load_config_preserves_valid_routing` — contrast: a valid
     `ROUTING_PER_CATEGORY` survives untouched (degrade fires only on invalid)
     and the `per_category` property tracks it.
2. **`tests/integration/test_ai_policy_store_generation_decode.py` (+1)** —
   `test_get_generation_folds_malformed_and_empty_rows_to_zero` (real Postgres):
   no row → `None` (never-configured state), a malformed `"not-a-number"` row →
   `0` (the `except ValueError` swallow — THE branch), an empty `""` row → `0`
   (the `str("") or 0` leg), and a well-formed `"7"` → `7` (proves the swallow
   is the malformed-only path). Rows seeded through the store's own pool seam;
   skips cleanly without asyncpg/Postgres like its `tests/integration` siblings.

## Verification

- `python3 -m pytest -q tests/unit/band2/test_policy_coercion_sweep.py
  tests/integration/test_ai_policy_store_generation_decode.py` → **14 passed**
  (9 pre-existing in the sweep file + my 4 = 13, plus the 1 integration).
- Full `python3 -m pytest -q --ignore=examples` (Postgres started; discord
  present) → **3707 passed, 2 skipped, 1 warning** in ~104s. The +5 delta over
  the `origin/main` baseline (3702, #598) is exactly this slice; no other test
  moved. The 2 skips are pre-existing/unrelated; the 1 warning is the
  pre-existing `discord/player.py` `audioop` DeprecationWarning (stdlib).
- Guards clean: `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

With this slice the domain-coercion category is exhausted — but exhaustion also
surfaces the full scatter it was pinning: `sb/domain/server_logging/service.py`
carries its OWN `_as_bool` + `_as_id_tuple` pair, distinct from the four
`_as_bool`/`_as_int` families the prior sweep pinned (welcome / automod /
moderation / counters) and karma's, and its `_as_id_tuple` (returns a `tuple`,
order-preserving) is a second mention parser next to `automod._ids` (returns a
`frozenset`). That is now SIX private truthy/falsy-token + mention-strip helper
families re-derived across the domain. `server_logging._as_bool` matches the
welcome/counters *hard-False* contract for an unrecognized present token, not
automod/moderation's *return-the-fallback* one — so the divergence the previous
card's 💡 flagged is real here too. Now that the enumeration is provably
complete (these tests pin every branch), the consolidation posture question is
ripe: a single shared `sb/kernel` coercion utility (one agreed
unrecognized-token contract, one mention parser parameterized on
tuple-vs-frozenset) could replace all six with zero behavior change — and this
test suite is exactly the regression net that would prove it. Guard recipe:
anchor on the six `_as_bool`/`_ids`/`_as_id_tuple` defs; a consolidation
collapses the divergent unrecognized-token assertions
(`test_logging_as_bool_recognizes_present_truthy_and_falsy_tokens` +
`test_automod_as_bool_unrecognized_returns_fallback`) into one.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-coercion-sweep.md` (`complete`, same
`opus-4.8 · high · test writing` class — the wholesale sweep that landed as
#598). Its conventions carried here byte-for-byte: a read-only HUNT proving the
exact gap before writing (confirmed `server_logging.load_config`'s only test
pins the all-UNSET path and `ai.get_generation`'s malformed leg is unexercised —
the write twin `bump_generation` only ever mints numeric text, so no DB-free
path reaches the `except ValueError` swallow); a born-red card as the sole first
commit holding the substrate-gate; tests in a second commit; a Verification
section re-running the exact commands with tails/counts; and the honesty seam —
assert only what the shipped code truly produces (`get_generation` on a missing
row is pinned as `None`, NOT `0`, distinct from the malformed→`0` fold; the
`_as_bool` fallback is pinned as the unrecognized-only leg, not applied to
present truthy/falsy tokens), with the helper-scatter posture routed to the 💡
idea rather than "fixed". The reused `_install` helper in the sweep file (added
by #598) drove the server_logging legs with no new fixture. Where this slice
diverges: it is the deliberate FLOOR — the predecessor's enumeration closed 13
branches / 6 modules and named the remainder; this closes the last 4 branches /
2 modules and reaches into `tests/integration` for the DB-backed
`get_generation` leg (the earlier rounds were all DB-free unit legs), so the
category is now provably exhausted, not merely advanced.
