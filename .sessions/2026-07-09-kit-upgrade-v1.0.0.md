# 2026-07-09 — vendored kit upgrade to substrate-kit v1.0.0

> **Status:** `in-progress`

## Scope

First real-world run of the kit's `upgrade` verb (founding plan §4.3): replace
this repo's pre-1.0 vendored `bootstrap.py` with the released v1.0.0 dist
(sha256 `5e518d4978a01926057bdece04d88bd5f1b7d433bbc19b36790bdeff14149313`,
verified against `release.json`). The flow: download `bootstrap.py.new` +
`release.json` next to the vendored copy, run `python3 bootstrap.py.new
upgrade` — it self-verifies, archives the old dist + `state.json` to
`.substrate/backup/`, classifies every planted doc by hash, replaces the
vendored file, and writes `.substrate/upgrade-report.md`. Closes the named
follow-up from the kit-version-pin session (the old dist's `Config.from_dict`
drops `kit_version` on any config round-trip; the new dist's declared field
fixes it).
