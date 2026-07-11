"""Band 6 — blackjack tournament orchestration (the shipped registration
→ launch → chips rounds → champion loop, headless) + the ORDER-004
walking-skeleton drive: boot the replay composition root, open
registration through the REAL pipeline (`!bjtournament` → the
golden-pinned embed + 🃏 Join button + the ✅ self-reaction primer),
sign up by button AND by the kernel reaction seam, launch with
`!bjstart` (fee debits at launch, shipped), click the chips rounds
through, and watch the champion payout land on the audited lane —
settle-once by the flag-row check-and-set (the #130 free-branch race,
closed for BOTH games; the direct-leg tests below pin it).
"""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore
from tests.unit.band6.test_band6_rps_tournament import FakeTournamentFlag

run = asyncio.run

# parity/harness/world.py constants (the skeleton's real world)
W_GUILD = 700_000_000_000_000_001
ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102
SECOND = 900_000_000_000_000_103
PERSONA = {ADMIN: "admin", MEMBER: "member", SECOND: "second_member"}


def _panel_ctx(params: dict, uid: int = ADMIN):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


# --- renderers: the golden-pinned registration embed --------------------------------


def test_registration_render_pins_the_golden_bytes():
    from sb.domain.blackjack.panels import (
        _render_registration,
        blackjack_registration_spec,
    )

    spec = blackjack_registration_spec()
    rendered = run(_render_registration(spec, _panel_ctx(
        {"entry_fee": 0, "rounds": 5, "duration_mins": 5, "players": 0})))
    assert rendered.embed.title == (
        "🃏 Blackjack Tournament — Registration Open")
    assert rendered.embed.style_token == "green"     # SUCCESS_COLOR 3066993
    assert rendered.embed.description == ""
    assert rendered.embed.fields == (
        ("Entry Fee", "Free", True), ("Rounds", "5", True),
        ("Duration", "5 min", True), ("Players", "0", True),
        ("Pot", "0 🪙", True))
    assert rendered.embed.footer == "React ✅ or click Join to register."
    (join,) = rendered.components
    assert (join.label, join.style, join.emoji, join.disabled) == (
        "Join Tournament", "success", "🃏", False)
    assert rendered.self_reactions == ("✅",)         # the shipped primer
    assert rendered.invoker_lock is None             # PUBLIC sign-up


def test_registration_render_paid_fee_and_pot():
    from sb.domain.blackjack.panels import (
        _render_registration,
        blackjack_registration_spec,
    )

    rendered = run(_render_registration(blackjack_registration_spec(),
                                        _panel_ctx({"entry_fee": 25,
                                                    "rounds": 3,
                                                    "duration_mins": 10,
                                                    "players": 2})))
    # the shipped _tourn_embed paid-fee formatting, verbatim
    assert rendered.embed.fields == (
        ("Entry Fee", "**25** 🪙", True), ("Rounds", "3", True),
        ("Duration", "10 min", True), ("Players", "2", True),
        ("Pot", "50 🪙", True))


def test_tournament_table_render_terminal_chip_line():
    from sb.domain.blackjack.panels import (
        _render_tournament_table,
        blackjack_tournament_table_spec,
    )

    spec = blackjack_tournament_table_spec()
    rendered = run(_render_tournament_table(spec, _panel_ctx({
        "uid": MEMBER, "player": ["K♠ 10", "9♦ 9"], "player_value": 19,
        "dealer": ["Q♣ 10", "8♥ 8"], "dealer_value": 18,
        "chips": 1200, "rounds_left": 4, "round_no": 1,
        "terminal": True, "result": "🎉 You win!", "delta": 200})))
    # the shipped _finish_round field bytes
    assert rendered.embed.fields[-1] == (
        "🎉 You win!", "Chips: **1200** | Rounds left: **4**", False)
    assert rendered.embed.fields[2] == ("Bet", "**200** chips", True)
    assert all(c.disabled for c in rendered.components)
    assert rendered.invoker_lock == MEMBER


