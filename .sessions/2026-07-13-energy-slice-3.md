# 2026-07-13 — mining energy slice 3: dig energy-spend into !fastmine

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · energy-lane slice 3 (fastmine dig gating,
  Option A) · stacked on #317 `mining-write-parity-wp3` (itself on #312
  `mining-write-parity-wp2`) per ORDER 017 rule 2 (branch from the
  highest unmerged head the work depends on, note the base in the PR
  body), with `origin/main` merged in (slices 1–2 + the energy core are
  main-only).

## Scope

Slice 3 of the energy lane per `docs/scoping/energy-system-scope.md`
(slice plan, "Slice 3 — wire dig energy-spend into `!fastmine` (ONLY
under Option A; sequence AFTER #317)"):

1. `sb/domain/mining/ops.py` — `record_mine` gains the dig energy
   spend inside the existing txn: `get_energy` → settle → `can_dig`
   gate → spend `DIG_COST=1` → `set_energy`, over the #320 pure energy
   core (`MAX_ENERGY=60`, `REGEN_SECONDS=10`) + the slice-1
   `get_energy`/`set_energy` store pair.
2. `sb/domain/mining/service.py` — `fastmine_route` out-of-energy
   refusal as a ROUTE-LEVEL PRE-TXN pure read (the slice-2
   ValidatorError-envelope trap), carrying the `~{wait}s` hint from
   `seconds_until_next_dig`. Refusal copy oracle-verbatim @ 87bbe1d.
3. Goldens (canonical D-0073 `capture_case`, double-captured):
   RE-MINT `sweep_fastmine.json` (its db_delta now carries the
   `mining_player_state` energy 60→59 write) + mint the NEW
   out-of-energy refusal golden.
4. Ratchet / count-pin reconcile against the post-WP-3
   `mining_player_state` contract (in-merge union: corpus 500 /
   minted 38 before this slice's mint).

Oracle copy source: `disbot/services/mining_workflow.py` `mine()` @
`87bbe1dbf0c504d1ef1fc9db466224303f16afba` (local clone, never MCP).

NOT this slice: no chop/explore energy gating (the scoping doc digs
only the mine leg), no migration, no new store functions.

## What shipped

(filled at flip time)

## 💡 Session idea

(filled at flip time)

## ⟲ Previous-session review

Previous card (`2026-07-13-energy-slice-2.md`, PR #385): its 💡 —
pinning the ValidatorError-envelope trap with the explicit instruction
that slice 3's out-of-energy refusal must be a route-level pure read —
is exactly the failure this session would otherwise have re-derived
from a red capture; writing the successor's trap into the predecessor's
card is the cheapest cross-slice insurance this lane has found.
