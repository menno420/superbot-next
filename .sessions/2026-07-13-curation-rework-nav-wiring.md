# 2026-07-13 — curation rework: panel nav/handler wiring (ORDER 017 item 2)

> **Status:** `complete`

- **📊 Model:** `fable-5` · NIGHT-RUN curation rework · mandate: ORDER 017 item 2 (curation report PR #327)

## Scope

The "panel nav/handler wiring" bundle from the night-run curation review
(`docs/review/curation-report-2026-07-13.md`): three trivial handler swaps
that retire 5 pending terminals whose live destinations already ship at
HEAD — no new surfaces, no wire-byte changes (every affected button's
label/style/custom_id stays golden-pinned verbatim; only the server-side
handler route moves).

1. `sb/domain/server_management/panels.py` — the hub's 🛡️ Moderation /
   🎭 Roles / 🧹 Cleanup buttons: `_pending(...)` terminals →
   `PanelRef("moderation.hub")` / `PanelRef("role.hub")` /
   `PanelRef("cleanup.hub")` (the Channels/Setup pattern in the same spec).
2. `sb/domain/mining/panels.py` — `mining.workshop.ws_back`:
   `mining.workshop_hub_pending` → `PanelRef("mining.hub")` (the `sk_hub`
   pattern).
3. `sb/domain/utility/panels.py` — `utility.panel.invite`:
   `utility.invite_pending` → the live argless
   `HandlerRef("utility.invite_view")` (the `!invite` command's route).

Excluded: cleanup panels (sibling rework lane) and btd6 paragon (own lane).

## What shipped

All three bundle items landed — none dropped (each claim re-verified
against HEAD before the swap; no open-PR/claim collision on any file):

- `sb/domain/server_management/panels.py` — the Moderation / Roles /
  Cleanup trio forwards to `moderation.hub` / `role.hub` / `cleanup.hub`;
  the three `*_pending` refs retired from
  `sb/domain/server_management/handlers.py`.
- `sb/domain/mining/panels.py` — `ws_back` → `PanelRef("mining.hub")`;
  `mining.workshop_hub_pending` retired from
  `_workshop_button_handlers()` (the craft-select terminal stays, D-0043).
- `sb/domain/utility/panels.py` — 🔗 Invite → `utility.invite_view`;
  `utility.invite_pending` + `_INVITE_DOWN` retired from
  `sb/domain/utility/handlers.py`.
- `manifest.snapshot.json` recompiled (`tools/manifest_compile.py
  --write`) — the diff is exactly the 5 ref retirements + 5 handler swaps.
- Tests: pins retired + nav asserts in
  `tests/unit/band6/test_band6_server_management_hub.py`; new
  `tests/unit/band6/test_curation_nav_wiring.py` (mining + utility nav
  pins, retired-refs-stay-gone sweep).

Verification: `python3 -m pytest tests/` — **2059 passed, 13 skipped**;
`manifest_compile` green; `check_symbol_shadowing` / `check_namespace` /
`check_no_skip` / `check_config_usage` / `check_compat_frozen` /
`check_sim_gate` all clean (no custom_id/label byte moved — every swap is
wire-byte-neutral, so no golden re-mint).

## 💡 Session idea

The five retired terminals shared one signature: a `pending_handler`
whose panel_id destination was ALREADY registered at HEAD
(`is_registered(PanelRef(...))` true while a sibling button in the same
spec still routed to `*_pending`). That is mechanically detectable — the
proposed `tools/check_completeness.py` (completeness-table card's idea)
should emit a "stale pending terminal" row whenever a pending ref's
obvious live twin (same subsystem hub panel, or a same-name `*_view`/
`*_route` handler) resolves, so the next curation pass starts from a
machine-derived worklist instead of a hand audit.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-completeness-table.md`.) Its table was this
bundle's shopping list — the "declared-honest pending terminal, not a
silent gap" framing held exactly (all five retirements were declared
refusal terminals with shipped custom_ids, so every swap was
byte-neutral and golden-safe, as its zero-unregistered-refs sweep
implied). Its 💡 idea (mechanize the sweep as `check_completeness.py`)
is reinforced, not consumed, by this session — see above. One friction
its card could not have warned about: parallel night lanes share the
container's single working tree, and a sibling lane's `git checkout -B`
between another lane's `checkout` and `commit` lands the commit on the
WRONG branch (this session's claim commit landed on the btd6-paragon
branch and was recovered via `git branch -f` + `git reset --keep` +
`git worktree add`). Guard recipe: every parallel lane should work in
its own `git worktree add <dir> <branch>` from the first commit —
verify with `git log --oneline origin/main..HEAD` on the intended
branch before push.