def test_results_render_medal_lines_and_payout_field():
    from sb.domain.blackjack.panels import (
        _render_results,
        blackjack_results_spec,
    )

    rendered = run(_render_results(blackjack_results_spec(), _panel_ctx({
        "ranking": [[ADMIN, 1400], [MEMBER, 800]],
        "names": {str(ADMIN): "Admin"}, "winner": ADMIN,
        "entry_fee": 25, "paid": True, "amount": 50, "balance": 125})))
    assert rendered.embed.title == "🏆 Blackjack Tournament Results"
    assert rendered.embed.style_token == "gold"      # ECONOMY_COLOR
    assert rendered.embed.description == (
        f"🥇 **Admin** — 1400 chips\n🥈 **<@{MEMBER}>** — 800 chips")
    assert rendered.embed.fields == (
        ("Winner's payout",
         f"<@{ADMIN}> receives **50** 🪙 (Balance: 125 🪙)", True),)
    assert rendered.components == ()


# --- the pure chips-round core --------------------------------------------------------


def test_try_join_guards_and_copy():
    from sb.domain.blackjack import tournament

    tournament.reset_tournaments_for_tests()
    state = tournament.get_state(1)
    ok, msg = run(tournament.register_player(1, 11))
    assert ok and msg == "✅ Registered! (1 player(s) so far)"
    ok, msg = run(tournament.register_player(1, 11))
    assert not ok and msg == "You're already registered!"
    state.started = True
    ok, msg = run(tournament.register_player(1, 22))
    assert not ok and msg == "The tournament has already started."
    tournament.reset_tournaments_for_tests()


def test_round_move_chips_bookkeeping():
    from sb.domain.blackjack import tournament

    tournament.reset_tournaments_for_tests()
    tournament.set_tournament_rng_for_tests(random.Random(7))
    try:
        state = tournament.get_state(1)
        state.rounds = 2
        state.started = True
        state.entrants = {"11": tournament.TournPlayer(user_id=11,
                                                       rounds_left=2)}
        view = tournament.deal_round(state, 11)
        assert view["chips"] == 1000 and view["round_no"] == 1
        assert view["dealer"][1] == "?"              # hole card hidden
        out = tournament.round_move(state, 11, "stand")
        assert out["stage"] == "round_done"
        entrant = state.entrants["11"]
        assert entrant.rounds_left == 1 and not entrant.done
        assert abs(out["delta"]) in (0, 200, 300)    # flat 200 bet (1.5× natural)
        assert entrant.chips == max(0, 1000 + out["delta"])
        # locks: a stranger and a dead hand
        assert tournament.round_move(state, 99, "stand") == {
            "stage": "not_yours"}
        assert tournament.round_move(state, 11, "stand")["stage"] == (
            "expired")                               # no live hand
        tournament.deal_round(state, 11)
        out = tournament.round_move(state, 11, "stand")
        assert out["stage"] == "round_done" and out.get("player_done")
        assert entrant.done and state.results["11"] == entrant.chips
        assert tournament.all_done(state)
        assert tournament.ranking(state)[0][0] == 11
    finally:
        tournament.set_tournament_rng_for_tests(None)
        tournament.reset_tournaments_for_tests()


# --- the settle-once payout guard (the #130 free-branch race, both games) -------------


@pytest.fixture()
def leg_seams(monkeypatch):
    economy = FakeEconomy().install(monkeypatch)
    games = FakeGamesStore().install(monkeypatch)
    flags = FakeTournamentFlag().install(monkeypatch)
    return economy, games, flags


def _leg_ctx(params: dict):
    from sb.kernel.interaction.request import ActorRef
    from sb.kernel.workflow.context import WorkflowContext

    import uuid

    return WorkflowContext(
        actor=ActorRef(user_id=ADMIN, is_guild_operator=True,
                       is_bot_owner=False, is_dm=False),
        guild_id=W_GUILD, request_id=f"race-{uuid.uuid4()}", params=params)


