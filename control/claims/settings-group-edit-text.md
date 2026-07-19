# Claim — settings-group-edit-text

- `claude/settings-group-edit-text` · **settings epic — free-text modal edit
  widget (S4).** Adds the free-text (string) modal edit widget onto the shipped
  `settings.group_edit` page frame (settings epic S0/S2/S3): picking a
  `str`-without-`allowed_values` scalar in the Edit select opens a session-view
  child (`settings.group_edit_text`) whose button ISSUES a G-10 `ModalSpec`
  free-text-input modal, and the submit validates (non-empty + declared
  `bounds` max-length per the SettingSpec) then commits through the existing
  `settings.set_scalar` K7 op (no new op minted). Ports the oracle text-edit
  modal (`disbot/views/settings/edit_text.py` + `subsystem_view.
  dispatch_edit_setting` free-form-string arm @ `menno420/superbot f87fa508`)
  behind the audited scalar lane. Bool (S1) + enum (S2) + number (S3) paths stay
  live; reset keeps clearing through `settings.clear_scalar`. Preserves the
  option-A boundary (the 5 operator-spine hub arms + the `games` panel arm are
  untouched). · files: `sb/domain/settings/panels.py`,
  `sb/domain/settings/handlers.py`, `parity/cases/curated.py`,
  `parity/goldens/settings/`, `tests/unit/settings_band/`,
  `compat/compat-frozen.json` · 2026-07-19
