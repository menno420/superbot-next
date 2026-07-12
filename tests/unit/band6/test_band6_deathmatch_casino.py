"""Band 6 slice 4 — deathmatch duels (g1 recipe, PvP stats, bot AI) +
casino pure layers (cards + hand evaluator) + the rps stats write."""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1, P2 = 1, 42, 43
CH = 777


def _ctx(params: dict, *, uid: int = P1, gid: int = GID,
         epoch: int = 1_000_000):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc))


class FakeDmStats:
    def __init__(self):
        self.results: list[tuple[int, int, int]] = []
        self.rows: dict[tuple[int, int], dict] = {}

    def install(self, monkeypatch):
        from sb.domain.deathmatch import store as ds

        async def record_result(conn, *, winner_id, loser_id, guild_id):
            self.results.append((winner_id, loser_id, guild_id))
            w = self.rows.setdefault((winner_id, guild_id),
                                     {"wins": 0, "losses": 0})
            w["wins"] += 1
            l = self.rows.setdefault((loser_id, guild_id),
                                     {"wins": 0, "losses": 0})
            l["losses"] += 1

        async def leaderboard(guild_id, conn=None):
            return sorted(
                [{"user_id": uid, **r}
                 for (uid, gid), r in self.rows.items() if gid == guild_id],
                key=lambda r: -r["wins"])[:15]

        monkeypatch.setattr(ds, "record_result", record_result)
        monkeypatch.setattr(ds, "leaderboard", leaderboard)
        return self


@pytest.fixture
def dm_stats(monkeypatch):
    return FakeDmStats().install(monkeypatch)


class _NoCrit(random.Random):
    """random() -> 0.99 (never crit); choice -> first element."""

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]


class _AlwaysCrit(_NoCrit):
    def random(self):
        return 0.0


# --- duel core ----------------------------------------------------------------------


def test_duel_core_attack_defend_crit():
    from sb.domain.deathmatch import core

    core.set_rng_for_tests(_NoCrit())
    duel = core.DuelState(player1=P1, player2=P2)
    damage, critical = duel.attack(P1, P2)
    assert (damage, critical) == (15, False)
    assert duel.player2_hp == 85

    duel.defend(P2)
    damage, _ = duel.attack(P1, P2)
    assert damage == 7                      # halved once
    assert duel.defense[P2] is False        # consumed
    damage, _ = duel.attack(P1, P2)
    assert damage == 15                     # back to full

    core.set_rng_for_tests(_AlwaysCrit())
    damage, critical = duel.attack(P1, P2)
    assert (damage, critical) == (30, True)

    state = duel.to_state()
    revived = core.DuelState.from_state(state)
    assert revived.player2_hp == duel.player2_hp
    assert revived.turn == duel.turn
    core.set_rng_for_tests(random.Random())


def test_bot_action_bias():
    from sb.domain.deathmatch import core

    core.set_rng_for_tests(_NoCrit())       # choice -> first element
    assert core.pick_bot_action(100) == "attack"
    assert core.pick_bot_action(30) == "attack"
    assert core.pick_bot_action(10) == "attack"
    core.set_rng_for_tests(random.Random(7))
    assert core.pick_bot_action(10) in ("attack", "defend")
    core.set_rng_for_tests(random.Random())


# --- duel lanes ---------------------------------------------------------------------


def _start_pvp(fake_games_store, dm_stats):
    """Challenge writes NOTHING (the ops-module D-0042-review note —
    the pending challenge is the session binding's args); the duel row
    and its g1 components are born at accept."""
    from sb.domain.deathmatch import ops

    out = run(ops._record_challenge(
        None, _ctx({"channel_id": CH, "target_id": P2})))
    assert out.after["challenger"] == P1
    assert out.after["target"] == P2
    assert "session_id" not in out.after     # no row, no session yet
    out = run(ops._record_accept(
        None, _ctx({"challenger": P1, "target": P2, "channel_id": CH},
                   uid=P2)))
    sid = out.after["session_id"]
    assert any(c.startswith("g1:deathmatch:") for c in
               out.after["components"])
    return sid, out


