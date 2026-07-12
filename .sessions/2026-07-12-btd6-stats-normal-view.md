# 2026-07-12 — btd6 per-crosspath combat-stats derivation (band 7, the boss estimator's named prerequisite)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The stats normal-view derivation `sb/domain/btd6/stats.py` explicitly
parked as a named successor ("the full tower/hero normal-view
derivation (per-tier headline stats over the cleaned nodes)") — the
prerequisite the #234 card named for the boss estimator, and exactly
what the oracle estimator's own docstring consumes ("per-crosspath
combat stats (:mod:`services.btd6_stats_service`)"). Read-only domain
math: zero ops/DB legs, zero EFFECT legs, compensator allowlist EMPTY.
The boss estimator itself is the NEXT slice — deliberately not started.

## Oracle reconstruction (trap 24 ledger)

Reconstruction head **b0713fcd** — and this window had a materially
stronger lane than fragment stitching: `raw.githubusercontent.com`
served FULL FILES at the pinned ref through the proxy (the
`api.github.com` 403 does not extend to raw). Fetched whole at
b0713fcd: `disbot/services/btd6_stats_service.py`,
`disbot/utils/btd6/tier_codes.py`, `disbot/utils/btd6/
paragon_degrees.py` (+ `paragon_math`/`difficulty_costs` for the
harness), `disbot/services/btd6_estimator_service.py` (readiness
bounding only), and both oracle unit suites
(`tests/unit/services/test_btd6_stats_service.py`,
`tests/unit/utils/test_btd6_tier_codes.py`). Drift check: the same two
source files re-fetched at the corpus pin **7f7628e1** diffed EMPTY —
zero capture-sha drift on this surface. Data check: 9 stats blobs
(bomb_shooter, wizard_monkey, druid, sniper_monkey, banana_farm,
beast_handler, heroes/quincy, heroes/obyn_greenfoot,
paragons/goliath_doomship) byte-identical between the oracle @b0713fcd
and our committed `sb/domain/btd6/data/stats/` tree.

## Anchor evidence (the #225 method, upgraded)

Before any port code was written, the ORACLE'S VERBATIM modules were
executed in a scratch harness over our committed data tree
(`derive_anchors` — stub `btd6_data_service` pointed at
`sb/domain/btd6/data`). The run reproduced every constant in the
oracle's own unit suite (bomb 375/600000/15-upgrades/64-tiers; base
bomb 1/Explosion/"Cannot damage Black"/22/1.5/40/no-camo; wizard 005
headline 2 dmg — NOT the reanimated BFB's 100; quincy pierce 3→9 with
camo at 20; goliath d65 cooldown 0.4215, d100 = d1·2+10) plus exact
byte anchors the oracle tests only substring-check (specials tuples
like "Bank $7,000 capacity, +15% interest/round"; the full
`crosspaths_for("200")` 10-tuple), plus a **corpus-wide census**: 25
towers, **1600 tier derivations**, 627 camo-true, 818 specials, sha256
`c8096554…41` over every tier's full normal view. The port re-ran the
same harness: **ANCHORS IDENTICAL**, digest included. Fragment-order
mistakes are ruled out by construction.

## What shipped

1. **sb/domain/btd6/tier_codes.py** (NEW) — oracle
   `utils/btd6/tier_codes.py` VERBATIM (the 5-2-0 legality rule,
   primary-path highest-tier-then-lowest-index — the oracle's own
   "2-0-2" bug-fix comment carried, candidate/preferred parents,
   canonical-16-then-crosspaths display order).
2. **sb/domain/btd6/stats.py** — grows the tower/hero lanes beside the
   existing paragon lane: `NormalStats`/`TowerStats` (tier accessor,
   `tier_codes()` display order, `crosspaths_for` — the per-crosspath
   seam) /`HeroStats` (+ loaders, per-id caches on the module's
   existing lock pattern, `reset_stats_cache` extended); the
   normal-view derivation verbatim (`_iter_dicts`,
   `_REANIMATED_MINION_NAMES` incl. both name generations,
   `_main_projectile`, `_money`, `_collect_specials` — stun/income/
   cash-crate/banana/bank/damageToBad/ability/knockback arms in the
   shipped order, `filterInvisible` camo scan); the per-attack
   breakdown layer verbatim (`DegreeAttack`, `attack_breakdown` with
   its degree arm, `rough_attack_dps`, `main_projectile_stats`,
   `ParagonDegreeStats`, `paragon_stats_at_degree`). Module docstring
   ledger updated: normal-view derivation retired from the NOT-here
   list (the D-0071/72/74/#208/#225/#234 retirement-loop, seventh
   application); still parked there: minion/sub-tower indexes, the
   upgrade-detail resolver, the paragon description/abilities join,
   `degree_row`.
