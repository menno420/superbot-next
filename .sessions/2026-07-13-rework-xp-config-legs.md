# 2026-07-13 — curation rework backlog slice 1: xp.config mutation legs

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · curation-report REWORK backlog,
  slice 1 · mandate: docs/review/curation-report-2026-07-13.md §Rework
  (c) Backlog — "**xp.config ×4** — port the xp config mutation legs
  (xp_range / xp_cooldown / xp_levelup_channel / xp_import) in
  sb/domain/xp — oracle xpconfig legs are live-wired; one contained
  slice."

## Scope

Arm the four `xp.config` panel pending-terminal buttons onto their live
targets (the cleanup-words / moderation.hub.warn modal-ingress
precedent, PR #333 lineage):

1. `xp_range` — button → G-10 modal (oracle `_XpRangeModal` verbatim:
   Min/Max fields, "❌ Both values must be integers." / "❌ Max must be
   ≥ min.") → two audited `settings.set_scalar` writes (xp_min, xp_max).
2. `xp_cooldown` — button → modal (oracle `_XpCooldownModal`:
   "❌ Cooldown must be an integer.") → `settings.set_scalar`
   (xp_cooldown).
3. `xp_levelup_channel` — button → modal (oracle `_XpChannelModal`:
   empty clears, numeric ID sets, "❌ Channel must be empty (to clear)
   or a numeric Discord channel ID.") → `settings.bind` /
   `settings.unbind` on the `xp.announce_channel` binding (the P0-3
   pointer lane; the server_logging bind precedent).
4. `xp_import` — button → modal ingress collecting source / channel /
   limit, delegating to the LIVE `!xpimport` front-door walk (the
   utility poll/remind backlog pattern). The select-driven
   XpImportSetupView picker and the preview/apply panel stay the
   import-preview slice's — the scan's honest BLOCKED boundaries are
   unchanged.

Files: `sb/domain/xp/panels.py`, `sb/domain/xp/handlers.py`,
`tests/unit/band4/test_band4_xp.py`, `manifest.snapshot.json`
(recompiled), `compat/compat-frozen.json` (regenerated — new modal-id
custom-id roots). No goldens touched (no golden clicks these buttons —
sb/domain/xp/panels.py pending note; handler refs are not wire bytes).

Oracle: menno420/superbot@cdb2680 disbot/views/xp/modals.py (fetched at
session time — copy mirrored verbatim where cited).

## What shipped

_(filled at completion)_
