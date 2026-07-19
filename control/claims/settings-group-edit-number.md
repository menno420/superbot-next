# Claim — settings-group-edit-number

- `claude/settings-group-edit-number` · **settings epic — number-modal edit
  widget (S3).** Adds the numeric-input modal edit widget onto the shipped
  `settings.group_edit` page frame (settings epic S0/S2): picking an `int` /
  `float` scalar in the Edit select opens a session-view child
  (`settings.group_edit_number`) whose button ISSUES a G-10 `ModalSpec`
  numeric-input modal, and the submit coerces + range-validates then commits
  through the existing `settings.set_scalar` K7 op (no new op minted). Ports
  the oracle number-edit modal (`disbot/views/settings/edit_number.py` +
  `subsystem_view.dispatch_edit_setting` numeric arm @
  `menno420/superbot f87fa508`) behind the audited scalar lane. Bool (S1) +
  enum (S2) paths stay live; reset keeps clearing through
  `settings.clear_scalar`. Preserves the option-A boundary (the 5
  operator-spine hub arms + the `games` panel arm are untouched). · files:
  `sb/domain/settings/panels.py`, `sb/domain/settings/handlers.py`,
  `parity/cases/curated.py`, `parity/goldens/settings/`,
  `tests/unit/settings_band/` · 2026-07-19
