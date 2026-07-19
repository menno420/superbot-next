# 2026-07-19 — settings epic S2: the enum-select edit widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

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

Landed the S2 enum-select edit widget on PR #580. Picking a str-with-
`allowed_values` setting in the `settings.group_edit` Edit select now opens
the windowed enum picker `settings.group_edit_enum`
(`sb/domain/settings/panels.py` `settings_group_edit_enum_spec` +
`_group_edit_enum_fields` / `_group_edit_enum_options` providers; the new
`_is_enum_spec` / `_group_edit_current` helpers), of the declared choices with
the current value pre-marked (`default=True`, description "current" — the
oracle `build_enum_select_view` shape). Picking a value commits the chosen
member through the existing K7 `settings.set_scalar` lane
(`sb/domain/settings/handlers.py` `group_edit_pick` enum branch +
`group_edit_enum_pick` / `group_edit_enum_back` handlers + the
`_refresh_group_edit_enum` in-place refresh) — no new op minted. The S1 bool
toggle stays live; enum reset keeps clearing through `settings.clear_scalar`
(the S0 reset select is type-agnostic). Option-A boundary preserved (the 5 hub
arms + `games` untouched). The group + setting ride the session-minted child
args (`GROUP_EDIT_PARAM` / the new `GROUP_EDIT_SETTING_PARAM`) — no parallel
session dict. Golden `settings_group_edit_enum_write.json` minted honestly via
the oracle-replay path (`moderation.warn_escalation_action` → `kick`; the
`settings` db_delta writes `moderation_warn_escalation_action=kick`). Manifest
snapshot recompiled (49 manifests). `python3 -m pytest --ignore=examples`:
**3540 passed, 15 skipped**; golden-parity gate **GREEN (529/529, 50
subsystems)**; `check_orphan_pendings` / `symbol_shadowing` / `namespace` /
`no_skip` / `config_usage` clean.

## 💡 Session idea

An intermediate-selection widget (enum, and the coming channel/role S5–S6)
doesn't need a parallel session dict OR a parent-message handle — it opens as
its OWN session-view child whose OPEN args bake the running selection (the
picked setting name) alongside the S0 group axis, so the value click carries
its full `(group, setting)` context for free and refreshes ITSELF in place.
This inverts the oracle's "ephemeral followup that edits the parent" into
"child session-view that refreshes itself" — no parent-message threading, no
side table, and the never-strand fence is met by a handler-Back that re-opens
the parent with its own baked group. S3's number modal and S4's text modal can
follow the same shape (a `ModalSpec` on a child session-view keyed by the
minted-child args), so S3–S7 each add one axis to the open args rather than a
new session-state mechanism. Worth a line in the panels playbook next to the
S0 note: "a two-step edit widget is a child session-view, not a followup — its
open-time selection rides the minted-child args and it refreshes itself."

## ⟲ Previous-session review

The S0 session (settings.group_edit frame + S1 bool) built the exact seam this
slice needed: its `group_edit_pick` already dispatched by SettingSpec type with
an honest "ports in a later slice" degrade, so S2 slotted in as one more branch
with zero frame churn — the mark of a well-cut slice boundary. One small drift
to note for the next hand: S0's `+2` mint was recorded in
`test_check_parity_depth.py`'s count-pin prose but not in
`test_replay_adapter.py`'s enumeration (only the number was bumped there); I
extended both blocks this slice (S0's `+2` and S2's `+1`), so the two
narrations are back in sync.
