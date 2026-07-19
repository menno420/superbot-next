# 2026-07-19 — settings epic S3: the number-modal edit widget

> **Status:** `in-progress`

- **📊 Model:** [[fill: family · effort · task-shape]]

## Scope

Execute **slice S3** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
number-edit modal (`disbot/views/settings/edit_number.py` +
`subsystem_view.dispatch_edit_setting` numeric arm @ `menno420/superbot
f87fa508`) onto the shipped `settings.group_edit` page frame (S0, PR #579;
S2 enum, PR #580). Picking an `int` / `float`-typed setting in the Edit
select opens a session-view child (`settings.group_edit_number`) whose button
ISSUES a G-10 `ModalSpec` numeric-input modal; the submit coerces +
range-validates the typed value and commits it through the existing
`settings.set_scalar` K7 op — no new op minted.

Stacked on S2 (#580): the number branch was cut from the pre-merge S2 branch;
S2 squash-merged into `main` (SHA `ee2f0a9`) before the first push, so the
branch was re-pointed onto the new `main` and the PR base is `main` with a
clean number-only diff.

Deliverables:
- The `settings.group_edit_number` widget panel: a session-view child whose
  single button issues the ported `NumberSettingModal` (a one-input numeric
  modal), opened from the `settings.group_edit` Edit select when the picked
  spec is number-shaped (`value_type` in `{int, float}`). The submit coerces
  + range-validates against the SettingSpec (bounds + type — the read path's
  own `coerce_value` seam) and commits through `settings.set_scalar` (the
  ADMIN-floor K7 scalar lane); an invalid / out-of-range entry rejects without
  a write. The (group, setting) ride the kernel modal-args stash restored at
  submit (the ai `settings_number_submit` precedent). The widget refreshes in
  place showing the new current.
- The bool toggle (S1) + enum select (S2) stay live; reset keeps clearing
  number settings through `settings.clear_scalar` (the S0 reset select is
  type-agnostic).
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Unit tests: a number setting opens the modal widget; a valid submit persists
  the scalar via `set_scalar`; an invalid / non-numeric / out-of-range submit
  is rejected without a write; reset clears a number setting.
- Golden: `parity/goldens/settings/group_edit_number_write.json`, minted
  honestly via the oracle-replay path.

## Result

[[fill: outcome + evidence on completion]]

## 💡 Session idea

[[fill: one genuine idea on completion]]

## ⟲ Previous-session review

[[fill: one-line remark on the S2 session on completion]]
