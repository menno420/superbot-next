# 2026-07-19 — settings epic S0: the `settings.group_edit` page frame + S1 bool widget

> **Status:** `in-progress`

- **📊 Model:** [[fill:model]]

## Scope

Execute **slice S0** of the settings `group_pending` epic
(`docs/design/settings-group-pending-epic-plan.md`): port the oracle
`SubsystemSettingsView` per-group scalar-EDIT page frame
(`disbot/views/settings/subsystem_view.py` @ `menno420/superbot f87fa508`)
into the superbot-next panel grammar as `settings.group_edit`, wired to at
least one live widget (S1 bool) so the slice is exercisable end-to-end (not a
dead frame).

Owner ruling **option A** (`docs/question-router.md` → Answered, 2026-07-18):
the ported edit page replaces `group_pending` for the **NON-HUB groups only**.
The 5 operator-spine hub groups (welcome / counters / security / automod /
image_moderation) keep their read-only `<group>.hub`, and the `games` panel
arm is untouched. S0 ships a unit test pinning that boundary.

Deliverables:
- The `settings.group_edit` page: a dynamic READ embed of the group's current
  scalar values (+ declared bindings / provisionable resources), a windowed
  **"Edit a setting…"** select, a windowed **"Reset a setting…"** select,
  **Back-to-Hub** + **Open-Panel** nav; the selected group rides the
  session-minted component args (the `_mint_ephemeral` binding), so no parallel
  session dict is needed.
- Re-point `settings.open_group`'s third arm from `group_pending` BLOCKED to
  `open_panel(settings.group_edit)` for non-hub groups; retire
  `group_pending` the way slices 1-3 retired the diagnostics' pending refs.
- The **S1 bool toggle**: picking a bool setting in the Edit select flips it
  through the existing `settings.set_scalar` K7 op (no new op); the Reset
  select clears through `settings.clear_scalar`.
- Unit test: non-hub `open_group` now opens `settings.group_edit`; the 5 hub
  arms + `games` arm route unchanged.
- Goldens: `parity/goldens/settings/group_edit_open.json` (page-open render)
  + `parity/goldens/settings/group_edit_bool_write.json` (the bool write),
  minted honestly via the oracle-replay path.

## Result

_(in progress — filled on flip to complete)_

## 💡 Session idea

_[[fill:idea]]_

## ⟲ Previous-session review

_[[fill:prev-review]]_
