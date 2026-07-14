"""Band 6 — RPS bot matches (`!rpsbot`, the deep bot-match flow): the
shipped per-player match loop headless (oracle: menno420/superbot
``disbot/cogs/rps_tournament/_bot_matches.py``) + the walking-skeleton
drive — boot the replay composition root, run `!rpsbot` through the REAL
pipeline, click a best-of-3 to completion, and watch every round's stats
land through the audited ``rps.bot_round`` lane. The view rides the
tournament port's ledgered home-channel BUTTON deviation (private match
channels + no-prefix message parsing stay the resource-provision
successor); every user-facing line is the shipped ``_bot_matches.py``
channel copy, byte-for-byte."""

from __future__ import annotations

import asyncio
import random
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

# parity/harness/world.py constants (the skeleton's real world)
W_GUILD = 700_000_000_000_000_001
ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102
SECOND = 900_000_000_000_000_103
PERSONA = {ADMIN: "admin", MEMBER: "member", SECOND: "second_member"}


class ScriptedBot:
    """A ``random.Random`` stand-in whose ``choice`` plays a scripted
    sequence of bot throws (the ops.set_bot_rng_for_tests pattern)."""

    def __init__(self, moves):
        self.moves = list(moves)

    def choice(self, seq):
        move = self.moves.pop(0)
        assert move in seq
        return move


def _panel_ctx(params: dict, uid: int = MEMBER):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


# --- renderer: the shipped bot-match channel copy, verbatim -------------------------


def test_botmatch_render_open_stage_keeps_shipped_lines():
    from sb.domain.rps.panels import _render_botmatch, rps_botmatch_spec

    rendered = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "open", "player": MEMBER, "match_id": "b1",
        "mode": "classic", "best_of": 3})))
    # the shipped match-channel announce (run_rps_bot_command), verbatim
    assert rendered.embed.description == (
        f"<@{MEMBER}> vs **Bot**\n"
        "Game mode: Classic, Best of 3\n"
        "Please enter your move.")
    assert rendered.embed.title == "✂️ RPS Bot Match"
    assert rendered.embed.style_token == "purple"
    labels = [(c.label, c.emoji, c.disabled) for c in rendered.components]
    assert labels == [("Rock", "🪨", False), ("Paper", "📄", False),
                      ("Scissors", "✂️", False)]
    # subsystem-scoped ids: `bot_move_*` (the match panel owns `move_*`)
    assert [c.custom_id for c in rendered.components] == [
        "rps_tournament.botmatch.bot_move_rock",
        "rps_tournament.botmatch.bot_move_paper",
        "rps_tournament.botmatch.bot_move_scissors"]
    assert rendered.invoker_lock is None


def test_botmatch_render_mode_subset_lizard_spock():
    from sb.domain.rps.panels import _render_botmatch, rps_botmatch_spec

    rendered = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "open", "player": MEMBER, "mode": "lizard_spock",
        "best_of": 3})))
    assert [c.label for c in rendered.components] == [
        "Rock", "Paper", "Scissors", "Lizard", "Spock"]


def test_botmatch_render_round_reveal_shipped_lines():
    from sb.domain.rps.panels import _render_botmatch, rps_botmatch_spec

    rendered = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "round", "player": MEMBER, "mode": "classic",
        "best_of": 3, "wins": 1, "bot_wins": 0, "move": "rock",
        "bot_move": "scissors", "result": "win"})))
    # shipped handle_bot_match_move sends, in wire order, verbatim
    assert rendered.embed.description == (
        f"<@{MEMBER}> vs **Bot**\n"
        "Game mode: Classic, Best of 3\n"
        "Bot played: Scissors.\n"
        f"<@{MEMBER}> wins this round!\n"
        "Please enter your next move.\n"
        f"Score: <@{MEMBER}> **1** — **0** Bot")
    assert not any(c.disabled for c in rendered.components)


