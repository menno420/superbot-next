# 2026-07-12 — btd6 boss-fight estimator (band 7, the last non-gated #144 parked domain item)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194 / ORDER 012)

## Scope

The deterministic boss-fight estimator — the successor slice the #237
card ledgered READY ("the boss estimator is now one self-contained
slice") and the last non-gated parked domain item on the #144 list.
Ships `sb/domain/btd6/estimator.py` (the port of shipped
`services/btd6_estimator_service.py`), the `estimate_card` command
surface (shipped `build_estimate_embed` query branch), and retires the
two ledgered deviation artifacts: the BLOCKED stub at
oracle_surface.py:137-140 and the oracle_cards.py:28 deviation bullet
(the ledger is now EMPTY). Read-only math: zero ops/DB legs, zero
EFFECT legs, compensator allowlist EMPTY.

## Oracle reconstruction (trap 24 ledger)

Reconstruction head **b0713fcd** (`git ls-remote` on the oracle —
UNCHANGED since #237's window; zero nightly churn this window). Fetched
WHOLE via raw.githubusercontent.com at the corpus pin **7f7628e1**:
`disbot/services/btd6_estimator_service.py` (570 lines),
`disbot/cogs/btd6/_builders.py` (the `build_estimate_embed` consumer),
plus the harness stack (`btd6_stats_service.py`, `tier_codes.py`,
`paragon_degrees.py`, `paragon_math.py`, `difficulty_costs.py`). Drift
check: estimator AND builders re-fetched at head b0713fcd diffed EMPTY
against the corpus pin — zero capture-sha drift on every file this
slice touches.

## Anchor evidence (the #225/#237 method)

Before any port code was written, the ORACLE'S VERBATIM
`btd6_estimator_service.py` was executed in a scratch harness over the
committed `sb/domain/btd6/data` tree (oracle-verbatim stats/tier_codes
stack; `resolve` delegated to the ported #208 resolver — the same
resolver both runs compose, itself anchor-verified). The run minted:
cost/DPS census over every tower × present valid+legal crosspath
(**1600 rows**, sha256 `39970a7c…6380`); the full cheapest-counters
surface (**all 7 bosses × tiers 1–5 = 35 rankings**, rows sha256
`81159c1c…2036`, rank-text sha256 `aa0719f6…79b4`); the 60-row track
index (sha256 `ee069c68…dc16`); 14 full KillEstimate grids covering
immunity-block (DartMonkey Sharp vs Dreadbloon), kills-before-exit
both verdicts, zero-DPS (BananaFarm), and all None-misses; find_boss/
find_map_track/parse_request/_extract_code tables; full format-text
byte anchors. The port re-ran the identical harness: **ANCHORS
IDENTICAL** — harness GLOBAL sha256 `5193d02961e3a2d1…f0bf` from both
runs.

## What shipped

1. **sb/domain/btd6/estimator.py** (NEW) — oracle
   `btd6_estimator_service.py` VERBATIM (KillEstimate/EstimateRequest/
   CounterRow, cost_for_code, dps_for_code with the
   `_INSTAKILL_DAMAGE_CAP` 100_000 sentinel exclusion, find_boss,
   `_track_index`/find_map_track greedy longest-name match, estimate
   with track context, resolve_tower/_extract_code/resolve_and_estimate,
   parse_request with tier-default-5 + map extraction, cheapest_counters
   `max(1, limit)` clamp, `_fmt_duration` + the two text formatters).
   Import seams only: stats→`sb.domain.btd6.stats`, tier_codes→ported
   tier_codes, resolver→`resolver.resolve` (#208),
   `get_dataset().bosses/.towers`/`read_blob`→`dataset.bosses()/
   towers()/read_blob`.
2. **sb/domain/btd6/oracle_cards.py** — `estimate_card(query)`: the
   shipped `build_estimate_embed` query branch verbatim (single-estimate
   / unresolvable / unknown-boss / counters arms, blurple, shipped
   title); the deviation bullet at line 28 RETIRED — the "Deviations"
   ledger is now `(none)`, with the PORTED parenthetical added in the
   freeplay/resolver retirement style.
3. **sb/domain/btd6/oracle_surface.py** — `cmd_estimate`'s BLOCKED
   stub (lines 137-140) RETIRED: non-empty query now renders
   `estimate_card` through the same `_card` lane as every sibling; the
   golden-pinned bare-usage branch untouched.
4. **tests/unit/band7/test_band7_btd6_estimator.py** — 70 tests: every
   anchor above pinned (full KillEstimate dict, full counters rows,
   full format-text bytes, `_fmt_duration` boundary table incl. the
   shipped 89.9s→"~90s" vs 90.0s→"~1.5 min" quirk, the shipped
   parse quirk "best vs vortex"→single-mode tower "best" carried), plus
   BOTH census digests (1600-row cost/DPS; 35-ranking counters) and the
   estimate_usage_card byte pin.

## Ingress verdict (trap-17/28, checked FIRST)

**DECLARED** — no golden blocks it. (a) trap-28: `_sweep_skips.json`
has NO estimate entry. (b) The prefix command `!btd6 estimate` was
ALREADY declared (manifest `_u("estimate", …)` since the #144-family
btd6 port) — `sweep_btd6_estimate` pins the BARE-usage card only, and
the query-bearing prefix path is golden-FREE, so the stub retirement
moves zero pinned bytes. (c) trap-17: `sweep_slash_btd6_estimate` pins
SLASH SILENCE (calls [], db_delta {}) — satisfied by the btd6 tree
being PREFIX-kind only; this slice declares no slash surface, so the
pin stays green by the same absence as every other sweep_slash_btd6_*.
Zero manifest/sim-gate/compat/lock/parity.yml/ratchet movement
(`--write-ratchet` untouched — no flip in this PR); manifest sha
unchanged (`96f34061…`, 48 manifests). No new exemption or disposition
classes.

## Ladder (serial, real Postgres — trap 25)

units **1715 passed / 2 skipped** (+70 = exactly this file over main's
1645); gate **GREEN 349/349 across 47 ported**; report **355/471
green, 471/471 replayable** (red-by-design); `check_parity_depth` OK
(50 subsystems, 46 ported, kernel ported, 471 goldens); full
named-gates fleet green (manifest_compile sha unchanged, namespace,
escape_hatches, schema_growth, amendments, compat_frozen, config_usage,
egress, metric_cardinality, money_race 0 violations, no_skip, sim_gate
1238 [A], symbol_shadowing, migrations 35, intent_survival, slash_cap
382); `bootstrap.py check --strict` green.

## What remains on the #144 parked list after this

CT-team flow (NK-live-gated — out of scope by standing order),
review-channel poster (parks with NL arming), live-NL leg
(OWNER-ACTION 5 key-gated), testing-report row 9 (live-testing pass) —
i.e. every remaining item is GATED; the non-gated domain ledger is
empty.

## 💡 Session idea

When a BLOCKED stub is the retirement target, mint the anchor set from
the CONSUMER file too (`_builders.py`, not just the service): the
query-branch copy ("I couldn't resolve that — …", the boss-roster
line) lives in the cog, not the service, and porting the service alone
would have left invented surface bytes. One raw fetch of the consumer
closed that hole and the whole surface is now byte-anchored.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-btd6-stats-normal-view.md`, #237.) Its
successor ledger was the best handoff this lane has produced: the
"needs exactly get_tower_stats+accessors, attack_breakdown(degree=None),
normal_stats, tier_codes.{4 fns}" list was verified EXACTLY right —
the estimator imported nothing else, and the slice needed zero new
stats work. Its raw-file-lane discovery (list it FIRST) held: this
session did zero search_code fragment stitching. One gap: the card's
readiness verdict bounded the SERVICE but not the CONSUMER — it named
"the two text formatters" in the service yet the cog's estimate-branch
copy (unresolvable/unknown-boss lines) wasn't in the scope list; the
session idea above is that lesson generalized.
