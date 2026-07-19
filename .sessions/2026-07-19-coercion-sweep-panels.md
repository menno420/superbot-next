# Session — coercion sweep TRUE-final slice (display-renderer floor)

> **Status:** `in-progress`
>
> Born-red: this card is the sole FIRST commit (it holds the substrate-gate
> red); the tests land in the second commit; the `in-progress` → `complete`
> flip is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · test writing

## Order

TRUE-final slice of the domain-coercion coverage sweep — close the last
enumerated same-shape untested coercion sites so the coercion SHAPE is
exhausted everywhere, not just the policy loaders. Prior rounds (#593–#599)
closed every `load_policy`/`load_config`/`get_generation` loader; this closes
the display-scope settings-status RENDERERS, the last places the same
truthy-token + `int()`-fallback shape appears untested.

## Scope

Test-only. Zero `sb/` source edited; no dependency change (pip-audit n/a). Pins
the EXISTING display-coercion behavior of the enumerated renderers —
behavior-preserving, no claimed semantics touched.

## Enumeration (the completeness proof)

The security + image_moderation subsystems each consist ONLY of a `panels.py`,
so each subsystem's `_render_status` renderer_override is its SOLE stored-config
coercion site. Both were driven only for registration + hub wiring (band6 /
band2 manifest), never for present/malformed stored-value RENDERING:

- `sb/domain/security/panels.py::_render_status` — local `_flag_of`
  (present truthy/falsy-token recognition over `enabled` / `raid_enabled` /
  `age_enabled`) and `_int_of` (`int(str(resolve(...)).strip())` with
  `except (TypeError, ValueError)` fallback over `raid_join_count` /
  `raid_window_seconds` / `raid_slowmode_seconds` / `raid_lockdown_seconds` /
  `age_min_days`), plus `age_action = str(resolve(...) or "alert")`. Removal →
  a silent WRONG DISPLAYED toggle / number / lockdown branch.
- `sb/domain/image_moderation/panels.py::_render_status` — same-shape local
  `_flag_of` (`enabled` / `sexual_enabled` / `violence_enabled` /
  `harassment_enabled` / `hate_enabled`) and `_int_of` (`threshold_percent`,
  fallback 80). Removal → a silent wrong displayed category toggle / threshold.

Count: **2 renderer coercion sites (2 subsystems) — the last same-shape
untested coercion sites.**

## What the tests pin

`tests/unit/band2/test_panel_status_coercion_sweep.py` (new file) — drives each
`_render_status` end-to-end through the same K7 `resolve` seam the panel uses
(`install_settings_reader` + `register_setting`, the `_install` helper the
sibling `test_policy_coercion_sweep.py` uses) and asserts the REAL rendered
embed bytes:

1. `test_security_status_flags_and_ints_from_present_stored_values` — present
   truthy master token, real-`bool` raid flag passthrough, unrecognized age
   token → off, a stripped numeric `raid_join_count` → 25, a malformed
   `raid_window_seconds` → fallback 60 (the `except` swallow), present
   `age_action` literal; no slowmode binding ⇒ the alert-only lockdown branch.
2. `test_security_status_slowmode_branch_pins_coerced_seconds` — monkeypatches
   `sb.kernel.db.settings.get_binding` to bind `raid_slowmode_channel` so the
   `applies_raid_slowmode` branch (the ONLY render path that displays
   `raid_slowmode_seconds` / `raid_lockdown_seconds`) fires: a stripped numeric
   slowmode → 15, a malformed lockdown → fallback 300.
3. `test_security_status_all_unset_renders_shipped_fallbacks` — contrast: every
   setting UNSET renders the shipped fallbacks (flags off, 10 joins / 60s,
   7 days, `age_action` → `"alert"` via `str(None or "alert")`).
4. `test_image_moderation_status_flags_and_threshold_from_present_values` —
   present truthy/falsy category tokens flip each displayed toggle, real-`bool`
   passthrough, stripped numeric `threshold_percent` → 55.
5. `test_image_moderation_status_malformed_threshold_reverts_to_default` —
   malformed `threshold_percent` → fallback 80; every unset flag renders off.

HONESTY: `_flag_of` here is the welcome/counters *membership* shape — a present
unrecognized token → `False` via the truthy-token membership test, with the
`fallback` argument the `None`/UNSET-only leg (every call site passes
`fallback=False`, so unset also renders off). The hazard pinned is the silent
wrong toggle (drop the membership tuple and a stored `"on"` renders off), not a
fallback-on-unrecognized contract — asserted only as the code truly produces.

## Verification

- `python3 -m pytest -q tests/unit/band2/test_panel_status_coercion_sweep.py`
  → _(placeholder — filled on flip)_.
- Full `python3 -m pytest -q --ignore=examples` → _(placeholder — tail +
  count filled on flip)_.
- Guards clean (4): `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`. Guard-fires delta: _(placeholder)_.
- `python3 bootstrap.py check` → _(placeholder — exit 0, card `complete`)_.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

_(placeholder — filled on flip.)_

## ⟲ Review

### previous-session review

_(placeholder — filled on flip.)_
