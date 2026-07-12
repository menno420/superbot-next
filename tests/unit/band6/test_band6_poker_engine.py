"""Band 6 — the Texas Hold'em **betting state machine** (the poker engine
ported from the oracle onto the aboard cards + evaluator).

Exhaustive coverage of the headless betting core: blind posting (incl. the
heads-up button rule), every action's legality + effect (fold / check / call /
raise / all-in), min-raise rules, betting-round advancement
(preflop→flop→turn→river), multi-all-in side-pot construction, showdown pot
distribution incl. odd-chip handling, full-hand end-to-end sequences, and the
serializable table-state snapshot.

Determinism: bet-mechanics tests seed the rng (card-independent asserts);
showdown / side-pot tests force the hole cards + board via :func:`_force` so
the winner of every pot layer is pinned.
"""

from __future__ import annotations

import json

import pytest

from sb.domain.casino.cards import card
from sb.domain.casino.engine import (
    Action,
    Player,
    PokerError,
    PokerGame,
    PotResult,
    Stage,
)


# --- helpers -----------------------------------------------------------------


def _seed(n: int):
    import random

    return random.Random(n)


def _players(*stacks: int) -> list[Player]:
    return [Player(user_id=i, name=f"P{i}", stack=s) for i, s in enumerate(stacks)]


def _force(game: PokerGame, holes: dict[int, tuple[str, str]], board: list[str]) -> None:
    """Pin the hand: overwrite each seat's hole cards and stack the deck so the
    remaining community cards deal (via ``deck.pop()``) as *board* in order."""
    for idx, (a, b) in holes.items():
        game.players[idx].hole = [card(a), card(b)]
    game.deck = [card(c) for c in reversed(board)]


# --- blind posting -----------------------------------------------------------


def test_blinds_three_handed():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(1))
    g.begin_hand()
    # button 0 → SB idx1, BB idx2, first-to-act idx0 (left of the BB).
    assert g.players[1].committed_round == g.small_blind == 1
    assert g.players[2].committed_round == g.big_blind == 2
    assert g.players[1].stack == 99 and g.players[2].stack == 98
    assert g.current_bet == 2
    assert g.current == 0
    assert g.pot_total == 3
    assert g.stage == Stage.PREFLOP


def test_blinds_heads_up_button_is_small_blind_and_acts_first():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(2))
    g.begin_hand()
    # heads-up: the button posts the SMALL blind and acts first preflop.
    assert g.players[0].committed_round == 1  # button == SB
    assert g.players[1].committed_round == 2  # BB
    assert g.current == 0  # SB (button) is first to act heads-up


def test_button_stays_on_hand_one_then_rotates():
    g = PokerGame(_players(100, 100, 100), button=1, rng=_seed(3))
    g.begin_hand()
    assert g.button == 1  # hand 1 keeps the caller's chosen button
    # end the hand fast (everyone but one folds), then re-deal.
    g.act(Action.FOLD)  # idx0 (UTG) folds
    g.act(Action.FOLD)  # next actor folds → uncontested
    assert g.stage == Stage.COMPLETE
    g.begin_hand()
    assert g.button == 2  # hand 2 rotates the button one funded seat on


def test_two_player_minimum_enforced():
    with pytest.raises(PokerError):
        PokerGame(_players(100), rng=_seed(4))


def test_begin_hand_needs_two_funded():
    g = PokerGame(_players(100, 0), rng=_seed(5))
    with pytest.raises(PokerError):
        g.begin_hand()


# --- query helpers -----------------------------------------------------------


def test_to_call_and_raise_bounds():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(6))
    g.begin_hand()  # SB idx0 committed 1, current_bet 2
    assert g.to_call() == 1  # 2 - 1
    assert g.min_raise_to() == 4  # current_bet 2 + min_raise 2
    assert g.max_raise_to() == 200  # committed_round 1 + stack 199


def test_legal_actions_preflop_shape():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(7))
    g.begin_hand()
    la = g.legal_actions()
    assert la["fold"] is True
    assert la["call"] == 1
    assert "check" not in la  # facing the BB
    assert la["raise"] == {"min": 4, "max": 200}


# --- action legality + effects ----------------------------------------------


def test_check_when_nothing_to_call():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(8))
    g.begin_hand()
    g.act(Action.CALL)  # idx0 calls the BB
    g.act(Action.CALL)  # idx1 (SB) completes
    # idx2 is the BB with nothing to call → may CHECK (the option).
    assert g.current == 2
    assert g.to_call() == 0
    la = g.legal_actions()
    assert la.get("check") is True and "call" not in la and "raise" in la
    g.act(Action.CHECK)
    assert g.stage == Stage.FLOP  # round closed on the BB's check


