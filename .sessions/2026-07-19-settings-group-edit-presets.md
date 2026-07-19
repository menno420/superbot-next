# 2026-07-19 — settings epic S7: the numeric-presets quick-set widget

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · kind]]

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

[[fill: on flip to complete]]
