# 2026-07-13 — settings admin slice 3: arm the hub Command Access panel

> **Status:** `in-progress`

- **📊 Lane:** settings-admin, slice 3 of 3 (FINAL)
  (branch `claude/settings-admin-3`, stacked on `claude/settings-admin-2`
  @ 93eea69 — PR #400, itself stacked on `claude/settings-admin-1`
  @ b7245e3 — PR #399)

## Scope

Arm the 🚪 Command access settings-hub button (`settings_hub.command_access`)
that routes to the `settings.command_access_pending` terminal today — the
oracle disbot/views/settings/edit_command_access.py port (PR-6: the three
mode buttons all_channels / selected_channels / disabled_except_bootstrap,
the multi-ChannelSelect allowlist replace, Back-to-Hub) onto the declared
panel grammar as a PanelRef open-child sub-panel — the slice-1/2 pattern,
plus this set's ONE write surface. All writes REUSE the live platform
command-access K7 lanes (`platform.set_access_mode` /
`platform.set_access_channels`, sb/domain/platform/command_access.py — the
setup-wizard step-8 seam, PR #397 context): audited, administrator-floor
authority, post-commit cache forget; no new write lane is minted. The
oracle's `replace_allowed_channels` atomic composite maps onto
`set_access_channels` (full DELETE + re-INSERT in one leg, implies
selected_channels when no policy row — the same shape). The oracle's
`delete_blocked_commands` toggle has NO seam in next (the policy store
carries mode + channels only) — honest under-port, mapped in the PR body.
Persistent `settings_hub.command_access` custom_id stays frozen
byte-verbatim — only the server-side route moves; the new panel's controls
are run-minted per-panel leaves. `group_pending` (the per-group edit page)
is OUT of scope and stays the honest terminal.

Definition of done: implemented + unit-tested
(tests/unit/settings_band/) + full pytest green + manifest snapshot
recompiled; goldens untouched (the hub open bytes carry no handler
routes).

## 💡 Session idea

(close-out fills this)

## ⟲ Previous-session review

(close-out fills this)
