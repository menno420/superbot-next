# 2026-07-19 — settings epic S3: the number-modal edit widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

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

Landed the S3 number-modal edit widget on PR #581. Picking an `int` / `float`
setting in the `settings.group_edit` Edit select now opens the number-modal
widget `settings.group_edit_number` (`sb/domain/settings/panels.py`
`settings_group_edit_number_spec` + `_group_edit_number_fields` provider; the
new `_is_number_spec` helper + the `_NUMBER_MODAL` G-10 `ModalSpec`), whose
"Enter a number…" button ISSUES the numeric modal. On submit, the typed value
coerces + range-validates against the `SettingSpec` through the read path's own
`coerce_value` seam (bounds + type) and commits through the existing K7
`settings.set_scalar` lane (`sb/domain/settings/handlers.py` `group_edit_pick`
number branch + `group_edit_number_submit` / `group_edit_number_back` handlers
+ the `_refresh_group_edit_number` in-place refresh) — no new op minted. An
invalid / non-numeric / out-of-range entry rejects without a write. The
(group, setting) ride the kernel modal-args stash restored at submit (the ai
`settings_number_submit` precedent) — no parallel session dict. Bool (S1) +
enum (S2) stay live; number reset keeps clearing through `settings.clear_scalar`
(the S0 reset select is type-agnostic). Option-A boundary preserved (the 5 hub
arms + `games` untouched). Manifest snapshot recompiled (49 manifests). Golden
`settings_group_edit_number_write.json` minted honestly via the oracle-replay
path (`moderation.warn_threshold` int, bounds 1-50 → `5`; the `settings`
db_delta writes `warn_threshold=5`; step-3 issues the type-9 modal, step-4
submits + commits). Golden corpus 529 → 530 (minted 67 → 68); count-pins
resynced in `test_check_parity_depth.py` + `test_replay_adapter.py`.
Targeted `python3 -m pytest tests/unit/settings_band/` — **131 passed**;
`test_check_parity_depth.py` + `test_replay_adapter.py` (count-pins) +
`test_band6_settings_panels.py` green; `check_symbol_shadowing` / `namespace` /
`no_skip` / `config_usage` / `check_orphan_pendings` clean. The full
`--ignore=examples` corpus + golden-parity replay is left to CI's authoritative
gates on the PR (a local full run under a single Postgres deadlocks against the
parity gate — the 19 apparent race failures there were the `DATABASE_URL`
parity-DB export leaking into the runtime-DB integration race tests, confirmed
env-only by a clean-env re-run of `test_mining_repair_race.py`).

## 💡 Session idea

The stash-carried modal is the missing third shape in the two-step-widget
playbook. S2's idea framed enum/channel/role as "child session-view whose OPEN
args bake the running selection." A MODAL widget can't be opened FROM a select
(selects auto-defer), so it needs a button to intermediate AND a place to keep
the (group, setting) across the modal round-trip — the kernel modal-args stash
(keyed per form × user × originating-message) is exactly that place, and it
round-trips faithfully in the parity replay as long as the golden drives the
issuing click before the submit step (the stash is process memory, populated at
modal-issue). So the playbook line should read: "a modal edit widget is a child
session-view + an issuing button; its selection rides the modal-args STASH (not
the open args), and its golden needs BOTH the issue click and the submit step
so the stash is populated at capture." Worth pinning next to the S0/S2 notes,
because S4 (free-text modal) follows this shape verbatim while S5/S6
(channel/role selects) follow S2's — the two shapes are now both documented.

## ⟲ Previous-session review

S2 (enum) cut the frame so cleanly that S3 slotted in as one more `is_*_spec`
dispatch arm with zero churn to the shared `group_edit_pick` / `_group_edit_
current` / reset seams — the `_is_enum_spec` predicate + child-panel-with-baked-
args pattern generalized to `_is_number_spec` for free. S2's own note about
keeping the `test_check_parity_depth.py` and `test_replay_adapter.py` count-pins
in sync was the right call — both were already aligned this slice, so the +1
resync landed in both without archaeology.
