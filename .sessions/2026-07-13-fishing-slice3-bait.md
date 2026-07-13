# 2026-07-13 — fishing depth slice 3 port: bait / craftbait / craftpearl / craftcharm (bait shelf)

> **Status:** `complete`

- **📊 Model:** fable-5 · high · feature build

## Scope

The faithful port of fishing depth slice 3 — the bait-shelf rung of the
fishing gear port (D-0043 named successor scope; lane claim
`control/claims/fishing-port-remaining.md`, built directly atop slice 2 =
PR #330 / `4493cc2`). Four shipped commands move from honest D-0043
pending terminals to real surfaces: `!bait` · `!craftbait` ·
`!craftpearl` · `!craftcharm`.

Planned shape (the #313/#330 slice recipe):

- **Domain** (`sb/domain/fishing/bait.py`, NEW): the shipped
  `utils/fishing/bait.py` ported verbatim — the six-entry BAIT_CATALOG
  (worm 🪱 150 / grub 🐛 400 / lure ✨ 1000 / minnow 🐟 200 / spinner 🌀
  600 / feast 👑 1800, ×10 charges each, the two orthogonal knob
  families), `effect_text`, CRAFT_RECIPES (worm 3≤3 · minnow 3≤3 ·
  grub 5≤6 · spinner 5≤6 · lure 6≤9), `recipe_text`/`craftable_key_for`,
  PEARL_BAIT_RECIPES (Royal Feast = 4 pearls) + the `pearl_*` helpers.
- **Domain** (`sb/domain/fishing/gear.py`, NEW): the shipped
  `utils/fishing/gear.py` charm-craft shelf verbatim — CHARM_RECIPES
  (fishing charm 8≤8 · anglers charm 12≤14 · master angler charm 18≤21;
  names byte-match the mining gear catalog), `charm_recipe`,
  `charm_recipe_text`, `craftable_charm_for`.
- **Store + migration**: `fishing_bait` (per-(user, guild) loaded bait
  key + remaining charges; absent row / 0 charges reads as bait-less —
  the shipped migration-091 shape) as a MEMBER_ID registered store with
  the `fishing.erase_subject_bait` delete-erasure body; migration
  `0050_fishing_bait.sql` (+ checksums).
- **Handlers**: `fishing.bait_shop` (the bait-shop panel — the 🪱 Bait
  Shop gold embed + buy/craft/pearl selects + ↩ Fishing menu),
  `fishing.craftbait_route` (no-arg opens the shop; the fish→bait
  craft: guards as pure reads, the write as an audited one-leg one-txn
  op), `fishing.craftpearl_route` (no-arg auto-selects the single pearl
  recipe; the pearl→bait craft), `fishing.craftcharm_route` (no-arg
  lists the recipes; the fish→charm craft), `fishing.bait_buy_route`
  (buy_bait — the audited coin debit leg, #217 locking-read pattern,
  balance event after commit; same-bait stacks, different-bait
  replaces). The four keys leave `PENDING`; their `*_pending` refs
  pruned from the composition-parity burn-down.
- **Parity**: the 4 `_unmapped` sweeps (sweep_bait / sweep_craftbait /
  sweep_craftpearl / sweep_craftcharm) re-homed into the gated `fishing`
  row (#193 law: `git mv` + the one sanctioned `subsystem` flip);
  `fishing_bait` is a NEW declared table surface EXEMPT under
  `guard-only-capture` (all four sweeps pin write-free bytes — the
  fresh-player shop renders and the no-pearls / recipe-list guards are
  pure reads). Ratchet: run `--write-ratchet` and commit whatever splice
  it produces — expect movement ONLY when a re-homed golden's db_delta
  carries a new table (the slice-2 lesson: guard-only sweeps move
  nothing).

## Verification (local, real Postgres 16, pristine parity_replay DB)

- **golden-parity GATE GREEN — all 478 golden(s) across 51 ported
  subsystem(s) replay clean** (the +4 re-home takes fishing 12 → 16,
  `_unmapped` 10 → 6; sweep_bait + sweep_craftbait replay
  byte-identical against the new bait-shop panel on first mint — every
  select option label/emoji/description, the No-bait-loaded embed and
  the live pearl/balance fields; sweep_craftpearl / sweep_craftcharm
  replay the guard/listing bytes).
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  484 goldens**; `fishing_bait` exempt (`guard-only-capture`).
- **check_migrations: clean (50)**; **manifest_compile: green
  (sha256:f6309386…cc96, 48 manifest(s))** (snapshot recompiled).
- **check_money_race: OK — 0 violations under sb/domain (2 allowlisted,
  0 ledgered known-risk)** — the buy_bait leg is advisory-fenced
  (`lock_bait_slot` BEFORE the loadout read → debit → load; the
  rod-slot #217 shape), craft_bait / craft_pearl_bait ride the same
  fence and craft_charm its own `lock_charm_slot` against a concurrent
  double-craft (the quick_craft posture — materials, so the lock is the
  only guard).
- **check_sim_gate: OK — 1363 [A] assignment(s), 546 auto-exempt
  below-floor** — the bait panel sits at exactly 4 declared
  actions + selectors (the ≤ 4 below-floor rule), so no overlay/lock
  rows minted (the #313/#330 posture).
- **check_compat_frozen: OK** (no new command names/aliases — all four
  commands were already declared; only their routes went live).
- **check_symbol_shadowing: clean** — one finding surfaced and fixed
  in-slice: the shipped bait `effect_text` collides with the slice-1
  weather `effect_text` (public names are package-unique, rule 2), so
  it lands as `bait_effect_text` with a provenance note; produced bytes
  identical (the goldens prove it).
- **check_namespace / check_escape_hatches / check_schema_growth /
  check_amendments / check_runtime_smoke / check_no_skip /
  check_config_usage / check_metric_cardinality / check_egress:
  clean.**
- **pytest tests/integration -q: 11 passed.**
- **pytest tests/: 2091 passed, 2 skipped** (includes the new
  `tests/unit/band6/test_band6_fishing_bait.py` — catalog/recipe
  verbatim numbers, effect-text bytes, the craftpearl/craftcharm/
  craftbait/buy guard bytes vs the goldens, panel spec component tree
  incl. every select option, store spec/erasure refs, manifest + hub
  route flips).

### 4 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_bait, sweep_craftbait, sweep_craftpearl, sweep_craftcharm — only
the `"subsystem"` line changed (`_unmapped` → `fishing`);
calls/events/db_delta bytes untouched (#193 law). All four pin
write-free guard/read bytes, so `fishing_bait` lands exempt, not
covered; the ratchet floor stays `{events: 1, tables: 4}` (the
`--write-ratchet` regen produced no change, exactly per the slice-2
doctrine: the floor moves only with a row-bearing golden).

## 💡 Session idea

The one surprise this slice was `check_symbol_shadowing` red on a
VERBATIM port: two oracle modules in the same package (weather.py,
bait.py) both export `effect_text`, which the oracle tolerates and this
repo's rule 2 (package-unique public names) correctly refuses — but the
port plan's "constants and copy VERBATIM" instruction is silent about
symbol names, so the collision only surfaced at gate time. A one-line
addition to the porting recipe — "before writing a new domain module,
grep the package for each public symbol you are about to add; a
collision means rename-with-provenance-note, bytes stay verbatim" —
turns a late gate red into a 30-second pre-check, and it will fire
again: the oracle's `curios.py` (slice 4) exports `cost_text` /
`craftable_key_for`, and `craftable_key_for` ALREADY exists in this
slice's bait.py — the next slice hits this exact case in the same
package.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-fishing-slice2-rod.md@4493cc2`.)
Its recipe transferred wholesale again — the born-red sequencing, the
#193 re-home mechanics, the guard-as-pure-read handler shape, the
advisory-fence-then-re-read op shape and the band6 test skeleton were
all reused verbatim, and its ratchet doctrine ("run `--write-ratchet`,
commit whatever it produces, expect movement only from row-bearing
goldens") predicted this slice's no-op regen exactly — the
reconciliation paragraph it had to write became one sentence here. One
gap: its card never mentioned symbol-shadowing as a port-time check,
and this slice's only red was exactly that (see the session idea) — the
slice-2 modules simply never collided, so the recipe carried a silent
assumption that verbatim oracle names are package-safe.
