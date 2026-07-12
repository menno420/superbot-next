# 2026-07-12 — slice 1 port: equip / unequip / gear / loadout / character (the equipment/wear/loadout/character-sheet system → EffectiveStats)

> **Status:** `in-progress`

- **📊 Model:** opus-4.8 · high · feature build (Q-0194)

## Scope

The faithful port of mining slice 1 — the equipment / wear / loadout-preset /
skills / character-sheet stack that produces the cross-game `EffectiveStats`
read model (deathmatch + casino defer to it, D-0045). Five shipped commands
move from honest D-0043 pending terminals to real handlers:
`!equip` · `!unequip` · `!gear` · `!loadout` · `!character`.

Delivered:

- **Domain modules** (`sb/domain/mining/`): `equipment.py` (the cross-game
  `EffectiveStats` frozen dataclass, the `_GEAR` catalog, set bonus,
  `compute_stats`, `MAX_DURABILITY`), `skills.py` (four capped branches →
  stats), `character.py` (`character_stats` = gear + skills), `loadout.py`
  (set-aware `best_loadout`), `workshop.py` (durability bar / wear plan /
  repair pricing) — ported VERBATIM from the oracle
  (`disbot/utils/equipment.py` + `disbot/utils/mining/*`). `compute_stats({})`
  is all-zero, so deathmatch/casino goldens are unchanged.
- **Stores + migrations**: `mining_equipment`, `mining_gear_wear`,
  `player_skills`, `mining_loadout_presets` — registered stores (declared
  mining surfaces) with CRUD + GDPR erasure legs; migrations
  `0039`–`0042` (+ the `mining_player_state.last_broken_item` column).
- **Audited write ops** (`ops.py`): equip / unequip / save-loadout /
  apply-loadout / delete-loadout mirror the core-loop one-leg one-txn shape
  (reset_inventory precedent).
- **Handlers** (`service.py` `_register()`): the three guard usage strings
  (`equip`/`unequip`/`loadout`) as `Reply(BLOCKED, …)` and the two
  attachment cards (`character_doll.png` / `character.png`) via
  `RenderedAttachment`; the 5 keys removed from `PENDING`.
- **A-16 depth floor**: four `depth.exemptions.mining` `guard-only-capture`
  rows (one per new write-surface table) — the imported sweep pins only the
  write-free guard bytes.
- **Golden re-home** (#193 law): the 5 `_unmapped` sweeps re-homed into the
  gated `mining` row (mining 12 → 17; gate 412 → 417) by `git mv` + the one
  sanctioned `subsystem` flip, verified byte-identical against the real
  handlers.

## Verification

(filled at close-out — bootstrap check --strict, pytest, golden-parity gate
replay of all 17 mining rows incl the 5 re-homed, check_parity_depth,
manifest verify, migrations checker.)

## 💡 Session idea

(filled at close-out)

## ⟲ Previous-session review

(filled at close-out — covers the immediately-preceding card.)