def test_botmatch_render_tie_and_loss_lines():
    from sb.domain.rps.panels import _render_botmatch, rps_botmatch_spec

    tie = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "round", "player": MEMBER, "mode": "classic",
        "best_of": 3, "wins": 0, "bot_wins": 0, "move": "rock",
        "bot_move": "rock", "result": "tie"})))
    assert "It's a tie!" in tie.embed.description          # shipped
    lost = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "match_lost", "player": MEMBER, "mode": "classic",
        "best_of": 3, "wins": 0, "bot_wins": 2, "move": "rock",
        "bot_move": "paper", "result": "loss"})))
    # shipped terminal copy, verbatim; controls dead; ERROR_COLOR accent
    assert "Bot wins this round!" in lost.embed.description
    assert "Bot wins the match!" in lost.embed.description
    assert "Please enter your next move." not in lost.embed.description
    assert lost.embed.style_token == "red"
    assert all(c.disabled for c in lost.components)


def test_botmatch_render_won_terminal():
    from sb.domain.rps.panels import _render_botmatch, rps_botmatch_spec

    won = run(_render_botmatch(rps_botmatch_spec(), _panel_ctx({
        "stage": "match_won", "player": MEMBER, "mode": "classic",
        "best_of": 3, "wins": 2, "bot_wins": 1, "move": "rock",
        "bot_move": "scissors", "result": "win"})))
    # shipped terminal copy, verbatim
    assert (f"<@{MEMBER}> wins the match against the bot!"
            in won.embed.description)
    assert won.embed.style_token == "green"
    assert all(c.disabled for c in won.components)


# --- the pure match core -------------------------------------------------------------


def test_botmatch_state_best_of_scoring_and_teardown():
    from sb.domain.rps import bot_match

    bot_match.reset_bot_matches_for_tests()
    bot_match.set_bot_rng_for_tests(ScriptedBot(
        ["rock", "scissors", "paper", "scissors"]))
    try:
        match = bot_match.start_match(1, 11, mode="classic", best_of=3)
        assert match.needed == 2                      # (3 // 2) + 1
        out = bot_match.record_bot_move(1, 11, match.match_id, "rock")
        assert out["stage"] == "round" and out["result"] == "tie"
        out = bot_match.record_bot_move(1, 11, match.match_id, "rock")
        assert out["stage"] == "round" and out["result"] == "win"
        out = bot_match.record_bot_move(1, 11, match.match_id, "rock")
        assert out["stage"] == "round" and out["result"] == "loss"
        out = bot_match.record_bot_move(1, 11, match.match_id, "rock")
        assert out["stage"] == "match_won" and out["result"] == "win"
        # terminal: state torn down; a late throw answers the shipped guard
        assert bot_match.bot_state_or_none(1, 11) is None
        assert bot_match.record_bot_move(
            1, 11, match.match_id, "rock")["stage"] == "over"
    finally:
        bot_match.set_bot_rng_for_tests(random.Random())
        bot_match.reset_bot_matches_for_tests()


def test_botmatch_state_alias_invalid_and_replacement():
    from sb.domain.rps import bot_match

    bot_match.reset_bot_matches_for_tests()
    bot_match.set_bot_rng_for_tests(ScriptedBot(["scissors"]))
    try:
        first = bot_match.start_match(1, 11, mode="classic", best_of=3)
        # an unknown token is the shipped invalid-move branch
        assert bot_match.record_bot_move(
            1, 11, first.match_id, "banana")["stage"] == "invalid"
        # a MOVE_ALIASES token normalizes (the shipped normalize_move)
        out = bot_match.record_bot_move(1, 11, first.match_id, "stone")
        assert out["move"] == "rock" and out["result"] == "win"
        # a new !rpsbot REPLACES the running match (the shipped overwrite);
        # the superseded view's clicks answer the already-over guard
        second = bot_match.start_match(1, 11, mode="classic", best_of=3)
        assert bot_match.record_bot_move(
            1, 11, first.match_id, "rock")["stage"] == "over"
        assert bot_match.bot_state_or_none(1, 11).match_id == second.match_id
    finally:
        bot_match.set_bot_rng_for_tests(random.Random())
        bot_match.reset_bot_matches_for_tests()


