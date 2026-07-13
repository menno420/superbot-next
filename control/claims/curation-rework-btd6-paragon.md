# Curation rework — BTD6 paragon wiring — `curation-rework-btd6-paragon`

> **CLAIM (2026-07-13)** — curation-rework lane (SuperBot World night run,
> ORDER 017 item 2; evidence: `docs/review/curation-report-2026-07-13.md`
> chunk 6, PR #327). This lane claims the wiring of the BTD6 paragon
> calculator surface (calc / requirements / stats buttons + their 4
> selects) onto the ALREADY-PORTED paragon math, so a concurrent fleet
> does not duplicate the slice.

**Scope.** `sb/domain/btd6/` (paragon_math.py successor pieces,
paragon surface handlers, panels.py paragon specs), `sb/manifest/btd6.py`
ensure wiring, `tests/unit/band7/` new paragon test band. No migrations,
no stores, no goldens re-minted (goldens/btd6/sweep_paragon pins the
initial open only — the click routes are golden-unpinned).

- `curation-rework-btd6-paragon` · **curation rework — wire btd6 paragon calc/requirements/stats panels + selects onto the ported paragon math (D-0046)** — retires the paragon_pending terminals; math already in-tree · sb/domain/btd6/, tests/ · 2026-07-13
