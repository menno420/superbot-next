"""Band 6 — blackjack PvP on the wire (the shipped challenge →
accept/decline → per-player hit/stand → result loop as ONE staged session
panel on g1: dynamic ids) + the ORDER-004 walking-skeleton drive: boot the
replay composition root, challenge through the REAL pipeline, Accept
(escrow + deal both hands in ONE txn), bust one hand / stand the other,
and watch the settle edit the match message to the shipped
`🃏 Blackjack PvP Result` embed.
"""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

GID, P1, P2, CH = 1, 42, 43, 900
SID = f"{GID}.{P1}.{CH}"

# parity/harness/world.py constants (the skeleton's real world)
W_GUILD = 700_000_000_000_000_001
ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102


def _panel_ctx(params: dict, uid: int = P1):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


def _ctx(params: dict, *, uid: int = P1, gid: int = GID):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000,
                                                tz=dt.timezone.utc))


class NoShuffle(random.Random):
    """Deck stays in construction order — pops come from the tail (K ♣ …)."""

    def shuffle(self, seq):
        return None


class NaturalDeck(random.Random):
    """Stacks every deck so the first two pops are A + K — a natural 21."""

    def shuffle(self, seq):
        ace = next(c for c in seq if c.startswith("A "))
        king = next(c for c in seq if c.startswith("K "))
        seq.remove(ace)
        seq.remove(king)
        seq.extend([king, ace])


# --- renderer: the shipped stage shapes ------------------------------------------


def test_pvp_render_challenge_stage():
    from sb.domain.blackjack.panels import _render_pvp, blackjack_pvp_spec

    spec = blackjack_pvp_spec()
    rendered = run(_render_pvp(spec, _panel_ctx({
        "stage": "challenge", "session_id": SID,
        "challenger": P1, "target": P2, "bet": 30})))
    assert rendered.embed.title == "🃏 Blackjack Challenge!"
    assert rendered.embed.style_token == "green"      # shipped SUCCESS_COLOR
    assert rendered.embed.description == (
        f"<@{P1}> challenges <@{P2}> to Blackjack "
        f"(**30** 🪙).\n<@{P2}>, do you accept?")
    accept, decline = rendered.components
    assert accept.custom_id == f"g1:blackjack:{SID}:accept"
    assert decline.custom_id == f"g1:blackjack:{SID}:decline"
    assert rendered.invoker_lock is None              # PUBLIC — ops own the locks


def test_pvp_render_match_stage_shows_both_hands():
    from sb.domain.blackjack.panels import _render_pvp, blackjack_pvp_spec

    rendered = run(_render_pvp(blackjack_pvp_spec(), _panel_ctx({
        "stage": "match", "session_id": SID, "p1": P1, "p2": P2,
        "bet": 30,
        "hands": {str(P1): {"cards": ["K ♣", "K ♦"], "value": 20,
                            "done": False},
                  str(P2): {"cards": ["K ♣", "K ♦"], "value": 20,
                            "done": True}}})))
    assert rendered.embed.title == "🃏 Blackjack PvP"
    lines = rendered.embed.description.splitlines()
    assert lines[0] == f"<@{P1}>: K ♣  K ♦ (**20**)"
    assert lines[1] == f"<@{P2}>: K ♣  K ♦ (**20**)  ✅"
    assert "Bet: **30** 🪙 each" in rendered.embed.description
    hit, stand = rendered.components
    assert hit.custom_id == f"g1:blackjack:{SID}:hit"
    assert (hit.label, hit.emoji, hit.style) == ("Hit", "👊", "success")
    assert (stand.label, stand.emoji) == ("Stand", "✋")


