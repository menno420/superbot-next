"""Unit coverage for the pure creature PvP battle engine
(sb/domain/creature/battle.py) — the verbatim oracle combat math (D-0079).

Pure stdlib + the catalog dataclass, no DB / no discord, so it runs in the
guarded-import unit lane. Pins the type chart, stat derivation, level
scaling, the damage-formula edges (min 1, the df=0 guard), the buff cap, and
a full deterministic seeded 6v6 resolution trace.
"""

from __future__ import annotations

import random

import pytest

from sb.domain.creature import battle as B
from sb.domain.creature.battle import BattleStats, Combatant
from sb.domain.creature.catalog import Creature


def _c(name: str, element: str, rarity: str = "Common",
       archetype: str = "balanced", emoji: str = "🔥") -> Creature:
    return Creature(name=name, element=element, rarity=rarity,
                    archetype=archetype, emoji=emoji)


# --------------------------------------------------------------- type chart
@pytest.mark.parametrize(
    "attack,defend,expected",
    [
        # Ember (index 0) around the 6-cycle: +1/+2 strong, +3 neutral,
        # +4/+5 (== -2/-1) weak, self neutral.
        ("Ember", "Tide", B.STRONG_MULT),      # delta 1
        ("Ember", "Bramble", B.STRONG_MULT),   # delta 2
        ("Ember", "Spark", B.NEUTRAL_MULT),    # delta 3 (opposite)
        ("Ember", "Stone", B.WEAK_MULT),       # delta 4
        ("Ember", "Gust", B.WEAK_MULT),        # delta 5
        ("Ember", "Ember", B.NEUTRAL_MULT),    # delta 0 (self)
        # wrap-around from Gust (index 5)
        ("Gust", "Ember", B.STRONG_MULT),      # delta 1
        ("Gust", "Tide", B.STRONG_MULT),       # delta 2
        ("Gust", "Stone", B.WEAK_MULT),        # delta 5
        # Normal ignores the chart entirely
        ("Normal", "Ember", B.NEUTRAL_MULT),
        ("Normal", "Gust", B.NEUTRAL_MULT),
        # unknown element on either side -> neutral fallback (never raises)
        ("Foo", "Ember", B.NEUTRAL_MULT),
        ("Ember", "Foo", B.NEUTRAL_MULT),
    ],
)
def test_effectiveness_matrix(attack: str, defend: str, expected: float) -> None:
    assert B.effectiveness(attack, defend) == expected


def test_type_chart_is_symmetric_cycle() -> None:
    # every element beats exactly two and loses to exactly two.
    for attacker in B.ELEMENT_CYCLE:
        strong = [d for d in B.ELEMENT_CYCLE
                  if B.effectiveness(attacker, d) == B.STRONG_MULT]
        weak = [d for d in B.ELEMENT_CYCLE
                if B.effectiveness(attacker, d) == B.WEAK_MULT]
        assert len(strong) == 2
        assert len(weak) == 2


# --------------------------------------------------------- stat derivation
def test_derive_stats_budget_and_weights() -> None:
    # balanced Common: 200 split evenly across four equal weights = 50 each.
    assert B.derive_stats(_c("A", "Ember")) == BattleStats(50, 50, 50, 50)
    # attacker Common (0.9,1.3,0.7,1.1) over total 4.0, budget 200.
    assert B.derive_stats(_c("B", "Ember", archetype="attacker")) == \
        BattleStats(hp=45, atk=65, df=35, spd=55)
    # tank Epic (1.3,0.8,1.3,0.6) over total 4.0, budget 300.
    assert B.derive_stats(_c("C", "Stone", "Epic", "tank")) == \
        BattleStats(hp=98, atk=60, df=98, spd=45)


def test_derive_stats_defaults_for_unknown_rarity_and_archetype() -> None:
    # unknown rarity -> Common budget (200); unknown archetype -> balanced.
    assert B.derive_stats(_c("D", "Ember", "Mythic", "wizard")) == \
        BattleStats(50, 50, 50, 50)


# ------------------------------------------------------------ level scaling
def test_level_scaling_normalized_level() -> None:
    cm = Combatant(_c("E", "Ember"), B.NORMALIZED_LEVEL)
    # hp: round(50 * (1 + 0.06*49)) = round(197.0) = 197
    assert cm.max_hp == 197
    # atk/df/spd: 50 * (1 + 0.035*49) = 135.75 (no buff)
    assert cm.atk == pytest.approx(135.75)
    assert cm.df == pytest.approx(135.75)
    assert cm.spd == pytest.approx(135.75)


def test_level_one_is_base_stats() -> None:
    cm = Combatant(_c("F", "Ember"), 1)
    assert cm.max_hp == 50
    assert cm.atk == pytest.approx(50.0)
    assert cm.spd == pytest.approx(50.0)


