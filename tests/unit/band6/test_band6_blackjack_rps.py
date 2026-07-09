"""Band 6 slice 1 — blackjack engine/legs and RPS rules/legs over the
in-memory substrate fakes."""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1, P2, CH = 1, 42, 43, 900


def _ctx(params: dict, *, uid: int = P1, gid: int = GID,
         epoch: int = 1_000_000):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc))


class NoShuffle(random.Random):
    """Deterministic 'shuffle' — deck stays in construction order, so
    pops come from the tail (K ♣ …)."""

    def shuffle(self, seq):
        return None


# --- engine math (shipped verbatim) ----------------------------------------------------


def test_hand_value_ace_demotion():
    from sb.domain.blackjack.engine import hand_value, is_blackjack

    assert hand_value(["A ♠", "K ♦"]) == 21
    assert is_blackjack(["A ♠", "K ♦"])
    assert hand_value(["A ♠", "A ♦", "9 ♣"]) == 21
    assert hand_value(["A ♠", "K ♦", "5 ♣"]) == 16
    assert hand_value(["K ♠", "Q ♦", "5 ♣"]) == 25


def test_dealer_stands_on_17():
    from sb.domain.blackjack.engine import dealer_play, hand_value

    deck = ["2 ♠"] * 10
    dealer = ["10 ♠", "7 ♦"]
    dealer_play(deck, dealer)
    assert dealer == ["10 ♠", "7 ♦"]          # 17: stand
    dealer = ["10 ♠", "6 ♦"]
    dealer_play(deck, dealer)
    assert hand_value(dealer) >= 17


# --- blackjack solo legs -----------------------------------------------------------------


def test_solo_start_deals_and_checkpoints(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops

    ops.set_rng_for_tests(NoShuffle())
    fake_economy.balances[(P1, GID)] = 100
    out = run(ops._record_solo_start(None, _ctx({"bet": 25})))
    after = out.after
    assert after["bet"] == 25 and not after["terminal"]
    assert any(c.startswith("g1:blackjack:") for c in after["components"])
    assert len(fake_games_store.rows) == 1
    # second start refused while a game is live
    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):
        run(ops._record_solo_start(None, _ctx({"bet": 0})))


