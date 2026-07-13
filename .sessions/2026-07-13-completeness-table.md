# 2026-07-13 — per-subsystem completeness table (ORDER 017 item 1)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` · NIGHT-RUN slice 1 · mandate: ORDER 017 (PR #323)

## Scope

Produce `docs/status/completeness-table-2026-07-13.md`: one row per
subsystem (every `sb/domain/*` + kernel panels + manifest surfaces) ×
three columns {core, admin, setup}, every non-✅ cell citing evidence
(file:line or PR #), plus a ranked "Top gaps" list that drives the
night's fix slices. Docs-only PR; no code changes. In-flight peer
lanes (mining write-parity WP-2 #312 / WP-3 #317, energy #320,
fishing slice 1 #313 owner-gated D-0043) get flags, not work.

## What shipped

- `docs/status/completeness-table-2026-07-13.md` (PR #326) — 50 rows
  (49 manifests + kernel) × {core, admin, setup}; headline core 41✅/9⚑,
  admin 43✅/7⚑, setup 47✅/3⚑; ranked Top-gaps list drives the next
  night-run slices. Linked from `docs/status/README-first.md`.
- Sweep result worth keeping: **zero unregistered refs** across 413
  commands / 370 actions / 57 selectors — every flag in the table is a
  declared-honest pending terminal, not a silent gap.

## 💡 Session idea

Turn the ad-hoc sweep script (compile manifests → run ENSURE_REFS →
resolve every route → classify `pending_handler` registrations) into
`tools/check_completeness.py --table`, so the completeness table
regenerates mechanically instead of being hand-derived; the
pending-terminal classifier already exists in
`sb/domain/operator_spine.py` (`pending_handler`) — the tool just
inventories it.

## ⟲ Previous-session review

Previous session (auto-merge enabler, PR #321) left a clean convention
trail — its card's watch-item ("the enabler proves itself on the next
real agent PR") is exercised by THIS PR: the born-red card held the
substrate gate red while checks ran, exactly as designed. One friction
found in its wake: local `bootstrap.py check --strict` runs dirty
`.substrate/guard-fires.jsonl` (kit state) into the working tree —
restore it before committing (`git checkout -- .substrate/…`), or the
next session stages kit noise.
