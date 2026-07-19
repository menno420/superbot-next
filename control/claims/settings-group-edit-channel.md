# Claim — settings-group-edit-channel

- `claude/settings-group-edit-channel` · **settings epic S5 — channel-select
  edit widget.** Adds the channel-picker edit widget onto the shipped
  `settings.group_edit` page frame (settings epic S0/S2/S3/S4): picking a
  `channel`-hinted scalar (`input_hint="channel"`) in the Edit select opens a
  session-view child (`settings.group_edit_channel`) whose windowed component
  select lists the guild's channels (fed by the channel-directory read seam,
  paged past Discord's 25-option ceiling via `selectwindow.py`), and a pick
  commits the chosen channel id through the existing `settings.set_scalar` K7
  op (no new op minted). The `group_edit_pick` dispatch now intercepts
  `input_hint == "channel"` BEFORE the `_is_number_spec` check, so channel
  settings (which are `int` + `input_hint="channel"`, e.g.
  `btd6.strategy_submission_channel` / `ai.review_channel`) open the channel
  picker instead of misrouting to the S3 number modal. Ports the oracle
  channel-edit widget (`disbot/views/settings/edit_channel.py` + the `channel`
  arm of `subsystem_view.dispatch_edit_setting` @ `menno420/superbot f87fa508`)
  behind the audited scalar lane. Bool (S1) + enum (S2) + number (S3) +
  free-text (S4) paths stay live; reset keeps clearing through
  `settings.clear_scalar`. Preserves the option-A boundary (the 5
  operator-spine hub arms + the `games` panel arm are untouched). · files:
  `sb/domain/settings/panels.py`, `sb/domain/settings/handlers.py`,
  `parity/cases/curated.py`, `parity/goldens/settings/`,
  `tests/unit/settings_band/`, `compat/compat-frozen.json` · 2026-07-19