def test_solo_start_refuses_overdraft_bet(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops
    from sb.kernel.interaction.errors import ValidatorError

    ops.set_rng_for_tests(NoShuffle())
    fake_economy.balances[(P1, GID)] = 10
    with pytest.raises(ValidatorError):
        run(ops._record_solo_start(None, _ctx({"bet": 25})))


def test_solo_stand_settles_and_clears(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops

    ops.set_rng_for_tests(NoShuffle())
    fake_economy.balances[(P1, GID)] = 100
    run(ops._record_solo_start(None, _ctx({"bet": 20})))
    ctx = _ctx({})
    out = run(ops._record_solo_stand(None, ctx))
    after = out.after
    assert after["terminal"] and after["result"]
    assert not fake_games_store.rows                 # checkpoint consumed
    # money moved consistently with the declared delta
    assert fake_economy.balances[(P1, GID)] == 100 + after["delta"]
    if after["delta"]:
        assert ctx.params["_balance_changes"]


def test_solo_double_needs_funding(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops
    from sb.kernel.interaction.errors import ValidatorError

    ops.set_rng_for_tests(NoShuffle())
    fake_economy.balances[(P1, GID)] = 25       # bet 20 -> double needs 40
    run(ops._record_solo_start(None, _ctx({"bet": 20})))
    with pytest.raises(ValidatorError):
        run(ops._record_solo_double(None, _ctx({})))


def test_expired_session_is_polite(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops
    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError, match="expired"):
        run(ops._record_solo_hit(None, _ctx({})))


# --- blackjack PvP flow ------------------------------------------------------------------


def _accept_pvp(ops, fake_economy):
    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 100
    run(ops._record_pvp_challenge(None, _ctx(
        {"target_id": P2, "bet": 30, "channel_id": CH})))
    sid = f"{GID}.{P1}.{CH}"
    run(ops._record_pvp_accept(None, _ctx(
        {"session_id": sid}, uid=P2)))
    return sid


def test_pvp_accept_escrows_both(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops

    ops.set_rng_for_tests(NoShuffle())
    _accept_pvp(ops, fake_economy)
    assert fake_economy.balances[(P1, GID)] == 70
    assert fake_economy.balances[(P2, GID)] == 70
    subsystems = {r["subsystem"] for r in fake_games_store.rows.values()}
    assert "blackjack_pvp_escrow" in subsystems
    assert "blackjack_pvp" in subsystems
    assert "blackjack_pvp_pending" not in subsystems


def test_pvp_stand_both_settles_pot_only(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops

    ops.set_rng_for_tests(NoShuffle())
    sid = _accept_pvp(ops, fake_economy)
    run(ops._record_pvp_move(None, _ctx(
        {"session_id": sid, "session_action": "stand"}, uid=P1)))
    ctx2 = _ctx({"session_id": sid, "session_action": "stand"}, uid=P2)
    out = run(ops._record_pvp_move(None, ctx2))
    after = out.after
    assert after["terminal"]
    # POT-ONLY settle (D-0042 deviation): total coins conserved
    total = (fake_economy.balances[(P1, GID)]
             + fake_economy.balances[(P2, GID)])
    assert total == 200
    assert not fake_games_store.rows                # match + escrow consumed


def test_pvp_accept_is_peer_locked(fake_economy, fake_games_store):
    from sb.domain.blackjack import ops
    from sb.kernel.interaction.errors import ValidatorError

    ops.set_rng_for_tests(NoShuffle())
    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 100
    run(ops._record_pvp_challenge(None, _ctx(
        {"target_id": P2, "bet": 10, "channel_id": CH})))
    sid = f"{GID}.{P1}.{CH}"
    with pytest.raises(ValidatorError, match="isn't for you"):
        run(ops._record_pvp_accept(None, _ctx({"session_id": sid},
                                              uid=777)))


# --- RPS ----------------------------------------------------------------------------------


def test_rps_rules_verbatim():
    from sb.domain.rps.rules import determine_winner, normalize_move

    assert normalize_move("🪨", "classic") == "rock"
    assert normalize_move("lizard", "classic") is None
    assert normalize_move("lizard", "lizard_spock") == "lizard"
    assert determine_winner("rock", "scissors", "classic") == 1
    assert determine_winner("rock", "paper", "classic") == 2
    assert determine_winner("spock", "scissors", "lizard_spock") == 1
    assert determine_winner("fire", "water", "elemental") == 2
    assert determine_winner("pawn", "pawn", "chess") == 0


class FixedChoice(random.Random):
    def __init__(self, value):
        super().__init__()
        self._value = value

    def choice(self, seq):
        return self._value


def _mute_rps_stats(monkeypatch):
    from sb.domain.rps import stats as rps_stats

    async def record_result(conn, **kwargs):
        return None

    monkeypatch.setattr(rps_stats, "record_result", record_result)


def test_rps_solo_win_and_free_play(fake_economy, fake_games_store,
                                    monkeypatch):
    from sb.domain.rps import ops

    _mute_rps_stats(monkeypatch)

    ops.set_rng_for_tests(FixedChoice("scissors"))
    fake_economy.balances[(P1, GID)] = 50
    out = run(ops._record_solo_play(None, _ctx({"move": "rock",
                                                "bet": 20})))
    assert "win" in out.after["result"]
    assert fake_economy.balances[(P1, GID)] == 70
    # free play win pays the fixed reward
    out = run(ops._record_solo_play(None, _ctx({"move": "rock"})))
    assert f"+{ops.FREE_WIN}" in out.after["result"]


def test_rps_solo_loss_floors(fake_economy, fake_games_store,
                              monkeypatch):
    from sb.domain.rps import ops

    _mute_rps_stats(monkeypatch)

    ops.set_rng_for_tests(FixedChoice("paper"))
    fake_economy.balances[(P1, GID)] = 10
    out = run(ops._record_solo_play(None, _ctx({"move": "rock",
                                                "bet": 20})))
    assert "lose" in out.after["result"]
    assert fake_economy.balances[(P1, GID)] == 0     # floored, never minted
    assert fake_economy.audit[-1]["delta"] == -10


def test_rps_pvp_full_flow_settles(fake_economy, fake_games_store):
    from sb.domain.rps import ops

    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 100
    run(ops._record_pvp_challenge(None, _ctx(
        {"target_id": P2, "bet": 25, "channel_id": CH})))
    sid = f"{GID}.{P1}.{CH}"
    run(ops._record_pvp_accept(None, _ctx({"session_id": sid}, uid=P2)))
    assert fake_economy.balances[(P1, GID)] == 75
    run(ops._record_pvp_move(None, _ctx(
        {"session_id": sid, "session_action": "move_rock"}, uid=P1)))
    ctx2 = _ctx({"session_id": sid, "session_action": "move_scissors"},
                uid=P2)
    out = run(ops._record_pvp_move(None, ctx2))
    assert out.after["winner"] == P1
    assert fake_economy.balances[(P1, GID)] == 125
    assert fake_economy.balances[(P2, GID)] == 75
    assert not fake_games_store.rows


def test_rps_pvp_tie_refunds(fake_economy, fake_games_store):
    from sb.domain.rps import ops

    fake_economy.balances[(P1, GID)] = 100
    fake_economy.balances[(P2, GID)] = 100
    run(ops._record_pvp_challenge(None, _ctx(
        {"target_id": P2, "bet": 25, "channel_id": CH})))
    sid = f"{GID}.{P1}.{CH}"
    run(ops._record_pvp_accept(None, _ctx({"session_id": sid}, uid=P2)))
    run(ops._record_pvp_move(None, _ctx(
        {"session_id": sid, "session_action": "move_rock"}, uid=P1)))
    run(ops._record_pvp_move(None, _ctx(
        {"session_id": sid, "session_action": "move_rock"}, uid=P2)))
    assert fake_economy.balances[(P1, GID)] == 100
    assert fake_economy.balances[(P2, GID)] == 100


# --- manifests are wired ------------------------------------------------------------------


def test_band6_manifests_register_sessions_and_dispatcher():
    import sb.manifest.blackjack  # noqa: F401
    import sb.manifest.games  # noqa: F401
    import sb.manifest.rps_tournament  # noqa: F401
    from sb.domain.games.session import registered_session_games
    from sb.manifest.blackjack import MANIFEST as BJ
    from sb.manifest.games import MANIFEST as GAMES
    from sb.manifest.rps_tournament import MANIFEST as RPS

    sb_mods = (BJ, GAMES, RPS)
    assert {m.key for m in sb_mods} == {"blackjack", "games",
                                        "rps_tournament"}
    # ENSURE_REFS re-arms after a ref-table wipe (compiler P1 contract)
    for mod_name in ("games", "blackjack", "rps_tournament"):
        import importlib

        mod = importlib.import_module(f"sb.manifest.{mod_name}")
        mod.ENSURE_REFS()
    games = registered_session_games()
    assert "blackjack" in games and "rps_tournament" in games
