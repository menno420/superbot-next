# 2026-07-13 — docs sweep: the parity report leg is live green — retire the red-by-design doctrine

> **Status:** `in-progress`

- **📊 Model:** Claude (Fable family) · docs sweep · mandate: golden-parity
  `report` flipped REAL GREEN on main — every repo guidance line still
  teaching "red-by-design / red-until-parity / judge only the `gate`" is
  stale and misleads the next fresh session.

## Verified milestone (TRUTH bar, before any rewrite)

- Latest golden-parity run on main at sweep time: **29238825392** (run 822,
  head `0215258`, 2026-07-13T09:22Z) — `report` job (86779742307)
  conclusion **success**. Log tail, verbatim:
  `corpus: 484 goldens across 51 subsystem dirs` ·
  `replayable: 484/484 (goldens with a reconstructable case + live binding)` ·
  `green: 484/484 replayed cases match their golden` ·
  `ported: 51/51 subsystems` · `report: GREEN — full-corpus parity.`
- First green: run **29222893993** (run 790, head `eae2e61`,
  2026-07-13T04:00Z — fishing port slice 4, #350); run 777 (02:44Z,
  slice 3) was still red. So the flip commit is `eae2e61` (#350).

## Scope

Doctrine docs + workflow comments only. Historical records (`.sessions/`
cards, `docs/retro/*`, `docs/decisions.md` verdicts, dated control
reports) are left as written — history is not rewritten. No workflow
logic changes; no golden, parity.yml, or code-behavior edits.

## Hits & classification (sweep: `red-by-design|red-until-parity|judge the gate|EXPECTED RED`)

Updated (doctrine / live guidance):
- `README.md` — "Reading the CI" paragraph
- `docs/status/README-first.md` — the red-orientation doctrine itself
- `docs/current-state.md` — stability-baseline line
- `docs/operations/local-verification.md` — ladder §2 report note
- `parity/README.md` — "red until parity" oracle line
- `.github/workflows/golden-parity.yml` — comments only (header + report
  job comment); step display-name left as-is (not a comment)
- `.github/workflows/named-gates.yml` — comments only (×2)

Left alone (history / other writers' files / code):
- `.sessions/*` (12 cards), `docs/retro/*` (3), `docs/decisions.md`
  (D-entry verdicts), `docs/retro/QUESTIONS.md` — historical records
- `control/status.md`, `control/outbox.md` — the coordinator seat's
  heartbeat + dated manager report (one writer per file; flagged to the
  coordinator instead)
- `control/README.md` — the `health:` vocabulary enum
  (`red-by-design (<why>)`) is a generic template, not the stale claim
- `tools/run_golden_parity.py` (printed report header still says "RED BY
  DESIGN until full parity"), `parity/run.py`, `parity/harness/runner.py`
  — code/docstrings, out of this docs-sweep's write scope → follow-up
- `.claude/CLAUDE.md` — no hit (render-managed; nothing for the kit)