def test_pvp_render_result_stage_bust_marker_and_gold():
    from sb.domain.blackjack.panels import _render_pvp, blackjack_pvp_spec

    rendered = run(_render_pvp(blackjack_pvp_spec(), _panel_ctx({
        "stage": "result", "session_id": SID, "p1": P1, "p2": P2,
        "bet": 30, "winner": P2,
        "result": f"<@{P2}> wins (opponent busted)!",
        "hands": {str(P1): {"cards": ["K ♣", "K ♦", "K ♥"], "value": 30,
                            "done": True},
                  str(P2): {"cards": ["K ♣", "K ♦"], "value": 20,
                            "done": True}}})))
    assert rendered.embed.title == "🃏 Blackjack PvP Result"
    assert rendered.embed.style_token == "gold"       # shipped ECONOMY_COLOR
    assert "💥" in rendered.embed.description
    assert rendered.embed.description.endswith(
        f"<@{P2}> wins (opponent busted)!")
    assert all(c.disabled for c in rendered.components)


def test_pvp_render_tie_keeps_game_color():
    from sb.domain.blackjack.panels import _render_pvp, blackjack_pvp_spec

    rendered = run(_render_pvp(blackjack_pvp_spec(), _panel_ctx({
        "stage": "result", "session_id": SID, "p1": P1, "p2": P2,
        "winner": None, "result": "🤝 Tie — both had **20**. "
                                  "No coins exchanged.",
        "hands": {}})))
    assert rendered.embed.style_token == "purple"     # shipped GAME_COLOR


# --- both dealt naturals settle inside the accept txn -----------------------------


def test_pvp_double_natural_settles_at_accept(fake_economy,
                                              fake_games_store):
    from sb.domain.blackjack import ops

    ops.set_rng_for_tests(NaturalDeck())
    try:
        fake_economy.balances[(P1, GID)] = 100
        fake_economy.balances[(P2, GID)] = 100
        run(ops._record_pvp_challenge(None, _ctx(
            {"target_id": P2, "bet": 30, "channel_id": CH})))
        out = run(ops._record_pvp_accept(None, _ctx(
            {"session_id": SID}, uid=P2)))
        after = out.after
        assert after["terminal"]
        assert after["winner"] is None
        assert after["result"] == ("🤝 Tie — both had **21**. "
                                   "No coins exchanged.")
        # escrow + refund both happened in the one leg: coins conserved,
        # nothing left on the table (no stuck match of two finished hands)
        assert fake_economy.balances[(P1, GID)] == 100
        assert fake_economy.balances[(P2, GID)] == 100
        assert not fake_games_store.rows
        reasons = [a["reason"] for a in fake_economy.audit]
        assert reasons == ["blackjack:pvp_escrow", "blackjack:pvp_escrow",
                           "blackjack:pvp_refund", "blackjack:pvp_refund"]
    finally:
        ops.set_rng_for_tests(None)


