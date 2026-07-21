"""Pure derivation-math coverage for ``sb/domain/mining/rewards.py``.

``mine_multiplier`` is already pinned in ``test_mining_grid.py``; the other
four public legs — the rounding/clamping/tie-break math that never raises on a
wrong answer — were untested. Every assertion below is pinned against a live
run of the real functions (shipped-verbatim math; behavior-preserving
coverage, no product-semantics change). rng is injected so the draws are
deterministic without monkeypatching the module-global ``random``.
"""

from __future__ import annotations

import random

from sb.domain.mining import rewards as R


# --- a deterministic rng that still returns REAL members of the passed
#     population, so the structural assertions stay honest -----------------------


class _FakeRandom:
    def __init__(self, *, pick_index: int = 0, randint_value: int = 1) -> None:
        self.pick_index = pick_index
        self.randint_value = randint_value
        self.choices_calls: list[tuple[list, list]] = []

    def choices(self, population, weights, k=1):  # noqa: D401 — rng shim
        self.choices_calls.append((list(population), list(weights)))
        return [population[self.pick_index]]

    def randint(self, a, b):  # returns a fixed value inside [a, b]
        assert a <= self.randint_value <= b
        return self.randint_value


# --- ore_weights_for_depth: the max(0.5, …) / max(0, depth) clamps --------------


def test_ore_weights_depth_zero_is_the_base_table() -> None:
    """Depth 0 reproduces ORE_WEIGHTS exactly (no scaling applied)."""
    w = R.ore_weights_for_depth(0)
    assert w == {
        "stone": 3, "bronze": 2.5, "iron": 2, "silver": 1.5, "gold": 1,
        "diamond": 0.5,
    }


def test_ore_weights_negative_depth_clamps_to_zero() -> None:
    """`max(0, depth)` — a negative depth is treated as the surface."""
    assert R.ore_weights_for_depth(-3) == R.ore_weights_for_depth(0)


def test_ore_weights_deep_hits_the_0_5_floor_and_scales_precious() -> None:
    """The `max(0.5, …)` floor keeps stone/bronze reachable at depth (never
    zero/negative, so `random.choices` always has positive mass on them),
    while the precious ores scale up linearly (+0.5·depth)."""
    w = R.ore_weights_for_depth(5)
    assert w["stone"] == 0.5          # max(0.5, 3 - 5)
    assert w["bronze"] == 0.5         # max(0.5, 2.5 - 2.5)
    assert w["iron"] == 4.5           # 2 + 0.5*5
    assert w["silver"] == 4.0
    assert w["gold"] == 3.5
    assert w["diamond"] == 3.0
    assert all(v > 0 for v in w.values())  # the guarantee the floor exists for


def test_ore_weights_stone_floor_engages_at_depth_three() -> None:
    """Boundary: stone = max(0.5, 3 - d) is 1.0 at d=2, exactly 0.5 at d=3."""
    assert R.ore_weights_for_depth(2)["stone"] == 1.0
    assert R.ore_weights_for_depth(3)["stone"] == 0.5


# --- roll_mine_loot: amount floor, depth pass-through, multiplier source --------


def test_roll_mine_loot_passes_depth_weights_and_returns_picked_ore() -> None:
    """The weights handed to `choices` ARE `ore_weights_for_depth(depth)`, and
    the returned ore is the key `choices` selected (population is the six ore
    names in table order)."""
    rng = _FakeRandom(pick_index=5, randint_value=2)  # index 5 == diamond
    ore, amount = R.roll_mine_loot(has_pickaxe=False, depth=3, multiplier=3.0,
                                   rng=rng)
    assert ore == "diamond"
    pop, weights = rng.choices_calls[0]
    assert pop == ["stone", "bronze", "iron", "silver", "gold", "diamond"]
    assert weights == list(R.ore_weights_for_depth(3).values())
    assert amount == 6                # round(2 * 3.0)


def test_roll_mine_loot_amount_never_drops_below_one() -> None:
    """`max(1, round(...))` — a sub-1 product (here 0.2, or the banker's
    rounding of 0.5→0) still awards at least one ore. This is the sharp guard:
    without the floor a fractional multiplier silently yields 0."""
    rng = _FakeRandom(pick_index=0, randint_value=1)  # 1 * 0.2 = 0.2, round→0
    ore, amount = R.roll_mine_loot(has_pickaxe=False, multiplier=0.2, rng=rng)
    assert ore == "stone"
    assert amount == 1


