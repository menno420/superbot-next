# 2026-07-13 — btd6 paragon calculator port (ORDER 017 night-run fix slice A)

> **Status:** `complete`

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

## 💡 Session idea

The requirements-page selector had to ship as `solve_strategy` instead
of the oracle's bare `strategy` because the manifest-wide never_strand
predicate pools component ids per SUBSYSTEM and the btd6 hub already
declares a `strategy` action (D-0086 deviation 2). Since session ids
are minted 32-hex on the wire anyway, scoping that pool per PANEL (or
admitting a panel-qualified id form in the manifest grammar) would let
every future port keep the shipped component ids verbatim — retiring
this rename-on-collision deviation class at zero wire cost.

## ⟲ Previous-session review

The completeness-table session (PR #326) is what made this slice cheap:
gap row 7 ranked the paragon panel the top free self-contained gap and
its evidence column named the exact oracle files
(`utils/btd6/paragon_math.py` + the paragon views), so orientation cost
was near zero — no re-derivation grep pass. Its headline sweep claim
("zero unregistered refs — every flag is a declared-honest pending
terminal") held here: `btd6.paragon_pending` was exactly that, a
declared terminal retired by a one-way A-16 flip, not a silent gap.
