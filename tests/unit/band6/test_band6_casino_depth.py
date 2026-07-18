"""Casino poker DEPTH coverage (band 6 play-layer port) — the behavioral gaps
the sibling ``test_band6_poker_play.py`` / ``test_band6_poker_engine.py`` files
leave open: the four LOBBY handlers' refusal/permission gates
(join/leave/start/close), the ``casino.poker_action`` REFUSAL seams (not the
happy-path dispatch, already covered), and the ``evaluate.py`` category ladder +
guards.

Fully DB-free, mirroring the shipped harness: ``resolve_ref(HandlerRef(...))`` +
a ``SimpleNamespace`` fake ``req`` + ``asyncio.run`` over the process-memory
table/game registries (``reset_*_for_tests`` + ``random.seed(42)`` per test).
Real assertions on the exact shipped BLOCK copy / outcome / score tuple — no
golden, no live adapter.
"""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

from sb.domain.casino import service as _service  # noqa: F401 — registers handlers
from sb.domain.casino import view as pv
from sb.domain.casino.cards import card
from sb.domain.casino.evaluate import (
    HandCategory,
    _straight_high,
    best_hand,
    score_five,
)
from sb.domain.casino.game import (
    get_game,
    reset_games_for_tests,
    start_game,
)
from sb.domain.casino.table import (
    MAX_SEATS,
    close_table,
    get_table,
    launch_table,
    reset_tables_for_tests,
)
from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef
from sb.spec.refs import resolve as resolve_ref

ADMIN = 900_000_000_000_000_201
MEMBER = 900_000_000_000_000_202
STRANGER = 900_000_000_000_000_203
CH = 5252


@pytest.fixture(autouse=True)
def _clean():
    reset_games_for_tests()
    reset_tables_for_tests()
    random.seed(42)
    yield
    reset_games_for_tests()
    reset_tables_for_tests()


def _seats():
    return [(ADMIN, "AdminActor"), (MEMBER, "MemberActor")]


def _lreq(uid, *, channel_id=CH, message_id="m1", action=None):
    """A lobby/game fake request — ``action`` rides ``session_action`` for the
    poker_action seams, absent for the lobby-click handlers."""
    args = {"session_action": action} if action is not None else {}
    return SimpleNamespace(
        surface=SimpleNamespace(value="component"),
        actor=SimpleNamespace(user_id=uid), guild_id=1,
        channel_id=channel_id, args=args,
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)))


def _call(ref_name, uid, **kw):
    fn = resolve_ref(HandlerRef(ref_name))
    return asyncio.run(fn(_lreq(uid, **kw)))


def _action(action, uid, **kw):
    return _call("casino.poker_action", uid, action=action, **kw)


