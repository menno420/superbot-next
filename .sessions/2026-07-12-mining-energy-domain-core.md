# 2026-07-12 — mining energy domain core (slice 0)

> **Status:** `complete`

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

1. `sb/domain/mining/energy.py` — the pure headless energy domain core, ported
   verbatim from the oracle `disbot/utils/mining/energy.py`, mirroring
   `sb/domain/fishing/energy.py` (structure, docstrings, `__all__`). Oracle-verbatim
   constants (`MAX_ENERGY=60`, `DIG_COST=1`, `REGEN_SECONDS=10`, `RESTORE_VALUES`)
   and all seven functions (`settle`/`can_dig`/`spend`/`restore`/`seconds_until`/
   `restore_value`/`bar`) with lazy on-access regen (value + timestamp, no ticker;
   a missing `(0,0)` row settles to full). No DB, no Discord, time is a parameter.
2. `tests/unit/mining/test_mining_energy.py` — 33 unit tests: regen math (partial
   tick, cap, `(0,0)`→full, exact/just-below `REGEN_SECONDS` boundary, negative
   elapsed, idempotence), `can_dig`/`spend` (refuse-at-0, floor clamp), `restore`
   (each `RESTORE_VALUES` item, cap clamp, full-refusal), `seconds_until`,
   `restore_value` (case/space-insensitive, non-food→None), `bar` rendering.
3. `docs/scoping/energy-system-scope.md` (+ `docs/scoping/README.md`) — the durable
   scope + deferred-owner-decision + slice plan record.
4. `control/claims/mining-energy-domain-core.md` — the lane claim.

**Explicitly NOT in this slice** (later, owner-gated): persistence/migration,
`mining_player_state` changes, `!cook`/`!use`/`!fastmine` wiring, any golden.
`!fastmine` dig-gating awaits an owner decision and sequences after WP-3 (#317).

## 💡 Session idea

The oracle keeps two near-identical energy modules (mining + fishing) by a
deliberate rule-of-three note; a future consolidation could hoist the shared
lazy-regen `settle` into one parametric core once a third copy appears.

## ⟲ Previous-session review

The WP lane pre-carved this exact "separate lane" (its claim lines 23-26), so the
collision surface was mapped before build — the claim ledger did its job.