def test_roll_mine_loot_uses_bankers_rounding_on_the_amount() -> None:
    """Python `round` is round-half-to-even: 1.5→2 AND 2.5→2. Pinned so a
    switch to arithmetic rounding (2.5→3) is caught as a behavior change."""
    assert R.roll_mine_loot(has_pickaxe=False, multiplier=1.5,
                            rng=_FakeRandom(randint_value=1))[1] == 2
    assert R.roll_mine_loot(has_pickaxe=False, multiplier=2.5,
                            rng=_FakeRandom(randint_value=1))[1] == 2


def test_roll_mine_loot_none_multiplier_takes_the_legacy_pickaxe_branch() -> None:
    """multiplier=None routes through has_pickaxe: the legacy pickaxe applies
    LEGACY_PICKAXE_MULT, bare hands applies 1.0. Within the real roll range
    (1..BASE_ROLL_MAX) the ×1.125 legacy curve rounds to the same integer as
    ×1.0, so this pins the branch is taken WITHOUT raising and floors correctly
    — not a spurious amount difference the shipped curve does not produce."""
    legacy = R.roll_mine_loot(has_pickaxe=True, multiplier=None,
                              rng=_FakeRandom(randint_value=2))
    plain = R.roll_mine_loot(has_pickaxe=False, multiplier=None,
                             rng=_FakeRandom(randint_value=2))
    assert legacy[1] == 2            # round(2 * 1.125) == 2
    assert plain[1] == 2            # round(2 * 1.0) == 2
    assert R.LEGACY_PICKAXE_MULT == 1.0 + 2 * R.TOOL_POWER_GAIN == 1.125


def test_roll_mine_loot_is_deterministic_under_a_seeded_rng() -> None:
    """Same seed ⇒ same (ore, amount): the injectable-rng contract."""
    a = R.roll_mine_loot(has_pickaxe=True, depth=4, rng=random.Random(99))
    b = R.roll_mine_loot(has_pickaxe=True, depth=4, rng=random.Random(99))
    assert a == b


# --- roll_harvest_amount: the axe-doubling leg ----------------------------------


def test_roll_harvest_amount_axe_doubles() -> None:
    """`randint(1,3) * (2 if has_axe else 1)`."""
    assert R.roll_harvest_amount(has_axe=True,
                                 rng=_FakeRandom(randint_value=3)) == 6
    assert R.roll_harvest_amount(has_axe=False,
                                 rng=_FakeRandom(randint_value=3)) == 3


def test_roll_harvest_amount_is_deterministic_under_a_seeded_rng() -> None:
    assert R.roll_harvest_amount(has_axe=True, rng=random.Random(7)) == \
        R.roll_harvest_amount(has_axe=True, rng=random.Random(7))


# --- roll_explore_outcome + EXPLORE_OUTCOMES table ------------------------------


def test_roll_explore_outcome_drops_the_weight_column() -> None:
    """One roll returns `(narration, item, amount)` — the 4th tuple slot (the
    weight) is dropped — and the weights handed to `choices` are the table's
    own weight column."""
    rng = _FakeRandom(pick_index=2)  # the monster-ambush hazard entry
    narration, item, amount = R.roll_explore_outcome(rng=rng)
    assert (narration, item, amount) == (
        "was attacked by monsters and lost 2 stone...", "stone", -2)
    _pop, weights = rng.choices_calls[0]
    assert weights == [w for *_x, w in R.EXPLORE_OUTCOMES]


def test_explore_outcomes_table_invariants() -> None:
    """The surface table: 4 entries, exactly one hazard (negative amount) and
    exactly one nothing-found (None item, 0 amount), all weights positive."""
    table = R.EXPLORE_OUTCOMES
    assert len(table) == 4
    hazards = [e for e in table if e[2] < 0]
    assert len(hazards) == 1 and hazards[0][1] == "stone"
    nothings = [e for e in table if e[1] is None]
    assert len(nothings) == 1 and nothings[0][2] == 0
    assert all(w > 0 for *_x, w in table)
    # the fresh-player gold camp entry, oracle-verbatim.
    assert table[0] == ("found 1 gold in an abandoned camp!", "gold", 1, 2.0)
