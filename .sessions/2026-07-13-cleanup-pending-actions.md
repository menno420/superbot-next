# 2026-07-13 — cleanup admin residue: the reachable pending actions port

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · completeness-remainders lane
  (claim `control/claims/completeness-remainders.md`, item 2 — cleanup
  admin residue; branch `claude/cleanup-pending-actions` off main
  @ a49d934)

## Scope

The completeness table's cleanup row is stale (`logging_pending` retired
with PR #333); the TRUE reachable-pending set, re-derived at HEAD and
verified bound to live panel buttons:

1. `cleanup.settings_pending` — the hub's ⚙️ Settings button
   (sb/domain/cleanup/panels.py:209, persistent `cleanup:settings`).
   Oracle: cogs/cleanup/panel.py `btn_settings` → the SubsystemSettingsView
   page for `cleanup` (views/settings/subsystem_view.py) — one scalar
   (`spam_window_seconds`, numeric_presets 10/15/30, cogs/cleanup/
   schemas.py) + the Domain-configuration discovery field. Port: the
   `ai.settings` precedent (panel + edit/reset selects + the
   numeric-presets widget page + Override… G-10 form) over the audited
   K7 `settings.set_scalar` lane.
2. `cleanup.anti_evasion_pending` — the words manager's 🛡️ Anti-evasion
   button (panels.py:299). Oracle: cleanup_cog.py `_WordMenuView.btn_strict`
   → `prohibited_words_service.set_wordfilter_strict` (migration 097
   `wordfilter_config`) + in-place re-render. Port: migration 0053 +
   store + audited K7 op + toggle handler; the words manager's
   `Current Words` / anti-evasion field literals flip to LIVE reads
   (the deferred word-mutation-slice leftover — runner reseeds the
   capture word-cache trajectory for `sweep.wordmenu` so the golden
   stays green, the sweep.word_list precedent).
3. `cleanup.policies_pending` — the hub's 🧹 Cleanup Policies button
   (panels.py:214, `cleanup:policies`). Oracle: views/cleanup/
   policy_panel.py (784 lines): diagnostics embed + presets builder
   (scope select → native channel/category selects → level select →
   dry-run preview → confirm apply) + custom builder + remove flow over
   services/cleanup_diagnostics + the governance pipeline. **Left
   honestly pending** — decision-sized: its own multi-view slice
   (chained ephemeral select flows, channel-directory reads for
   stale-scope diagnostics, D-0054-style confirm surfaces); the
   governance seams exist (sb/domain/governance store/service cleanup
   lanes) but the surface is a full lane slice, not a residue action.

Definition of done: 1–2 implemented + unit-tested, manifest snapshot
recompiled, goldens green (sweep_wordmenu via the reseed lane), full
pytest + `bootstrap.py check --strict` green, PR opened (never
self-merged), 3 flagged in card + PR body.

## 💡 Session idea

(filled at close)

## ⟲ Previous-session review

(filled at close)
