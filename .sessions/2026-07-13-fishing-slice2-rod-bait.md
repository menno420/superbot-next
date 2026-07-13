# 2026-07-13 — fishing depth slice 2 port: rod / bait (the gear-shop rung)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · high · feature build (Q-0194)

## Scope

The faithful port of fishing depth slice 2 — the gear-shop rung of the
D-0043 fishing ladder (slice 1 landed weather + venue on PR #313; this
branch is based on that PR's post-merge head `47ef721`, unmerged at
branch time). Two shipped commands moved from honest D-0043 pending
terminals to real surfaces: `!rod` · `!bait` — the oracle's own module
grouping (`utils/fishing/rods.py` + `bait.py` +
`views/fishing/rod_shop.py` + `bait_shop.py`; the craft* family is the
NEXT rung, per slice 1's 💡 idea: batch the argful craft lanes last).

Delivered:

- **Domain** (`sb/domain/fishing/rods.py` + `bait.py`, NEW): the shipped
  pure modules ported verbatim — the 5-rung `ROD_LADDER` (knobs +
  prices), `rod_for_tier`/`next_rod`, the `ROD_RECIPES` fish→rod shelf
  (carried as DATA — the shop embed's craft line is golden-pinned; the
  craft LANE rides the craft* rung); the 6-bait `BAIT_CATALOG`,
  `effect_text`, the `CRAFT_RECIPES` + `PEARL_BAIT_RECIPES` shelves
  (data — the shop's craft fields are golden-pinned, the lanes pending).
- **Stores + migrations**: `fishing_rod` (no row = starter tier 0 —
  shipped 087 shape; migration `0049`) and `fishing_bait` (no row / 0
  charges = bait-less — shipped 091 shape; migration `0050`) as
  MEMBER_ID registered stores with `fishing.erase_subject_rod` /
  `fishing.erase_subject_bait` delete-erasure legs (+ checksums).
- **Ops (money)**: `fishing.rod_upgrade` + `fishing.bait_buy` — audited
  one-leg buy txns (advisory fence → tier/loadout read →
  `wager.debit_in_txn` → tier bump / bait load; `_balance_changes` →
  `economy.balance_changed` after commit — the mining.vault_upgrade
  precedent). Oracle `buy_rod`/`buy_bait` success + refusal copy and
  the `fishing:rod_purchase`/`fishing:bait_purchase` reasons verbatim;
  same-bait stacking / different-bait replace semantics carried.
- **Handlers**: `fishing.rod_view` / `fishing.bait_view` (panel opens),
  `fishing.rod_upgrade_route` / `fishing.bait_buy_route` (guards as
  PURE reads — maxed / unknown-key / insufficient answer without a
  write, exactly as the oracle's rollback; only funded moves run ops).
- **Panels**: `fishing.rod_shop` (⬆️ Upgrade success · 🎣 Craft primary ·
  📋 Recipes secondary · ↩ Fishing menu; ECONOMY_COLOR gold; at-max
  disables Upgrade/Craft) and `fishing.bait_shop` (buy / craft-from-fish
  / craft-from-pearls selects with provider-fed rich options + ↩ back;
  live pearl count off mining_inventory) — both `session_lifecycle`,
  NO standard nav (the shipped views carried only their own back
  button); hub 🎒 Rod / 🪱 Bait repoint pending → `PanelRef` opens.
  Craft buttons/selects route the pending terminals, now registered at
  IMPORT in panels.py (burn-down pruned: `rod`/`bait` pending vanish;
  `craftbait`/`craftpearl`/`craftrod`/`rodrecipes` go import-visible).
- **Deferred (D-0043, honest)**: the cast LEG still rolls starter knobs
  — the owned rod's `rarity_pull`, the bait per-cast consume and the
  reel-fight knobs ride the minigame rung (deviation note updated in
  ops.py). The oracle's shop-panel note-footer rerender is under-ported
  to the result-card lane (the farm in-place-edit precedent); no golden
  pins a click.
- **Parity**: the 2 `_unmapped` sweeps re-homed into the gated `fishing`
  row (#193 law: `git mv` + the one sanctioned subsystem flip). The two
  new tables sit behind run-minted session components no imported
  golden can drive → 2 exemption rows: `fishing_rod` time-driven (the
  fishing_catch_log run-minted-button precedent), `fishing_bait`
  select-driven (the D-0064 select-ingress class). Ratchet UNCHANGED
  (the shop opens add no new covered tables — `--write-ratchet` was a
  no-op splice).

## Verification (local, real Postgres, provisioned per
docs/operations/local-verification.md)

- **golden-parity GATE GREEN — all 473 golden(s) across 51 ported
  subsystem(s) replay clean** (the +2 re-home; the rod/bait panels
  replay byte-identical through the PORTED fishing row).
- **check_parity_depth: OK — 51 subsystems (50 ported), kernel ported,
  484 goldens.**
- **pytest tests/: 2080 passed, 2 skipped** (includes the new
  `tests/unit/band6/test_band6_fishing_gear.py` — rod/bait modules
  verbatim, both shop renderers against the golden bytes, the option
  providers, both buy routes' guard copy, both buy legs' debit/stack/
  replace + refusal rollback, store specs/erasure refs, manifest + hub
  + panel shapes); **tests/integration: 11 passed**.
- **check_migrations: clean (50)**; **manifest_compile: green**
  (snapshot recompiled); **check_runtime_smoke: clean** (992 dispatch
  targets, 228 panels).
- **check_money_race: OK — 0 violations** (both buy legs advisory-fence
  before the read-then-settle debit — the #217 doctrine).
- **check_sim_gate: OK — 1360 [A] assignment(s), 543 auto-exempt
  below-floor** (both new panels sit at ≤4 actions+selectors →
  below-floor auto-exempt).
- **check_compat_frozen: OK** (rod/bait commands + aliases were already
  declared; only their routes went live — no new compat surface).
- The whole `tools/check_*.py` fleet: exit 0 across the board.
- `bootstrap.py check --strict`: the only red was the by-design
  born-red HOLD while this card declared `in-progress` — flipped
  `complete` in this final commit.

### 2 re-homed goldens (git mv `_unmapped → fishing`, subsystem flip only)

sweep_rod, sweep_bait — only the `"subsystem"` line changed
(`_unmapped` → `fishing`); calls/events/db_delta bytes untouched (#193
law). Both are read-only shop opens, so `fishing_rod`/`fishing_bait`
land exempt (button/select-driven writes) — the slice-1 💡 prediction
("the argful/gated lanes will need exemption rows") held exactly.

## 💡 Session idea

The kit's claim-bullet date regex (`\b20\d\d-\d\d-\d\d\b`) silently
fails on a full ISO timestamp — `2026-07-13T00:54:49Z` has no word
boundary between `13` and `T`, so a claim dated with the (natural)
`date -u` ISO form is invisible to the duplicate scan and warns
`claims-format` (three lanes' claims have hit this: mining's, slice 1's
and this one's first draft). One-line kit fix: allow `T` after the date
(`(?=[T\s·)]|$)`) or document "bare date only" in the claim template —
until then, write `· YYYY-MM-DD (claimed HH:MM:SSZ)`.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-fishing-slice1-forecast-sail.md`.) Its
💡 idea drove this slice's shape directly — "front-load the bare-write
toggles, batch the argful craft lanes last" is exactly why rod/bait
(open-only shops, one reviewed exemption block) came before the craft*
family, and the prediction priced correctly: both new tables landed
exempt, zero surprises at the depth gate. Its verification ladder
transcript also replayed verbatim (same commands, same green shapes),
which made this session's gate run mechanical. One gap: the card says
"the hub ⛵ Set sail / Dock button repoints … byte-neutral" but does not
name the PATTERN (pending → live is always byte-neutral when the golden
pins label + minted id only) — this slice re-derived that for the 🎒/🪱
buttons; slice 3's porter should treat "hub button repoint is
byte-neutral unless the golden pins a custom_id_override" as standing
doctrine.