def test_challenge_accept_move_settle(fake_games_store, dm_stats):
    from sb.domain.deathmatch import core, ops
    from sb.kernel.interaction.errors import ValidatorError

    core.set_rng_for_tests(_NoCrit())
    sid, out = _start_pvp(fake_games_store, dm_stats)
    assert "It's <@42>'s turn" in out.after["message"]

    with pytest.raises(ValidatorError):     # not your turn
        run(ops._record_move(None, _ctx({"session_id": sid,
                                         "session_action": "attack"},
                                        uid=P2)))
    # both trade 15-damage attacks: P2 falls on P1's 7th swing
    for _ in range(6):
        run(ops._record_move(None, _ctx({"session_id": sid,
                                         "session_action": "attack"})))
        run(ops._record_move(None, _ctx({"session_id": sid,
                                         "session_action": "attack"},
                                        uid=P2)))
    out = run(ops._record_move(None, _ctx({"session_id": sid,
                                           "session_action": "attack"})))
    assert out.after["terminal"] and "🏆 <@42> wins!" in \
        out.after["message"]
    assert dm_stats.results == [(P1, P2, GID)]
    # row consumed — settle-once
    with pytest.raises(ValidatorError):
        run(ops._record_move(None, _ctx({"session_id": sid,
                                         "session_action": "attack"})))
    core.set_rng_for_tests(random.Random())


def test_challenge_guards_and_decline(fake_games_store, dm_stats):
    """Shipped guard semantics: ``active_duels`` held only ACCEPTED
    duels, so the already-in-a-duel refusal keys on duel rows (challenge
    AND accept both check); a pending challenge is session-binding
    memory — decline consumes nothing durable (the card's expire owns
    single-answer, the shipped ``view.stop()``)."""
    from sb.domain.deathmatch import ops
    from sb.kernel.interaction.errors import ValidatorError

    pending = {"challenger": P1, "target": P2, "channel_id": CH}
    with pytest.raises(ValidatorError):     # self-challenge
        run(ops._record_challenge(
            None, _ctx({"channel_id": CH, "target_id": P1})))
    run(ops._record_challenge(
        None, _ctx({"channel_id": CH, "target_id": P2})))
    with pytest.raises(ValidatorError):     # only the target may accept
        run(ops._record_accept(None, _ctx(dict(pending), uid=99)))
    with pytest.raises(ValidatorError):     # ...or decline
        run(ops._record_decline(None, _ctx(dict(pending), uid=99)))
    out = run(ops._record_decline(None, _ctx(dict(pending), uid=P2)))
    assert out.after["terminal"]
    assert dm_stats.results == []
    # an ACCEPTED duel arms the shipped either-already-in-a-duel guard
    # on both the challenge and the accept lanes
    run(ops._record_accept(None, _ctx(dict(pending), uid=P2)))
    with pytest.raises(ValidatorError):
        run(ops._record_challenge(
            None, _ctx({"channel_id": 888, "target_id": P2}, uid=99)))
    with pytest.raises(ValidatorError):     # double-accept lands on the row
        run(ops._record_accept(None, _ctx(dict(pending), uid=P2)))


def test_bot_duel_no_stats(fake_games_store, dm_stats):
    from sb.domain.deathmatch import core, ops

    core.set_rng_for_tests(_NoCrit())       # bot always attacks, no crits
    out = run(ops._record_bot_start(None, _ctx({})))
    sid = out.after["session_id"]
    # player + bot trade 15s; player1 (100hp) lands first each round
    last = None
    for _ in range(7):
        last = run(ops._record_bot_move(
            None, _ctx({"session_id": sid,
                        "session_action": "bot_attack"})))
        if last.after.get("terminal"):
            break
    assert last.after["terminal"] and "🏆 <@42> wins!" in \
        last.after["message"]
    assert "off the leaderboard" in last.after["message"]
    assert dm_stats.results == []           # PR-6 rule
    core.set_rng_for_tests(random.Random())