def test_check_facing_a_bet_is_illegal():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(9))
    g.begin_hand()  # idx0 faces a 1-chip to-call
    with pytest.raises(PokerError):
        g.act(Action.CHECK)


def test_call_nothing_to_call_is_illegal():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(10))
    g.begin_hand()
    g.act(Action.CALL)
    g.act(Action.CALL)  # now BB with 0 to call
    with pytest.raises(PokerError):
        g.act(Action.CALL)


def test_call_effect_moves_chips():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(11))
    g.begin_hand()
    before = g.players[0].stack
    g.act(Action.CALL)  # idx0 calls 2
    assert g.players[0].stack == before - 2
    assert g.players[0].committed_hand == 2
    assert g.players[0].acted is True


def test_fold_reduces_to_one_awards_uncontested():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(12))
    g.begin_hand()  # pot = 3 (blinds)
    g.act(Action.FOLD)  # SB/button folds → BB wins uncontested
    assert g.stage == Stage.COMPLETE
    assert g.players[1].stack == 101  # 98 + 3
    assert g.players[0].stack == 99
    assert g.results == [PotResult(user_id=1, amount=3, hand_label=None)]


def test_act_with_no_current_player_raises():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(13))
    g.begin_hand()
    g.act(Action.FOLD)  # hand over
    with pytest.raises(PokerError):
        g.act(Action.CHECK)


# --- raise / min-raise rules -------------------------------------------------


def test_raise_below_min_is_illegal():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(14))
    g.begin_hand()  # current_bet 2, min_raise_to 4
    with pytest.raises(PokerError):
        g.act(Action.RAISE, raise_to=3)


def test_raise_not_exceeding_current_bet_is_illegal():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(15))
    g.begin_hand()
    with pytest.raises(PokerError):
        g.act(Action.RAISE, raise_to=2)  # == current_bet


def test_raise_over_stack_is_illegal():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(16))
    g.begin_hand()
    with pytest.raises(PokerError):
        g.act(Action.RAISE, raise_to=201)  # > max_raise_to (200)


def test_raise_requires_target():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(17))
    g.begin_hand()
    with pytest.raises(PokerError):
        g.act(Action.RAISE)  # no raise_to


def test_min_raise_updates_the_floor():
    g = PokerGame(_players(200, 200), button=0, rng=_seed(18))
    g.begin_hand()
    g.act(Action.RAISE, raise_to=4)  # legal min raise
    assert g.current_bet == 4
    assert g.min_raise == 2  # increment 4 - 2
    # BB now faces min_raise_to 6.
    assert g.min_raise_to() == 6
    with pytest.raises(PokerError):
        g.act(Action.RAISE, raise_to=5)


def test_raise_reopens_action():
    g = PokerGame(_players(200, 200, 200), button=0, rng=_seed(19))
    g.begin_hand()
    g.act(Action.CALL)  # idx0 calls
    g.act(Action.CALL)  # idx1 (SB) completes
    g.act(Action.RAISE, raise_to=8)  # idx2 (BB) raises the option
    # every other live seat must act again.
    assert g.players[0].acted is False and g.players[1].acted is False
    assert g.to_call() > 0


# --- all-in ------------------------------------------------------------------


def test_all_in_is_raise_to_max_even_below_nominal_min():
    # Short SB: max_raise_to (3) sits below the nominal min_raise_to (4); the
    # all-in-to-max raise is still legal (all-in == raise to max).
    g = PokerGame(_players(3, 200), button=0, rng=_seed(20))
    g.begin_hand()  # SB idx0: posts 1 (stack 2, committed 1)
    la = g.legal_actions()
    assert la["raise"] == {"min": 3, "max": 3}  # clamped to the all-in size
    g.act(Action.RAISE, raise_to=3)  # all-in to max
    assert g.players[0].all_in is True
    assert g.players[0].stack == 0
    assert g.current_bet == 3


def test_call_all_in_when_short():
    g = PokerGame(_players(200, 3, 200), button=0, rng=_seed(21))
    g.begin_hand()  # SB idx1 posts 1 (stack 2), BB idx2 posts 2
    g.act(Action.RAISE, raise_to=10)  # idx0 raises
    # idx1 (SB, stack 2, committed 1) can only call all-in for its last 2.
    assert g.current == 1
    g.act(Action.CALL)
    assert g.players[1].all_in is True
    assert g.players[1].stack == 0
    assert g.players[1].committed_hand == 3  # 1 blind + 2 call


# --- betting-round advancement ----------------------------------------------


