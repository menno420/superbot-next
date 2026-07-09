# 2026-07-09 — kit-version pin (substrate-kit v1.0.0)

> **Status:** `complete`

## Scope

Consumer half of kit-lab done-condition D2 (founding plan §4.2): record the
substrate-kit release pin in `substrate.config.json` — add
`kit_version: "1.0.0"` (the released tag,
sha256 `5e518d4978a01926057bdece04d88bd5f1b7d433bbc19b36790bdeff14149313`,
verified at upgrade time against `release.json`, not stored in config) — and
fix the stale `cadence.reconciliation_prs` default 20 → 30 (founding plan
§3.4, superbot Q-0134). Config-only; no code.

## What shipped

- `substrate.config.json`: top-level `"kit_version": "1.0.0"` (sorted key
  position matches the kit's `to_json` serialisation) +
  `cadence.reconciliation_prs` 20 → 30.
- Verified the current **vendored** `bootstrap.py` (pre-v1.0.0 dist)
  tolerates the new key: `Config.from_dict` drops unknown keys, so nothing
  breaks — but a load→save round-trip through the OLD dist would strip
  `kit_version` (the exact trap the v1.0.0 `Config.kit_version` declared
  field fixes). The pin is stable as long as config writes go through a
  v1.0.0+ dist.

## Follow-up (named, not this session)

- **Upgrade the vendored `bootstrap.py` to the v1.0.0 release asset** via the
  §4.3 `upgrade` flow (download `bootstrap.py.new`, `python3 bootstrap.py.new
  upgrade` — it verifies sha256 against `release.json`, archives the old dist
  to `.substrate/backup/`, and re-records `kit_version` durably). Until then
  avoid config-writing verbs (`bootstrap answer`) through the old dist, or
  re-add the key after.

## 💡 Session idea

Add a `check --strict` advisory that compares the config's `kit_version`
against the running dist's own stamped version and warns on mismatch — it
would have flagged this repo's "pinned 1.0.0 but running a pre-release
vendored dist" state automatically instead of relying on a session to notice.

## ⟲ Previous-session review

Previous session (PR #41, band 6 slice 2) shipped a large, well-verified
slice with an honest WIP→finish commit pair and explicit "NOT ready" interim
notes — good discipline. One gap this session inherited: no `.sessions/` log
was committed for it (the `.sessions/` dir held only the README despite the
born-red convention being written there), so the kit's session-log check ran
advisory-forever. This session commits the repo's first real session card;
improvement: sessions here should start doing so consistently, which arms the
check --strict session gate that CI already runs.