# --- walking skeleton ----------------------------------------------------------------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams
    (the rps tournament fixture, plus bot-match state + a stats recorder)."""
    from sb.adapters.parity.boot import Harness

    economy = FakeEconomy().install(monkeypatch)
    FakeGamesStore().install(monkeypatch)

    import contextlib

    from sb.kernel.db import pool
    from tests.unit.workflow.conftest import FakeConn

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)

    # per-round stats evidence: record the audited op's rps_players write
    from sb.domain.rps import stats as rps_stats

    stat_rows: list[tuple[int, str]] = []

    async def record_result(conn, *, user_id, guild_id, name, result):
        stat_rows.append((int(user_id), str(result)))

    monkeypatch.setattr(rps_stats, "record_result", record_result)

    h = asyncio.run(Harness.start(require_db=False))

    from sb.domain.games.session import install_games_dispatcher
    from sb.domain.rps import bot_match
    from sb.domain.rps.panels import register_rps_sessions

    bot_match.reset_bot_matches_for_tests()
    register_rps_sessions()
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
    yield h, economy, stat_rows
    bot_match.set_bot_rng_for_tests(random.Random())
    bot_match.reset_bot_matches_for_tests()
    asyncio.run(h.close())


def _components(call) -> list[dict]:
    out = []
    for row in call.payload.get("components", []):
        out.extend(row["components"])
    return out


def _texts(calls) -> list[str]:
    return [str((c.payload or {}).get("content")) for c in calls if c.payload]


def test_walking_skeleton_rpsbot_best_of_three(skeleton):
    harness, economy, stat_rows = skeleton
    from sb.domain.rps import bot_match

    bot_match.set_bot_rng_for_tests(ScriptedBot(["scissors", "paper", "paper"]))

    # 1. !rpsbot — the shipped announce lines on the opened view
    run(harness.send_command("!rpsbot classic 3", persona="member"))
    calls = harness.take_calls()
    view_calls = [c for c in calls if (c.payload or {}).get("embeds")]
    assert len(view_calls) == 1
    (embed,) = view_calls[0].payload["embeds"]
    assert embed["description"] == (
        f"<@{MEMBER}> vs **Bot**\n"
        "Game mode: Classic, Best of 3\n"
        "Please enter your move.")
    buttons = {b["label"]: b["custom_id"] for b in _components(view_calls[0])}
    assert set(buttons) == {"Rock", "Paper", "Scissors"}
    view_id = view_calls[0].response_id

    # 2. a bystander's click is peer-locked (deviation lock, tourney copy)
    run(harness.click(message_id=view_id, custom_id=buttons["Rock"],
                      persona="admin"))
    foreign = harness.take_calls()
    assert any("You're not part of this match." in str(c.payload)
               for c in foreign if c.payload)
    assert stat_rows == []                       # no stats moved

    # 3. round 1 — bot scripted scissors: the player takes the throw
    run(harness.click(message_id=view_id, custom_id=buttons["Rock"],
                      persona="member"))
    calls = harness.take_calls()
    edits = [c for c in calls if (c.payload or {}).get("embeds")]
    (round_embed,) = edits[-1].payload["embeds"]
    assert round_embed["description"] == (
        f"<@{MEMBER}> vs **Bot**\n"
        "Game mode: Classic, Best of 3\n"
        "Bot played: Scissors.\n"
        f"<@{MEMBER}> wins this round!\n"
        "Please enter your next move.\n"
        f"Score: <@{MEMBER}> **1** — **0** Bot")
    assert stat_rows == [(MEMBER, "win")]

    # 4. round 2 — bot paper: the bot takes the throw
    run(harness.click(message_id=view_id, custom_id=buttons["Rock"],
                      persona="member"))
    calls = harness.take_calls()
    (round_embed,) = [c for c in calls
                      if (c.payload or {}).get("embeds")][-1].payload["embeds"]
    assert "Bot played: Paper." in round_embed["description"]
    assert "Bot wins this round!" in round_embed["description"]
    assert f"Score: <@{MEMBER}> **1** — **1** Bot" in round_embed["description"]
    assert stat_rows == [(MEMBER, "win"), (MEMBER, "loss")]

    # 5. round 3 — bot paper vs scissors: match won, view terminal
    run(harness.click(message_id=view_id, custom_id=buttons["Scissors"],
                      persona="member"))
    calls = harness.take_calls()
    final = [c for c in calls if (c.payload or {}).get("embeds")][-1]
    (final_embed,) = final.payload["embeds"]
    assert (f"<@{MEMBER}> wins the match against the bot!"
            in final_embed["description"])
    assert all(b["disabled"] for b in _components(final))
    assert stat_rows == [(MEMBER, "win"), (MEMBER, "loss"), (MEMBER, "win")]
    assert bot_match.bot_state_or_none(W_GUILD, MEMBER) is None

    # 6. a late click on the finished view politely expires
    run(harness.click(message_id=view_id, custom_id=buttons["Rock"],
                      persona="member"))
    late = harness.take_calls()
    assert any("expired" in str(c.payload).lower() for c in late if c.payload)

    # free play: the shipped bot match moves no money
    assert not economy.audit


def test_rpsbot_even_best_of_refuses_with_shipped_copy(skeleton):
    harness, economy, stat_rows = skeleton

    # shipped run_rps_bot_command guard copy, verbatim
    for cmd in ("!rpsbot classic 4", "!rpsbot 4"):
        run(harness.send_command(cmd, persona="member"))
        assert any("Please provide an odd positive integer for the number "
                   "of rounds." in t
                   for t in _texts(harness.take_calls())), cmd
    from sb.domain.rps import bot_match

    assert bot_match.bot_state_or_none(W_GUILD, MEMBER) is None


def test_rpsbot_multi_player_views_are_per_player(skeleton):
    harness, economy, stat_rows = skeleton
    from sb.domain.rps import bot_match

    bot_match.set_bot_rng_for_tests(ScriptedBot(["scissors"]))
    run(harness.send_command(
        f"!rpsbot classic 1 <@{MEMBER}> <@{SECOND}>", persona="admin"))
    calls = harness.take_calls()
    views = [c for c in calls if (c.payload or {}).get("embeds")]
    assert len(views) == 2                       # one view per player
    descs = [v.payload["embeds"][0]["description"] for v in views]
    assert any(f"<@{MEMBER}> vs **Bot**" in d for d in descs)
    assert any(f"<@{SECOND}> vs **Bot**" in d for d in descs)
    # the invoker isn't a player on either view
    member_view = views[0] if f"<@{MEMBER}>" in descs[0] else views[1]
    buttons = {b["label"]: b["custom_id"] for b in _components(member_view)}
    run(harness.click(message_id=member_view.response_id,
                      custom_id=buttons["Rock"], persona="admin"))
    assert any("You're not part of this match." in str(c.payload)
               for c in harness.take_calls() if c.payload)
    # the named player plays their own view to the terminal (best of 1)
    run(harness.click(message_id=member_view.response_id,
                      custom_id=buttons["Rock"], persona="member"))
    calls = harness.take_calls()
    (embed,) = [c for c in calls
                if (c.payload or {}).get("embeds")][-1].payload["embeds"]
    assert f"<@{MEMBER}> wins the match against the bot!" in embed["description"]
    assert stat_rows == [(MEMBER, "win")]
    # the second player's match is untouched
    assert bot_match.bot_state_or_none(W_GUILD, SECOND) is not None