def test_streets_advance_preflop_to_showdown():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(22))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD"), 2: ("QS", "QD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    # preflop: everyone limps to the BB, BB checks the option.
    g.act(Action.CALL)  # idx0
    g.act(Action.CALL)  # idx1 (SB)
    g.act(Action.CHECK)  # idx2 (BB option)
    assert g.stage == Stage.FLOP and len(g.board) == 3
    # flop: checks around (first to act is left of the button).
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    assert g.stage == Stage.TURN and len(g.board) == 4
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    assert g.stage == Stage.RIVER and len(g.board) == 5
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    g.act(Action.CHECK)
    assert g.stage == Stage.COMPLETE
    # idx0's aces take the whole 6-chip pot.
    assert g.players[0].stack == 100 + (6 - 2)
    assert g.results[0].user_id == 0
    assert sum(r.amount for r in g.results) == 6


def test_postflop_first_actor_is_left_of_button():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(23))
    g.begin_hand()
    g.act(Action.CALL)
    g.act(Action.CALL)
    g.act(Action.CHECK)
    assert g.stage == Stage.FLOP
    assert g.current == 1  # first live seat left of the button


# --- side pots + showdown distribution --------------------------------------


def test_multi_all_in_side_pots():
    # Stacks 25 / 50 / 100. idx0 shoves 25, idx1 shoves 50, idx2 calls 50.
    # Main pot (75, all three) → idx0's aces. Side pot (50, idx1+idx2) → idx1's
    # kings. idx2's queens win nothing.
    g = PokerGame(_players(25, 50, 100), button=0, rng=_seed(24))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD"), 2: ("QS", "QD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.RAISE, raise_to=25)  # idx0 all-in
    g.act(Action.RAISE, raise_to=50)  # idx1 all-in
    g.act(Action.CALL)  # idx2 calls 48 more (to 50)
    assert g.stage == Stage.COMPLETE
    assert g.pot_total == 125
    # main pot 75 → idx0, side pot 50 → idx1, idx2 wins nothing.
    assert g.players[0].stack == 75
    assert g.players[1].stack == 50
    assert g.players[2].stack == 50
    got = {r.user_id: r.amount for r in g.results}
    assert got == {0: 75, 1: 50}
    assert 2 not in got


def test_odd_chip_goes_to_earliest_left_of_button():
    # All three commit 25; idx1 and idx2 tie for the best hand, idx0 loses.
    # 75 / 2 = 37 each, the odd chip to the earliest winner left of the button
    # (idx1).
    g = PokerGame(_players(25, 25, 25), button=0, rng=_seed(25))
    g.begin_hand()
    _force(
        g,
        {0: ("KS", "KD"), 1: ("AS", "AD"), 2: ("AH", "AC")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.RAISE, raise_to=25)  # idx0 all-in
    g.act(Action.CALL)  # idx1 calls all-in
    g.act(Action.CALL)  # idx2 calls all-in
    assert g.stage == Stage.COMPLETE
    assert g.pot_total == 75
    assert g.players[0].stack == 0
    assert g.players[1].stack == 38  # 37 + the odd chip
    assert g.players[2].stack == 37


def test_folder_dead_money_swells_the_pot_for_live_contenders():
    # idx2 (BB) folds after posting; its 2 chips are dead money that swell the
    # low pot layer but only the live contenders (idx0, idx1) can win them.
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(40))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD"), 2: ("QS", "QD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.RAISE, raise_to=6)  # idx0 raises
    g.act(Action.CALL)  # idx1 (SB) calls to 6
    g.act(Action.FOLD)  # idx2 (BB) folds, leaving its 2-chip blind behind
    assert g.stage == Stage.FLOP
    for _ in range(3):  # flop, turn, river checked down
        g.act(Action.CHECK)
        g.act(Action.CHECK)
    assert g.stage == Stage.COMPLETE
    assert g.pot_total == 14  # 6 + 6 + 2 (the dead blind)
    # idx0's aces take the whole pot, dead money included; chips conserve.
    assert g.players[0].stack == 108  # 100 - 6 + 14
    assert g.players[1].stack == 94  # 100 - 6
    assert g.players[2].stack == 98  # 100 - 2 (folded blind lost)
    assert sum(p.stack for p in g.players) == 300
    got = {r.user_id: r.amount for r in g.results}
    assert got == {0: 14}


