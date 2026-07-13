# 2026-07-13 — fishing depth slice 4 port: curios / craftcurio / tidepool / dock / boathouse / fishery (locations slice — FINAL)

> **Status:** `in-progress`

- **📊 Model:** fable-5 · high · feature build

## Scope

The faithful port of fishing depth slice 4 — the FINAL rung of the
fishing gear port (D-0043 named successor scope; lane claim
`control/claims/fishing-port-remaining.md`, built directly atop slice 3 =
PR #342 / `3e4a77d`). The last six shipped commands move from honest
D-0043 pending terminals to real surfaces: `!curios` · `!craftcurio` ·
`!tidepool` · `!dock` · `!boathouse` · `!fishery` — after this the
fishing PENDING roster is EMPTY (20/20 commands live) and
`parity/goldens/_unmapped/` carries ZERO fishing sweeps.

Planned shape (the #313/#330/#342 slice recipe — NO migration this
slice; the fishing structures ride the EXISTING generic
`mining_structures` table as additive rows, curios/pearls/coral ride
`mining_inventory` via the sanctioned lazy-import mining.store seam):

- **Domain** (`sb/domain/fishing/curios.py`, NEW): the shipped
  `utils/fishing/curios.py` ported verbatim — the four-entry
  CURIO_CATALOG (Carved Coral Shell 🐚 2 / Coral Seahorse 🌊 4 /
  Coral Idol 🗿 8 / Coral Leviathan 🐉 16 coral), `cost_text`,
  `collection_progress`, `curio_by_key`; the shipped
  `craftable_key_for` lands as `curio_craftable_key_for` (bait.py
  already exports the package's `craftable_key_for` —
  check_symbol_shadowing rule 2, the slice-3 precedent; bytes
  identical).
- **Domain** (`sb/domain/mining/structures.py`, EXTENDED): the four
  fishing structures verbatim from the oracle module that owns them —
  TIDE_POOL/DOCK/BOATHOUSE/FISHERY keys, level names (Reef Pool /
  Tidal Basin / Grand Reef · Fishing Dock / Deepwater Pier · Boathouse
  / Grand Boathouse · Fishery / Grand Fishery), build ladders
  (coins + coral(+wood)) and the four mult/bonus functions
  (pull 0.04 · bite 0.06 · regen 0.12 · bonus 0.05 steps).
- **Ops**: `fishing.craft_curio` (coral −cost, +1 curio item, one txn —
  the oracle craft_curio inventory-only conversion) and
  `fishing.build_structure` (the DECIDE-AND-FLAG fork, resolved PORT
  THE WRITE: the oracle `mining_workflow.build_structure` one-txn coin
  debit + material consume + level raise, #217 advisory-fenced locking
  read via a new `mining.store.lock_structure_build_slot`; balance
  event after commit; mining_structures written ONLY through
  `mining.store.set_structure_level` — the sole-writer seam).
- **Handlers/panels**: `fishing.curios_view` (the 🪸 Coral Curios blue
  card, cog-inline embed verbatim), `fishing.craftcurio_route` (guard:
  "That isn't a carvable curio…"), the four structure panels
  (tide_pool/dock/boathouse/fishery — Build + ↩ Structures buttons,
  teal/dark-teal embeds, goldens pin the component trees) + the live
  structures sub-hub (oracle structures_hub.py); the fishing hub 🏗
  Structures button repoints from `fishing.structures_pending` to the
  live sub-hub (byte-neutral vs goldens/fishing/sweep_fishing). The
  six keys leave `PENDING` (EMPTYING it); their `*_pending` refs
  pruned from the composition-parity burn-down.
- **Parity**: the FINAL 6 `_unmapped` sweeps (sweep_curios /
  sweep_craftcurio / sweep_tidepool / sweep_dock / sweep_boathouse /
  sweep_fishery) re-homed into the gated `fishing` row (#193 law:
  `git mv` + the one sanctioned `subsystem` flip) → `_unmapped`
  fishing sweeps 6 → 0. NO new tables → ratchet expected unchanged
  (run `--write-ratchet`, commit whatever it produces);
  mining_structures/mining_inventory coverage already rides mining's
  rows/exemptions. Sim-gate: the structures sub-hub is the one
  above-floor panel (5 actions) → legacy-seed exempt overlay rows +
  baseline regen (the fishing.hub precedent); the four structure
  panels sit at 2 actions each (below-floor auto-exempt).

## Verification (local, real Postgres, pristine parity_replay DB)

(filled at close-out)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out)
