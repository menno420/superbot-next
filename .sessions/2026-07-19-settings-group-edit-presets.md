# 2026-07-19 — settings epic S7: the numeric-presets quick-set widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

## Scope

Execute **slice S7** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
numeric-presets quick-set widget
(`disbot/views/settings/edit_number_presets.py` + the `numeric_presets` arm of
`subsystem_view.dispatch_edit_setting` @ `menno420/superbot f87fa508`) onto the
shipped `settings.group_edit` page frame (S0, PR #579; S2 enum, #580; S3
number, #581; S4 text, #582; S5 channel, #583). Picking a
`numeric_presets`-hinted scalar (`input_hint="numeric_presets"` + a declared
`presets` tuple) in the Edit select opens a session-view child
(`settings.group_edit_presets`) that renders one quick-set button per declared
preset value; clicking a preset commits that fixed value through the existing
`settings.set_scalar` K7 op — no new op minted.

The `group_edit_pick` dispatch routes by `value_type` and (as of S5) intercepts
`input_hint == "channel"` BEFORE the `_is_number_spec` check. S7 adds a second
interception for `input_hint == "numeric_presets"` (settings carrying `presets`)
BEFORE `_is_number_spec` — mirroring the S5 channel ordering (the oracle checks
input_hint first: channel → role → numeric_presets → value_type). Preset
settings are `int` + `input_hint="numeric_presets"` (e.g. `xp.xp_cooldown`,
`karma.cooldown_seconds`), so the value-type-only dispatch would misroute them
to the S3 number modal; the presets arm intercepts the hint first so they open
the quick-set buttons instead.

Deliverables:
- The `settings.group_edit_presets` widget panel: a session-view child hosting
  one quick-set button per declared preset value (relabelled per-setting by a
  renderer override; current value marked primary), opened from the
  `settings.group_edit` Edit select when the picked spec is presets-hinted. A
  preset click commits its fixed value through `settings.set_scalar` (the
  ADMIN-floor K7 scalar lane); the widget refreshes in place. A Back button
  re-opens the group's edit page. Reset stays on the type-agnostic S0 reset
  select (`settings.clear_scalar`).
- Bool (S1) + enum (S2) + number (S3) + free-text (S4) + channel (S5) paths stay
  live.
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Unit tests: a presets-hinted setting opens the buttons (NOT the number
  modal — a pinned regression); clicking a preset persists that value via
  `set_scalar`; reset clears it; all declared presets render.
- Golden: `parity/goldens/settings/settings_group_edit_presets_write.json`,
  minted honestly via the oracle-replay path against `xp.xp_cooldown`.

## Result

Landed the S7 numeric-presets quick-set widget on PR #584 (base main; S5 #583
already merged, so the diff is presets-only — branched from origin/main rather
than rebasing the pre-merge S5 branch). The `group_edit_pick` dispatch now
intercepts `input_hint == "numeric_presets"` BEFORE the value_type arms (right
after the S5 channel arm — the oracle checks input_hint first), so picking a
presets-hinted scalar in the `settings.group_edit` Edit select opens the
quick-set buttons widget `settings.group_edit_presets`
(`sb/domain/settings/panels.py` `settings_group_edit_presets_spec` +
`_group_edit_presets_fields` provider + the `_render_group_edit_presets`
renderer override + the new `_is_presets_spec` predicate;
`sb/domain/settings/handlers.py` `group_edit_pick` presets branch +
`group_edit_presets_pick` / `group_edit_presets_back` handlers + the
`_refresh_group_edit_presets` in-place refresh). The widget renders one quick-set
button per declared preset value: static `pval_0…pval_9` PanelActionSpec slots
that the render override relabels with each preset value (the current value
marked primary), dropping the surplus slots — the `_render_access`
dynamic-component precedent (this grammar renders buttons from declared actions,
so the per-setting labels ride the override). A preset click commits its fixed
value through the existing K7 `settings.set_scalar` lane — no new op — and
refreshes in place; the clicked slot's index rides `session_action` and the value
is re-derived from `spec.presets` (never trusted from the wire). A stale slot
beyond the declared presets rejects without a write.

**Regression fixed + pinned:** `xp.xp_cooldown` (and `karma.cooldown_seconds` /
`karma.daily_cap`, etc.) are `int` + `input_hint="numeric_presets"`; the
value_type-only dispatch tail misrouted them to the S3 number modal. The presets
arm now intercepts the hint first, so they open the quick-set buttons
(`test_presets_pick_opens_the_buttons_not_the_number_modal` pins this against the
real xp setting — asserting the opened panel id, not merely the predicate).

