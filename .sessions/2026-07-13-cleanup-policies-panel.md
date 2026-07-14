# 2026-07-13 — cleanup: port the 🧹 Cleanup Policies panel (the last reachable cleanup pending)

> **Status:** `complete`

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

Shipped as PR #411 (`claude/cleanup-policies-panel` @ 9e6e36e, off main
@ 1eab517 — origin/main did not move during the slice, no merge needed):

- `python3 -m pytest tests/ -q` (local Postgres DOWN — the banner-test
  posture): **2821 passed, 15 skipped**.
- `python3 tools/run_golden_parity.py --gate` (local Postgres up):
  **GREEN — all 494 golden(s) across 50 ported subsystem(s) replay
  clean**, including the new `cleanup_policies_open` (minted via the
  canonical D-0073 capture path, double-captured across fresh harness
  boots — byte-identical ×2; pins the hub open + the 🧹 click editing
  into the empty-state diagnostics embed with the persistent
  `cleanup_policy:build/remove/refresh` trio + the `nav:back:cleanup.hub`
  route; a pure read — no `cleanup_policies` db_delta).
- `tools/check_parity_depth.py` OK (494); `manifest_compile` green
  (sha 99a39ac5…); `check_compat_frozen` regenerated (--write, the new
  persistent `cleanup_policy:*` roots — the #408 procedure) then OK;
  namespace / shadowing / no-skip / config-usage clean.
- `bootstrap.py check --strict`: green modulo this card's designed
  born-red hold (flips with this commit) + one pre-existing
  claims-format advisory (control/claims/mining-write-parity-lane.md,
  not this lane's file).
- FULL port — no deferred legs. Fidelity deltas are ledgered engine
  idioms only (page-swap chain + ↩ Back routes, roster category select
  per D-0070(a), engine authority grammar for the admin re-checks);
  nothing for docs/question-router.md.
- COUNT-PIN CORRECTION for successors: the corpus pins are FIVE call
  sites, not the four the #410 card listed — parity.yml
  (`minted_goldens` + the on-disk arithmetic comment),
  test_replay_adapter.py (docstring + `golden_count`),
  test_check_parity_depth.py ×3 (`len(goldens)`, the "N goldens" output
  byte, AND `source["minted_goldens"]` — the one the four-site list
  missed; this session found it as a post-mint test red).

## 💡 Session idea

`grep -rn "== 493"` before minting would have found all five pin sites
up front; instead the fifth (`source["minted_goldens"] == 31`) surfaced
as a full-suite red AFTER the bump. Until #410's derive-don't-pin idea
lands (single authoritative triple in parity.yml + tests asserting
against IT — still the right structural fix), the cheap interim guard
is one test that greps the tree for the literal corpus count and fails
listing every site when they disagree — turning the scavenger hunt into
a single red with a checklist. Guard recipe: extend
tests/unit/parity_gate/test_check_parity_depth.py with a
count-pin-coherence test over parity.yml `minted_goldens` +
`_golden_counts()`.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-fishing-howtofish.md` @ 1eab517, PR #410.)
Load-bearing and accurate: its Postgres-DOWN pytest posture, its
mint-ledger paragraph (the direct template for this card's golden
entry), and its double-capture-×2 discipline all transferred verbatim.
Its 💡 (derive the corpus counts, don't pin them) was proven right
AGAIN within hours — this session hit the exact collision class it
predicted, plus a fifth pin site its own four-site enumeration missed
(corrected above), which strengthens rather than weakens its argument:
prose enumerations of pin sites go stale the moment a new test pins the
same number. Its previous-session review's "third re-invention — build
the tool" call on `tools/mint_golden.py` is now a FOURTH re-invention
(this session's scratch mint script); the tool remains unbuilt and
remains the single highest-leverage small build on this corpus.
