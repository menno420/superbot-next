"""Band 6 slice 1 — the games substrate: wager escrow/settle-once, the
shared game-XP track (soft cap + conditional level_up), the g1: session
registry/dispatcher, and the GC sweep leg."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1, P2, CH = 1, 42, 43, 900


@pytest.fixture(autouse=True)
def _clean_session_registry():
    from sb.domain.games.session import reset_session_registry_for_tests

    reset_session_registry_for_tests()
    yield
    reset_session_registry_for_tests()


def _ctx(params: dict, *, uid: int = P1, gid: int = GID,
         epoch: int = 1_000_000):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc))


# --- wager primitives ------------------------------------------------------------------


def test_escrow_settle_once(fake_economy, fake_games_store):
    from sb.domain.games import wager

    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 100
    escrow = run(wager.escrow_pvp_in_txn(
        None, guild_id=GID, channel_id=CH, subsystem="t_escrow", version=1,
        p1_id=P1, p2_id=P2, stake=40, reason="t:escrow", now=1000))
    assert escrow.escrowed and escrow.stake == 40
    assert fake_economy.balances[(P1, GID)] == 60
    assert fake_economy.balances[(P2, GID)] == 60
    assert len(fake_games_store.rows) == 2

    settle = run(wager.settle_pvp_in_txn(
        None, guild_id=GID, channel_id=CH, subsystem="t_escrow",
        p1_id=P1, p2_id=P2, winner_id=P2, reason="t:win"))
    assert settle.paid and settle.amount == 80
    assert fake_economy.balances[(P2, GID)] == 140
    # replay: rows consumed — no double pay (the shipped guard)
    replay = run(wager.settle_pvp_in_txn(
        None, guild_id=GID, channel_id=CH, subsystem="t_escrow",
        p1_id=P1, p2_id=P2, winner_id=P2, reason="t:win"))
    assert not replay.paid and fake_economy.balances[(P2, GID)] == 140


def test_escrow_insufficient_funds_raises(fake_economy, fake_games_store):
    from sb.domain.economy.service import InsufficientFundsError
    from sb.domain.games import wager

    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 10
    with pytest.raises(InsufficientFundsError):
        run(wager.escrow_pvp_in_txn(
            None, guild_id=GID, channel_id=CH, subsystem="t_escrow",
            version=1, p1_id=P1, p2_id=P2, stake=40, reason="t:escrow",
            now=1000))


def test_refund_returns_own_stakes(fake_economy, fake_games_store):
    from sb.domain.games import wager

    fake_economy.balances[(P1, GID)] = 50
    fake_economy.balances[(P2, GID)] = 50
    run(wager.escrow_pvp_in_txn(
        None, guild_id=GID, channel_id=CH, subsystem="t_escrow", version=1,
        p1_id=P1, p2_id=P2, stake=30, reason="t:escrow", now=1000))
    refund = run(wager.refund_pvp_in_txn(
        None, guild_id=GID, channel_id=CH, subsystem="t_escrow",
        p1_id=P1, p2_id=P2, reason="t:refund"))
    assert refund.paid and refund.amount == 60
    assert fake_economy.balances[(P1, GID)] == 50
    assert fake_economy.balances[(P2, GID)] == 50


def test_tournament_pot_is_summed_truth(fake_economy, fake_games_store):
    from sb.domain.games import wager

    for uid, held in ((P1, 100), (P2, 100), (77, 100)):
        fake_economy.balances[(uid, GID)] = held
    for uid in (P1, P2, 77):
        run(wager.enter_tournament_in_txn(
            None, guild_id=GID, user_id=uid, channel_id=0,
            subsystem="t_tourn", version=1, fee=25, reason="t:fee",
            now=1000))
    payout = run(wager.payout_tournament_in_txn(
        None, guild_id=GID, subsystem="t_tourn", winner_id=P2,
        reason="t:pot"))
    assert payout.paid and payout.amount == 75
    assert fake_economy.balances[(P2, GID)] == 150
    # replay is a no-op
    assert not run(wager.payout_tournament_in_txn(
        None, guild_id=GID, subsystem="t_tourn", winner_id=P2,
        reason="t:pot")).paid


def test_debit_floor_records_actual_delta(fake_economy, fake_games_store):
    from sb.domain.games import wager

    fake_economy.balances[(P1, GID)] = 30
    actual, balance = run(wager.debit_floor_in_txn(
        None, guild_id=GID, user_id=P1, amount=100, reason="t:loss",
        actor_id=P1))
    assert (actual, balance) == (-30, 0)
    assert fake_economy.audit[-1]["delta"] == -30


# --- game XP -----------------------------------------------------------------------------


def test_award_amounts_and_depth_scaling():
    from sb.domain.games.xp import apply_soft_cap, base_amount

    assert base_amount("mine", depth=5) == 8      # 3 + depth
    assert base_amount("fish") == 5
    assert base_amount("sell") == 0               # money moves award nothing
    assert apply_soft_cap(8, 0) == 8
    assert apply_soft_cap(8, 400) == 2            # capped 25%
    assert apply_soft_cap(1, 10_000) == 1         # floor 1, never zero


def test_award_in_txn_levels_and_soft_cap(fake_games_store):
    from sb.domain.games import xp

    award = run(xp.award_in_txn(None, user_id=P1, guild_id=GID,
                                game="mining", action="depth_record",
                                now=1_000_000))
    assert award.amount == 25 and award.new_total_xp == 25
    assert not award.leveled_up
    # burn past the daily cap in one game
    for _ in range(16):
        run(xp.award_in_txn(None, user_id=P1, guild_id=GID, game="mining",
                            action="depth_record", now=1_000_000))
    capped = run(xp.award_in_txn(None, user_id=P1, guild_id=GID,
                                 game="mining", action="depth_record",
                                 now=1_000_000))
    assert capped.amount == 6                     # 25 * 0.25
    # a different game has its own budget
    fresh = run(xp.award_in_txn(None, user_id=P1, guild_id=GID,
                                game="fishing", action="fish",
                                now=1_000_000))
    assert fresh.amount == 5


def test_levelup_payload_is_conditional(fake_games_store):
    from sb.domain.games import ops, xp

    ctx = _ctx({})
    ctx.params["_gxp"] = run(xp.award_in_txn(
        None, user_id=P1, guild_id=GID, game="mining", action="harvest",
        now=1_000_000))
    assert ops._gxp_levelup_payload(ctx, None) is None      # non-boundary
    assert ops._gxp_awarded_payload(ctx, None)["delta"] == 2


# --- g1 session registry + dispatcher ------------------------------------------------


def test_session_id_roundtrip_and_budget():
    from sb.domain.games.session import (
        mint_custom_id,
        mint_session_id,
        parse_session_id,
    )

    sid = mint_session_id(10**17, 10**17, 10**17)
    assert parse_session_id(sid) == (10**17, 10**17, 10**17)
    cid = mint_custom_id("blackjack", sid, "double")
    assert cid.startswith("g1:blackjack:") and len(cid) <= 100


def test_prefix_claim_collision_refused():
    from sb.domain.games.session import register_session_actions

    register_session_actions("gamex", {"a": object()})
    register_session_actions("gamex", {"a": object()})    # idempotent shape
    with pytest.raises(ValueError):
        register_session_actions("gamex", {"b": object()})


def test_dispatcher_polite_expiry_and_resolve_reentry(monkeypatch):
    from sb.domain.games import session
    from sb.kernel.panels.router import parse_g1

    class Responder:
        def __init__(self):
            self.denials = []

        async def deny(self, message, ephemeral=False):
            self.denials.append(message)

    # unknown game -> polite expiry
    responder = Responder()
    route = parse_g1("g1:ghost:1.2.3:hit")
    assert run(session._dispatch(route, SimpleNamespace(guild=None),
                                 responder)) is None
    assert "expired" in responder.denials[0]

    # claimed game + known action -> re-enters resolve() with the spec
    seen = {}

    async def fake_resolve(req):
        seen["req"] = req
        return "resolved"

    import importlib

    resolve_mod = importlib.import_module("sb.kernel.interaction.resolve")
    monkeypatch.setattr(resolve_mod, "resolve", fake_resolve)
    spec = object()
    session.register_session_actions("gamey", {"hit": spec})
    route = parse_g1("g1:gamey:1.2.3:hit")
    out = run(session._dispatch(
        route, SimpleNamespace(guild=None, user=None, channel_id=CH,
                               id=5), Responder()))
    assert out == "resolved"
    req = seen["req"]
    assert req.target.spec is spec
    assert req.args["session_id"] == "1.2.3"
    assert req.args["session_action"] == "hit"


# --- the GC sweep leg ---------------------------------------------------------------


def test_gc_sweep_row_refunds_and_deletes(fake_economy, fake_games_store):
    from sb.domain.games import ops, wager

    # a stranded escrow row with a bet
    fake_economy.balances[(P1, GID)] = 5
    from sb.domain.games import store as gs

    run(gs.upsert_checkpoint(None, guild_id=GID, user_id=P1,
                             channel_id=CH, subsystem="t_gc",
                             state={"bet": 40}, version=1, now=10))
    row = run(gs.list_active("t_gc", guild_id=GID))[0]
    ctx = _ctx({"row": row, "reason": "games:gc_refund"})
    out = run(ops._record_gc_sweep_row(None, ctx))
    assert out.after["refunded"] == 40 and out.after["deleted"] == 1
    assert fake_economy.balances[(P1, GID)] == 45
    assert ctx.params["_balance_changes"][0][1] == 40


def test_world_card_text(fake_games_store):
    from sb.domain.games import service, xp

    run(xp.award_in_txn(None, user_id=P1, guild_id=GID, game="mining",
                        action="depth_record", now=1_000_000))
    text = run(service.world_card_text(P1, GID))
    assert "World level" in text and "Mining" in text and "25" in text


def test_world_card_view_handler_reply_shape(fake_games_store):
    # resolve.py's HandlerRef leg requires the Reply duck-shape
    # (.outcome/.user_message); a raw dict AttributeErrors live !worldcard.
    from sb.domain.games import service
    from sb.spec.outcomes import SUCCESS

    req = SimpleNamespace(actor=SimpleNamespace(user_id=P1), guild_id=GID)
    reply = run(service._world_card_view(req))
    assert reply.outcome == SUCCESS
    assert "World level" in reply.user_message
