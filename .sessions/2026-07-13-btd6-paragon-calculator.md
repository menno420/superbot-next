# 2026-07-13 — btd6 paragon calculator port (ORDER 017 night-run fix slice A)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT-RUN fix slice A · mandate: ORDER 017
  (PR #323), gap row 7 of `docs/status/completeness-table-2026-07-13.md`

## Scope

Retire the `btd6.paragon_pending` session terminal: arm the 3 pending
actions (🧮 Calculate degree · 🎯 Requirements · 📊 Stats) + 4 selectors
(paragon / players / difficulty / extra-T5) on the `btd6.paragon` landing
panel as a self-contained pure-compute port of the oracle's
`views/btd6/paragon_view.py` + `utils/btd6/paragon_math.py` power model
(menno420/superbot). The live-API reconciliation lane stays a named
successor (D-0046) — the compute here is the API-replica local formula,
which the oracle validated field-by-field against the live endpoint.

Definition of done: implemented + tested + golden-parity
(goldens/btd6/sweep_paragon initial-open bytes unchanged) + real error
copy + final user-facing copy.
