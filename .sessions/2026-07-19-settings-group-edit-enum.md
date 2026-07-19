# 2026-07-19 — settings epic S2: the enum-select edit widget

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · class]]

## Scope

Execute **slice S2** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
enum-select edit widget (`disbot/views/settings/edit_enum.py` +
`subsystem_view.dispatch_edit_setting` @ `menno420/superbot f87fa508`) onto
the shipped `settings.group_edit` page frame (S0, PR #579). Picking a
`str`-typed setting that declares `allowed_values` opens a windowed select of
the declared choices; committing a choice dispatches the chosen member through
the existing `settings.set_scalar` K7 op — no new op minted.

Stacked on S0 (#579): this branch was cut after S0 squash-merged into `main`,
so the page frame is already present and the PR base is `main` with a clean
enum-only diff.

Deliverables:
- The `settings.group_edit_enum` picker panel: a windowed enum select of a
  setting's `allowed_values` (current value pre-marked), opened from the
  `settings.group_edit` Edit select when the picked spec is enum-shaped
  (`value_type == "str"` with non-empty `allowed_values`). The picked value
  commits through `settings.set_scalar` (the ADMIN-floor K7 scalar lane);
  the picker refreshes in place showing the new current. The group + setting
  ride the session-minted child args (GROUP_EDIT_PARAM / the new
  GROUP_EDIT_SETTING_PARAM) — no parallel session dict.
- The bool toggle (S1) stays live; reset keeps clearing enum settings through
  `settings.clear_scalar` (the S0 reset select is type-agnostic).
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Unit tests: the enum select renders the declared choices; a pick commits
  `set_scalar` with the chosen member; an out-of-window pick still resolves;
  a non-allowed value is rejected without a write; reset clears an enum
  setting.
- Golden: `parity/goldens/settings/group_edit_enum_write.json`, minted
  honestly via the oracle-replay path.

## Result

[[fill: on completion]]

## 💡 Session idea

[[fill: on completion]]

## ⟲ Previous-session review

[[fill: on completion — remark on the S0 session]]
