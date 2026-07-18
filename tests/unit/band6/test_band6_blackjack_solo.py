"""Band 6 — the blackjack solo table (the shipped views/blackjack/solo_view
as a session-lifecycle panel with IN-PLACE refresh) + the ORDER-004
walking-skeleton drive: boot the replay composition root, deal through the
REAL pipeline, click a minted Hit button, and watch the audited move op
edit the table message (deferred-update ack + edit) to the terminal shape.
"""

from __future__ import annotations

import asyncio
import random
import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

_HEX32 = re.compile(r"^[0-9a-f]{32}$")

GID, UID = 1, 42


def _panel_ctx(params: dict, uid: int = UID):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


class NoShuffle(random.Random):
    """Deck stays in construction order — pops come from the tail (K ♣ …)."""

    def shuffle(self, seq):
        return None


# --- renderer: the shipped _game_embed shape ------------------------------------


def test_table_render_in_hand_shape():
    from sb.domain.blackjack.panels import _render_table, blackjack_table_spec

    spec = blackjack_table_spec()
    rendered = run(_render_table(spec, _panel_ctx({
        "player": ["4 ♣", "4 ♦"], "player_value": 8,
        "dealer": ["3 ♠", "?"], "dealer_value": None,
        "bet": 10, "doubled": False, "terminal": False})))
    assert rendered.embed.title == "🃏 Blackjack"
    assert rendered.embed.style_token == "green"
    assert rendered.embed.fields == (
        ("Dealer (3+?)", "3 ♠  ||?||", False),
        ("Your hand (8)", "4 ♣  4 ♦", False),
        ("Bet", "**10** 🪙", True))
    hit, stand, double = rendered.components
    assert (hit.label, hit.style, hit.emoji, hit.disabled) == (
        "Hit", "success", "👊", False)
    assert (stand.label, stand.style, stand.disabled) == (
        "Stand", "secondary", False)
    assert (double.label, double.style, double.disabled) == (
        "Double Down", "primary", False)
    assert rendered.invoker_lock == UID


def test_table_render_free_play_disables_double():
    from sb.domain.blackjack.panels import _render_table, blackjack_table_spec

    rendered = run(_render_table(blackjack_table_spec(), _panel_ctx({
        "player": ["J ♠", "2 ♣"], "player_value": 12,
        "dealer": ["A ♥", "?"], "bet": 0, "terminal": False})))
    assert rendered.embed.fields[0] == ("Dealer (11+?)", "A ♥  ||?||", False)
    assert rendered.embed.fields[2] == ("Bet", "Free (win = +50 🪙)", True)
    assert [c.disabled for c in rendered.components] == [False, False, True]


def test_table_render_third_card_disables_double():
    from sb.domain.blackjack.panels import _render_table, blackjack_table_spec

    rendered = run(_render_table(blackjack_table_spec(), _panel_ctx({
        "player": ["4 ♣", "4 ♦", "2 ♦"], "player_value": 10,
        "dealer": ["3 ♠", "?"], "bet": 10, "terminal": False})))
    assert [c.disabled for c in rendered.components] == [False, False, True]


def test_table_render_terminal_reveals_and_disables():
    from sb.domain.blackjack.panels import _render_table, blackjack_table_spec

    rendered = run(_render_table(blackjack_table_spec(), _panel_ctx({
        "player": ["K ♣", "K ♦"], "player_value": 20,
        "dealer": ["K ♥", "K ♠"], "dealer_value": 20,
        "bet": 0, "terminal": True, "result": "🤝 Push — tie.",
        "delta": 0, "balance": 0})))
    assert rendered.embed.style_token == "purple"      # shipped GAME_COLOR push
    assert rendered.embed.fields[0] == ("Dealer (20)", "K ♥  K ♠", False)
    assert rendered.embed.fields[3] == (
        "🤝 Push — tie.", "+0 🪙  |  Balance: **0** 🪙", False)
    assert all(c.disabled for c in rendered.components)


def test_shipped_result_colors():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["green"] == 3066993     # SUCCESS_COLOR
    assert STYLE_TOKEN_COLORS["red"] == 15158332      # ERROR_COLOR
    assert STYLE_TOKEN_COLORS["gold"] == 15844367     # the daily card


