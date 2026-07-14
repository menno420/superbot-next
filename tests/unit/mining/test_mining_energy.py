"""Mining energy pure-domain core (slice 0) — ported verbatim from the oracle
``utils/mining/energy.py``, mirroring ``sb/domain/fishing/energy.py``.

Headless, deterministic (time is always a parameter). Exhaustive edge coverage
of the lazy on-access regen math and the consumption/food helpers. Disturbs no
golden — this slice carries the domain core only (persistence and command
wiring are later, owner-gated slices).
"""

from __future__ import annotations

from sb.domain.mining import energy


# --- constants (oracle-verbatim) ----------------------------------------------

def test_constants_verbatim():
    assert (energy.MAX_ENERGY, energy.DIG_COST, energy.REGEN_SECONDS) == (60, 1, 10)


def test_restore_values_verbatim():
    assert energy.RESTORE_VALUES == {
        "ration": 25,
        "energy drink": 50,
        "cooked fish": 30,
    }


# --- settle: lazy on-access regen ---------------------------------------------

def test_settle_missing_row_zero_zero_goes_full():
    # a missing row is (0, 0) — the huge elapsed-from-epoch clamps to the cap,
    # so every fresh/legacy player settles straight to a full bar.
    assert energy.settle(energy.EnergyState(0, 0), 1_000_000_000) == \
        energy.EnergyState(60, 1_000_000_000)


def test_settle_already_full_restamps_now():
    # at/over the cap short-circuits and stamps *now* (no elapsed math).
    assert energy.settle(energy.EnergyState(60, 0), 1_000) == \
        energy.EnergyState(60, 1_000)


def test_settle_partial_tick_preserves_remainder():
    # 75s @ +1/10s = 7 whole units; the stamp advances by WHOLE intervals only
    # (70s), so the leftover 5s of progress is preserved, never evaporated.
    assert energy.settle(energy.EnergyState(10, 1_000), 1_075) == \
        energy.EnergyState(17, 1_070)


def test_settle_exact_regen_boundary_gains_one():
    # exactly REGEN_SECONDS elapsed → exactly one unit, stamp = now.
    assert energy.settle(energy.EnergyState(10, 1_000), 1_010) == \
        energy.EnergyState(11, 1_010)


def test_settle_just_below_boundary_gains_nothing():
    # one second short of the interval → no gain, stamp unchanged.
    assert energy.settle(energy.EnergyState(10, 1_000), 1_009) == \
        energy.EnergyState(10, 1_000)


def test_settle_reaching_cap_midregen_restamps_now():
    # 30s would add 3 (58→61) but caps at 60 and stamps *now*, not the
    # whole-interval stamp.
    assert energy.settle(energy.EnergyState(58, 1_000), 1_030) == \
        energy.EnergyState(60, 1_030)


def test_settle_negative_elapsed_clamps_to_zero_gain():
    # now < updated_at (clock skew) → max(0, ...) elapsed → no gain, no restamp.
    assert energy.settle(energy.EnergyState(10, 2_000), 1_000) == \
        energy.EnergyState(10, 2_000)


def test_settle_is_idempotent():
    # settling every second must equal settling once (the remainder invariant).
    once = energy.settle(energy.EnergyState(10, 1_000), 1_075)
    twice = energy.settle(once, 1_075)
    assert once == twice == energy.EnergyState(17, 1_070)


# --- can_dig ------------------------------------------------------------------

def test_can_dig_true_when_covered():
    assert energy.can_dig(energy.EnergyState(1, 1_000), 1_000) is True


def test_can_dig_refuses_at_zero():
    # exactly DIG_COST short — the 0-energy refusal path.
    assert energy.can_dig(energy.EnergyState(0, 1_000), 1_000) is False


def test_can_dig_settles_before_checking():
    # 0 now, but 10s of regen lands +1 → dig becomes possible.
    assert energy.can_dig(energy.EnergyState(0, 1_000), 1_010) is True


# --- spend --------------------------------------------------------------------

