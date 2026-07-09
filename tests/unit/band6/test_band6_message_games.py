"""Band 6 slice 3 — message games: the counting parser/mode cores +
V/M/A decision engine + config lanes, and the chain rule + canonical
writer lanes."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID, P1, P2 = 1, 42, 43
CH = 777


def _ctx(params: dict, *, uid: int = P1, gid: int = GID):
    import datetime as dt

    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=SimpleNamespace(user_id=uid, actor_type="user"), guild_id=gid,
        request_id="r1", confirmed=True, params=params,
        clock=lambda: dt.datetime.fromtimestamp(1_000_000,
                                                tz=dt.timezone.utc))


class FakeCountingStore:
    def __init__(self):
        self.states: dict[int, dict] = {}

    def install(self, monkeypatch):
        from sb.domain.counting import store as cs

        async def get_state(guild_id, conn=None):
            return self.states.get(guild_id, {})

        async def set_state(conn, *, guild_id, state):
            self.states[guild_id] = state

        async def fetchall_rows(conn=None):
            return [{"guild_id": g, "state": s}
                    for g, s in self.states.items()]

        monkeypatch.setattr(cs, "get_state", get_state)
        monkeypatch.setattr(cs, "set_state", set_state)
        return self


class FakeChainStore:
    def __init__(self):
        self.rows: dict[int, dict] = {}

    def install(self, monkeypatch):
        from sb.domain.chain import store as ch

        async def get_chain_channel(channel_id, conn=None):
            row = self.rows.get(channel_id)
            return dict(row) if row else None

        async def get_all_chain_channels(guild_id, conn=None):
            return [dict(r) for r in self.rows.values()
                    if r["guild_id"] == guild_id]

        async def set_chain_channel(conn, *, channel_id, guild_id, word,
                                    limit=0):
            self.rows[channel_id] = {
                "channel_id": channel_id, "guild_id": guild_id,
                "word": word, "word_limit": limit,
                "chain_count": self.rows.get(channel_id, {}).get(
                    "chain_count", 0)}

        async def set_chain_limit(conn, *, channel_id, limit):
            self.rows[channel_id]["word_limit"] = limit

        async def delete_chain_channel(conn, *, channel_id):
            self.rows.pop(channel_id, None)

        async def increment_chain_count(conn, *, channel_id):
            row = self.rows.get(channel_id)
            if not row:
                return 0
            row["chain_count"] = row.get("chain_count", 0) + 1
            return row["chain_count"]

        monkeypatch.setattr(ch, "get_chain_channel", get_chain_channel)
        monkeypatch.setattr(ch, "get_all_chain_channels",
                            get_all_chain_channels)
        monkeypatch.setattr(ch, "set_chain_channel", set_chain_channel)
        monkeypatch.setattr(ch, "set_chain_limit", set_chain_limit)
        monkeypatch.setattr(ch, "delete_chain_channel",
                            delete_chain_channel)
        monkeypatch.setattr(ch, "increment_chain_count",
                            increment_chain_count)
        return self


@pytest.fixture
def counting_store(monkeypatch):
    return FakeCountingStore().install(monkeypatch)


@pytest.fixture
def chain_store(monkeypatch):
    return FakeChainStore().install(monkeypatch)


# --- counting parser (shipped verbatim) ---------------------------------------------


def test_parse_message_shapes():
    from sb.domain.counting import parsing

    assert parsing.parse_message("21") == 21
    assert parsing.parse_message("twenty-one") == 21
    assert parsing.parse_message("a dozen") == 12
    assert parsing.parse_message("XIV") == 14
    assert parsing.parse_message("3 + 4") == 7
    assert parsing.parse_message("sqrt(49)") == 7
    assert parsing.parse_message("5!") == 120
    assert parsing.parse_message("2 ** 5") == 32
    assert parsing.parse_message("hello world") is None


def test_expected_count_modes():
    from sb.domain.counting import game_logic

    assert game_logic.calculate_expected_count({}, 5, "normal") == 6
    assert game_logic.calculate_expected_count(
        {"step": 3}, 9, "reverse") == 6
    assert game_logic.calculate_expected_count(
        {"step": 5}, 0, "skip") == 1
    assert game_logic.calculate_expected_count(
        {"step": 5}, 6, "skip") == 11
    assert game_logic.calculate_expected_count(
        {"sequence_index": 4}, 0, "fibonacci") == 5
    assert game_logic.calculate_expected_count(
        {"sequence_index": 2}, 0, "squares") == 9
    assert game_logic.calculate_expected_count(
        {"sequence_index": 2}, 0, "cubes") == 27
    assert game_logic.calculate_expected_count(
        {"sequence_index": 2}, 0, "factorials") == 6
    assert game_logic.calculate_expected_count(
        {"custom_sequence": [2, 4, 8], "sequence_index": 1}, 2,
        "custom") == 4
    assert game_logic.calculate_expected_count(
        {"custom_sequence": [2], "sequence_index": 1}, 2, "custom") is None
    assert game_logic.is_prime(13) and not game_logic.is_prime(9)


def test_top_counters_ranking():
    from sb.domain.counting import game_logic

    ranked = game_logic.top_counters(
        {"1": 5, "2": 9, "3": 0, "4": 5}, limit=3)
    assert ranked == [("2", 9), ("1", 5), ("4", 5)]


# --- counting decision engine -------------------------------------------------------


def _channel(mode="normal", **over):
    from sb.domain.counting.ops import channel_config

    data = channel_config(mode)
    data.update(over)
    return data


def test_decision_accepts_and_tallies():
    from sb.domain.counting import engine

    data = _channel(current_count=4)
    decision = engine.compute_decision(
        content="5", author_mention="@p", channel_data=data, user_id="42")
    assert decision.accepted and decision.add_reaction == "✅"
    assert decision.state_mutated
    assert data["current_count"] == 5 and data["leaderboard"] == {"42": 1}


def test_decision_wrong_count_and_reset_mode():
    from sb.domain.counting import engine

    data = _channel(current_count=4)
    decision = engine.compute_decision(
        content="7", author_mention="@p", channel_data=data, user_id="42")
    assert not decision.accepted and decision.delete_message
    assert "should be 5" in decision.reply
    assert data["current_count"] == 4          # no reset by default

    data = _channel(current_count=4, reset_on_wrong_count=True,
                    leaderboard={"42": 3})
    decision = engine.compute_decision(
        content="7", author_mention="@p", channel_data=data, user_id="42")
    assert decision.state_mutated and "reset" in decision.reply
    assert data["current_count"] == 0 and data["leaderboard"] == {}


def test_decision_taking_turns_and_multiples():
    from sb.domain.counting import engine

    data = _channel(current_count=4, taking_turns=True, last_user="42")
    decision = engine.compute_decision(
        content="5", author_mention="@p", channel_data=data, user_id="42")
    assert not decision.accepted
    assert "twice in a row" in decision.reply

    data = _channel("multiples", multiple=3, current_count=3, step=3)
    decision = engine.compute_decision(
        content="6", author_mention="@p", channel_data=data, user_id="42")
    assert decision.accepted
    data = _channel("multiples", multiple=3, current_count=3, step=1)
    decision = engine.compute_decision(
        content="4", author_mention="@p", channel_data=data, user_id="42")
    assert not decision.accepted and "multiples of 3" in decision.reply


def test_decision_random_mode_guessing():
    from sb.domain.counting import engine

    data = _channel("random", current_count=0, next_expected=40,
                    range_lo=20, range_hi=60)
    decision = engine.compute_decision(
        content="30", author_mention="@p", channel_data=data,
        user_id="42")
    assert not decision.accepted and decision.state_mutated
    assert "Higher" in decision.reply
    assert data["range_hi"] - data["range_lo"] >= 10

    data["next_expected"], data["range_lo"], data["range_hi"] = 33, 20, 60
    decision = engine.compute_decision(
        content="33", author_mention="@p", channel_data=data,
        user_id="42")
    assert decision.accepted and data["current_count"] == 33
    assert data["leaderboard"] == {"42": 1}
    assert data["next_expected"] > 33          # fresh round rolled


# --- counting config lanes ----------------------------------------------------------


def test_counting_enable_disable_lanes(counting_store):
    from sb.domain.counting import ops
    from sb.kernel.interaction.errors import ValidatorError

    out = run(ops._record_enable(
        None, _ctx({"channel_id": CH, "mode": "skip", "skip_step": 5})))
    assert "Started a **Skip** counting match" in out.after["message"]
    assert "Count up by **5**" in out.after["message"]
    state = counting_store.states[GID]
    assert str(CH) in state["channels"]
    assert state["channels"][str(CH)]["step"] == 5

    with pytest.raises(ValidatorError):        # duplicate enable
        run(ops._record_enable(
            None, _ctx({"channel_id": CH, "mode": "normal"})))
    with pytest.raises(ValidatorError):        # bad mode
        run(ops._record_enable(
            None, _ctx({"channel_id": 1, "mode": "bogus"})))

    run(ops._record_disable(None, _ctx({"channel_id": CH})))
    assert str(CH) not in counting_store.states[GID]["channels"]
    with pytest.raises(ValidatorError):        # already gone
        run(ops._record_disable(None, _ctx({"channel_id": CH})))


def test_counting_toggle_reset_and_skip_lanes(counting_store):
    from sb.domain.counting import ops
    from sb.kernel.interaction.errors import ValidatorError

    run(ops._record_enable(
        None, _ctx({"channel_id": CH, "mode": "skip"})))
    out = run(ops._record_toggle(
        None, _ctx({"channel_id": CH, "flag": "taking_turns"})))
    assert out.after["value"] is True
    out = run(ops._record_set_skip(
        None, _ctx({"channel_id": CH, "step": 7})))
    assert "**7**" in out.after["message"]
    data = counting_store.states[GID]["channels"][str(CH)]
    data["current_count"] = 50
    data["leaderboard"] = {"42": 4}
    run(ops._record_reset(None, _ctx({"channel_id": CH})))
    data = counting_store.states[GID]["channels"][str(CH)]
    assert data["current_count"] == 0 and data["leaderboard"] == {}
    assert data["step"] == 7                   # config preserved

    run(ops._record_enable(None, _ctx({"channel_id": 555,
                                       "mode": "normal"})))
    with pytest.raises(ValidatorError):        # skip step on non-skip mode
        run(ops._record_set_skip(None, _ctx({"channel_id": 555,
                                             "step": 3})))


def test_counting_record_count_lane_and_scrub(counting_store):
    from sb.domain.counting import ops

    run(ops._record_enable(
        None, _ctx({"channel_id": CH, "mode": "normal"})))
    out = run(ops._record_count(
        None, _ctx({"channel_id": CH, "content": "1",
                    "author_mention": "@p"})))
    assert out.after["accepted"] and out.after["add_reaction"] == "✅"
    out = run(ops._record_count(
        None, _ctx({"channel_id": CH, "content": "cabbage",
                    "author_mention": "@p"})))
    assert not out.after["accepted"] and out.after["delete_message"]
    out = run(ops._record_count(
        None, _ctx({"channel_id": 999, "content": "1",
                    "author_mention": "@p"})))
    assert out.after == {"active": False}

    # erasure body: strip the subject everywhere
    data = counting_store.states[GID]["channels"][str(CH)]
    assert data["leaderboard"] == {str(P1): 1}

    async def fetchall(sql, params=(), conn=None):
        return [{"guild_id": g, "state": s}
                for g, s in counting_store.states.items()]

    import sb.domain.counting.store as cs
    real_execute_calls = []

    async def execute(sql, params=(), conn=None):
        # emulate the UPDATE write-back
        counting_store.states[params[0]] = __import__("json").loads(
            params[1])
        real_execute_calls.append(sql)

    import unittest.mock as mock
    with mock.patch.object(cs, "fetchall", fetchall), \
            mock.patch.object(cs, "execute", execute):
        touched = run(cs.scrub_subject(None, user_id=P1))
    assert touched == 1
    data = counting_store.states[GID]["channels"][str(CH)]
    assert data["leaderboard"] == {} and data["last_user"] is None


# --- chain rule core ----------------------------------------------------------------


def test_chain_rule_decisions():
    from sb.domain.chain.engine import check_message

    ok = check_message(content="hi", author_mention="@p", word=None,
                       word_limit=3)
    assert not ok.delete_message and ok.record_progress

    wrong = check_message(content="nope", author_mention="@p",
                          word="hi", word_limit=None)
    assert wrong.delete_message
    assert "Only the word `hi` is allowed" in wrong.warning

    over = check_message(content="one two three four", author_mention="@p",
                         word=None, word_limit=3)
    assert over.delete_message and "at most 3 words" in over.warning

    both = check_message(content="one two three four", author_mention="@p",
                         word="one", word_limit=3)
    assert both.delete_message and "and messages must" in both.warning

    exact = check_message(content="  HI  ", author_mention="@p",
                          word="hi", word_limit=None)
    assert not exact.delete_message and exact.record_progress


# --- chain lanes --------------------------------------------------------------------


def test_chain_create_preserves_existing_limit(chain_store):
    from sb.domain.chain import ops
    from sb.kernel.interaction.errors import ValidatorError

    # a limit-only row exists (word empty)
    chain_store.rows[CH] = {"channel_id": CH, "guild_id": GID, "word": "",
                            "word_limit": 4, "chain_count": 0}
    out = run(ops._record_create(
        None, _ctx({"channel_id": CH, "word": "  Banana  "})))
    assert "banana" in out.after["message"]
    assert chain_store.rows[CH]["word"] == "banana"
    assert chain_store.rows[CH]["word_limit"] == 4     # PRESERVED

    with pytest.raises(ValidatorError):        # active word refuses
        run(ops._record_create(None, _ctx({"channel_id": CH,
                                           "word": "other"})))
    with pytest.raises(ValidatorError):        # empty word refuses
        run(ops._record_create(None, _ctx({"channel_id": 555,
                                           "word": "   "})))


def test_chain_limit_delete_and_progress(chain_store):
    from sb.domain.chain import ops
    from sb.kernel.interaction.errors import ValidatorError

    with pytest.raises(ValidatorError):        # no row yet
        run(ops._record_set_limit(None, _ctx({"channel_id": CH,
                                              "limit": 3})))
    run(ops._record_create(None, _ctx({"channel_id": CH, "word": "go"})))
    out = run(ops._record_set_limit(None, _ctx({"channel_id": CH,
                                                "limit": 3})))
    assert chain_store.rows[CH]["word_limit"] == 3
    out = run(ops._record_set_limit(None, _ctx({"channel_id": CH,
                                                "limit": 3})))
    assert out.after.get("no_change") is True  # skip-write lane

    out = run(ops._record_progress(None, _ctx({"channel_id": CH})))
    assert out.after["chain_count"] == 1
    out = run(ops._record_progress(None, _ctx({"channel_id": CH})))
    assert out.after["chain_count"] == 2

    run(ops._record_delete(None, _ctx({"channel_id": CH})))
    assert CH not in chain_store.rows
    with pytest.raises(ValidatorError):
        run(ops._record_delete(None, _ctx({"channel_id": CH})))


# --- registration surfaces ----------------------------------------------------------


def test_manifests_and_provider_registered():
    import importlib

    for key in ("counting", "chain"):
        mod = importlib.import_module(f"sb.manifest.{key}")
        assert mod.MANIFEST.key == key

    from sb.domain.community.rank_providers import get_provider

    provider = get_provider("countlb")
    assert provider is not None and provider.name == "counting"


def test_counting_command_names_verbatim():
    import importlib

    mod = importlib.import_module("sb.manifest.counting")
    names = {c.name for c in mod.MANIFEST.commands}
    assert names == {
        "countingmenu", "start_match", "end_match", "reset_count",
        "toggle_turns", "count_info", "counttop", "count_rules",
        "set_skip_numbers", "toggle_reset_on_wrong_count"}
    aliases = {a for c in mod.MANIFEST.commands for a in c.aliases}
    assert {"cm", "sm", "em", "rc", "tt", "ci", "ct", "counting_top",
            "cr", "ssn", "trwc"} <= aliases