# --- ORDER-004 walking skeleton: challenge → accept → bust/stand → settled edit ---


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams,
    so the challenge, escrow-deal, and settle legs run end-to-end in CI."""
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

    # re-arm the g1 session table + dispatcher (module imports are cached,
    # so an earlier suite's registry reset would otherwise stick)
    from sb.domain.blackjack.panels import register_blackjack_sessions
    from sb.domain.games.session import install_games_dispatcher

    register_blackjack_sessions()
    install_games_dispatcher()

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


def test_walking_skeleton_blackjack_pvp_end_to_end(skeleton):
    from sb.domain.blackjack import ops

    harness, economy, games = skeleton
    ops.set_rng_for_tests(NoShuffle())
    try:
        economy.balances[(ADMIN, W_GUILD)] = 100
        economy.balances[(MEMBER, W_GUILD)] = 100

        # 1. the challenge: the shipped embed + Accept/Decline on g1 ids
        run(harness.send_command(f"!blackjack <@{MEMBER}> 30",
                                 persona="admin"))
        calls = harness.take_calls()
        assert [c.method for c in calls] == ["send_message"]
        (embed,) = calls[0].payload["embeds"]
        assert embed["title"] == "🃏 Blackjack Challenge!"
        assert embed["color"] == 3066993              # shipped SUCCESS_COLOR
        assert embed["description"] == (
            f"<@{ADMIN}> challenges <@{MEMBER}> to Blackjack "
            f"(**30** 🪙).\n<@{MEMBER}>, do you accept?")
        (row,) = calls[0].payload["components"]
        accept, decline = row["components"]
        assert accept["custom_id"].startswith("g1:blackjack:")
        message_id = calls[0].response_id
        assert not economy.audit                      # no coins moved yet

        # 2. a stranger's Accept is peer-locked by the op
        run(harness.click(message_id=message_id,
                          custom_id=accept["custom_id"],
                          persona="second_member"))
        stranger = harness.take_calls()
        assert any("This challenge isn't for you." in str(c.payload)
                   for c in stranger if c.payload)

        # 3. the target's Accept escrows BOTH stakes + deals both hands in
        # ONE txn, and edits the message onto the match stage
        run(harness.click(message_id=message_id,
                          custom_id=accept["custom_id"], persona="member"))
        accepted = harness.take_calls()
        assert [c.method for c in accepted] == ["interaction_response",
                                                "edit_followup"]
        assert accepted[0].payload == {"type": 6}
        (match_embed,) = accepted[1].payload["embeds"]
        assert match_embed["title"] == "🃏 Blackjack PvP"
        # NoShuffle: each player's fresh deck pops K ♣ + K ♦ = 20
        assert f"<@{ADMIN}>: K ♣  K ♦ (**20**)" in match_embed["description"]
        assert f"<@{MEMBER}>: K ♣  K ♦ (**20**)" in match_embed["description"]
        (mrow,) = accepted[1].payload["components"]
        buttons = {b["label"]: b["custom_id"] for b in mrow["components"]}
        assert buttons["Hit"].endswith(":hit")
        assert buttons["Stand"].endswith(":stand")
        assert economy.balances[(ADMIN, W_GUILD)] == 70
        assert economy.balances[(MEMBER, W_GUILD)] == 70
        assert [a["reason"] for a in economy.audit] == [
            "blackjack:pvp_escrow", "blackjack:pvp_escrow"]

        # 4. the challenger hits into a bust (20 + K = 30) — the edit shows
        # the bust marker; the match stays open for the opponent
        run(harness.click(message_id=message_id, custom_id=buttons["Hit"],
                          persona="admin"))
        busted = harness.take_calls()
        assert [c.method for c in busted] == ["interaction_response",
                                              "edit_followup"]
        (bust_embed,) = busted[1].payload["embeds"]
        assert f"<@{ADMIN}>: K ♣  K ♦  K ♥ (**30**)  💥" in (
            bust_embed["description"])

        # 5. the opponent stands on 20 and takes the pot: the shipped
        # result embed, escrow rows consumed
        run(harness.click(message_id=message_id, custom_id=buttons["Stand"],
                          persona="member"))
        settled = harness.take_calls()
        assert [c.method for c in settled] == ["interaction_response",
                                               "edit_followup"]
        (result_embed,) = settled[1].payload["embeds"]
        assert result_embed["title"] == "🃏 Blackjack PvP Result"
        assert result_embed["color"] == 15844367      # shipped ECONOMY_COLOR
        assert result_embed["description"].endswith(
            f"<@{MEMBER}> wins (opponent busted)!")
        (frow,) = settled[1].payload["components"]
        assert all(b["disabled"] for b in frow["components"])
        assert economy.balances[(ADMIN, W_GUILD)] == 70
        assert economy.balances[(MEMBER, W_GUILD)] == 130
        assert economy.audit[-1]["reason"] == "blackjack:pvp_win"
        assert not games.rows                         # match + escrow consumed

        # 6. a late click routes to the op and gets the polite expiry from
        # the consumed checkpoint row
        run(harness.click(message_id=message_id, custom_id=buttons["Hit"],
                          persona="admin"))
        late = harness.take_calls()
        assert any("expired" in str(c.payload) for c in late if c.payload)
    finally:
        ops.set_rng_for_tests(None)
