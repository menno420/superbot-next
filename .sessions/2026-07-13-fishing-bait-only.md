# 2026-07-13 — fishing: bait-only port (coordinated fill, lane #324)

> **Status:** `complete`

- **📊 Model:** Claude (Fable family) · high · feature build

## Scope

The BAIT-ONLY fill of the fishing gear rung, per the 2026-07-13
coordinator adjudication: PR #328 (`claude/fishing-slice2-rod-bait` @
`3ced297`, the rod+bait slice) collided with the #324 whole-lane fishing
claim (`control/claims/fishing-port-remaining.md`, earlier at HEAD) and
its landed rod slice (#330, merged at `4493cc2`). Ruling: rod is CEDED
to #330; this branch re-scopes the salvageable half — `!bait` and the
bait shop — as a coordinated fill of the one gear surface the #324 lane
has NOT put in flight (verified: no open PR / `claude/*` branch carries
bait work at branch time).

Planned shape (salvaged from `3ced297`, adapted to main's landed #330
shapes — `lock_rod_slot`, `fishing.buy_rod` op naming, the
`fishing.rod_panel` panel ids, the slice-2 PENDING dict):

- **Domain** (`sb/domain/fishing/bait.py`, NEW): the shipped
  `utils/fishing/bait.py` ported verbatim — the 6-bait `BAIT_CATALOG`
  (worm/grub/lure · minnow/spinner · feast), `effect_text`, the
  `CRAFT_RECIPES` + `PEARL_BAIT_RECIPES` shelves carried as DATA (the
  shop embed's craft fields are golden-pinned; the craft LANES stay
  pending — the craft* rung).
- **Store + migration**: `fishing_bait` (no row / 0 charges = bait-less
  — shipped 091 shape; migration `0050_fishing_bait.sql`, renumbered to
  follow main's 0049 ladder) as a MEMBER_ID registered store with the
  `fishing.erase_subject_bait` delete-erasure body (+ checksums).
- **Op (money)**: `fishing.buy_bait` — audited one-leg buy txn
  (advisory `lock_bait_slot` fence → loadout read → `wager.debit_in_txn`
  → load in ONE txn; `_balance_changes` → `economy.balance_changed`
  after commit — the #330 `fishing.buy_rod` / mining vault_upgrade
  precedent). Oracle `buy_bait` copy + the `fishing:bait_purchase`
  reason verbatim; same-bait stacking / different-bait replace carried.
- **Handlers**: `fishing.bait_shop` (panel open — the #330
  `fishing.rod_shop` naming), `fishing.bait_buy_route` (guards as PURE
  reads — unknown-key / insufficient answer without a write; only a
  funded pick runs the op).
- **Panel**: `fishing.bait_panel` (buy / craft-from-fish /
  craft-from-pearls selects with provider-fed rich options + ↩ Fishing
  menu; live pearl count off mining_inventory; ECONOMY_COLOR gold,
  `session_lifecycle`, NO standard nav); hub 🪱 Bait repoints pending →
  `PanelRef`. The craft selects route the `craftbait`/`craftpearl`
  pending terminals, registered at IMPORT in panels.py (burn-down
  pruned: `bait`/`craftbait`/`craftpearl` pending leave ensure-only).
- **Parity**: `goldens/_unmapped/sweep_bait.json` re-homed into the
  gated `fishing` row (#193 law: `git mv` + the one sanctioned
  `subsystem` flip); `fishing_bait` lands EXEMPT (select-driven — the
  D-0064 class); ratchet unchanged (a read-only open adds no covered
  table — the #330 lesson).
- **NO rod work anywhere in the diff** — rod/rodrecipes/craftrod are
  #330's, landed.

## Verification (local, real Postgres per docs/operations/local-verification.md)

- golden-parity `--gate`: **GREEN — all 475 golden(s) across 51 ported
  subsystem(s) replay clean** (474 at #330's merge + the re-homed
  sweep_bait replaying through the PORTED fishing row).
- `check_parity_depth`: OK — 51 subsystems (50 ported), kernel ported,
  484 goldens.
- `pytest tests/ -q`: **2086 passed, 2 skipped** ·
  `tests/integration -q`: 11 passed.
- `manifest_compile`: green (48 manifests, snapshot recompiled) ·
  `check_migrations` clean (50) · `check_money_race` 0 violations ·
  `check_sim_gate` OK (the bait panel's 4 slots are below-floor
  auto-exempt) · `check_compat_frozen` OK (the bait command's
  name/aliases/description bytes unchanged by the `_pending`→`_cmd`
  flip) · namespace / shadowing / no-skip / config-usage /
  runtime-smoke / escape-hatches / slash-cap all clean.
- `bootstrap.py check --strict`: exit 0 (the born-red hold flips with
  this landing commit; one pre-existing claims-format advisory on
  another lane's claim file).
- One environmental note: the local `parity_replay` DB carried the OLD
  branch's 0049 checksum in `schema_migrations` (this container ran the
  #328 replay earlier); one `DROP SCHEMA public CASCADE` reset per the
  runbook's recovery posture and the gate ran clean — local state, not
  a repo defect.

## Reconcile addendum (02:51Z)

While #338's first CI run was in flight, the #324 lane landed its OWN
bait slice — #342 (`3e4a77d`, bait / craftbait / craftpearl /
craftcharm) — a functional superset of this branch's port with
near-identical shapes (same `fishing.bait_shop` / `bait_buy_route`
handler names, same `fishing.bait_panel` id, same `lock_bait_slot` +
`record_buy_bait` stacking leg; their `bait_effect_text` vs this
branch's `effect_text` alias the same bytes). Per coordinator ruling:
this branch merged `origin/main` (merge, never rebase), resolved every
functional file to main's landed #342 version, and re-scoped the PR to
the DELTA ONLY — three tests #342's suite lacks, appended to its own
`tests/unit/band6/test_band6_fishing_bait.py`:

- `test_bait_buy_leg_loads_stacks_and_replaces` — the leg's oracle
  Loaded/Topped-up copy, same-bait stack / different-bait replace
  arithmetic, `_balance_changes` shape (main pinned guards only).
- `test_bait_buy_leg_insufficient_is_defensive_and_writes_nothing` —
  the defensive leg path rolls back without a load.
- `test_bait_shop_renderer_loaded_state_bytes` — the LOADED-state shop
  description (sweep_bait pins only the fresh bait-less open; no golden
  covers this branch of `build_bait_embed`).

Fishing is fully the #324 lane's from here — no further fishing work.

## 💡 Session idea

Adjudicated re-scopes should salvage by PATHS, not by commits: cherry-
picking any of `3ced297`'s commits would have dragged rod hunks into a
lane that ceded rod, while path-level extraction (`git show
SHA:path`, then adapt refs to the landed peer shapes — `lock_rod_slot`,
`fishing.buy_rod` naming, `fishing.rod_panel` ids) produced a clean
bait-only diff in one pass. A three-line "salvage by path, adapt names
to the landed winner, verify the golden byte-for-byte" note in the
porting skill would make the next collision re-scope mechanical.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-13-fishing-slice2-rod.md@4493cc2` — the peer
lane's rod slice this fill builds on.) Its shapes transferred verbatim:
the `lock_rod_slot` fence wording, the `_op_after` handler pattern, the
guard-as-pure-read posture and the exemption-row format were all
directly reusable for the bait twin, and its ratchet lesson ("guard-only
sweeps move nothing — the floor rises only with a row-bearing golden")
is exactly why this fill ships with the fishing ratchet untouched. One
friction: its card and #330 body don't state whether the lane's NEXT
slice had started, so this fill had to prove the negative from the
remote branch list + open-PR sweep — a one-line "next slice: not
started" trailer on lane cards would make coordinated fills instant.
