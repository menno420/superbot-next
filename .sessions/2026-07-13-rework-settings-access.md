# 2026-07-13 — curation rework: arm the settings.access explorer (rows 82-87)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · curation rework lane · mandate: curation report
  rows 82-87 (`docs/review/curation-report-2026-07-13.md` L1237-1242),
  claim `control/claims/settings-access-rework.md` (PR #374), token
  `claude/rework-settings-access`.

## Scope

Arm the six pending controls of the Settings → Access explorer
(`sb/domain/settings/panels.py` `settings_access_spec()`): subsystem
select, scope select, explain, reset, prev/next paging. Build an honest
governance-resolution read seam (the pending copy names
`governance.resolve_subsystem_state`, which does not exist at HEAD) that
reports resolved state + provenance (per-guild override / global /
default; visibility row vs settings KV). Explorer-open golden
(`parity/goldens/settings/sweep_settings_access.json`) must replay
byte-identical — persistent custom_ids stay pinned. `reset` is the one
WRITE: wire through a sanctioned op if one fits, else leave it pending
with upgraded honest copy naming the settings-mutation park.

## What shipped

(in progress)

## 💡 Session idea

(pending close-out)

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-curation-rework-nav-wiring.md`.) Review
pending — to be written at close-out.
