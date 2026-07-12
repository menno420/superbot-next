# 2026-07-12 — CUT-2/CUT-3 cutover runbook consolidation + tooling wiring (SLICE 4)

> **Status:** `complete`

- **📊 Model:** Claude Opus 4.8 · high · docs/runbook + tooling wiring (Q-0194 / ORDER 012)

## Scope

Owner-directed (production lane, 2026-07-12): deliver ONE authoritative
cutover runbook that consolidates the CUT-2 and CUT-3 steps that today
exist only as scattered checklist items
(`docs/status/rebuild-completion-report-2026-07-09.md` §3(d) items 32–33),
plus the SLICE-4 tooling wiring the test plane allows:

1. `docs/operations/cutover-runbook.md` — preconditions/HARD GATES, CUT-2
   (import dry-run, reaction-capture window, live permission census,
   verify-import, public→private flip), CUT-3 (same-app-id token swap,
   `platform.cutover_flip_ts` write-once, N=7d rollback window, A-18
   coverage-debt publication, day-8–10 checklist), a ROLLBACK section, and
   a per-step OWNER (⚑) vs AGENT ownership table.
2. Tooling wiring: exercise `tools/check_verified_live.py --debt-list`,
   commit its output as a dated status artifact; investigate the
   permission-census live-GET wiring gap; drive verify-import as far as the
   test plane allows.

## What shipped

1. **docs/operations/cutover-runbook.md** — the consolidated CUT-2/CUT-3
   runbook. Preconditions/HARD GATES (G1 verified-restore, G2 backup, G3
   deploy packaging, G4 `SB_PROD_ATTEST`/CL-5b, G5 same-app-id/PG-5, G6
   lockfile) each with its exact check; CUT-2 (C2.1 import dry-run · C2.2
   reaction-capture window · C2.3 census GET+partition+carry-verify · C2.4
   verify-import · C2.5 public→private flip BEFORE artifacts); CUT-3 (C3.1
   freeze→delta→same-app-id token swap · C3.2 `platform.cutover_flip_ts`
   write-once · C3.3 post-swap carry-verify · C3.4 A-18 `--debt-list`
   publication · C3.5 N=7d rollback window · C3.6 day-8–10/A-20); a ROLLBACK
   section deferring to `rollback-playbook.md` (`tools/importer/reverse`, the
   `cutover_flip_ts` boundary, owner-signed M1/M2); and the ⚑ OWNER-vs-AGENT
   ownership table with exact commands.
2. **docs/status/coverage-debt-2026-07-12.md** — verbatim
   `check_verified_live.py --debt-list` output (0 rows, exit 0), the A-18(3)
   published remainder, as a dated `living-ledger` status artifact.
3. **rollback-playbook.md** — one cross-link line so the runbook is
   reachability-linked (strict-check clean).

## Tooling-wiring outcomes (SLICE 4)

- **debt-list** — `python3 tools/check_verified_live.py --debt-list` runs
  green in the test plane: `0 row(s)`, exit 0. Committed verbatim.
- **permission-census** — the offline partition + carry-verify paths run
  (`--census`/`--rename-map`/`--verify`/`--json`); a synthetic 2-override
  fixture returned `1 preserved, 1 renamed` with the correct admin-notice.
  The **live GET sweep** (`GET /applications/{app}/guilds/{g}/commands/
  permissions`) is **not implemented in-tool and not test-plane runnable** —
  the module consumes a captured JSON and has no network code; capture needs
  the production bot token. Left **owner-gated** (documented C2.3); no live
  Discord call made, and no unverifiable network code added to a
  prod-critical tool.
- **verify-import** — `SB_VERIFY_BOOT=true SB_DATA_PLANE=test python3 -m
  sb.app.verify_boot` correctly FAIL_FASTs at preflight (missing
  `DISCORD_BOT_TOKEN_PRODUCTION`/`DATABASE_URL`); with dummy env it reaches
  the `db_init` stage and stops (`asyncpg` not installed / no Postgres). The
  full dry-run invariant sweep runs only after `db_init` succeeds, so it is
  **owner-gated** on a restored Postgres snapshot. The forward importer
  (CUT-2 dry-run) is not built yet — `tools/importer/` ships only `reverse/`.

## 💡 Session idea

The runbook's ⚑ OWNER/AGENT column and the completion-report's §3(d) rows are
the SAME cutover taxonomy from two sides — the report says WHAT is unexecuted,
the runbook says WHO executes each leg. A mechanical follow-up: a tiny checker
that asserts every §3(d) CUT-2/CUT-3 sub-item has a matching runbook step id
(G*/C2.*/C3.*) and vice-versa would make the runbook self-fencing against the
report drifting — the same "two lenses, one spine" discipline `check_verified_live`
V4 already applies to the parity/verified dashboards. Successor: once the
forward importer lands with the CUT-2 build, wire its dry-run report format
into C2.1 with an exact command (today it is necessarily prose).

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-btd6-seed-data-terminal.md`.) Its
"publish-your-own-anchors" discipline transferred directly: this runbook's
every command and constraint was reconstructed from the SHIPPED tools and
frozen docs (the `permission_census.py`/`check_verified_live.py` docstrings,
`verify_boot.py`'s own run line, the rollback-playbook's step-4 sequence,
D-0021/D-0033 verdicts) rather than from memory — three independent sources
agreed on PG-5 same-app-id (the census docstring, the completion report, the
D-0033 ruling) before the runbook asserted it NON-NEGOTIABLE. One thing that
card's successor-map would have saved re-deriving: it did not flag that the
"reaction window" appears in TWO senses (the old-bot telemetry-sidecar capture
window, item 31, vs the A-18(3) coverage-debt reaction-window publication) —
a successor note disambiguating the two would have shortcut a search here.