**Port deviation (flagged):** the oracle's `NumericPresetsView` carried an
`Override…` button that reopened the free-form `NumberSettingModal` for an
arbitrary value; the port OMITS it as a deliberate under-port — carrying it would
need either a new `ModalSpec` custom_id (compat-frozen §5.3 drift, which this
slice avoids by design) or reusing the S3 number modal across two panels (submit
routing ambiguity). The arbitrary-value path is a follow-up. Clearing rides the
shared type-agnostic S0 reset select (`settings.clear_scalar`), the S2/S5 posture.

**Sim-gate note (flagged):** the widget declares 11 components (10 preset slots +
Back), above `PANEL_FLOOR=4`, so unlike the ≤4-component S2–S5 widgets (which are
auto-exempt below-floor) its [A] layout is NOT auto-exempt. Its mechanical
quick-set grid (5-per-row, mirroring the oracle) is pinned **Exempt** in
`manifest/layout/settings.lock.json` + the sim-gate baseline — the
`settings.access` / `ai.settings_edit_presets` precedent (both above-floor,
both Exempt legacy-seed).

Bool (S1) + enum (S2) + number (S3) + free-text (S4) + channel (S5) stay live;
presets reset clears through `settings.clear_scalar` (the S0 reset select is
type-agnostic). Option-A boundary preserved (the 5 hub arms + `games` untouched).
Manifest snapshot recompiled. Golden
`parity/goldens/settings/settings_group_edit_presets_write.json` minted honestly
via the oracle-replay path against `xp.xp_cooldown` (open the xp edit page → pick
`xp_cooldown` → click the preset `30` → the `settings` db_delta writes
`xp_cooldown=30`; the quick-set buttons render `0/15/30/60/120/300`, and the
in-place refresh re-marks the `30` button primary). Golden corpus 532 → 533
(minted 70 → 71); count-pins resynced in `test_check_parity_depth.py` +
`test_replay_adapter.py`. `check_compat_frozen` GREEN with NO drift — the buttons
add run-minted component custom_ids but no ModalSpec custom_id, so the frozen
§5.3 contract is untouched (the defensive S3.5 prediction held). Full
`python3 -m pytest tests/unit --ignore=examples` — **3546 passed, 15 skipped**;
`check_symbol_shadowing` / `namespace` / `no_skip` / `config_usage` /
`orphan_pendings` / `sim_gate` clean. The full golden-parity replay is left to
CI's authoritative gates on the PR (not blocked locally per the slice rule).

## 💡 Session idea

S7 completes the widget frontier the S4/S5 cards mapped, and it surfaces a THIRD
axis the pointer-arm rule (S5) did not name: the port frame's dispatch order is a
property of the SEQUENCE, but the port frame's *component grammar* is a property
of the COMPONENT COUNT. Every S2–S5 widget stayed under `PANEL_FLOOR=4` (a select
+ a Back, or a modal button + a Back), so its arrangement was auto-exempt from
the sim gate — invisibly. S7 is the first group_edit widget whose faithful shape
(one button per preset) crosses that floor, and it is exactly the crossing that
forces the layout into the reviewed-or-Exempt gate. Worth pinning as the
widget-count rule: "a ported widget stays below the sim gate's radar only while
its declared component count ≤ PANEL_FLOOR; the moment a widget's honest shape is
a *variable-arity component set* (preset buttons, a role-chip row, a multi-slot
grid) it crosses the floor and needs an explicit Exempt or sim record — the
auto-exempt below-floor carve-out is a property of the widget's ARITY, not of it
being a group_edit widget." That is why S7 is the first slice to touch
`settings.lock.json` at all, and why S6 (role select, a single native picker)
will NOT need to — it is back under the floor.

## ⟲ Previous-session review

S5 (channel select, #583) left the dispatch in exactly the shape S7 needed — its
`input_hint == "channel"` interception, routed BEFORE `_is_number_spec`, was the
literal template for S7's `numeric_presets` arm (same ordering rationale: a
hinted `int` satisfies `_is_number_spec` too, so ORDER, not the predicate, is
what keeps it off the number modal), and its card's pointer-arm rule ("test the
ORDER, not just the predicate") is precisely why
`test_presets_pick_opens_the_buttons_not_the_number_modal` asserts the opened
panel id. The one thing S5 could not foresee: that S7's widget would be the first
to cross `PANEL_FLOOR` and so the first to need a `settings.lock.json` Exempt — S5
was a windowed select (2 components, auto-exempt), so its card's "no drift"
posture held for compat-frozen but silently side-stepped the sim gate entirely,
a surface S7 was the first to meet.
