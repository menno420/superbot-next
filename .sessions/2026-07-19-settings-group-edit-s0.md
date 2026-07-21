# 2026-07-19 — settings epic S0: the `settings.group_edit` page frame + S1 bool widget

> **Status:** `complete`

- **📊 Model:** opus · high · feature build

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

Landed the `settings.group_edit` page frame + the S1 bool toggle on PR #579.
`settings.open_group`'s non-hub arm now opens the ported page
(`sb/domain/settings/panels.py` `settings_group_edit_spec` + the
`_group_edit_*` providers/renderer; `sb/domain/settings/handlers.py` the
re-pointed `open_group` + the `group_edit_pick` / `group_edit_reset` /
`group_open_panel` handlers); the 5 hub arms + `games` are untouched (option
A, D-0097). `settings.group_pending` retired — the last orphan pending, so
`tools/check_orphan_pendings.py` `_KNOWN_ORPHANS` is now empty. Two goldens
minted honestly via the oracle-replay path (`settings_group_edit_open` +
`settings_group_edit_bool_write`, corpus 528). The read embed reproduces the
oracle `build_subsystem_embed` header/fields verbatim; the bool write
persists the `settings` row through the K7 `set_scalar` lane + refreshes in
place. `python3 -m pytest --ignore=examples`: **3531 passed, 15 skipped**;
golden-parity gate **GREEN (528/528, 50 subsystems)**; manifest snapshot
recompiled; `check_orphan_pendings` / `symbol_shadowing` / `namespace` /
`no_skip` / `config_usage` clean.

## 💡 Session idea

The selected group never needed a parallel `_GROUP_EDIT_SESSIONS` dict: it
rides the engine's `_mint_ephemeral` binding args, which bake the opening
request's args onto every session-minted child, so a click already carries
its page context (`GROUP_EDIT_PARAM`) alongside the live `values`. That is a
reusable convention for every future per-entity session panel — S2–S7 inherit
the group axis for free, and the diagnostics/command-access panels that
currently keep their own `_ACCESS_SESSIONS`-style dicts could fold onto it
where the axis is a pure open-time constant (not a running selection). Worth a
one-liner in the panels playbook: "a session-view's open-time key rides the
minted-child args, not a side table."

## ⟲ Previous-session review

The 2026-07-18 verify-C2/C3-backlog card (verify/review class) modelled
the discipline this build leaned on: it closed each hardening item by citing
the live class-killer invariant (an emptied `_ALLOWLIST` / `_KNOWN_ENSURE_ONLY`)
rather than just a PR number. S0 does the same in the other direction —
retiring the last `group_pending` orphan empties `_KNOWN_ORPHANS` to a zero
floor, so the checker now proves "no orphan pending exists" as a standing
invariant, not a one-time cleanup. Handoff read clean; no drift to reconcile.
