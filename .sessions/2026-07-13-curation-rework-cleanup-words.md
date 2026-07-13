# 2026-07-13 — curation rework: cleanup words panel + logging nav (ORDER 017 item 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · NIGHT-RUN curation rework · mandate: ORDER 017
  item 2 (curation review chunk 3, PR #327)

## Scope

Wire the `cleanup.words` panel's pending-terminal buttons to their live
targets, plus the `cleanup.hub` 📝 Logging Status nav:

1. `word_add` / `word_remove` — button → modal → the live
   `cleanup.word_add_op` / `word_remove_op` command-twin workflows
   (goldens sweep_word_add / sweep_word_remove; the moderation.hub.warn
   modal-ingress precedent).
2. `scan_history` — the live `cleanup.history_scan` handler
   (`!cleanuphistory` is the command front door).
3. `word_refresh` — one-liner REFRESH_PANEL nav (the `cl_refresh` pattern).
4. `cleanup.hub` logging button — nav to `panel:logging.hub` (the
   server-logging successor slice already landed).

Files: `sb/domain/cleanup/panels.py`, `sb/domain/cleanup/handlers.py`,
`tests/unit/band6/test_band6_cleanup_panels.py`, `manifest.snapshot.json`
(recompiled). DO NOT touch server_management / mining / utility / btd6
panels (sibling rework PRs own those).

## What shipped

All four items landed — none dropped (each verified still-pending at HEAD
`291361d`; no claim/PR collision on sb/domain/cleanup):

- `sb/domain/cleanup/panels.py` — two G-10 ModalSpecs
  (`cleanup.word_add_form` / `word_remove_form`, single `word` field
  feeding `ops._word_from`), ➕/➖ rewired `defer_mode=MODAL` →
  `WorkflowRef(cleanup.word_add_op/word_remove_op)`; 🔄 →
  `PanelRef("cleanup.words")` + REFRESH_PANEL; 🔍 →
  `HandlerRef("cleanup.history_scan")`; hub 📝 → `PanelRef("logging.hub")`.
- `sb/domain/cleanup/handlers.py` — 5 retired pending terminals pruned
  (settings / policies / anti_evasion stay honest pending).
- `tests/unit/band6/test_band6_cleanup_panels.py` — wiring assertions
  (modal ids/fields/on_submit, refresh render mode, live scan route, hub
  logging nav) + a retired-refs-are-gone burn-down pin.
- `manifest.snapshot.json` recompiled (`manifest_compile --write`);
  `compat/compat-frozen.json` regenerated (+2 modal-id custom-id roots,
  CODEOWNERS-routed — owner sign-off carried by the PR by design).
- Verify: `pytest tests/ -q` → 2058 passed, 13 skipped; check_namespace /
  check_runtime_smoke / check_compat_frozen / check_sim_gate /
  check_escape_hatches / check_slash_cap / check_parity_depth /
  check_symbol_shadowing / check_no_skip / check_config_usage all OK.
  Goldens untouched (sweep_cleanup / sweep_wordmenu pin labels/styles/ids
  only — handler refs are not wire bytes).

Deliberate leave-behinds: the words manager's `Current Words`/anti-evasion
field literals stay the golden-pinned under-port (a live read would redden
sweep_wordmenu replay) — the word-mutation slice owns the live-read flip.

## 💡 Session idea

Shared-checkout collision guard: two night-run workers sharing one clone
race on `git checkout -B` — this session's first commit landed on a
sibling's branch (`claude/curation-rework-btd6-paragon`) because the
sibling switched HEAD between my checkout and commit. Guard recipe: make
`git worktree add /home/user/sb-<slug> <branch>` the FIRST step of every
parallel lane (the nav-wiring sibling already does this); candidate for a
one-liner in docs/AGENT_ORIENTATION.md § "Start every session" so the
convention is planted, not rediscovered per session.

## ⟲ Previous-session review

Previous session (completeness table, PR #326 — `.sessions/2026-07-13-
completeness-table.md`): clean card, and its headline claim ("every flag
is a declared-honest pending terminal, not a silent gap") held exactly for
this slice — all 5 cleanup terminals were declared + honest, which made
the rework mechanical. Its 💡 (mechanize the sweep as
`tools/check_completeness.py`) is still unbuilt and would have shaved this
session's verification pass too — worth picking up.
