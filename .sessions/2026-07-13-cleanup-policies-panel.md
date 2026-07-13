# 2026-07-13 — cleanup: port the 🧹 Cleanup Policies panel (the last reachable cleanup pending)

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · completeness-remainders lane
  (claim `control/claims/completeness-remainders.md`, item 2 residue —
  the `cleanup.policies_pending` terminal PR #408 deliberately left;
  branch `claude/cleanup-policies-panel` off main @ 1eab517)

## Scope

Port the cleanup hub's 🧹 **Cleanup Policies** button — today the ONE
remaining reachable pending (`cleanup.policies_pending`,
sb/domain/cleanup/panels.py hub spec, persistent `cleanup:policies`) —
onto the declared panel grammar, oracle-verbatim.

Oracle source (LOCAL clone /home/user/superbot @ `9776401`):
`disbot/views/cleanup/policy_panel.py` (783 lines) over
`disbot/services/cleanup_diagnostics.py` + `services/cleanup_levels.py`:

1. **Diagnostics** (read-only): every stored `cleanup_policies` row named
   back to its level, stale-scope + ineffective-legacy-row flags, the
   Command Access disambiguation tip, level counts.
2. **Presets builder**: scope select (guild/category/channel) → target
   pick → level select (Off/Light/Standard/Strict/Custom…) → **dry-run
   preview** (real-resolver current vs after + warnings) → confirm →
   audited apply.
3. **Custom builder**: 3 pickers (delete-after duration, invalid Y/N,
   failed Y/N) → same preview + audited apply.
4. **Remove flow**: stored-row select (flags legacy/stale) → audited
   remove.

**Scope decision: FULL port** — every leg fits existing engine seams,
no new engine capability needed:

- audited writes: the live K7 `governance.set_cleanup` /
  `governance.remove_cleanup` ops via the
  `sb/domain/governance/service.py` wrappers (write + audit in one txn,
  post-commit cache invalidation) — the wizard slice armed them;
- dry-run preview: the REAL `sb.domain.governance.cleanup.
  resolve_cleanup_policy` resolver (preview == runtime, never a
  reimplementation — the oracle doctrine, carried);
- level vocabulary: `sb.domain.setup.cleanup.LEVELS` +
  `cleanup_scope_id` imported (the oracle's single-source-of-truth
  doctrine — setup/** untouched); `level_for_columns` inverse added
  locally in the new policy service;
- native channel pick: `SelectorKind.CHANNEL` (the D-0070 ledgered
  lane); the CATEGORY pick rides the roster-fed string select — the
  D-0070(a) LEDGERED engine posture (the engine's native picker is
  text-channel-typed), not a new decision;
- channel/category names + stale detection: the ai guild-scope roster
  port (`install_guild_scope_roster`) via a NEW public accessor
  `guild_scope_roster()` on sb/domain/ai/policy_widgets.py (the
  cross-domain import class the repo already carries); an uninstalled/
  empty roster degrades to mention labels + NO staleness flags (never a
  false ⚠️ in headless replay);
- the multi-page chained flow: the ai policy/behavior/tools page-swap
  precedent (`open_panel` + session args) replaces the oracle's
  ephemeral-message chain — each sub-page carries a ↩ Back to Policies
  route (the never-strand posture the ai pickers set).

Planned shape:

- `sb/domain/cleanup/policy_service.py` — cleanup_diagnostics.py port
  (rows/diagnostics/preview dataclasses, collect/preview/apply/remove).
- `sb/domain/cleanup/policy_panels.py` — 8 PanelSpecs:
  `cleanup.policies` (diagnostics + 🔧/🗑️/🔄, persistent
  `cleanup_policy:build|remove|refresh` verbatim), `policies_scope`,
  `policies_channel_pick`, `policies_category_pick`, `policies_level`,
  `policies_custom`, `policies_preview` (✅ Apply / ✖ Cancel),
  `policies_remove`; `cl_pol_`-prefixed action/selector ids (K1
  repo-global claims — the cl_refresh precedent).
- `sb/domain/cleanup/policy_widgets.py` — the pick/apply/remove
  handlers + option providers.
- Hub `policies` button repoints `cleanup.policies_pending` →
  `PanelRef("cleanup.policies")`, byte-neutral vs
  goldens/cleanup/sweep_cleanup (the Dex-button repoint precedent);
  the pending RETIRES (trap 12a).
- Manifest: the new specs join sb/manifest/cleanup.py;
  manifest.snapshot.json recompiled; compat pin regenerated if the new
  persistent roots move it (the #408 procedure).
- Golden per D-0073: `!cleanup` → click 🧹 Cleanup Policies →
  diagnostics render, minted via the canonical capture path,
  double-captured byte-identical ×2; corpus pins re-summed at all four
  sites (parity.yml + test_replay_adapter.py +
  test_check_parity_depth.py ×2 — the #410 collision pattern watched).
- Unit tests: new band6 file + the two stale pins in
  tests/unit/band6/test_band6_cleanup_panels.py (lines 81/232) flipped.

## Verification

(filled at close-out)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out)
