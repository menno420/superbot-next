# 2026-07-13 — curation rework: arm the settings.access explorer (rows 82-87)

> **Status:** `complete`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  rows 82-87 (`docs/review/curation-report-2026-07-13.md` L1237-1242),
  claim `control/claims/settings-access-rework.md` (PR #374), token
  `claude/rework-settings-access`.

## Scope

Arm the six pending controls of the Settings → Access explorer
(`sb/domain/settings/panels.py` `settings_access_spec()`): subsystem
select, scope select, explain, reset, prev/next paging. The pending copy
named `governance.resolve_subsystem_state`, which did not exist at HEAD —
build it honestly. Explorer-open golden
(`parity/goldens/settings/sweep_settings_access.json`) must replay
byte-identical.

## What shipped

All six controls armed (6/6 — reset included):

- **Read seam** — `resolve_subsystem_state` in
  `sb/domain/governance/service.py` (+ `SubsystemResolution`/`ScopeCheck`
  frozen shapes): resolved state + provenance for one subsystem over the
  REAL access resolve chain — scope-chain `subsystem_visibility` rows
  (thread > channel > category > guild) → registry default, with
  hard-dependency propagation. Same store read + chain walk as
  `resolve_visibility` (composes `_resolve_single_subsystem` +
  `apply_dependency_rules`), so the diagnostic can never drift from the
  dispatch gate. Placement: domain/governance (it owns the visibility
  store); domain/settings calls it LAZILY (the `sections.py` seam shape,
  PL-001) — kernel untouched. Honest-provenance note: the K7 settings-KV
  chain (per-guild → global → default) is a DIFFERENT lane that never
  gates subsystem access; provenance vocabulary here is visibility row
  vs registry default vs dependency block (documented on the dataclass).
- **Controls** (`sb/domain/settings/handlers.py`): subsystem/scope
  selects update per-message session state (`_ACCESS_SESSIONS`, keyed by
  panel message id — engine ephemeral bindings freeze opening args, so
  running state lives domain-side) and re-render in place via
  `refresh_session_view` (games-sections posture; a miss degrades to an
  honest text summary). Explain renders the walked chain verbatim
  (matched row / explicit-inherit / shadowed / no-row + registry-default
  terminus + dependency line). Prev/Next page the roster with clamped
  bounds. **Reset armed** through the sanctioned governance K7
  `SET_VISIBILITY` clear lane (`set_subsystem_visibility` with
  `enabled=None` = override delete — the games-sections Enable-all
  precedent; audited, actor WorkflowContext, administrator-tier spec
  gate) at the selected scope. Rationale: the write path already exists
  and is proven — parking reset would have been false modesty; the
  settings-mutation PARK covers the settings.hub ×5 rows (per-group edit
  UI + diagnostics), NOT the explorer (boundary confirmed against
  docs/review/admin-surface-audit-2026-07-12.md §4.2).
- **Renderer/provider** (`sb/domain/settings/panels.py`):
  `_access_fields` + `_render_access` are params-driven with the
  params-empty branches reducing EXACTLY to the shipped bytes (golden
  open state untouched); page 2 of the subsystem roster re-derives from
  the governance registry (18 remainder subsystems, curated hub labels
  where they exist, mechanical title-case otherwise — unpinned bytes,
  flagged as honest derivation, never fabricated "shipped" copy);
  selections move the `default` flag on re-render only.
- `manifest.snapshot.json` recompiled — the diff is exactly the 5
  handler-ref swaps (no new custom_ids anywhere; `check_compat_frozen`
  green without a pin amend).
- **Tests**: `tests/unit/settings_band/test_settings_access_explorer.py`
  (31 tests: seam resolution/provenance/inherit/dependency/fail-open,
  every armed control incl. degrade paths, reset scope mapping +
  failed-write, paging clamps, spec fences, explorer-open byte pin,
  page-2 roster invariants); pending-refs list updated + retired-refs
  sweep in `tests/unit/band6/test_band6_settings_panels.py`.

Verification: `python3 -m pytest tests/` — **2423 passed, 13 skipped**;
manifest_compile / check_compat_frozen / check_schema_growth + the full
23-checker fleet green; `bootstrap.py check --strict` exit 0; parity
gate **GREEN — 484 goldens / 51 subsystems** (the explorer-open golden
replays unchanged).

## 💡 Session idea

The engine's session-lifecycle panels have NO kernel home for
cross-click selection state: ephemeral bindings freeze the OPENING args,
so every stateful panel (this explorer, and any future
select-then-act surface) re-invents a domain-side
message-key → state dict + refresh_session_view params plumbing. A small
kernel `PanelSession.params` bag (updated by refresh, passed to the
renderer automatically) would delete this per-domain boilerplate and
make "selection survives re-render" an engine guarantee — worth a
design note before a third surface copies the pattern.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-curation-rework-nav-wiring.md`.) Its
"stale pending terminal" framing held here in inverted form: these six
were NOT stale (no live twin existed — the seam had to be built), which
its proposed `check_completeness.py` heuristic would correctly have
skipped; the pending-copy-names-the-seam convention
(`governance.resolve_subsystem_state`) proved load-bearing — the copy
was a buildable spec, and the seam landed under the exact promised name.
Its worktree guard recipe (parallel lanes sharing one working tree →
commits on the wrong branch) did not bite this session (single lane),
but the branch-before-first-commit discipline it prescribes was
followed. Its retired-refs-stay-gone sweep pattern was copied verbatim
into both test files touched here.
