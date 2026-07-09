# 2026-07-09 — kit-version pin (substrate-kit v1.0.0)

> **Status:** `in-progress`

## Scope

Consumer half of kit-lab done-condition D2 (founding plan §4.2): record the
substrate-kit release pin in `substrate.config.json` — add
`kit_version: "1.0.0"` (the released tag,
sha256 `5e518d4978a01926057bdece04d88bd5f1b7d433bbc19b36790bdeff14149313`,
verified at upgrade time against `release.json`, not stored in config) — and
fix the stale `cadence.reconciliation_prs` default 20 → 30 (founding plan
§3.4, superbot Q-0134). Config-only; no code.
