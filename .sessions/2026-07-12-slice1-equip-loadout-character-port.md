# 2026-07-12 — slice 1 port: equip / unequip / gear / loadout / character (the equipment/wear/loadout/character-sheet system → EffectiveStats)

> **Status:** `complete`

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

## Verification (local, real Postgres — PG16)

- **golden-parity gate GREEN — all 417 golden(s) across 51 ported
  subsystem(s) replay clean** (`golden-parity gate: 51 ported / 1
  pending`, pending `_unmapped [51]`). Was 412 before the re-home; the
  5 re-homed sweeps (sweep_equip/unequip/gear/loadout/character) each
  verified byte-identical against the REAL handlers by a targeted
  `replay_case` pass BEFORE the `git mv` (all five GREEN), then again
  in the full gate after.
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  468 goldens** (the four new declared write-tables covered by the
  `guard-only-capture` exemption rows; R3 ratchet untouched — re-home
  only adds coverage).
- **manifest_compile: green** (P9 recompile-parity; snapshot rewritten
  `59635087… → b9ba39f7…`). **check_migrations: clean (42)**.
- check_compat_frozen · check_sim_gate · check_data_lifecycle (70
  stores) · check_schema_growth · check_rollback_disposition (72
  stores) · check_namespace · check_egress · check_money_race ·
  check_escape_hatches · check_metric_cardinality · check_no_skip ·
  check_intent_survival · check_config_usage · check_symbol_shadowing ·
  check_slash_cap · check_cost_posture · check_amendments — **all
  green**.
- **pytest tests/unit: 1741 passed / 5 skipped**; **tests/integration:
  11 passed** (the F-001/F-002 mining/farm money-race regressions
  included). New `tests/unit/mining/test_equipment_stats.py` (15
  cases) pins the all-zero baseline + set bonus + durability + branch
  mappings; the composition-parity burndown pruned by the 5 now-live
  refs.
- `bootstrap.py check --strict`: green except the by-design born-red
  HOLD (this card was in-progress until this final flip) and a
  pre-existing non-exit-affecting control/status.md owner-action
  advisory (untouched — status.md is the one-writer heartbeat).

## 💡 Session idea

The write-lane goldens the four `guard-only-capture` exemptions are
holding open (argful `!equip <owned item>`, `!loadout save <name>`, a
geared wear tick, an argful `!skill` spend) are all now
CORPUS-EXPRESSIBLE against LIVE handlers — the ops exist and write real
rows. A follow-up "argful mining capture" slice could drive those four
paths once against a seeded-inventory persona, mint four row-bearing
goldens, and DELETE all four exemptions (the D-0069 class's own exit
condition: "a future argful capture deletes it"). That converts the
honest-but-uncovered surface into real coverage and is the natural
next depth increment on this row. Sequence it after `!skill`/`!skills`
themselves flip live (they stay D-0043 pending this slice — only the
`player_skills` store + `skill_stats` math shipped, not the spend
command), so the skill golden lands with its own handler rather than
riding character's.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-parity-flips-wave8.md`, the parity
program's completion card.) Its headline — "THE PARITY PROGRAM IS
COMPLETE AT 50/50, the only pending directory is `_unmapped`, the
re-home pool" — framed this slice exactly: every real subsystem row is
ported, so slice 1's work was NOT a flip but a depth-deepening of the
already-ported `mining` row plus a five-golden re-home out of
`_unmapped`. Its trap doctrine held: the `_unmapped` sweeps really did
pin only the bare/guard bytes (trap: "the create-carrying golden lives
in `_unmapped`" generalized here to "the guard-carrying golden lives
in `_unmapped`"), and the re-home really was a `git mv` + one-line
`subsystem` flip with byte-identical replay (its wave-7 "price by
golden count × substrate distance" note priced this correctly — five
goldens but a DEEP substrate: EffectiveStats + 4 stores + 4 migrations
+ 5 audited ops, the bulk of the seat). One thing its 💡 idea got
half-right: it called the remaining `_unmapped` pool "attribution/
re-home work … none of it is porting." For the btd6-family strays that
holds, but the five mining strays this slice re-homed were NOT pure
attribution — they were guard bytes over UNBUILT handlers (the D-0043
pending terminals), so honoring them required the full equipment port
first. The correction: a `_unmapped` sweep over a PORTED row's already-
live surface is a pure re-home, but a sweep over a row's PENDING
sub-surface is a port gated behind the re-home — check which before
pricing.
