"""Band 7 — BTD6 difficulty-cost pricing math
(``sb/domain/btd6/difficulty_costs.py``, the port of shipped
``utils/btd6/difficulty_costs.py`` @7f7628e1 VERBATIM).

Why this is worth pinning: the module derives every-difficulty tower/upgrade
prices from the published Medium price and is a LIVE consumer surface — it feeds
``sb/domain/ai/tools.py`` (the ``all_difficulty_costs`` grounding tool whose
numbers are answered to users), ``paragon_math.py``, and ``context.py`` (the
BTD6 grounding context). A silent regression in a multiplier or in the
round-to-nearest-$5 **ties-DOWN** rule would ship wrong in-game costs into the
bot's answers with no loud failure. These are honest goldens: every expected
value was verified against the module itself before being written down.

The multipliers (exact against the published Bomb Shooter table): Easy ×0.85 ·
Medium ×1.00 · Hard ×1.08 · Impoppable ×1.20; rounding to the nearest $5 with
exact half-of-five ties resolving DOWN; CHIMPS prices as Hard.
"""

from __future__ import annotations

import pytest

from sb.domain.btd6 import difficulty_costs as dc


# --- multipliers + the medium passthrough ---------------------------------------

def test_all_difficulty_costs_exact_multipliers():
    # ×0.85 / ×1.00 / ×1.08 / ×1.20 over a base that needs no rounding for easy.
    assert dc.all_difficulty_costs(100) == {
        "easy": 85, "medium": 100, "hard": 110, "impoppable": 120,
    }
    assert dc.all_difficulty_costs(1000) == {
        "easy": 850, "medium": 1000, "hard": 1080, "impoppable": 1200,
    }


def test_medium_is_exact_passthrough():
    # Medium multiplier is 1 and short-circuits BEFORE the rounding path, so odd
    # bases survive verbatim (no snap to a $5 multiple).
    assert dc.cost_for_difficulty(213, "medium") == 213
    assert dc.cost_for_difficulty(7, "medium") == 7


# --- the load-bearing rounding rule: nearest $5, exact ties resolve DOWN ---------

def test_exact_five_tie_rounds_down():
    # 50 * 0.85 = 42.5 — an exact tie between 40 and 45. Round-half-UP would give
    # 45; the module's Fraction-exact ties-DOWN rule gives 40. This is the whole
    # reason the module rounds with math.ceil(v/5 - 1/2) rather than round().
    assert dc.cost_for_difficulty(50, "easy") == 40


def test_ordinary_nearest_five_is_not_a_tie():
    # 51 * 0.85 = 43.35 — not a tie; nearest $5 is 45.
    assert dc.cost_for_difficulty(51, "easy") == 45
    # 200 * 1.08 = 216 — nearest $5 is 215 (down, but not a tie: 216 is closer).
    assert dc.cost_for_difficulty(200, "hard") == 215


# --- mode aliases + the explicit fail-loud contract -----------------------------

@pytest.mark.parametrize("label", ["", "normal", "standard", " Standard ", "MEDIUM"])
def test_medium_aliases_normalize(label):
    assert dc.normalize_difficulty(label) == "medium"


def test_chimps_prices_as_hard():
    assert dc.normalize_difficulty("chimps") == "hard"
    assert dc.cost_for_difficulty(100, "chimps") == dc.cost_for_difficulty(100, "hard") == 110


def test_impoppable_is_canonical():
    assert dc.normalize_difficulty("Impoppable") == "impoppable"


def test_unknown_difficulty_raises_never_silent_medium():
    # The module's stated contract: an unrecognised label RAISES rather than
    # silently pricing as Medium.
    with pytest.raises(ValueError, match="unknown BTD6 difficulty"):
        dc.normalize_difficulty("lunatic")


# --- shape / ordering -----------------------------------------------------------

def test_difficulty_order_and_dict_keys():
    assert dc.DIFFICULTIES == ("easy", "medium", "hard", "impoppable")
    assert list(dc.all_difficulty_costs(100).keys()) == list(dc.DIFFICULTIES)