def test_rps_champion_payout_fires_exactly_once(leg_seams):
    """Two racing champion resolutions on a FREE tournament: the flag-row
    check-and-set lets exactly one pay the 100 🪙 consolation."""
    from sb.domain.rps.ops import _record_tournament_payout
    from tests.unit.workflow.conftest import FakeConn

    economy, games, flags = leg_seams
    flags.flags[W_GUILD] = "rps"
    first = run(_record_tournament_payout(FakeConn(), _leg_ctx(
        {"winner_id": MEMBER, "entry_fee": 0, "free_reward": 100})))
    assert first.after == {"paid": True, "amount": 100}
    second = run(_record_tournament_payout(FakeConn(), _leg_ctx(
        {"winner_id": MEMBER, "entry_fee": 0, "free_reward": 100})))
    assert second.after == {"paid": False, "amount": 0}
    assert economy.balances[(MEMBER, W_GUILD)] == 100   # exactly once
    assert [a["reason"] for a in economy.audit] == [
        "rps:tournament_free_reward"]
    assert W_GUILD not in flags.flags


def test_blackjack_champion_payout_fires_exactly_once(leg_seams):
    from sb.domain.blackjack.ops import _record_tournament_payout
    from tests.unit.workflow.conftest import FakeConn

    economy, games, flags = leg_seams
    flags.flags[W_GUILD] = "blackjack"
    first = run(_record_tournament_payout(FakeConn(), _leg_ctx(
        {"winner_id": MEMBER, "entry_fee": 0, "free_reward": 200})))
    assert first.after["paid"] and first.after["amount"] == 200
    second = run(_record_tournament_payout(FakeConn(), _leg_ctx(
        {"winner_id": MEMBER, "entry_fee": 0, "free_reward": 200})))
    assert second.after == {"paid": False, "amount": 0}
    assert economy.balances[(MEMBER, W_GUILD)] == 200
    assert [a["reason"] for a in economy.audit] == [
        "blackjack:tournament_free_reward"]
    assert W_GUILD not in flags.flags


# --- ORDER-004 walking skeleton -----------------------------------------------------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams
    (the #124/#130 fixture, blackjack-tournament flavored)."""
    from sb.adapters.parity.boot import Harness

    economy = FakeEconomy().install(monkeypatch)
    games = FakeGamesStore().install(monkeypatch)
    flags = FakeTournamentFlag().install(monkeypatch)

    import contextlib

    from sb.kernel.db import pool
    from tests.unit.workflow.conftest import FakeConn

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)

    h = asyncio.run(Harness.start(require_db=False))

    from sb.domain.blackjack import tournament
    from sb.domain.blackjack.panels import register_blackjack_sessions
    from sb.domain.games.session import install_games_dispatcher

    tournament.reset_tournaments_for_tests()
    tournament.register_reaction_signup()
    tournament.set_tournament_rng_for_tests(random.Random(11))
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
    yield h, economy, games, flags
    tournament.set_tournament_rng_for_tests(None)
    tournament.reset_tournaments_for_tests()
    asyncio.run(h.close())


def _components(call) -> list[dict]:
    out = []
    for row in call.payload.get("components", []):
        out.extend(row["components"])
    return out


def _round_views(calls) -> list:
    return [c for c in calls if (c.payload or {}).get("embeds")
            and "🃏 Blackjack Tournament —"
            in c.payload["embeds"][0].get("title", "")
            and _components(c)]


def _stand(harness, view_call, uid: int):
    buttons = {b["label"]: b["custom_id"] for b in _components(view_call)}
    run(harness.click(message_id=view_call.response_id,
                      custom_id=buttons["Stand"], persona=PERSONA[uid]))
    return harness.take_calls()


def test_bjstart_without_tournament_keeps_the_pinned_guard(skeleton):
    harness, economy, games, flags = skeleton
    run(harness.send_command("!bjstart", persona="admin"))
    calls = harness.take_calls()
    assert any("No pending tournament." in str(c.payload) for c in calls
               if c.payload)
    assert not economy.audit


