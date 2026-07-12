# 2026-07-12 — mining energy domain core (slice 0)

> **Status:** `in-progress`

- **📊 Model:** agent · high · feature build

## Scope

Port the PURE mining energy domain core from the oracle
(`menno420/superbot` `disbot/utils/mining/energy.py`) into
`sb/domain/mining/energy.py`, headless and faithful, mirroring the already-ported
`sb/domain/fishing/energy.py`. Full unit coverage. This slice deliberately does
NOT wire energy into any command, does NOT add persistence/migration, and does
NOT touch `mining_player_state` or any golden — those are later, owner-gated
slices (see `docs/scoping/energy-system-scope.md`).

## What shipped

_(born-red HOLD — flips to `complete` when the domain core + tests land green)_

## 💡 Session idea

The oracle keeps two near-identical energy modules (mining + fishing) by a
deliberate rule-of-three note; a future consolidation could hoist the shared
lazy-regen `settle` into one parametric core once a third copy appears.

## ⟲ Previous-session review

The WP lane pre-carved this exact "separate lane" (its claim lines 23-26), so the
collision surface was mapped before build — the claim ledger did its job.