# ===================================================================== P1 · JOIN
def test_join_closed_table_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    close_table(CH)                                  # table gone from registry
    reply = _call("casino.poker_join", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This table has closed."


def test_join_started_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    get_table(CH).started = True
    reply = _call("casino.poker_join", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This game has already started."


def test_join_already_seated_blocks():
    launch_table(CH, ADMIN, "AdminActor")            # host seated at seat 0
    reply = _call("casino.poker_join", ADMIN)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "You're already seated at this table."


def test_join_full_table_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    lobby = get_table(CH)
    # fill to MAX_SEATS (host already occupies seat 0).
    for i in range(1, MAX_SEATS):
        lobby.seats.append((ADMIN + 1000 + i, f"Filler{i}"))
    assert len(lobby.seats) == MAX_SEATS
    reply = _call("casino.poker_join", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == f"This table is full ({MAX_SEATS} seats)."


def test_join_happy_seats_player():
    launch_table(CH, ADMIN, "AdminActor")
    before = len(get_table(CH).seats)
    reply = _call("casino.poker_join", MEMBER)
    assert reply.outcome == SUCCESS and reply.user_message is None
    lobby = get_table(CH)
    assert len(lobby.seats) == before + 1
    assert lobby.is_seated(MEMBER)


# ==================================================================== P1 · LEAVE
def test_leave_not_seated_blocks():
    launch_table(CH, ADMIN, "AdminActor")            # only the host is seated
    reply = _call("casino.poker_leave", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "You're not seated at this table."


def test_leave_non_host_removed_table_survives():
    launch_table(CH, ADMIN, "AdminActor")
    get_table(CH).seats.append((MEMBER, "MemberActor"))
    reply = _call("casino.poker_leave", MEMBER)
    assert reply.outcome == SUCCESS
    lobby = get_table(CH)
    assert lobby is not None and not lobby.ended        # table survives
    assert not lobby.is_seated(MEMBER)                  # leaver removed
    assert lobby.is_seated(ADMIN)                       # host stays


def test_leave_host_tears_down():
    launch_table(CH, ADMIN, "AdminActor")
    get_table(CH).seats.append((MEMBER, "MemberActor"))
    reply = _call("casino.poker_leave", ADMIN)         # host leaves
    assert reply.outcome == SUCCESS
    assert get_table(CH) is None                        # table folds


def test_leave_last_seat_empties_tears_down():
    # Craft the ``not lobby.seats`` teardown branch in isolation: a lone
    # non-host occupant whose exit empties the table (host_id unseated).
    launch_table(CH, ADMIN, "AdminActor")
    lobby = get_table(CH)
    lobby.seats = [(MEMBER, "MemberActor")]            # host no longer occupies a seat
    reply = _call("casino.poker_leave", MEMBER)
    assert reply.outcome == SUCCESS
    assert get_table(CH) is None                        # emptied → torn down


# ==================================================================== P1 · START
def test_start_closed_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    close_table(CH)
    reply = _call("casino.poker_start", ADMIN)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This table has closed."


def test_start_non_host_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    get_table(CH).seats.append((MEMBER, "MemberActor"))
    reply = _call("casino.poker_start", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Only the host can start the table."


def test_start_already_started_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    lobby = get_table(CH)
    lobby.seats.append((MEMBER, "MemberActor"))
    lobby.started = True
    reply = _call("casino.poker_start", ADMIN)          # host, but already live
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This game has already started."


def test_start_below_min_players_blocks():
    launch_table(CH, ADMIN, "AdminActor")               # host only → 1 seat
    reply = _call("casino.poker_start", ADMIN)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Need at least 2 players to start."


def test_start_happy_deals_and_flags_started(monkeypatch):
    # The happy path opens the public game panel; the presenter is a live-adapter
    # concern, so stub ``open_panel`` (the shipped access_map recipe) and assert
    # the handler's own effects: lobby flipped + a hand dealt into the registry.
    from sb.kernel.panels import engine

    async def _fake_open(ref, req):
        return ""

    monkeypatch.setattr(engine, "open_panel", _fake_open)
    launch_table(CH, ADMIN, "AdminActor")
    lobby = get_table(CH)
    lobby.seats.append((MEMBER, "MemberActor"))
    reply = _call("casino.poker_start", ADMIN)
    assert reply.outcome == SUCCESS
    assert lobby.started is True
    game = get_game(CH)
    assert game is not None
    assert [p.user_id for p in game.players] == [ADMIN, MEMBER]


# ==================================================================== P1 · CLOSE
def test_close_closed_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    close_table(CH)
    reply = _call("casino.poker_close", ADMIN)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This table has closed."


def test_close_non_host_blocks():
    launch_table(CH, ADMIN, "AdminActor")
    get_table(CH).seats.append((MEMBER, "MemberActor"))
    reply = _call("casino.poker_close", MEMBER)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Only the host can close this table."


def test_close_host_tears_down():
    launch_table(CH, ADMIN, "AdminActor")
    reply = _call("casino.poker_close", ADMIN)
    assert reply.outcome == SUCCESS
    assert get_table(CH) is None


# ============================================================ P2 · ACTION SEAMS
def test_action_game_gone_blocks():
    # No live hand for this channel → the shipped "hand has ended" terminal.
    reply = _action("poker_fold", ADMIN)
    assert reply.outcome == BLOCKED
    assert reply.user_message == "This hand has ended."


def test_action_deal_next_mid_hand_blocks():
    launch_table(CH, ADMIN, "AdminActor")               # host = ADMIN
    start_game(CH, _seats())                            # a live, unfinished hand
    reply = _action("poker_deal_next", ADMIN)           # host, but hand not over
    assert reply.outcome == BLOCKED
    assert reply.user_message == "Finish this hand first."


def test_action_unknown_session_action_blocks():
    game = start_game(CH, _seats())
    cur = game.current_player.user_id                   # gate is the seat to act
    reply = _action("poker_bogus_button", cur)
    assert reply.outcome == BLOCKED
    assert "session has expired" in reply.user_message


def test_action_illegal_raise_surfaces_pokererror():
    # Crafted state: shrink the actor's stack so its only legal move is a call —
    # a min-raise then maps to raise_to == current_bet, which the engine rejects,
    # and the handler surfaces the PokerError as a "♠ {exc}" BLOCK.
    game = start_game(CH, _seats())
    actor = game.current_player
    actor.stack = 5                                     # committed_round 5 + 5 == BB(10)
    reply = _action("poker_raise_min", actor.user_id)
    assert reply.outcome == BLOCKED
    assert reply.user_message.startswith("♠ ")
    assert "raise must exceed" in reply.user_message


def test_action_deal_next_insufficient_funded_closes():
    # Host deals the next hand but only one seat is funded → begin_hand raises
    # PokerError → the table auto-closes with the shipped copy (teardown).
    launch_table(CH, ADMIN, "AdminActor")
    game = start_game(CH, _seats())
    for _ in range(40):                                 # check/call down to showdown
        if game.is_hand_over:
            break
        _action("poker_checkcall", game.current_player.user_id)
    assert game.is_hand_over
    game.players[1].stack = 0                           # bust a seat → <2 funded
    reply = _action("poker_deal_next", ADMIN)
    assert reply.outcome == SUCCESS
    assert reply.user_message == (
        "♠ Not enough funded players — the table closed.")
    assert get_game(CH) is None
    assert get_table(CH) is None


# ======================================================= P3 · EVALUATE LADDER
def test_score_five_untested_categories():
    pair = score_five([card(c) for c in ("AS", "AD", "KH", "QC", "JS")])
    assert pair.category is HandCategory.PAIR
    assert pair.key == (HandCategory.PAIR, 14, 13, 12, 11)

    two_pair = score_five([card(c) for c in ("AS", "AD", "KH", "KC", "QS")])
    assert two_pair.category is HandCategory.TWO_PAIR
    assert two_pair.key == (HandCategory.TWO_PAIR, 14, 13, 12)

    trips = score_five([card(c) for c in ("AS", "AD", "AH", "KC", "QS")])
    assert trips.category is HandCategory.THREE_OF_A_KIND
    assert trips.key == (HandCategory.THREE_OF_A_KIND, 14, 13, 12)


def test_category_ladder_is_strictly_monotonic():
    # One representative hand per category, weakest → strongest; the key tuples
    # must sort in the same order (this locks the category-value ordering).
    ladder = [
        ("HIGH_CARD", ("AS", "KD", "QH", "JC", "9S")),
        ("PAIR", ("2S", "2D", "7H", "9C", "JS")),
        ("TWO_PAIR", ("3S", "3D", "5H", "5C", "9S")),
        ("THREE_OF_A_KIND", ("4S", "4D", "4H", "8C", "KS")),
        ("STRAIGHT", ("5S", "6D", "7H", "8C", "9S")),
        ("FLUSH", ("2S", "4S", "6S", "8S", "10S")),
        ("FULL_HOUSE", ("6S", "6D", "6H", "9C", "9S")),
        ("FOUR_OF_A_KIND", ("7S", "7D", "7H", "7C", "KS")),
        ("STRAIGHT_FLUSH", ("5S", "6S", "7S", "8S", "9S")),
    ]
    ranks = []
    for name, codes in ladder:
        r = score_five([card(c) for c in codes])
        assert r.category is HandCategory[name], name
        ranks.append(r)
    keys = [r.key for r in ranks]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)                  # strictly increasing


def test_straight_high_normal_wheel_and_ace_high():
    assert _straight_high([10, 9, 8, 7, 6]) == 10       # normal straight
    assert _straight_high([14, 13, 12, 11, 10]) == 14   # ace-HIGH straight
    assert _straight_high([14, 5, 4, 3, 2]) == 5        # ace-low wheel → high 5
    assert _straight_high([14, 13, 7, 4, 2]) is None    # no run of five
    # ace-high straight OUT-scores the wheel through score_five's key.
    ace_high = score_five([card(c) for c in ("AS", "KD", "QH", "JC", "10S")])
    wheel = score_five([card(c) for c in ("AS", "2D", "3H", "4C", "5S")])
    assert ace_high.category is HandCategory.STRAIGHT
    assert wheel.category is HandCategory.STRAIGHT
    assert ace_high.key == (HandCategory.STRAIGHT, 14)
    assert wheel.key == (HandCategory.STRAIGHT, 5)
    assert ace_high.key > wheel.key


def test_kicker_tiebreak_within_a_category():
    ace_kicker = score_five([card(c) for c in ("8S", "8D", "AH", "5C", "3S")])
    king_kicker = score_five([card(c) for c in ("8S", "8D", "KH", "5C", "3S")])
    assert ace_kicker.category is king_kicker.category is HandCategory.PAIR
    assert ace_kicker.key > king_kicker.key             # A kicker beats K kicker


def test_score_five_and_best_hand_length_guards():
    with pytest.raises(ValueError):
        score_five([card(c) for c in ("AS", "KD", "QH", "JC")])       # 4 cards
    with pytest.raises(ValueError):
        score_five([card(c) for c in ("AS", "KD", "QH", "JC", "9S", "8D")])  # 6
    with pytest.raises(ValueError):
        best_hand([card(c) for c in ("AS", "KD", "QH", "JC")])        # <5


def test_best_hand_picks_the_best_five():
    # 7-card showdown: four aces beat every 5-subset that omits one.
    seven = best_hand([card(c) for c in
                       ("AS", "AD", "AH", "AC", "KS", "QD", "2C")])
    assert seven.category is HandCategory.FOUR_OF_A_KIND
    assert seven.key[:2] == (HandCategory.FOUR_OF_A_KIND, 14)
    # 6-card: the straight flush is found by dropping the off-suit king.
    six = best_hand([card(c) for c in
                     ("2S", "3S", "4S", "5S", "6S", "KD")])
    assert six.category is HandCategory.STRAIGHT_FLUSH
    assert six.key == (HandCategory.STRAIGHT_FLUSH, 6)


# ============================================================ P4 · VIEW POLISH
def test_public_view_folded_allin_tags_and_turn_marker():
    snap = {
        "stage": "flop",
        "current_user_id": 1,
        "pot_total": 40,
        "hand_number": 2,
        "board": ["2C", "7H", "9D"],
        "log": ["P1 to act."],
        "players": [
            {"user_id": 1, "name": "Alice", "stack": 90},
            {"user_id": 2, "name": "Bob", "stack": 0, "folded": True},
            {"user_id": 3, "name": "Cara", "stack": 0, "all_in": True},
        ],
        "results": [],
    }
    v = pv.public_spectator_view(snap)
    players_field = dict(v["fields"])["Players"]
    assert "▶ Alice — 90 chips" in players_field           # current-turn marker
    assert "Bob — 0 chips · folded" in players_field       # folded tag
    assert "Cara — 0 chips · all-in" in players_field      # all-in tag
    assert v["complete"] is False


def test_raise_targets_degenerate_guard():
    assert pv.raise_targets({"current": None, "players": []}) == {
        "min": 0, "pot": 0, "max": 0}
    # current index out of range is equally degenerate.
    assert pv.raise_targets({"current": 5, "players": []}) == {
        "min": 0, "pot": 0, "max": 0}
