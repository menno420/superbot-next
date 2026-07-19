# Session — mining rewards roll/derivation math: cover the untested pure legs

> **Status:** `in-progress`
>
> Born-red: this card is the session's FIRST commit (holds the substrate-gate).
> The test lands next; the flip to `complete` is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 5) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Read-only HUNT on
UNCLAIMED-domain pure math found that `sb/domain/mining/rewards.py` has FIVE
public derivation legs and only ONE (`mine_multiplier`) is tested
(`tests/unit/mining/test_mining_grid.py`). The rounding/clamping/tie-break legs
— exactly the btd6-costs pattern (pure, never raises on a wrong answer) — are
uncovered: `ore_weights_for_depth` (the `max(0.5, …)`/`max(0, depth)` clamps),
`roll_mine_loot` (the `max(1, round(...))` amount floor + None-multiplier legacy
branch), `roll_harvest_amount` (axe doubling), `roll_explore_outcome` (the
weight-drop tuple shape) and the `EXPLORE_OUTCOMES` table invariants.

## Scope

Test-only. Added `tests/unit/mining/test_mining_rewards.py`. Zero `sb/` source
edited; no dependency change (pip-audit n/a). Mining is NOT a claimed domain
this round.

## What the tests pin

[[fill: assertion summary after write — verified against a live run of the real
functions]]

## Verification

[[fill: pytest tail + counts, guard exits, bootstrap check]]

## 💡 Session idea

[[fill]]

## ⟲ Previous-session review

[[fill: previous-session review byte-form]]