# --- item 5: the hub Solo buttons open the interactive table, not a card --------

CH = 900


@dataclass
class _FakeReq:
    """A component/modal-surface fake req for the hub Solo buttons — the
    fields ctx_from_request threads (actor/guild/request_id/confirmed) plus
    channel_id + args. A dataclass (not a SimpleNamespace) so
    ``dataclasses.replace`` inside the deal→open-table body works."""

    actor: object
    guild_id: int = GID
    channel_id: int = CH
    request_id: str = "r1"
    confirmed: bool = True
    args: dict = dc_field(default_factory=dict)


def _hub_req(args: dict | None = None, uid: int = UID):
    return _FakeReq(actor=SimpleNamespace(user_id=uid),
                    args=dict(args or {}))


def _stub_deal(monkeypatch, dealt: dict):
    """Stub blackjack.solo_start + open_panel so the hub_solo routing is
    tested DB-free: capture the op run and the panel opened."""
    from sb.kernel.panels import engine as panel_engine
    from sb.kernel.workflow import engine as wf_engine
    from sb.spec.outcomes import SUCCESS

    seen: dict = {}

    async def fake_run(ref, ctx):
        seen["op"] = ref.name
        seen["params"] = dict(ctx.params)
        return SimpleNamespace(outcome=SUCCESS, user_message=None,
                               after={"solo_start": dict(dealt)})

    async def fake_open(ref, req):
        seen["panel"] = ref.name
        seen["panel_args"] = dict(req.args)
        return "msg-1"

    monkeypatch.setattr(wf_engine, "run", fake_run)
    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    return seen


def test_hub_solo_actions_route_the_interactive_table_not_a_bare_op():
    """The item-5 fix: both hub Solo buttons (and the bet modal's submit)
    route the blackjack.hub_solo HANDLER — which opens the interactive
    table view — instead of the bare blackjack.solo_start WORKFLOW (whose
    RESULT_CARD gave a dead, unplayable deal)."""
    from sb.domain.blackjack import handlers  # noqa: F401 — registers hub_solo
    from sb.domain.blackjack.panels import SOLO_BET_MODAL, blackjack_hub_spec
    from sb.spec.refs import HandlerRef

    actions = {a.action_id: a for a in blackjack_hub_spec().actions}
    hub_solo = HandlerRef("blackjack.hub_solo")
    assert actions["bj_solo_free"].handler == hub_solo
    assert actions["bj_solo_bet"].handler == hub_solo
    assert SOLO_BET_MODAL.on_submit == hub_solo


def test_hub_solo_free_play_deals_and_opens_the_table(monkeypatch):
    from sb.domain.blackjack import handlers  # noqa: F401 — registers hub_solo
    from sb.spec.outcomes import SUCCESS
    from sb.spec.refs import HandlerRef
    from sb.spec.refs import resolve as resolve_ref

    seen = _stub_deal(monkeypatch, {
        "player": ["K ♣", "K ♦"], "player_value": 20,
        "dealer": ["K ♥", "?"], "bet": 0, "terminal": False})
    reply = run(resolve_ref(HandlerRef("blackjack.hub_solo"))(_hub_req()))

    assert (reply.outcome, reply.user_message) == (SUCCESS, None)
    assert seen["op"] == "blackjack.solo_start"
    assert seen["panel"] == "blackjack.table"       # the playable table view
    assert seen["panel_args"]["player"] == ["K ♣", "K ♦"]
    assert "bet" not in seen["params"]              # free play threads no bet


def test_hub_solo_bet_threads_the_modal_bet_into_solo_start(monkeypatch):
    from sb.domain.blackjack import handlers  # noqa: F401 — registers hub_solo
    from sb.spec.refs import HandlerRef
    from sb.spec.refs import resolve as resolve_ref

    seen = _stub_deal(monkeypatch, {
        "player": ["9 ♣", "7 ♦"], "player_value": 16,
        "dealer": ["A ♥", "?"], "bet": 25, "terminal": False})
    reply = run(resolve_ref(HandlerRef("blackjack.hub_solo"))(
        _hub_req({"bet": "25"})))

    assert reply.user_message is None
    assert seen["op"] == "blackjack.solo_start"
    assert seen["params"]["bet"] == "25"            # modal field → the op
    assert seen["panel"] == "blackjack.table"


