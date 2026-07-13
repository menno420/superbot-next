# 2026-07-13 — settings admin slice 2: arm the hub audit view

> **Status:** `in-progress`

- **📊 Lane:** settings-admin, slice 2 of 3
  (branch `claude/settings-admin-2`, stacked on `claude/settings-admin-1`
  @ b7245e3 — PR #399)

## Scope

Arm the 🕒 Recent changes settings-hub button (`settings_hub.audit`) that
routes to the `settings.audit_pending` terminal today — the oracle
disbot/views/settings/audit_view.py port (last 10 settings-mutation audit
rows, DM guard + missing-table + empty-table degrades) onto the declared
panel grammar as a PanelRef open-child sub-panel, the slice-1 pattern
verbatim. The oracle's `settings_mutation_audit` table maps onto the K7
central audit spine here: `audit_log` rows with `subsystem='settings'`
(the workflow engine's `emit_central_audit` writes one row per settings
compound op — set_scalar/clear_scalar/bind/unbind), read via the btd6
D-0046 re-home precedent (domain read off the spine through the K3 pool
seam). Persistent `settings_hub.audit` custom_id stays frozen
byte-verbatim — only the server-side route moves. 🚪 Command access stays
on its honest pending terminal — slice 3 of this lane.

Definition of done: implemented + unit-tested
(tests/unit/settings_band/) + full pytest green + manifest snapshot
recompiled; goldens untouched (the hub open bytes carry no handler
routes).

## 💡 Session idea

(close-out fills this)

## ⟲ Previous-session review

(close-out fills this)