def test_walking_skeleton_blackjack_tournament_end_to_end(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.blackjack import tournament
    from sb.kernel.interaction.reactions import (
        ReactionEvent,
        dispatch_reaction,
    )

    # 1. !bjtournament (free, 1 round) — the golden-pinned registration
    #    message + ✅ primer + the shipped flag row
    run(harness.send_command("!bjtournament 0 1 5", persona="admin"))
    calls = harness.take_calls()
    assert [c.method for c in calls] == ["send_message", "add_reaction"]
    (embed,) = calls[0].payload["embeds"]
    assert embed["title"] == "🃏 Blackjack Tournament — Registration Open"
    assert embed["color"] == 3066993               # shipped SUCCESS_COLOR
    assert embed["footer"] == {"text": "React ✅ or click Join to register."}
    assert embed["fields"] == [
        {"inline": True, "name": "Entry Fee", "value": "Free"},
        {"inline": True, "name": "Rounds", "value": "1"},
        {"inline": True, "name": "Duration", "value": "5 min"},
        {"inline": True, "name": "Players", "value": "0"},
        {"inline": True, "name": "Pot", "value": "0 🪙"}]
    (join,) = _components(calls[0])
    assert (join["label"], join["style"]) == ("Join Tournament", 3)
    assert join["emoji"] == {"id": None, "name": "🃏"}
    reg_id = calls[0].response_id
    assert calls[1].args == {"channel_id": harness.world.channels["general"],
                             "emoji": "✅", "message_id": reg_id}
    assert flags.flags[W_GUILD] == "blackjack"     # the audited flag row

    # a second !bjtournament is guarded with the shipped copy
    run(harness.send_command("!bjtournament", persona="admin"))
    dup_open = harness.take_calls()
    assert any("A tournament is already running." in str(c.payload)
               for c in dup_open if c.payload)

    # 2. sign-ups: Join button (admin + member), duplicate refused,
    #    reaction (second_member) through the kernel seam — silent
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="admin"))
    first_join = harness.take_calls()
    assert any("✅ Registered! (1 player(s) so far)" in str(c.payload)
               for c in first_join if c.payload)
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="member"))
    harness.take_calls()
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="member"))
    dup = harness.take_calls()
    assert any("You're already registered!" in str(c.payload) for c in dup
               if c.payload)
    run(dispatch_reaction(ReactionEvent(
        guild_id=W_GUILD, channel_id=harness.world.channels["general"],
        message_id=reg_id, user_id=SECOND, emoji="✅")))
    assert harness.take_calls() == []
    state = tournament.get_state(W_GUILD)
    assert state.players == [ADMIN, MEMBER, SECOND]

    # !bjstatus reads the live in-memory tournament
    run(harness.send_command("!bjstatus", persona="admin"))
    status = harness.take_calls()
    assert any("registration open" in str(c.payload) for c in status
               if c.payload)

    # 3. !bjstart launches: free play (no debits), welcome + one round
    #    view per entrant
    run(harness.send_command("!bjstart", persona="admin"))
    calls = harness.take_calls()
    texts = [str((c.payload or {}).get("content")) for c in calls]
    assert sum("rounds and start with **1000** chips. Good luck! 🃏" in t
               for t in texts) == 3
    views = _round_views(calls)
    assert len(views) == 3
    assert not economy.audit                       # free: no launch debits
    for view in views:
        assert {b["label"] for b in _components(view)} == {"Hit", "Stand"}

    # 4. rounds: each entrant stands their single round out; the view
    #    edits in place (type-6 ack) and the finish line lands
    by_uid = {}
    for view in views:
        title = view.payload["embeds"][0]["title"]
        uid = int(title.split("<@")[1].split(">")[0])
        by_uid[uid] = view
    for uid in (ADMIN, MEMBER):
        done_calls = _stand(harness, by_uid[uid], uid)
        assert [c.method for c in done_calls][:2] == [
            "interaction_response", "edit_followup"]
        assert done_calls[0].payload == {"type": 6}
        (edited,) = done_calls[1].payload["embeds"]
        assert "Chips: **" in str(edited["fields"])
        assert all(b["disabled"] for b in _components(done_calls[1]))
        assert any("✅ You finished the tournament with **" in str(
            (c.payload or {}).get("content")) for c in done_calls)
        assert tournament.state_or_none(W_GUILD) is not None

    # 5. the last entrant's stand settles the tournament: results embed,
    #    free consolation exactly once, flag row consumed, state gone
    final_calls = _stand(harness, by_uid[SECOND], SECOND)
    results = [c for c in final_calls if (c.payload or {}).get("embeds")
               and c.payload["embeds"][0].get("title")
               == "🏆 Blackjack Tournament Results"]
    assert len(results) == 1
    (res_embed,) = results[0].payload["embeds"]
    assert res_embed["color"] == 15844367          # shipped ECONOMY_COLOR
    assert "🥇" in res_embed["description"]
    assert "chips" in res_embed["description"]
    assert "fields" not in res_embed or not res_embed.get("fields")
    assert [a["reason"] for a in economy.audit] == [
        "blackjack:tournament_free_reward"]
    (payout,) = economy.audit
    assert payout["delta"] == 200                  # shipped free_reward
    assert W_GUILD not in flags.flags              # cleared in the SAME txn
    assert tournament.state_or_none(W_GUILD) is None

    # 6. a late click on a settled round view politely expires
    buttons = {b["label"]: b["custom_id"]
               for b in _components(by_uid[SECOND])}
    run(harness.click(message_id=by_uid[SECOND].response_id,
                      custom_id=buttons["Hit"], persona="second_member"))
    late = harness.take_calls()
    assert any("expired" in str(c.payload).lower() for c in late
               if c.payload)


