# 2026-07-13 — cleanup admin residue: the reachable pending actions port

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · completeness-remainders lane
  (claim `control/claims/completeness-remainders.md`, item 2 — cleanup
  admin residue; branch `claude/cleanup-pending-actions` off main
  @ a49d934, merged forward to 100df5f; PR #408)

## Scope

The completeness table's cleanup row was stale (`logging_pending` retired
with PR #333); the TRUE reachable-pending set, re-derived at HEAD and
verified bound to live panel buttons:

1. `cleanup.settings_pending` — the hub's ⚙️ Settings button
   (sb/domain/cleanup/panels.py, persistent `cleanup:settings`). Oracle:
   cogs/cleanup/panel.py `btn_settings` → SubsystemSettingsView("cleanup")
   (views/settings/subsystem_view.py @9776401) — one scalar
   (`spam_window_seconds`, numeric_presets 10/15/30, cogs/cleanup/
   schemas.py) + the Domain-configuration discovery field.
2. `cleanup.anti_evasion_pending` — the words manager's 🛡️ button.
   Oracle: cleanup_cog.py `_WordMenuView.btn_strict` →
   `set_wordfilter_strict` (migration 097 `wordfilter_config`) +
   in-place re-render.
3. `cleanup.policies_pending` — the hub's 🧹 Cleanup Policies button.
   Oracle: views/cleanup/policy_panel.py (784 lines — diagnostics +
   presets builder + custom builder + remove flow).

## What shipped (PR #408)

1 and 2 landed oracle-verbatim; 3 stays the ONE declared honest terminal
(decision-sized: its own multi-view slice; the governance
`cleanup_policies` seams it needs already exist in next — flagged in the
PR body as a follow-up claim).

- `cleanup.settings` + `cleanup.settings_edit_presets` panels (the
  ai.settings precedent) + `sb/domain/cleanup/settings_{schema,widgets}.py`
  over the audited K7 `settings.set_scalar` lane; the manifest settings
  facet corrected to the shipped schema bytes (bounds 1..300, presets
  10/15/30 — the old stub carried (1,3600) and no presets). `cl_`-prefixed
  action ids: `back_to_hub`/`open_panel`/`preset_N`/`override_btn` are
  ai's repo-global K1 claims (the cl_refresh precedent).
- migration 0053 `wordfilter_config` (+ checksum) + store pair + audited
  `cleanup.wordfilter_strict_op` + the toggle handler (in-place
  re-render; text confirm degrade).
- Words manager fields flipped LIVE (Current Words cache read + strict
  flag + the shipped empty-state description);
  `CAPTURE_WORLD_WORD_CACHE["sweep.wordmenu"]` reseeds the capture
  trajectory so the imported golden's `test` byte replays green.
- MINTED golden `cleanup/cleanup_anti_evasion_toggle_write.json` (D-0073
  capture_case procedure; local Postgres) — the first row-bearing
  `wordfilter_config` capture. Corpus pins 491→492; parity.yml
  `minted_goldens` 29→30 with the ledger paragraph.
- Verify: `python3 -m pytest tests/ -q` → 2775 passed, 15 skipped
  (post-merge of origin/main @ 100df5f); `tools/run_golden_parity.py
  --gate` → GREEN, all 492 goldens across 50 ported subsystems;
  `bootstrap.py check --strict` → green modulo this card's designed
  born-red hold + one pre-existing advisory
  (control/claims/mining-write-parity-lane.md, not this lane's file).

## 💡 Session idea

Minting a D-0073 golden required hand-rolling a scratch script around
`sb.adapters.parity.runner.capture_case` (boot Harness → capture → write
`golden_path`). A `tools/mint_golden.py --case <id>` one-liner (case from
CURATED_CASES, refuses to overwrite without `--force`, prints the
db_delta tables it pinned) would turn the procedure's riskiest manual
step into a reviewed tool — every write-parity lane since D-0073 has
re-invented this script.

## ⟲ Previous-session review

Previous lane card (.sessions/2026-07-13-settings-admin-3.md, PR #401):
clean and accurate — its "reuse the live K7 lanes, never re-mint" posture
transferred directly (this slice re-used `settings.set_scalar` and the
word-op runner shape without new write lanes). Its 💡 (an engine-owned
`refresh_after` facet for mutation handlers) would have deleted BOTH
hand-rolled refresh tails this session wrote (the toggle's and the
widgets'); still unbuilt, still worth picking up. One friction it
predicted materialized again: the retired-terminal rename rippled into
the band-6 test file's burn-down list — the cross-slice test-churn
pattern it flagged remains unaddressed.
