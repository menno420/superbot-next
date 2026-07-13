# 2026-07-13 — fishing depth slice 3 port: bait / craftbait / craftpearl / craftcharm (bait shelf)

> **Status:** `in-progress`

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

## Verification (local, real Postgres, pristine parity_replay DB)

(pending — filled at the card flip)

### 4 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_bait, sweep_craftbait, sweep_craftpearl, sweep_craftcharm — only
the `"subsystem"` line changes (`_unmapped` → `fishing`);
calls/events/db_delta bytes untouched (#193 law).

## 💡 Session idea

(pending — filled at the card flip)

## ⟲ Previous-session review

(pending — filled at the card flip; covers
`.sessions/2026-07-13-fishing-slice2-rod.md@4493cc2`.)
