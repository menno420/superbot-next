# Claim — settings-group-edit-s0

- `claude/settings-group-edit-s0` · **settings epic S0 — the
  `settings.group_edit` per-group scalar-edit page frame + the S1 bool toggle
  widget wired end-to-end.** Ports the oracle `SubsystemSettingsView`
  (`disbot/views/settings/subsystem_view.py` @ `menno420/superbot f87fa508`)
  behind the audited seam: dynamic READ embed of the group's scalar values, a
  windowed "Edit a setting…" select, a windowed "Reset a setting…" select,
  Back-to-Hub + Open-Panel nav. Re-points the `settings.open_group` third arm
  from the `group_pending` BLOCKED terminal to
  `open_panel(settings.group_edit)` for NON-HUB groups only (owner option A,
  `docs/question-router.md` Answered); the 5 operator-spine hub arms + the
  `games` panel arm stay untouched (pinned by unit test). Commits ride the
  existing `settings.set_scalar` / `settings.clear_scalar` K7 ops — no new op
  minted. · files: `sb/domain/settings/panels.py`,
  `sb/domain/settings/handlers.py`, `parity/cases/curated.py`,
  `parity/goldens/settings/`, tests under `tests/unit/settings_band/` ·
  2026-07-19