def test_orphaned_dead_layer_is_refunded_not_burned():
    # Chip-conservation regression (Codex P1 on engine.py:496).  A folded
    # all-in short stack contributes MORE to the pot than any *live* contender
    # matched, creating a top side-pot layer no un-folded player is eligible
    # for.  That uncalled money must be returned to its contributor, not
    # silently dropped.
    #
    # Layout: stacks P0=1, P1=1, P2=3, button=0.  P1 posts SB all-in (1), P2
    # posts BB (2), P0 calls all-in (1), then P2 folds facing nothing to call.
    # Contributions at showdown are {0:1, 1:1, 2:2}: the level-1 layer (3
    # chips) is contested by P0+P1; the level-2 layer (1 chip) is pure dead
    # money from P2's uncalled blind — no contender committed 2 — so it must
    # be refunded to P2.
    g = PokerGame(_players(1, 1, 3), button=0, rng=_seed(41))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD"), 2: ("QS", "QD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    before = sum(p.stack + p.committed_hand for p in g.players)
    assert before == 5
    g.act(Action.CALL)  # P0 (first to act) calls all-in for 1
    g.act(Action.FOLD)  # P2 (BB) folds with nothing to call
    assert g.stage == Stage.COMPLETE
    assert g.pot_total == 4  # 1 + 1 + 2 (P2's full posted blind)
    # P0's aces take the 3-chip contested layer; P2's uncalled odd chip comes
    # back; not one chip is burned.
    assert g.players[0].stack == 3  # won the 3-chip main layer
    assert g.players[1].stack == 0  # lost, was all-in
    assert g.players[2].stack == 2  # 1 left after the blind + 1 refunded
    # Pot-conservation invariant: total table chips are unchanged.
    assert sum(p.stack for p in g.players) == 5
    # Result awards (the contested pot) plus refunds reconcile to the pot.
    awarded = sum(r.amount for r in g.results)
    assert awarded == 3
    got = {r.user_id: r.amount for r in g.results}
    assert got == {0: 3}  # the refund is a return of dead money, not a "win"


def test_split_pot_even():
    # Heads-up dead heat, even pot → clean split, no odd chip.
    g = PokerGame(_players(100, 100), button=0, rng=_seed(26))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("AH", "AC")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.CALL)  # idx0 (SB) completes
    g.act(Action.CHECK)  # idx1 (BB) checks → flop
    for _ in range(3):  # flop, turn, river all check
        g.act(Action.CHECK)
        g.act(Action.CHECK)
    assert g.stage == Stage.COMPLETE
    assert g.players[0].stack == 100  # each gets its 2 back
    assert g.players[1].stack == 100
    assert {r.amount for r in g.results} == {2}


# --- end-to-end --------------------------------------------------------------


def test_full_hand_with_raise_to_showdown_winner():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(27))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.RAISE, raise_to=6)  # idx0 (SB) raises
    g.act(Action.CALL)  # idx1 (BB) calls to 6
    assert g.stage == Stage.FLOP
    for _ in range(3):  # flop, turn, river checked down
        g.act(Action.CHECK)
        g.act(Action.CHECK)
    assert g.stage == Stage.COMPLETE
    assert g.pot_total == 12
    assert g.players[0].stack == 106  # 100 - 6 + 12
    assert g.players[1].stack == 94
    assert g.results == [PotResult(user_id=0, amount=12, hand_label="Pair")]


def test_showdown_rank_lookup():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(28))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.CALL)
    g.act(Action.CHECK)
    for _ in range(3):
        g.act(Action.CHECK)
        g.act(Action.CHECK)
    assert g.showdown_rank(0) is not None
    assert g.showdown_rank(0).label == "Pair"
    assert g.showdown_rank(999) is None  # unknown user


# --- snapshot ----------------------------------------------------------------


def test_snapshot_is_json_serializable_and_shaped():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(29))
    g.begin_hand()
    s = g.snapshot()
    json.dumps(s)  # must not raise
    assert s["stage"] == "preflop"
    assert s["button"] == 0
    assert s["small_blind"] == 1 and s["big_blind"] == 2
    assert s["current"] == 0 and s["current_user_id"] == 0
    assert s["current_bet"] == 2 and s["to_call"] == 2
    assert s["pot_total"] == 3
    assert s["board"] == []
    assert len(s["players"]) == 3
    assert all(len(p["hole"]) == 2 for p in s["players"])
    assert s["legal_actions"]["fold"] is True
    assert g.to_state() == s  # alias returns the same shape


def test_snapshot_carries_results_after_showdown():
    g = PokerGame(_players(100, 100), button=0, rng=_seed(30))
    g.begin_hand()
    g.act(Action.FOLD)  # uncontested
    s = g.snapshot()
    json.dumps(s)
    assert s["stage"] == "complete"
    assert s["current_user_id"] is None
    assert s["to_call"] == 0
    assert s["results"] == [{"user_id": 1, "amount": 3, "hand_label": None}]
    assert s["log"]  # the hand narrated at least one line


def test_snapshot_board_codes_after_flop():
    g = PokerGame(_players(100, 100, 100), button=0, rng=_seed(31))
    g.begin_hand()
    _force(
        g,
        {0: ("AS", "AD"), 1: ("KS", "KD"), 2: ("QS", "QD")},
        ["2C", "7H", "9D", "JC", "3S"],
    )
    g.act(Action.CALL)
    g.act(Action.CALL)
    g.act(Action.CHECK)
    s = g.snapshot()
    assert s["stage"] == "flop"
    assert s["board"] == ["2C", "7H", "9D"]
