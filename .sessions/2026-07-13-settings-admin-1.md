# 2026-07-13 — settings admin slice 1: arm the hub diagnostics

> **Status:** `complete`

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

Two of the three sub-panels needed full renderer overrides whose ONLY
job is footer text (the needs-setup coverage count, the invalid-view
conditional footer). A declared `footer_provider` facet on `PanelSpec`
— a callable resolved like a FieldsBlock provider, feeding just the
footer slot — would let dynamic/conditional footers stay declarative
and retire the override-for-a-footer pattern before more read-only
diagnostic panels copy it.

## ⟲ Previous-session review

This previous-session review covers the setup-wizard successors
(#397/#398): their oracle-verbatim port discipline and the PR #375
route-swap precedent (frozen `settings_hub.*` custom_ids, only
server-side HandlerRef → PanelRef moves) transplanted onto this lane
with zero re-derivation — the seams were exactly where their PR bodies
said. One friction: retiring a pending terminal still means
hand-editing the band6 panels-tuple test every time; a
membership-style assertion would stop that churn.
