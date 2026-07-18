# 2026-07-18 — D5 e2e-test-harness: sharpen into a decision-ready package

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · medium · docs-only

## Scope

Take `docs/design/D5-e2e-test-harness.md` (the tiered e2e proposal — an
in-process adapter tier D5.1 + an optional LIVE guild sweep D5.2, 7 open
questions) from a raw plan to a **decision-ready package**. Ground the
in-process-tier proposal in the actual test surfaces and the discord adapter
seam (verify, don't invent), then:

- Resolve the **agent-decidable** design picks — above all D5.1's central
  fake-`discord`-shim vs installed-library call — as flagged decide-and-flag
  defaults with an honest, seam-grounded recommendation.
- Route ONLY the genuinely **owner-gated** bits (the LIVE-tier token / cadence /
  cost / signer-identity) as one crisp OPEN router entry.
- If the in-process tier is buildable-now with no owner input, FLAG it as a
  recommended executable follow-up (do NOT build the harness here).

Docs-only slice. No `sb/` source edit. Contained + reversible.

## What landed

_(placeholder — resolved on flip)_

## Verification

_(placeholder — resolved on flip)_

## 💡 Session idea

_(placeholder — resolved on flip)_

## ⟲ Previous-session review

_(placeholder — resolved on flip)_
