# 2026-07-13 — curation rework: btd6 paragon wiring (ORDER 017 item 2)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · NIGHT-RUN curation rework · mandate: ORDER 017
  item 2 (curation report PR #327, chunk 6)

## Scope

Wire the BTD6 Paragon calculator surface — `btd6.paragon` calc /
requirements / stats buttons plus their 4 selects — onto the ported
paragon math (`sb/domain/btd6/paragon_math.py`, `paragon_degrees.py`,
`stats.py`), retiring the `btd6.paragon_pending` terminals
(sb/domain/btd6/service.py:366, panels.py:348-403). This is D-0046's
named successor port ("the paragon power calculator (sacrifice
math/reverse solver)"). Oracle: disbot views/btd6/paragon_view.py +
paragon_modals.py + services/paragon_service.py — copy/fields matched
where the ported math exposes them; no invented numbers. No stores, no
migrations; goldens/btd6/sweep_paragon pins the initial open only and
must stay byte-identical.

## What shipped

(fills at close-out)

## 💡 Session idea

(fills at close-out)

## ⟲ Previous-session review

(fills at close-out)