# --- rps stats write ----------------------------------------------------------------


def test_rps_solo_writes_stats(fake_economy, fake_games_store,
                               monkeypatch):
    from sb.domain.rps import ops as rps_ops
    from sb.domain.rps import stats as rps_stats

    calls = []

    async def record_result(conn, *, user_id, guild_id, name, result):
        calls.append((user_id, guild_id, name, result))

    monkeypatch.setattr(rps_stats, "record_result", record_result)

    class _FixedRng:
        def choice(self, seq):
            return "scissors"               # bot always throws scissors

    rps_ops.set_rng_for_tests(_FixedRng())
    out = run(rps_ops._record_solo_play(
        None, _ctx({"move": "rock", "bet": 0})))
    assert "win" in out.after["result"].lower() or "🎉" in \
        out.after["result"]
    assert calls == [(P1, GID, f"<@{P1}>", "win")]
    rps_ops.set_rng_for_tests(random.Random())


def test_rps_stats_store_result_vocab(monkeypatch):
    from sb.domain.rps import stats

    executed = []

    async def execute(sql, params=(), conn=None):
        executed.append(sql)

    monkeypatch.setattr(stats, "execute", execute)
    run(stats.record_result(None, user_id=P1, guild_id=GID, name="n",
                            result="win"))
    assert any("wins=wins+1" in s for s in executed)
    executed.clear()
    run(stats.record_result(None, user_id=P1, guild_id=GID, name="n",
                            result="bogus"))
    assert len(executed) == 1               # ensure-row only, no stat


# --- casino pure layers -------------------------------------------------------------


def test_cards_and_hand_evaluator():
    from sb.domain.casino.cards import card, make_deck
    from sb.domain.casino.evaluate import (
        HandCategory,
        best_hand,
        score_five,
    )

    deck = make_deck(shuffle=False)
    assert len(deck) == len(set(deck)) == 52

    def hand(*codes):
        return [card(c) for c in codes]

    assert best_hand(hand("AS", "KS", "QS", "JS", "10S", "2H", "3D")
                     ).category == HandCategory.STRAIGHT_FLUSH
    assert score_five(hand("AH", "AD", "AC", "AS", "9H")
                      ).category == HandCategory.FOUR_OF_A_KIND
    assert score_five(hand("AH", "2D", "3C", "4S", "5H")
                      ).category == HandCategory.STRAIGHT  # wheel
    full = score_five(hand("KH", "KD", "KC", "2S", "2H"))
    flush = score_five(hand("AH", "9H", "7H", "5H", "3H"))
    assert full.key > flush.key             # full house beats flush
    tie_a = score_five(hand("AH", "KD", "QC", "JS", "9H"))
    tie_b = score_five(hand("AS", "KC", "QD", "JH", "9C"))
    assert tie_a.key == tie_b.key           # split-pot detectable


# --- registration surfaces ----------------------------------------------------------


def test_slice4_manifests_and_providers():
    import importlib

    dm = importlib.import_module("sb.manifest.deathmatch")
    assert {c.name for c in dm.MANIFEST.commands} == {"dm_challenge",
                                                      "dm_help"}
    aliases = {a for c in dm.MANIFEST.commands for a in c.aliases}
    assert {"deathmatch", "challenge", "dm", "deathmatch_help"} <= aliases
    assert dm.MANIFEST.settings[0].settings_key == \
        "deathmatch_turn_timeout"

    cas = importlib.import_module("sb.manifest.casino")
    assert {c.name for c in cas.MANIFEST.commands} == {"casino", "poker"}

    from sb.domain.community.rank_providers import get_provider

    assert get_provider("dm_lb").name == "deathmatch"
    assert get_provider("board").name == "deathmatch"
    assert get_provider("rpslb").name == "rps"

    rps = importlib.import_module("sb.manifest.rps_tournament")
    assert any(s.table == "rps_players" for s in rps.MANIFEST.stores)