def test_spend_debits_dig_cost_keeping_settled_stamp():
    # spends DIG_COST=1 and keeps the SETTLED updated_at (not `now`).
    assert energy.spend(energy.EnergyState(5, 1_000), 1_000) == \
        energy.EnergyState(4, 1_000)


def test_spend_floor_clamps_at_zero():
    # spending at 0 never mints negative energy.
    assert energy.spend(energy.EnergyState(0, 1_000), 1_000) == \
        energy.EnergyState(0, 1_000)


def test_spend_settles_first():
    # 0 now, +2 after 20s regen, then debit 1 → 1 left, stamp = whole-interval.
    assert energy.spend(energy.EnergyState(0, 1_000), 1_020) == \
        energy.EnergyState(1, 1_020)


# --- restore (food / boosters) ------------------------------------------------

def test_restore_adds_amount():
    assert energy.restore(energy.EnergyState(10, 1_000), 1_000, 25) == \
        energy.EnergyState(35, 1_000)


def test_restore_clamps_at_max():
    assert energy.restore(energy.EnergyState(50, 1_000), 1_000, 50) == \
        energy.EnergyState(60, 1_000)


def test_restore_when_full_stays_capped():
    # full bar restamps to now on settle; the food adds nothing over the cap.
    assert energy.restore(energy.EnergyState(60, 1_000), 1_000, 25) == \
        energy.EnergyState(60, 1_000)


def test_restore_each_food_item():
    base = energy.EnergyState(0, 1_000)  # settles to (0, 1000) at now=1000
    for item, amount in energy.RESTORE_VALUES.items():
        assert energy.restore(base, 1_000, amount) == \
            energy.EnergyState(amount, 1_000), item


# --- seconds_until ------------------------------------------------------------

def test_seconds_until_zero_when_already_at_target():
    assert energy.seconds_until(energy.EnergyState(5, 1_000), 1_000, 1) == 0


def test_seconds_until_one_unit_from_empty():
    # 0 energy, need 1 → one full 10s interval.
    assert energy.seconds_until(energy.EnergyState(0, 1_000), 1_000, 1) == 10


def test_seconds_until_subtracts_partial_remainder():
    # 5s already elapsed toward the next unit → only 5s left.
    assert energy.seconds_until(energy.EnergyState(0, 1_000), 1_005, 1) == 5


def test_seconds_until_target_clamps_to_max():
    # a target above the cap is clamped to MAX_ENERGY.
    assert energy.seconds_until(energy.EnergyState(0, 1_000), 1_000, 100) == 600


def test_seconds_until_for_dig_cost():
    assert energy.seconds_until(
        energy.EnergyState(0, 1_000), 1_000, energy.DIG_COST) == 10


# --- restore_value ------------------------------------------------------------

def test_restore_value_known_items():
    assert energy.restore_value("ration") == 25
    assert energy.restore_value("energy drink") == 50
    assert energy.restore_value("cooked fish") == 30


def test_restore_value_case_and_space_insensitive():
    assert energy.restore_value("  RATION ") == 25
    assert energy.restore_value("Energy Drink") == 50


def test_restore_value_non_food_is_none():
    assert energy.restore_value("torch") is None
    assert energy.restore_value("") is None


# --- bar rendering ------------------------------------------------------------

def test_bar_full():
    assert energy.bar(60) == "⚡ 60/60 [▰▰▰▰▰▰▰▰▰▰]"


def test_bar_empty():
    assert energy.bar(0) == "⚡ 0/60 [▱▱▱▱▱▱▱▱▱▱]"


def test_bar_partial():
    assert energy.bar(42) == "⚡ 42/60 [▰▰▰▰▰▰▰▱▱▱]"
    assert energy.bar(30) == "⚡ 30/60 [▰▰▰▰▰▱▱▱▱▱]"


def test_bar_clamps_below_zero():
    assert energy.bar(-5) == "⚡ 0/60 [▱▱▱▱▱▱▱▱▱▱]"


def test_bar_clamps_above_max():
    assert energy.bar(100) == "⚡ 60/60 [▰▰▰▰▰▰▰▰▰▰]"
