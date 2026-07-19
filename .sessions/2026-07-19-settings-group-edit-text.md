# 2026-07-19 — settings epic S4: the free-text modal edit widget

> **Status:** `in-progress`

- **📊 Model:** [[fill: family-level model line, no exact id]]

## Scope

Execute **slice S4** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
free-text edit modal (`disbot/views/settings/edit_text.py` +
`subsystem_view.dispatch_edit_setting` free-form-string arm @ `menno420/superbot
f87fa508`) onto the shipped `settings.group_edit` page frame (S0, PR #579;
S2 enum, PR #580; S3 number, PR #581). Picking a `str`-without-`allowed_values`
scalar in the Edit select opens a session-view child
(`settings.group_edit_text`) whose button ISSUES a G-10 `ModalSpec`
free-text-input modal; the submit validates (non-empty + declared `bounds`
max-length per the SettingSpec) and commits the entered string through the
existing `settings.set_scalar` K7 op — no new op minted.

Stacked on S3 (#581): the text branch was cut from the pre-merge S3 branch;
S3 squash-merged into `main` before the first push, so the branch was rebased
`--onto origin/main` and the PR base is `main` with a clean text-only diff.

Deliverables:
- The `settings.group_edit_text` widget panel: a session-view child whose
  single button issues the ported `TextSettingModal` (a one-input free-text
  modal), opened from the `settings.group_edit` Edit select when the picked
  spec is free-text-shaped (`value_type == str` AND no `allowed_values`). The
  submit rejects an empty value and a value over the declared `bounds`
  max-length (`(max_len,)` for str), and commits through `settings.set_scalar`
  (the ADMIN-floor K7 scalar lane); a rejected entry writes nothing. The
  (group, setting) ride the kernel modal-args stash restored at submit (the S3
  `group_edit_number_submit` precedent). The widget refreshes in place.
- The bool toggle (S1) + enum select (S2) + number modal (S3) stay live; reset
  keeps clearing text settings through `settings.clear_scalar` (the S0 reset
  select is type-agnostic).
- Preserve the option-A boundary: the 5 operator-spine hub arms + the `games`
  panel arm untouched.
- Compat-frozen §5.3 pin amended for the new `settings.group_edit_text_form`
  modal custom_id (via `tools/check_compat_frozen.py --write`).
- Unit tests: a text setting opens the modal widget; a valid submit persists
  the scalar via `set_scalar`; an empty / over-length submit is rejected
  without a write (with the error copy); reset clears a text setting.
- Golden: `parity/goldens/settings/group_edit_text_write.json`, minted
  honestly via the oracle-replay path.

## Result

[[fill: result narrative]]

## 💡 Session idea

[[fill: one genuine idea]]

## ⟲ Previous-session review

[[fill: one-line review remark on the S3 session]]
