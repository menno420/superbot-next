# 2026-07-13 — night audit-doc strict fix: #440's fleet-cleanup audit orphaned + re-cites D-0046

> **Status:** `in-progress`

- **📊 Model:** `Fable (Claude 5 family)` · night lane worker · ⚑ Self-initiated: upkeep — main `--strict` red introduced by #440 (no order/claim; contained doc-hygiene remediation per PL-001)

## Scope

PR #440 (commit b66aa80) landed the external fleet-cleanup audit as
`docs/audits/2026-07-13-fleet-cleanup-audit.md` — the first and only doc
under `docs/audits/` — and turned `bootstrap.py check --strict` red on
main with two findings:

- `[reachable]` — the doc is badged `reference` and nothing links it from
  a read-path root (`AGENT_ORIENTATION.md`, `current-state.md`, any
  `README.md`), so the reachability walker reports it as an orphan.
- `[stamp]` — the audit's narrative twice names decision `D-0046` with
  the bare token (lines ~76 and ~166), re-citing a decision whose stamp
  home is `docs/status/rebuild-completion-report-2026-07-09.md` — the
  exact double-cite class #439 just cleaned out of the completeness
  table.

Fix minimally, preserving the audit's factual content: reword the two
token sites descriptively (pointer to the stamp home, no bare
`D-`-prefixed id), and resolve the orphan by the sibling convention.
Convention check: `docs/audits/` has no siblings and no README index
(unlike `docs/review/`, whose README links its `audit`-badged docs);
`docs/retro/`'s one-off dated records are badged `historical`, which is
reachability-exempt (`_EXEMPT_BADGES` in bootstrap.py). The doc
self-describes as a "one-off external audit, not part of the repo's own
doc rotation", so the badge flip `reference` → `historical` is the
minimal reversible move, per the finding's own suggestion. Do NOT touch
the stamp home or the audit's findings/tables.

Definition of done: both findings reproduced on origin/main pre-fix,
gone post-fix; `bootstrap.py check --strict` exit 0 (claims advisories
expected, never exit-affecting); `python3 -m pytest tests/ -q` green;
READY PR open. No merge, no trigger arming.