def test_walking_skeleton_entry_fee_pot_and_launch_skip(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.blackjack import tournament

    economy.balances[(ADMIN, W_GUILD)] = 100
    economy.balances[(MEMBER, W_GUILD)] = 100

    run(harness.send_command("!bjtournament 25 1 5", persona="admin"))
    calls = harness.take_calls()
    (embed,) = calls[0].payload["embeds"]
    assert embed["fields"][0] == {"inline": True, "name": "Entry Fee",
                                  "value": "**25** 🪙"}
    (join,) = _components(calls[0])
    reg_id = calls[0].response_id

    # a broke player is fee-gated at JOIN with the shipped copy
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="second_member"))
    broke = harness.take_calls()
    assert any("❌ Need **25** 🪙 to enter (you have 0)." in str(c.payload)
               for c in broke if c.payload)

    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="admin"))
    harness.take_calls()
    run(harness.click(message_id=reg_id, custom_id=join["custom_id"],
                      persona="member"))
    harness.take_calls()
    # fees debit at LAUNCH, not at join (shipped)
    assert economy.balances[(ADMIN, W_GUILD)] == 100
    assert economy.balances[(MEMBER, W_GUILD)] == 100
    assert not economy.audit

    # member goes broke between join and launch → silently skipped
    economy.balances[(MEMBER, W_GUILD)] = 0
    run(harness.send_command("!bjstart", persona="admin"))
    calls = harness.take_calls()
    assert economy.balances[(ADMIN, W_GUILD)] == 75
    assert [a["reason"] for a in economy.audit] == ["tournament:entry_fee"]
    assert sorted(r["subsystem"] for r in games.rows.values()) == [
        "blackjack_tournament"]                    # recovery-refundable row
    views = _round_views(calls)
    assert len(views) == 1                         # only the paid entrant

    final_calls = _stand(harness, views[0], ADMIN)
    results = [c for c in final_calls if (c.payload or {}).get("embeds")
               and c.payload["embeds"][0].get("title")
               == "🏆 Blackjack Tournament Results"]
    assert len(results) == 1
    (res_embed,) = results[0].payload["embeds"]
    # the shipped Winner's payout field on a paid pot
    (field,) = res_embed["fields"]
    assert field["name"] == "Winner's payout"
    assert f"<@{ADMIN}> receives **25** 🪙" in field["value"]
    assert economy.audit[-1]["reason"] == "blackjack:tournament_win"
    assert economy.balances[(ADMIN, W_GUILD)] == 100   # 75 + the 25 pot
    assert not games.rows                          # entry rows consumed
    assert W_GUILD not in flags.flags
    assert tournament.state_or_none(W_GUILD) is None