def test_buff_step_and_cap() -> None:
    cm = Combatant(_c("G", "Ember"), 1)
    cm.apply_buff("atk")
    assert cm.atk_stage == pytest.approx(B.BUFF_STEP)          # +0.25
    cm.apply_buff("atk")
    assert cm.atk_stage == pytest.approx(B.BUFF_CAP)           # +0.50
    cm.apply_buff("atk")
    assert cm.atk_stage == pytest.approx(B.BUFF_CAP)           # capped
    # +ATK actually lifts the effective atk stat by the stage.
    assert cm.atk == pytest.approx(50.0 * (1 + B.BUFF_CAP))
    cm.apply_buff("def")
    assert cm.def_stage == pytest.approx(B.BUFF_STEP)


# --------------------------------------------------------- damage formula
def test_move_damage_floor_is_one() -> None:
    # a feeble attacker into a wall still deals at least 1.
    weak = Combatant(_c("weak", "Ember", archetype="tank"), 1)
    wall = Combatant(_c("wall", "Spark", "Epic", "tank"), B.NORMALIZED_LEVEL)
    normal = B.moves_for(weak.creature)[0]
    rng = random.Random(0)
    for _ in range(50):
        assert B.move_damage(weak, wall, normal, rng) >= 1


def test_move_damage_df_zero_guard_no_zero_division() -> None:
    attacker = Combatant(_c("atk", "Ember", archetype="attacker"), 50)
    defender = Combatant(_c("def", "Tide"), 1)
    # force a degenerate df=0 to exercise the max(1.0, df) guard.
    defender.stats = BattleStats(hp=1, atk=1, df=0, spd=1)
    defender.cur_hp = 1
    assert defender.df == 0.0
    move = B.moves_for(attacker.creature)[0]
    # must not raise ZeroDivisionError; guard divides by max(1.0, 0)=1.0.
    dmg = B.move_damage(attacker, defender, move, random.Random(3))
    assert dmg >= 1
    assert B.expected_damage(attacker, defender, move) > 0


def test_expected_damage_zero_for_buff_moves() -> None:
    a = Combatant(_c("a", "Ember"), 50)
    d = Combatant(_c("d", "Tide"), 50)
    buff = [m for m in B.moves_for(a.creature) if m.kind == B.BUFF][0]
    assert B.expected_damage(a, d, buff) == 0.0


# --------------------------------------------------- deterministic 6v6 trace
_TEAM_A = (
    ("Cindling", "Ember"), ("Rippling", "Tide"), ("Sproutle", "Bramble"),
)
_TEAM_B = (
    ("Emberpaw", "Ember", "attacker"), ("Splashfin", "Tide", "attacker"),
    ("Thornkit", "Bramble", "attacker"),
)


def test_resolve_battle_deterministic_trace() -> None:
    """A fixed-seed 3v3 resolution pins the exact winner, event count, first
    action, KO sequence, and final HP — so any drift in the combat math or
    RNG threading trips this test."""
    team_a = B.build_team([_c(n, el) for n, el in _TEAM_A], 50)
    team_b = B.build_team([_c(n, el, "Common", arch) for n, el, arch in _TEAM_B], 50)
    rng = random.Random("trace-seed-1")
    out = B.resolve_battle(team_a, team_b, rng=rng)

    assert out.winner == "a"
    assert out.a_won is True
    assert len(out.events) == 59

    first = out.events[0]
    assert (first.turn, first.side, first.actor, first.move, first.kind,
            first.target, first.damage, first.effectiveness,
            first.target_hp_left, first.faint) == \
        (1, "b", "Emberpaw", "Cinderlash", "damage", "Cindling", 16, 1.0,
         181, False)

    faints = [(e.turn, e.actor, e.target) for e in out.events if e.faint]
    assert faints == [
        (11, "Cindling", "Emberpaw"),
        (15, "Splashfin", "Cindling"),
        (22, "Rippling", "Splashfin"),
        (30, "Rippling", "Thornkit"),
    ]

    # the whole B team is down; A keeps at least one survivor.
    assert all(m.fainted for m in team_b)
    assert any(not m.fainted for m in team_a)
    assert [m.cur_hp for m in team_a] == [-3, 16, 197]


def test_resolve_battle_same_seed_is_reproducible() -> None:
    def _run() -> tuple[str, int]:
        ta = B.build_team([_c(n, el) for n, el in _TEAM_A], 50)
        tb = B.build_team([_c(n, el, "Common", a) for n, el, a in _TEAM_B], 50)
        out = B.resolve_battle(ta, tb, rng=random.Random(1234))
        return out.winner, len(out.events)

    assert _run() == _run()


def test_standard_team_one_per_covered_element() -> None:
    pool = [_c("Cindling", "Ember"), _c("Emberpaw", "Ember", archetype="attacker"),
            _c("Rippling", "Tide"), _c("Zephyrl", "Gust")]
    team = B.standard_team(pool, random.Random(7), level=50)
    elements = [m.element for m in team]
    # one per element the pool covers (Ember, Tide, Gust), in cycle order.
    assert elements == ["Ember", "Tide", "Gust"]
    assert all(m.level == 50 for m in team)


def test_standard_team_empty_pool_is_empty() -> None:
    assert B.standard_team([], random.Random(0)) == []