# --- ORDER-004 walking skeleton: boot → !blackjack → hit → edited terminal ------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams,
    so the deal + the click leg's audited op run end-to-end in CI."""
    from sb.adapters.parity.boot import Harness

    economy = FakeEconomy().install(monkeypatch)
    games = FakeGamesStore().install(monkeypatch)

    import contextlib

    from sb.kernel.db import pool
    from tests.unit.workflow.conftest import FakeConn

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)

    h = asyncio.run(Harness.start(require_db=False))

    from sb.kernel.interaction.resolve import (
        install_access_policy_reader,
        install_visibility_reader,
    )

    async def _no_policy(guild_id):
        return None

    async def _all_visible(guild_id, subsystem):
        return True

    install_access_policy_reader(_no_policy)
    install_visibility_reader(_all_visible)
    yield h, economy, games
    asyncio.run(h.close())


def test_walking_skeleton_blackjack_solo_end_to_end(skeleton):
    from sb.domain.blackjack import ops

    harness, economy, games = skeleton
    ops.set_rng_for_tests(NoShuffle())
    try:
        run(harness.send_command("!blackjack", persona="admin"))
        calls = harness.take_calls()
        assert [c.method for c in calls] == ["send_message"]
        payload = calls[0].payload
        (embed,) = payload["embeds"]
        assert embed["title"] == "🃏 Blackjack"
        assert embed["color"] == 3066993
        # NoShuffle deck pops from the tail: player K ♣ + K ♦, dealer K ♥ + K ♠
        assert embed["fields"][0] == {
            "name": "Dealer (10+?)", "value": "K ♥  ||?||", "inline": False}
        assert embed["fields"][1] == {
            "name": "Your hand (20)", "value": "K ♣  K ♦", "inline": False}
        assert embed["fields"][2] == {
            "name": "Bet", "value": "Free (win = +50 🪙)", "inline": True}
        (row,) = payload["components"]
        buttons = row["components"]
        assert [b["label"] for b in buttons] == ["Hit", "Stand",
                                                 "Double Down"]
        assert all(_HEX32.match(b["custom_id"]) for b in buttons)
        assert [b["disabled"] for b in buttons] == [False, False, True]
        assert len(games.rows) == 1                    # checkpoint written
        message_id = calls[0].response_id

        # a stranger's click is invoker-locked (the shipped interaction_check)
        run(harness.click(message_id=message_id,
                          custom_id=buttons[0]["custom_id"],
                          persona="member"))
        stranger = harness.take_calls()
        assert any("This game isn't yours." in str(c.payload)
                   for c in stranger if c.payload)

        # the invoker's Hit runs the audited op and EDITS the table in
        # place: deferred-update ack (type 6) + edit_followup, terminal
        # bust shape (20 + Q ♣ = 30), checkpoint cleared, no coins moved.
        run(harness.click(message_id=message_id,
                          custom_id=buttons[0]["custom_id"],
                          persona="admin"))
        clicked = harness.take_calls()
        assert [c.method for c in clicked] == ["interaction_response",
                                               "edit_followup"]
        assert clicked[0].payload == {"type": 6}
        edited = clicked[1].payload
        assert "content" not in edited
        (edited_embed,) = edited["embeds"]
        assert edited_embed["color"] == 15158332       # ERROR_COLOR bust
        assert edited_embed["fields"][1]["name"] == "Your hand (30)"
        assert edited_embed["fields"][3]["name"] == "💥 Bust — you lose!"
        (edited_row,) = edited["components"]
        assert [b["custom_id"] for b in edited_row["components"]] == [
            b["custom_id"] for b in buttons]           # ids stable across edits
        assert all(b["disabled"] for b in edited_row["components"])
        assert not games.rows                          # checkpoint consumed
        assert not economy.audit                       # free-play bust: no coins

        # terminal expired the session — a late click gets the polite expiry
        run(harness.click(message_id=message_id,
                          custom_id=buttons[1]["custom_id"],
                          persona="admin"))
        late = harness.take_calls()
        assert any("expired" in str(c.payload) for c in late if c.payload)
    finally:
        ops.set_rng_for_tests(None)