def test_bjstart_cancel_branches(skeleton):
    harness, economy, games, flags = skeleton
    from sb.domain.blackjack import tournament

    # no players registered
    run(harness.send_command("!bjtournament", persona="admin"))
    reg = harness.take_calls()
    run(harness.send_command("!bjstart", persona="admin"))
    calls = harness.take_calls()
    assert any("❌ Tournament cancelled — no players registered."
               in str(c.payload) for c in calls if c.payload)
    assert W_GUILD not in flags.flags              # shipped clear_active
    assert tournament.state_or_none(W_GUILD) is None

    # nobody can afford the fee at launch
    economy.balances[(ADMIN, W_GUILD)] = 50
    run(harness.send_command("!bjtournament 50", persona="admin"))
    reg = harness.take_calls()
    (join,) = _components(reg[0])
    run(harness.click(message_id=reg[0].response_id,
                      custom_id=join["custom_id"], persona="admin"))
    harness.take_calls()
    economy.balances[(ADMIN, W_GUILD)] = 0
    run(harness.send_command("!bjstart", persona="admin"))
    calls = harness.take_calls()
    assert any("❌ Tournament cancelled — no players could afford the "
               "entry fee." in str(c.payload) for c in calls if c.payload)
    assert W_GUILD not in flags.flags
    assert tournament.state_or_none(W_GUILD) is None
    assert not economy.audit                       # nothing ever debited


def test_results_embed_renders_exactly_once_under_a_settled_race(skeleton):
    """The #133-review cosmetic race: two racing final stands both pass
    ``all_done`` — the in-memory ``state.settled`` check-and-set (the
    twin of the payout op's flag-row guard) makes the losing racer's
    ``_finish_tournament`` a no-op: no second results embed, no payout
    op run, no double teardown."""
    harness, economy, games, flags = skeleton
    from sb.domain.blackjack import tournament

    run(harness.send_command("!bjtournament 0 1 5", persona="admin"))
    reg = harness.take_calls()
    (join,) = _components(reg[0])
    for persona in ("admin", "member"):
        run(harness.click(message_id=reg[0].response_id,
                          custom_id=join["custom_id"], persona=persona))
        harness.take_calls()
    run(harness.send_command("!bjstart", persona="admin"))
    views = _round_views(harness.take_calls())
    assert len(views) == 2
    by_uid = {}
    for view in views:
        title = view.payload["embeds"][0]["title"]
        by_uid[int(title.split("<@")[1].split(">")[0])] = view

    _stand(harness, by_uid[ADMIN], ADMIN)          # not all done yet
    state = tournament.get_state(W_GUILD)
    assert not state.settled

    # the racing winner claimed the render between the two resolutions
    state.settled = True
    final_calls = _stand(harness, by_uid[MEMBER], MEMBER)
    texts = [str((c.payload or {}).get("content")) for c in final_calls
             if c.payload]
    # the finish line still lands, but NO results embed and NO payout
    assert any("✅ You finished the tournament with **" in t for t in texts)
    assert not [c for c in final_calls if (c.payload or {}).get("embeds")
                and c.payload["embeds"][0].get("title")
                == "🏆 Blackjack Tournament Results"]
    assert not economy.audit
    assert flags.flags.get(W_GUILD) == "blackjack"  # flag row intact
    assert tournament.state_or_none(W_GUILD) is not None
