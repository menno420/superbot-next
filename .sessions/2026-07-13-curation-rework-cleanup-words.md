# 2026-07-13 — curation rework: cleanup words panel + logging nav (ORDER 017 item 2)

> **Status:** `in-progress`

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

_(fills at close-out)_

## 💡 Session idea

_(fills at close-out)_

## ⟲ Previous-session review

_(fills at close-out)_
