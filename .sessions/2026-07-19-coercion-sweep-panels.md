# Session — coercion sweep TRUE-final slice (display-renderer floor)

> **Status:** `complete`
>
> Born-red: this card was the sole FIRST commit (it held the substrate-gate
> red); the tests landed in the second commit; this `in-progress` →
> `complete` flip is the deliberate LAST commit.

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
  → **5 passed** in ~0.2s.
- Full `python3 -m pytest -q --ignore=examples` (Postgres started; discord
  present) → **3712 passed, 2 skipped, 1 warning** in ~101s. The +5 delta over
  the `origin/main` baseline (3707, #599) is exactly this slice; no other test
  moved. The 2 skips are pre-existing/unrelated; the 1 warning is the
  pre-existing `discord/player.py` `audioop` DeprecationWarning (stdlib).
- Guards clean (4): `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip` — each exit 0. Guard-fires delta:
  **0 fires** attributable to this slice (test-only, zero `sb/` source edited).
- `python3 bootstrap.py check` → exit 0; card validates `complete` at HEAD.
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

The coercion shape is now provably exhausted — but the SAME divergent helper
scatter the prior sweep flagged reaches one layer further. Each `_render_status`
re-derives its OWN `_flag_of`/`_int_of` pair as function-LOCAL closures (unlike
the module-level loader helpers `_as_bool`/`_as_int`/`_ids`/`_as_id_tuple` the
loader sweep pinned and could import directly), and `_flag_of` matches the
welcome/counters *hard-False-on-unrecognized* contract, not automod/
server_logging's *return-the-fallback* one — so there are now EIGHT truthy/
falsy-token helper families across the domain, two of them un-importable
closures. A single shared `sb/kernel` coercion utility (one agreed
unrecognized-token contract) would let these renderers drop their inline
closures with zero behavior change, and this suite plus the loader sweep is the
regression net that would prove it. A honest should-but-doesn't rides alongside,
routed here not "fixed": `_flag_of`'s `fallback` parameter is effectively dead
for a present-unrecognized token (that leg always returns `False` via the
membership test; `fallback` is reached only for `None`/UNSET), so a future flag
wanting `fallback=True` on a garbled row would silently get `False` — harmless
today (every call site passes `fallback=False`) but a latent trap a shared
utility would erase.

## ⟲ Review

### previous-session review

Predecessor: `.sessions/2026-07-19-coercion-sweep-final.md` (`complete`, same
`opus-4.8 · high · test writing` class — the category-floor slice that landed as
#599). Its conventions carried here byte-for-byte: a read-only HUNT proving the
exact gap before writing (confirmed both panels are driven only for
registration/hub-wiring, never for present/malformed stored-value rendering, and
that each subsystem is `panels.py`-only so `_render_status` is its SOLE coercion
site); a born-red card as the sole first commit holding the substrate-gate;
tests in a second commit; a Verification section re-running the exact commands
with tails/counts (+5 delta named against the #599 baseline); and the honesty
seam — assert only what the shipped code truly produces (`_flag_of` pinned as
membership *hard-False* on an unrecognized present token, NOT a
fallback-on-unrecognized contract; `age_action` empty/unset pinned as `"alert"`
via `str(None or "alert")`), with the helper-scatter posture routed to the 💡
idea rather than "fixed". The `_install` reader-seam helper the #598 sweep added
to `test_policy_coercion_sweep.py` was mirrored verbatim into the new file.
Where this slice diverges: the predecessor closed the last *loader* branches and
declared the category exhausted at the loader layer; this reaches the display
RENDERERS — the last same-shape untested sites — driving `_render_status`
through the `resolve` seam AND (a new seam for this sweep) monkeypatching
`get_binding` to reach the slowmode lockdown branch that no reader-only drive
can. With both layers pinned the coercion SHAPE is exhausted everywhere, not
merely at the loaders — this is the true floor.