3. **tests/unit/band7/test_band7_btd6_stats_normal_view.py** — 48
   tests: the oracle's two unit suites carried (tier_codes legality/
   classification/parents/ordering; loader/derivation/crosspath/hero/
   breakdown pins), tightened to exact oracle-run byte anchors, plus
   the corpus-wide census digest pin. One deviation from a first-guess
   assertion, data-corrected: `canonical` in the committed blobs is
   game-native `"BombShooter"` (not display-form) — pinned as the data
   says.

Zero new commands/panels/modals/events/tables/settings; no parity.yml,
ratchet (`--write-ratchet` byte-stable), compat, sim-gate, or lock-file
movement; manifest hash unchanged (48 manifests). No new exemption or
disposition classes. Trap-17/28: no command surface is declared or
touched by this slice, so no sweep-skip/undeclared-surface question
arises. **Zero golden movement, stated per the slice rules:** no golden
pins any normal-view stats surface — the derivation is new domain math
no handler consumes yet (the estimator slice will be its first
consumer); gate count unchanged at 347/347.

## Ladder (serial, real Postgres — trap 25)

units **1654 passed / 2 skipped** (+48 = exactly this file over #234's
1606/2); gate **GREEN 347/347 across 46 ported**; report **353/471
green, 471/471 replayable** (movement is parallel-lane, not this
slice); `check_parity_depth` OK (50 subsystems, 45 ported, kernel
ported, 471 goldens); full named-gates fleet green (manifest_compile
sha unchanged, namespace, escape_hatches, schema_growth, amendments,
compat_frozen, config_usage, egress, metric_cardinality, money_race 0
violations, no_skip, sim_gate 1232 [A], symbol_shadowing, migrations
34, intent_survival, slash_cap 382); `bootstrap.py check --strict`
green.

## Estimator readiness (successor verdict)

The boss estimator (`btd6_estimator_service.py` @b0713fcd, fetched
whole) is now **one self-contained slice**: its stats-side needs are
exactly `get_tower_stats` (+ `.tier`/`.tiers`/`.upgrades`/`.base_cost`/
`.canonical`/`.has_combat_stats`), `attack_breakdown` (degree=None
arm), `normal_stats` (damage_type/can_see_camo), and `tier_codes`
(`is_valid_code`/`digits`/`is_legal`/`format_code`) — ALL shipped
here and anchor-verified. Its remaining inputs already exist:
`bosses.json` + `map_track_lengths.json` are committed blobs,
`resolver.resolve` is ported (#208). Estimator scope for the successor:
`KillEstimate`/`CounterRow`/`EstimateRequest`, cost_for_code,
dps_for_code (`_INSTAKILL_DAMAGE_CAP` 100_000), find_boss,
`_track_index`/find_map_track, estimate, parse_request (tier default
5), cheapest_counters, the two text formatters, plus the
`!btd6 estimate` surface (check `_sweep_skips.json` + trap-17 before
declaring; the oracle_surface BLOCKED stub at oracle_surface.py:137-140
and the oracle_cards.py:28 deviation bullet are the retirement
targets).

## 💡 Session idea

`raw.githubusercontent.com` at a pinned sha punches through where
`api.github.com` 403s — full-file oracle reconstruction with an exact
ref pin beats fragment stitching on both fidelity and cost (one curl vs
~30 search_code queries), and it upgrades the #225 anchor method: you
can run the oracle's OWN code over the port's data and diff outputs
mechanically instead of transcribing published anchors by hand. The
census-digest pattern (hash every derived tuple corpus-wide, pin one
sha) turns "the port matches the oracle" from a sample claim into a
1600-point proof that lives in the unit suite forever.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-btd6-seed-data-terminal.md`, #234.) Its
successor pick was exactly right and priced right: "the boss estimator
should start by shipping the stats normal-view derivation as its OWN
slice" — this session is that slice, and the estimator file confirms
the split (the estimator body is thin arithmetic over this seam). Its
trap-24 ledger habit (name the reconstruction head in the card)
transferred and paid off: knowing the corpus pin let this session prove
zero drift instead of assuming it. One under-call: it framed the
reconstruction lane as search_code-only ("search_code fragments
returned…"); the raw-file lane was available all along and would have
saved #234's fragment pass too — successor cards should list it first.
