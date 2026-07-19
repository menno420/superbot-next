# 2026-07-19 — settings epic S5: the channel-select edit widget

> **Status:** `in-progress`

- **📊 Model:** [[fill: family-level model line at completion]]

## Scope

Execute **slice S5** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
channel-select edit widget (`disbot/views/settings/edit_channel.py` + the
`channel` arm of `subsystem_view.dispatch_edit_setting` @ `menno420/superbot
f87fa508`) onto the shipped `settings.group_edit` page frame (S0, PR #579; S2
enum, PR #580; S3 number, PR #581; S4 text, PR #582). Picking a
`channel`-hinted scalar (`input_hint="channel"`) in the Edit select opens a
session-view child (`settings.group_edit_channel`) whose windowed component
select lists the guild's channels (fed by the channel-directory read seam,
paged past the 25-option ceiling via `selectwindow.py`); a pick commits the
chosen channel id through the existing `settings.set_scalar` K7 op — no new op
minted.

The `group_edit_pick` dispatch currently routes purely by `value_type` and
IGNORES `input_hint`, so channel settings (`int` + `input_hint="channel"`)
misroute to the S3 number modal. S5 intercepts `input_hint == "channel"`
BEFORE the `_is_number_spec` check (the oracle checks `input_hint` first), so
those settings open the channel picker instead.

Deliverables:
- The `settings.group_edit_channel` widget panel: a session-view child hosting
  a windowed ENUM-kind component select whose options are the guild's channels
  (via `sb.domain.channel.service.active_directory().list_channels`), the
  current channel pre-marked, opened from the `settings.group_edit` Edit select
  when the picked spec is channel-hinted. A pick commits the channel id through
  `settings.set_scalar` (the ADMIN-floor K7 scalar lane); the picker refreshes
  in place. A Back button re-opens the group's edit page. Reset stays on the
  type-agnostic S0 reset select (`settings.clear_scalar`).
- Bool (S1) + enum (S2) + number (S3) + free-text (S4) paths stay live.
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Unit tests: a channel-hinted setting opens the channel picker (NOT the number
  modal — a pinned regression); a pick persists the channel id via
  `set_scalar`; reset clears it; windowed paging works for a many-channel
  guild.
- Golden: `parity/goldens/settings/settings_group_edit_channel_write.json`,
  minted honestly via the oracle-replay path against
  `btd6.strategy_submission_channel`.

## Result

[[fill: result at completion]]

## 💡 Session idea

[[fill: one genuine idea at completion]]

## ⟲ Previous-session review

[[fill: one-line review remark on the S4 session at completion]]
