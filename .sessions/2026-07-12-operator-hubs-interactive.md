# 2026-07-12 — arm the operator hubs' read-only navigation (SLICE 4)

> **Status:** `in-progress`

- **📊 Model:** Claude Opus 4.8 · high · feature build (SLICE 4 — operator hubs to interactive "where cheap")

## Scope

The operator-hub analog of the shipped help-hub category-select (D-0055):
give the operator surfaces a CHEAP + SAFE read-only interactive win, no
state mutation. Independent of the D-0034 browse lane (base = `main`).

## Step A — ASSESS (oracle gate, done FIRST)

Read `sb/domain/operator_spine.py` — the shared read-only hub (`hub_spec`
builds TextBlock + FieldsBlock over the K7 settings, NO action/menu
components; `pending_handler` returns BLOCKED). Enumerated the subsystems
that render it via `ensure_hub`: **welcome, counters, security, automod,
image_moderation** (5). These `.hub` panels are registered but ORPHANS —
nothing routes to them, no golden touches them.

Oracle (`menno420/superbot`, read via raw):
- `disbot/views/settings/hub.py` `SettingsHubView` — a "Open a settings
  group…" subsystem SELECT that NAVIGATES (read-only, does NOT mutate) to
  each group's `SubsystemSettingsView`; plus diagnostic buttons (navigate)
  and a Command-access door (mutation).
- The per-group `SubsystemSettingsView` carried the scalar edit + reset
  controls — the MUTATION surface.

Interactivity split:
- **CHEAP + SAFE (read-only)**: the group-select NAVIGATION. Already
  ported into `settings.hub` (`subsystem_select`, custom_id
  `settings_hub.subsystem_select`) but collapsed to the
  `settings.group_pending` BLOCKED terminal. Arming it to open the
  read-only operator hub restores the oracle navigation as a faithful
  READ SUBSET.
- **WRITE-SEAM-GATED (mutation, DEFERRED)**: the per-group scalar
  edit/reset (`SubsystemSettingsView`), the Command-access door, the
  explorer legs. These need the audited settings-mutation endpoint
  (`sb/domain/settings/ops.py` `SettingsMutationPipeline` exists; the
  PANEL port is not armed). NOT built here.

**Verdict: PROCEED** — arm the group-select navigation to the 5 read-only
operator hubs; groups without one keep the pending terminal. No mutation.

## Plan

- `operator_spine.py`: a read-only registry of ensured hubs
  (`has_operator_hub`) populated by `ensure_hub`.
- `settings/handlers.py`: a read-only `settings.open_group` handler —
  open `<group>.hub` when `has_operator_hub(group)`, else the unchanged
  BLOCKED fallback. Mirrors `help.open_category` (select → open_panel).
- `settings/panels.py`: repoint `subsystem_select.on_select`
  `settings.group_pending` → `settings.open_group` (custom_id unchanged →
  zero render churn).
- Golden posture: ZERO churn — no golden clicks the select (goldens pin
  the rendered component, not its route); the wire custom_id is unchanged.
- Tests: mirror the help select-handler tests + the settings panel tests.

## ⟲ Previous-session review

(pending — filled at close-out)

## ⚑ Flags

- **Write-seam-gated (deferred):** the per-group scalar edit/reset
  (`SubsystemSettingsView`) is a MUTATION surface — it needs the audited
  settings-mutation panel port (not the read-only nav armed here). Groups
  without a read-only operator hub keep the `settings.group_pending`
  terminal.
- **Presentation sign-off:** the oracle group-select opened the FULL
  settings page (read + edit); this arms the READ SUBSET (the operator
  read-only hub). Same navigation gesture, edit controls deferred.
- **Oracle copy provenance:** the group roster + select copy are the
  already-shipped `settings.hub` bytes (goldens/settings pin them); the
  navigation gesture is `SettingsHubView` (raw fetch, path in the PR).

## 💡 Session idea

The remaining settings groups (proof_channel, role, cleanup, moderation,
logging, ai, economy…) will light up the SAME select the moment each
gains a read-only operator hub OR the settings-mutation panel port arms
the full edit page — the router is already data-driven
(`has_operator_hub`), so no handler change is needed, only new hubs.
