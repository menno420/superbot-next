# Claim — settings-group-edit-presets

- `claude/settings-group-edit-presets` · **settings epic S7 — numeric-presets
  quick-set widget.** Adds the numeric-presets quick-set button widget onto the
  shipped `settings.group_edit` page frame (settings epic S0/S2/S3/S4/S5):
  picking a `numeric_presets`-hinted scalar (`input_hint="numeric_presets"` +
  a declared `presets` tuple, e.g. `xp.xp_cooldown` / `karma.cooldown_seconds`)
  in the Edit select opens a session-view child (`settings.group_edit_presets`)
  that renders one quick-set button per declared preset value; clicking a preset
  commits that fixed value through the existing `settings.set_scalar` K7 op (no
  new op minted). The `group_edit_pick` dispatch now intercepts
  `input_hint == "numeric_presets"` BEFORE the `_is_number_spec` check (mirroring
  the S5 channel interception ordering — the oracle checks input_hint first:
  channel → role → numeric_presets → value_type), so preset settings (which are
  `int` + `input_hint="numeric_presets"`) open the quick-set buttons instead of
  misrouting to the S3 number modal. Ports the oracle numeric-presets widget
  (`disbot/views/settings/edit_number_presets.py` + the `numeric_presets` arm of
  `subsystem_view.dispatch_edit_setting` @ `menno420/superbot f87fa508`) behind
  the audited scalar lane. Bool (S1) + enum (S2) + number (S3) + free-text (S4) +
  channel (S5) paths stay live; reset keeps clearing through
  `settings.clear_scalar`. Preserves the option-A boundary (the 5 operator-spine
  hub arms + the `games` panel arm are untouched). · files:
  `sb/domain/settings/panels.py`, `sb/domain/settings/handlers.py`,
  `sb/manifest/settings.py`, `parity/cases/curated.py`,
  `parity/goldens/settings/`, `tests/unit/settings_band/` · 2026-07-19
