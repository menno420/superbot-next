"""Casino poker PLAY-LAYER coverage (band 6 play-layer port) — the headless
game registry, the pure snapshot projections, the game panel spec, and the
``casino.poker_action`` session-action dispatch (each button → the correct
engine transition → refresh).

Oracle: menno420/superbot disbot/views/casino/poker_table.py (SeatView +
_refresh_public / _broadcast) over disbot/utils/poker/engine.py. Play-chips
only; per-player LIVE ephemeral delivery is the owner-armed D-0045 step — the
per-player VIEW is a pure snapshot projection, tested here without any live
adapter.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from sb.domain.casino import service as _service  # noqa: F401 — registers handlers
from sb.domain.casino import view as pv
from sb.domain.casino.engine import Stage
from sb.domain.casino.game import get_game, reset_games_for_tests, start_game
from sb.domain.casino.table import (
    BIG_BLIND,
    GAME_TIMEOUT,
    SMALL_BLIND,
    START_STACK,
    TURN_SECONDS,
    close_table,
    launch_table,
    reset_tables_for_tests,
)
from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef
from sb.spec.refs import resolve as resolve_ref

ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102
CH = 4242


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


def _fake_req(action, uid, *, channel_id=CH, message_id="m1"):
    return SimpleNamespace(
        surface=SimpleNamespace(value="component"),
        actor=SimpleNamespace(user_id=uid), guild_id=1,
        channel_id=channel_id, args={"session_action": action},
        origin=SimpleNamespace(message=SimpleNamespace(id=message_id)))


def _action(action, uid, **kw):
    fn = resolve_ref(HandlerRef("casino.poker_action"))
    return asyncio.run(fn(_fake_req(action, uid, **kw)))


# --------------------------------------------------------------- constants
def test_missing_constants_added():
    # the shipped poker_table.py play-layer constants, verbatim.
    assert TURN_SECONDS == 90
    assert GAME_TIMEOUT == 1800
    # untouched lobby constants stay the shipped values.
    assert (SMALL_BLIND, BIG_BLIND, START_STACK) == (5, 10, 1000)


# ------------------------------------------------------------ game registry
def test_start_game_seats_and_deals():
    game = start_game(CH, _seats())
    assert get_game(CH) is game
    assert [p.user_id for p in game.players] == [ADMIN, MEMBER]
    # every seat starts on the shipped START_STACK minus its posted blind.
    assert sum(p.stack + p.committed_hand for p in game.players) == 2 * START_STACK
    assert all(len(p.hole) == 2 for p in game.players)
    assert game.stage == Stage.PREFLOP
    assert game.small_blind == SMALL_BLIND and game.big_blind == BIG_BLIND


# ----------------------------------------------------------- pure projections
def test_public_spectator_view_shape_and_copy():
    game = start_game(CH, _seats())
    v = pv.public_spectator_view(game.snapshot())
    assert v["title"] == "♠ Poker Table"
    assert v["footer"] == "Blinds 5/10 · Texas Hold'em"
    assert v["style_token"] == "purple"
    names = [n for n, _ in v["fields"]]
    assert names == ["Board", "💰 Pot", "Hand #", "Players"]
    # no hole cards leak onto the public surface.
    blob = repr(v)
    for p in game.players:
        for card in p.hole:
            assert card.code not in blob


def test_player_hand_view_is_private_and_turn_aware():
    game = start_game(CH, _seats())
    snap = game.snapshot()
    cur = snap["current_user_id"]
    me = pv.player_hand_view(snap, cur)
    other = MEMBER if cur == ADMIN else ADMIN
    assert me["title"] == "🟢 Your Hand — your turn!"
    assert me["footer"] == "Blinds 5/10 · Texas Hold'em"
    assert pv.player_hand_view(snap, other)["title"] == "♠ Your Hand"
    # the seat sees its OWN hole cards.
    hole = next(p.hole for p in game.players if p.user_id == cur)
    assert me["fields"][0][0] == "Your cards"
    assert me["fields"][0][1] == "  ".join(c.code for c in hole)
    # a non-seated user gets nothing (the shipped guard).
    assert pv.player_hand_view(snap, 999) is None


def test_seat_lobby_view_copy():
    v = pv.seat_lobby_view()
    assert v["title"] == "♠ You're seated!"
    assert v["footer"] == "Texas Hold'em · play-chips"
    assert "1000" in v["description"] and "5/10" in v["description"]


def test_action_button_plan_and_raise_targets():
    game = start_game(CH, _seats())
    snap = game.snapshot()          # preflop, SB to act facing the BB
    plan = pv.action_button_plan(snap)
    assert plan["poker_fold"]["enabled"]
    assert plan["poker_checkcall"]["label"].startswith("Call ")
    assert plan["poker_raise_min"]["enabled"]
    assert not plan["poker_deal_next"]["enabled"]     # only at showdown
    t = pv.raise_targets(snap)
    assert t["min"] == snap["current_bet"] + snap["min_raise"]
    assert t["max"] >= t["min"] and t["pot"] >= t["min"]


# ------------------------------------------------------------- panel spec
def test_poker_game_panel_spec():
    from sb.domain.casino.panels import POKER_GAME_PANEL_ID, poker_game_spec

    spec = poker_game_spec()
    assert spec.panel_id == POKER_GAME_PANEL_ID
    assert spec.session_lifecycle is True
    assert spec.audience.value == "public"
    assert spec.anchor_policy.value == "channel_anchor"
    assert spec.timeout_s == GAME_TIMEOUT
    ids = [a.action_id for a in spec.actions]
    assert ids == ["poker_fold", "poker_checkcall", "poker_raise_min",
                   "poker_raise_pot", "poker_allin", "poker_deal_next",
                   "poker_end"]
    assert all(a.handler == HandlerRef("casino.poker_action")
               for a in spec.actions)
    assert spec.renderer_override == HandlerRef("casino.render_poker_game")


def test_render_poker_game_reads_live_snapshot():
    from sb.domain.casino.panels import _render_poker_game, poker_game_spec

    start_game(CH, _seats())
    ctx = SimpleNamespace(channel_id=CH, params={}, guild_id=1,
                          actor=SimpleNamespace(user_id=ADMIN))
    rendered = asyncio.run(_render_poker_game(poker_game_spec(), ctx))
    assert rendered.embed.title == "♠ Poker Table"
    # exactly the seven declared buttons, on canonical ids (remap-ready).
    assert [c.custom_id for c in rendered.components] == [
        f"casino.poker_game.{a}" for a in
        ("poker_fold", "poker_checkcall", "poker_raise_min",
         "poker_raise_pot", "poker_allin", "poker_deal_next", "poker_end")]


# --------------------------------------------------- session-action dispatch
def test_dispatch_fold_advances_engine():
    game = start_game(CH, _seats())
    cur = game.current_player.user_id
    reply = _action("poker_fold", cur)
    assert reply.outcome == SUCCESS
    folded = next(p for p in game.players if p.user_id == cur)
    assert folded.folded is True


def test_dispatch_checkcall_maps_to_call_then_check():
    game = start_game(CH, _seats())
    sb = game.current_player.user_id             # SB owes the blind → CALL
    assert game.to_call() > 0
    _action("poker_checkcall", sb)
    bb = game.current_player.user_id             # BB has the option → CHECK
    assert game.to_call() == 0
    _action("poker_checkcall", bb)
    assert game.stage == Stage.FLOP              # both acted → next street


def test_dispatch_raise_maps_to_engine_raise():
    game = start_game(CH, _seats())
    sb = game.current_player.user_id
    before = game.current_bet
    _action("poker_raise_min", sb)
    assert game.current_bet > before             # a real raise landed


def test_dispatch_rejects_out_of_turn_click():
    game = start_game(CH, _seats())
    cur = game.current_player.user_id
    other = MEMBER if cur == ADMIN else ADMIN
    reply = _action("poker_fold", other)
    assert reply.outcome == BLOCKED
    assert "not your turn" in reply.user_message.lower()
    assert not any(p.folded for p in game.players)   # engine untouched


def test_dispatch_full_hand_to_showdown():
    game = start_game(CH, _seats())
    # everyone checks/calls down — the deck is irrelevant to legality.
    for _ in range(40):
        if game.is_hand_over:
            break
        _action("poker_checkcall", game.current_player.user_id)
    assert game.stage == Stage.COMPLETE
    assert game.results and sum(r.amount for r in game.results) > 0
    v = pv.public_spectator_view(game.snapshot())
    assert v["complete"] is True
    assert v["footer"] == 'Host: press "Deal next hand". Hands aren\'t restart-safe.'


def test_dispatch_deal_next_is_host_gated():
    launch_table(CH, ADMIN, "AdminActor")        # host = admin
    game = start_game(CH, _seats())
    for _ in range(40):
        if game.is_hand_over:
            break
        _action("poker_checkcall", game.current_player.user_id)
    assert game.is_hand_over
    # a non-host cannot deal the next hand.
    assert _action("poker_deal_next", MEMBER).outcome == BLOCKED
    # the host deals hand #2 (funded seats remain).
    reply = _action("poker_deal_next", ADMIN)
    assert reply.outcome == SUCCESS
    assert get_game(CH).hand_number == 2
    assert get_game(CH).stage == Stage.PREFLOP


def test_dispatch_end_table_tears_down():
    launch_table(CH, ADMIN, "AdminActor")
    game = start_game(CH, _seats())
    for _ in range(40):
        if game.is_hand_over:
            break
        _action("poker_checkcall", game.current_player.user_id)
    assert _action("poker_end", MEMBER).outcome == BLOCKED     # host-only
    assert _action("poker_end", ADMIN).outcome == SUCCESS
    assert get_game(CH) is None                                 # torn down


def test_dispatch_end_blocked_mid_hand():
    launch_table(CH, ADMIN, "AdminActor")
    start_game(CH, _seats())
    # the hand is live — the host end-control refuses until it is over.
    assert _action("poker_end", ADMIN).outcome == BLOCKED
    assert get_game(CH) is not None
    close_table(CH)


# --------------------------------------------------- minted-golden integrity
_GOLDEN_PATH = (Path(__file__).resolve().parents[3]
                / "parity" / "goldens" / "casino"
                / "casino_poker_full_hand.json")


def _walk(node):
    """Yield every (key, value) pair and every scalar reachable in a doc."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_full_hand_golden_leaks_no_hole_cards():
    """The public spectator embed is the ONLY poker surface the minted golden
    pins — the private per-seat hand (hole cards) rides the owner-armed live
    step, so the golden must expose ZERO hole-card data for any seat."""
    raw = _GOLDEN_PATH.read_text(encoding="utf-8")
    doc = json.loads(raw)
    # no snapshot 'hole' array and no private "Your cards" field ever reach
    # the public capture (defence in depth against a projection regression).
    for key, _value in _walk(doc):
        assert key != "hole", "engine hole-card array leaked into the golden"
    assert "Your cards" not in raw, "private hand field leaked into the golden"
    assert '"hole"' not in raw


def test_full_hand_golden_is_canonically_encoded():
    """Byte-provenance guard: the minted golden must use the canonical capture
    writer (parity/run.py: indent=1, sort_keys=True, ensure_ascii=False) so a
    re-capture never emits a spurious \\uXXXX re-encoding diff and the file
    stays byte-consistent with every sibling golden."""
    raw = _GOLDEN_PATH.read_text(encoding="utf-8")
    # ensure_ascii=False emits raw UTF-8 (♠ · — → 👑 …), never \uXXXX escapes.
    assert "\\u" not in raw, "golden was serialized with ensure_ascii=True"
    canonical = json.dumps(json.loads(raw), indent=1, sort_keys=True,
                           ensure_ascii=False) + "\n"
    assert raw == canonical, "golden is not byte-canonical for its content"
