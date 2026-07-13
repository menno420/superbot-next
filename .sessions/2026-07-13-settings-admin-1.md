# 2026-07-13 — settings admin slice 1: arm the hub diagnostics

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · settings-admin lane, slice 1 of 3
  (branch `claude/settings-admin-1`)

## Scope

Arm the three READ-ONLY settings-hub diagnostic buttons that route to
pending terminals today: 📋 Needs setup (`settings_hub.needs_setup`),
⚠️ Invalid settings (`settings_hub.invalid`) and 🔗 Missing bindings
(`settings_hub.missing_bindings`) — oracle-verbatim ports of
disbot/views/settings/needs_setup.py / invalid_settings.py /
missing_bindings.py onto the declared panel grammar (three sub-panels +
FieldsBlock providers over the K7 declaration/resolve seams and the
binding store read). Persistent `settings_hub.*` custom_ids stay frozen
byte-verbatim — only server-side HandlerRefs move (the PR #375 explorer
precedent). 🕒 Recent changes (`audit`) and 🚪 Command access stay on
their honest pending terminals — slices 2/3 of this lane.

Definition of done: implemented + unit-tested
(tests/unit/settings_band/) + full pytest green + manifest snapshot
recompiled; goldens untouched (the hub open bytes carry no handler
routes).

## 💡 Session idea

(close-out fills this)

## ⟲ Previous-session review

(close-out fills this)
