# Session — mining rewards roll/derivation math: cover the untested pure legs

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`): the first commit was this card alone (born-red, held
> the substrate-gate); the test landed in the second commit; this flip is the
> last.

- **📊 Model:** opus-4.8 · high · test writing

## Order

High-bar improvement probe (round 5) — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Read-only HUNT on
UNCLAIMED-domain pure math found that `sb/domain/mining/rewards.py` has five
public derivation legs and only ONE (`mine_multiplier`) is tested
(`tests/unit/mining/test_mining_grid.py`). The rounding/clamping/tie-break legs
— exactly the btd6-costs pattern (pure, never raises on a wrong answer) — were
uncovered.

## Scope

Test-only. Added `tests/unit/mining/test_mining_rewards.py` (13 tests). Zero
`sb/` source edited; no dependency change (pip-audit n/a). Mining is NOT a
claimed domain this round.

## What the tests pin

Behavior of the four untested legs of `sb/domain/mining/rewards.py`, each
assertion verified against a live run of the real functions:

1. **`ore_weights_for_depth` — the clamps.** Depth 0 reproduces `ORE_WEIGHTS`
   verbatim; a negative depth clamps to the surface (`max(0, depth)`); at depth
   5 the `max(0.5, …)` floor holds stone AND bronze at 0.5 while the precious
   ores scale +0.5·depth — and every weight stays `> 0` (the guarantee the
   floor exists for: stone/bronze never reach zero/negative mass in
   `random.choices`). Boundary pinned: stone is 1.0 at depth 2, exactly 0.5 at
   depth 3.
2. **`roll_mine_loot` — floor, depth pass-through, multiplier source, tie-break.**
   The weights handed to `choices` ARE `ore_weights_for_depth(depth)` and the
   returned ore is the selected key; **the `max(1, round(...))` amount floor**
   (a 0.2 product → 1, never 0 — the sharpest guard: a fractional multiplier
   would otherwise award zero ore silently); banker's rounding pinned (1.5→2
   AND 2.5→2, so an arithmetic-rounding regression is caught); the
   None-multiplier→has_pickaxe legacy branch is exercised WITHOUT a spurious
   amount claim (honestly noted: within the real 1..2 roll range the ×1.125
   legacy curve rounds to the same integer as ×1.0, so the test pins the branch
   is taken and floors, not a difference the shipped math does not produce);
   seeded-rng determinism.
3. **`roll_harvest_amount`** — `randint(1,3) * (2 if has_axe else 1)`
   (axe → 6, bare → 3) + seeded determinism.
4. **`roll_explore_outcome` + `EXPLORE_OUTCOMES`** — one roll returns
   `(narration, item, amount)` with the 4th weight slot dropped, and the
   weights passed to `choices` are the table's weight column; table invariants
   (4 entries, exactly one hazard with negative amount, exactly one None-item
   nothing-found, all weights positive, the oracle-verbatim gold-camp row).

## Verification

- `python3 -m pytest -q tests/unit/mining/test_mining_rewards.py` →
  **13 passed** in 0.05s.
- Full `python3 -m pytest -q --ignore=examples` (Postgres started + discord
  present) → **3649 passed, 2 skipped, 1 warning** in 115s. The 2 skips are
  pre-existing/unrelated; the 1 warning is the pre-existing `discord/player.py`
  `audioop` DeprecationWarning (stdlib, unrelated). Baseline for this branch was
  3636 (the egress card's run) — the +13 delta is exactly this file, no other
  test moved.
- Guards clean (**0 fires** attributable to this slice): `check_namespace`,
  `check_symbol_shadowing`, `check_config_usage`, `check_no_skip` — each exit 0.
- `python3 bootstrap.py check` → exit 0; this card validates `complete` at HEAD
  (born-red hold cleared by this flip). Any guard-fires delta appended by the
  check is pre-existing ADVISORY telemetry unrelated to this test-only slice
  (committed per the check's own "commit the delta" instruction).
- No dependency change — `requirements.lock` untouched, pip-audit gate n/a.

## 💡 Session idea

The mining reward legs are the shipped *legacy* (`multiplier=None`) surface;
`mine_multiplier` is the *equipped-tool* curve that now feeds `roll_mine_loot`
via its `multiplier=` arg. A latent honesty seam surfaced while writing test 4:
within the real `randint(1, BASE_ROLL_MAX=2)` range the ×1.125 legacy pickaxe
bonus rounds to the SAME integer as bare hands (`round(1.125)=1`,
`round(2.25)=2`) — so the legacy pickaxe is a **no-op on the loot amount** for
every possible roll, only paying off once `BASE_ROLL_MAX` grows or a tool
multiplier ≥ ~1.3 is passed. That is shipped-verbatim (not a bug), but it means
the "pre-equipment players lose nothing" comment is stronger than the reward it
describes: the legacy bonus is currently invisible. Worth a one-line note on
`LEGACY_PICKAXE_MULT` (or a decisions.md row) so a future rebalance that raises
`BASE_ROLL_MAX` knows the legacy curve silently activates. Guard recipe: anchor
on `LEGACY_PICKAXE_MULT`/`BASE_ROLL_MAX` in `sb/domain/mining/rewards.py`; if a
behavioral pin is ever wanted, a golden over `roll_mine_loot(has_pickaxe=True)`
across the full roll range documents the no-op explicitly.

## ⟲ Previous-session review

Predecessor convention carried from the night's test-writing thread
(`.sessions/2026-07-19-egress-allowed-mentions.md`, `complete` — same
`opus-4.8 · high · test writing` class): read-only HUNT first, a born-red card
as the sole first commit holding the substrate-gate, a verification section that
re-runs the exact commands and records tails/counts, and a scope adding ONE
self-contained test file touching zero `sb/` source. One concrete carry heeded:
that card's `previous-session review` flagged the *partially-covered seam*
discipline (prove the exact untested branches are genuinely uncovered before
writing, don't re-pin what an existing test already asserts) — applied here by
first confirming `mine_multiplier` IS covered in `test_mining_grid.py` and the
four roll/derivation legs are NOT, then testing only the genuine gap. Where this
slice diverges: the egress gap was a security fence (mass-ping); this is
game-economy loot math — lower blast radius, but the same "never raises on a
wrong answer" failure mode (a silent 0-ore award or a dropped weight floor),
which is exactly why the `max(1, …)` and `max(0.5, …)` clamps are the assertions
that earn their keep.
