# 2026-07-12 — btd6 freeplay MOAB scaling (band 7, the #144 parked domain item)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The next item on the #144 parked DOMAIN list (freeplay MOAB scaling ·
~~resolver maps/modes~~ (#208) · boss estimator · CT-team flow ·
seed-data terminals): the oracle's recursive ``bloon_rbe_at_round``
spawn-tree walk and every freeplay-scaling surface our ported tree
consumes it through. This retires the oracle_cards.py deviation-ledger
bullet "freeplay MOAB scaling (effective RBE, rounds 81+) is not
recomputed" — the D-0071/72/74/#208 parked-item retirement loop applied
a fifth time (grep the ledger sentence, port, retire it in the same
diff).

## Oracle reconstruction (trap 24 ledger)

search_code fragments returned ref **1ecc2113** throughout (the oracle
default branch churned past the 7349c8a7/b2b7fe0c heads the #208 wrap-up
ledgered; corpus pin stays `7f7628e1`). Sources reconstructed fragment
by fragment: `disbot/services/btd6_data_service.py`
(`HealthScalingBracket`, `moab_class_health_multiplier`,
`bloon_health_at_round`, `_rbe_at_round`, `bloon_rbe_at_round`,
`_group_fortified`, `_effective_round_rbe`, the `round_rbe` effective
wiring incl. the capped-`per_round` `any_scaled` quirk),
`disbot/cogs/btd6/_builders.py` (`build_rbe_embed`'s scaled single-round
desc + two-column range table + `scaling_note` footer — the UNSCALED
branch matched our shipped bytes verbatim, validating the #144-era
port — the round-range card's effective-in-column/`rbe_total`/footer
note, `build_round_embed`'s "Effective RBE (freeplay-scaled)" field),
`disbot/services/btd6_context_service.py` (the `[btd6_bloon]` MOAB-class
late-game scaling note), `disbot/data/btd6/bloon_scaling.json`
(byte-identical to our committed copy), and the oracle's own tests
(`test_btd6_bloon_scaling.py`, `test_btd6_round_rbe.py`). Fragments were
diffed against the goldens FIRST: the only goldens on this surface
(sweep_btd6_rbe / sweep_btd6ref_rbe, round 3) pin PRE-scaling bytes —
zero capture-sha drift risk on pinned bytes, and the round-3 render is
byte-identical before/after (unit-pinned + gate-proven).

The reconstruction was verified END-TO-END against the oracle's own
anchors before any test was written: v(100)=1.40 / v(140)=5.00, BAD
r100 = 28,000 HP / **67,200 RBE** (per-unit chain MOAB 552 → BFB 3,188 →
ZOMG 18,352, DDT 832 — the oracle 2026-06-23 session card's figures,
reproduced to the unit), fortified BAD r140 = 200,000 HP, superceramic
68/128, and the methodology proof (rounds 1–80: per-group spawn-tree sum
== stored base RBE, ZERO mismatches over the full default set).

## What shipped

1. **sb/domain/btd6/freeplay.py** (NEW) — the scaling block:
   `HealthScalingBracket` + the `bloon_scaling.json` parse
   (`FreeplayScaling`), `moab_class_health_multiplier` (piecewise-linear
   brackets, `round(·, 4)`, below-first-bracket → 1.0, past-last →
   clamp), `bloon_health_at_round`, the recursive `_rbe_at_round` walk
   (ceramic → Super Ceramic bottom-out, non-MOAB → stored base,
   MOAB-class → scaled body + children recursion, per-child fortified
   inheritance `"fortified" in modifiers` — oracle bytes), the
   `bloon_rbe_at_round` wrapper, and `effective_round_rbe` over our raw
   round dicts (the oracle's `RoundEntry` types ride D-0046 — ledgered).
2. **sb/domain/btd6/dataset.py** — `BloonEntry` grows `children_list`
   (dict-rows-only parse posture, oracle verbatim).
3. **sb/domain/btd6/oracle_cards.py** — `round_rbe` wires
   `effective_rbe`/`effective_rbe_total`/`scaled` for real (single:
   `effective != base`; range: all-or-None total, `any_scaled` over the
   CAPPED per_round rows — quirk carried); `rbe_card` gains the shipped
   scaled single-round desc, the two-column scaled range table (incl.
   the dead inner `'—'` conditional, carried) and the `scaling_note`
   footer (set ONLY when scaled — round-3 golden bytes carry no footer,
   unchanged); `_round_range_card` shows effective-in-column, totals the
   effective figure, and appends "RBE freeplay-scaled (rounds 81+)" to
   the footer; `round_card` gains the "Effective RBE (freeplay-scaled)"
   field on scaled rounds; module-docstring deviation ledger updated
   (MOAB bullet retired; boss-estimator bullet stands).
4. **sb/domain/btd6/context.py** — `_render_bloon` gains the shipped
   MOAB-class `[btd6_bloon]` late-game scaling note (×1.4-by-r100 /
   r100 HP + RBE figures); docstring names the parked freeplay-adjacent
   context surfaces (the deterministic "HP of <bloon> at round N" reply,
   the richer "Round N — RBE, cash & XP" grounding block).
5. **tests/unit/band7/test_band7_btd6_freeplay_scaling.py** — 39 tests:
   the bracket curve pins (16 rounds incl. clamp + below-first-bracket +
   fixture-absent → None), the oracle health/RBE anchors, the per-unit
   r100 chain, superceramic swap pins, the rounds-1–80 methodology
   proof, round_rbe single/range wiring (r81 effective < base — the
   oracle's own divergence test), the round-3 golden bytes pinned
   unchanged, scaled card byte pins (single/two-column/footers/field),
   and the context note pins.

Zero new commands/panels/modals/events/tables/settings; no parity.yml,
ratchet, compat, sim-gate, or lock-file movement; no exemptions, no new
reason classes, compensator allowlist EMPTY (read-only domain slice, no
ops/DB legs). Trap-28 check: `/btd6 rbe` (slash) is a listed sweep-skip
("dataset-scale compute races the settle budget") and stays undeclared;
the golden-pinned prefix `!btd6 rbe` / `!btd6ref rbe` surfaces are
untouched in the manifest.

## Parked (unchanged, honest)

The head's `roundset="alternate"`/ABR parameter on `round_rbe`/
`round_cash`/`build_rbe_embed` and the single-round `breakdown` key
(+ `_bloon_base_rbe`) are post-capture oracle drift — not carried
(ledgered in freeplay.py). The context-side deterministic "HP of <bloon>
at round N" reply and the round-economy grounding block ride the context
docstring's parked list. Still on the #144 parked list: the boss
estimator arm, the CT-team guided-set flow (NK-live-gated), the
`!btd6 ops seed-data` terminals (sweep-skip, trap 28).

## Ladder (serial, real Postgres — trap 25)

units **1544 passed / 2 skipped** (+39 = this file; baseline moved
1496→1505 under the parallel #224 casino flip); gate **GREEN 331/331
across 41 ported** (btd6-family 103/103 green); report **337/467 green,
467/467 replayable**; check_parity_depth OK (50 subsystems, 41 ported,
467 goldens); manifest_compile green (47 manifests, hash unchanged) +
the full 20-checker committed fleet green. The slice mints zero goldens
and moves zero gate/report counts — no golden pins any 81+ round render
(stated per the slice rules).

## 💡 Session idea

The strongest fidelity check this session wasn't a golden — it was the
oracle's OWN redundancy: reconstruct the formula from fragments, then
replay the oracle's published anchors (session-card per-unit chains,
its unit tests' constants, the data file's validation prose) against
the port BEFORE writing any test. When three independent oracle sources
agree with the reconstruction to the unit, fragment-order mistakes are
effectively ruled out; future walk-ports should treat "does the oracle
publish its own anchors anywhere?" as step zero.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-11-btd6-resolver-maps-modes.md` + the
band-7 continuation wrap-up card.) The #208 card's parked list and the
wrap-up's remaining map were exactly right, including the warning that
this item is NOT self-contained like maps/modes — "budget a full trap-24
fragment pass before writing code" was accurate (the reconstruction took
~30 search_code queries across four oracle files before one line of
port was written). Its trap-24 discipline (diff fragments against
goldens FIRST) transferred verbatim; the empty-state/golden check
happened before any edit here too. One thing the wrap-up under-called:
it framed the kernel-band minted golden set as the higher-value pick —
but the parallel parity lane's btd6-family re-homes (103/103 green at
this head) made the domain walk the better complement, since the freshly
re-homed btd6 goldens now gate this file's every byte on every PR.
