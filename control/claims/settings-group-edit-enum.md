# Claim — settings-group-edit-enum

- `claude/settings-group-edit-enum` · **settings epic — enum-select edit
  widget (S2).** Adds the windowed enum-select edit widget onto the shipped
  `settings.group_edit` page frame (settings epic S0, PR #579): picking a
  `str`-typed setting that declares `allowed_values` opens a windowed select
  of the declared choices, and committing a choice dispatches through the
  existing `settings.set_scalar` K7 op (no new op minted). Ports the oracle
  enum-edit widget (`disbot/views/settings/edit_enum.py` +
  `subsystem_view.dispatch_edit_setting` @ `menno420/superbot f87fa508`)
  behind the audited scalar lane. The S1 bool toggle stays live; reset keeps
  clearing through `settings.clear_scalar`. Preserves the option-A boundary
  (the 5 operator-spine hub arms + the `games` panel arm are untouched). ·
  files: `sb/domain/settings/panels.py`, `sb/domain/settings/handlers.py`,
  `sb/manifest/settings.py`, `parity/cases/curated.py`,
  `parity/goldens/settings/`, `tests/unit/settings_band/` · 2026-07-19
