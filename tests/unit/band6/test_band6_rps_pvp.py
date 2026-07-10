"""Band 6 — RPS PvP on the wire (the shipped challenge → accept/decline →
both-pick → result loop as ONE staged session panel on g1: dynamic ids) +
the ORDER-004 walking-skeleton drive: boot the replay composition root,
challenge through the REAL pipeline, click Accept (escrow), throw both
moves, and watch the settle edit the challenge message to the shipped
`✂️ RPS PvP Result` embed.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

GID, UID = 1, 42
SID = "1.42.900"

# parity/harness/world.py constants (the skeleton's real world)
W_GUILD = 700_000_000_000_000_001
ADMIN = 900_000_000_000_000_101
MEMBER = 900_000_000_000_000_102


def _panel_ctx(params: dict, uid: int = UID):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


# --- renderer: the shipped stage shapes ------------------------------------------


def test_pvp_render_challenge_stage():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    spec = rps_pvp_spec()
    rendered = run(_render_pvp(spec, _panel_ctx({
        "stage": "challenge", "session_id": SID,
        "challenger": 42, "target": 43, "bet": 25})))
    assert rendered.embed.title == "✂️ RPS Challenge!"
    assert rendered.embed.description == (
        "<@42> challenges <@43> to Rock Paper Scissors "
        "(**25** 🪙).\n<@43>, do you accept?")
    assert rendered.embed.style_token == "purple"     # shipped GAME_COLOR
    accept, decline = rendered.components
    assert (accept.label, accept.style, accept.emoji, accept.disabled) == (
        "Accept", "success", "✅", False)
    assert (decline.label, decline.style, decline.emoji) == (
        "Decline", "danger", "❌")
    assert accept.custom_id == f"g1:rps_tournament:{SID}:accept"
    assert decline.custom_id == f"g1:rps_tournament:{SID}:decline"
    assert rendered.invoker_lock is None              # PUBLIC — ops own the locks


def test_pvp_render_free_play_challenge_line():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    rendered = run(_render_pvp(rps_pvp_spec(), _panel_ctx({
        "stage": "challenge", "session_id": SID,
        "challenger": 42, "target": 43, "bet": 0})))
    assert "(free play)" in rendered.embed.description


def test_pvp_render_match_stage():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    rendered = run(_render_pvp(rps_pvp_spec(), _panel_ctx({
        "stage": "match", "session_id": SID})))
    assert rendered.embed.description == (
        "✅ Challenge accepted — both players, choose your move!")
    labels = [(c.label, c.emoji, c.disabled) for c in rendered.components]
    assert labels == [("Rock", "🪨", False), ("Paper", "📄", False),
                      ("Scissors", "✂️", False)]
    assert [c.custom_id for c in rendered.components] == [
        f"g1:rps_tournament:{SID}:move_{m}"
        for m in ("rock", "paper", "scissors")]


def test_pvp_render_declined_stage_disables():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    rendered = run(_render_pvp(rps_pvp_spec(), _panel_ctx({
        "stage": "declined", "session_id": SID, "decliner": 43})))
    assert rendered.embed.description == (
        "❌ <@43> declined the challenge.")
    assert all(c.disabled for c in rendered.components)


def test_pvp_render_result_stage():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    rendered = run(_render_pvp(rps_pvp_spec(), _panel_ctx({
        "stage": "result", "session_id": SID, "p1": 42, "p2": 43,
        "moves": {"42": "rock", "43": "scissors"}, "winner": 42,
        "result": "🎉 <@42> wins!"})))
    assert rendered.embed.title == "✂️ RPS PvP Result"
    assert rendered.embed.style_token == "green"      # shipped SUCCESS_COLOR
    assert rendered.embed.description == (
        "<@42>: **rock** 🪨\n<@43>: **scissors** ✂️\n\n🎉 <@42> wins!")
    assert all(c.disabled for c in rendered.components)


def test_pvp_render_tie_keeps_game_color():
    from sb.domain.rps.panels import _render_pvp, rps_pvp_spec

    rendered = run(_render_pvp(rps_pvp_spec(), _panel_ctx({
        "stage": "result", "session_id": SID, "p1": 42, "p2": 43,
        "moves": {"42": "rock", "43": "rock"}, "winner": None,
        "result": "🤝 Tie! No coins exchanged."})))
    assert rendered.embed.style_token == "purple"


# --- the !rps challenge branch opens the panel ------------------------------------


def test_challenge_opens_the_pvp_panel(monkeypatch, fake_economy,
                                       fake_games_store):
    import contextlib
    import dataclasses

    import sb.manifest.games as games_manifest
    import sb.manifest.rps_tournament as rps_manifest
    from sb.kernel.db import pool
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import HandlerRef, resolve as resolve_ref
    from tests.unit.workflow.conftest import FakeConn

    # re-arm after any earlier suite's ref-table/registry reset
    games_manifest.ENSURE_REFS()
    rps_manifest.ENSURE_REFS()

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)
    fake_economy.balances[(UID, GID)] = 100
    opened = []

    async def fake_open(ref, req):
        opened.append((ref.name, dict(req.args)))

    monkeypatch.setattr(panel_engine, "open_panel", fake_open)

    @dataclasses.dataclass
    class Req:                       # the handler replaces args via dataclasses
        args: dict
        actor: object
        guild_id: int
        channel_id: int
        request_id: str
        confirmed: bool

    play = resolve_ref(HandlerRef("rps.play"))
    reply = run(play(Req(
        args={"argv": ("<@43000000000000043>", "25")},
        actor=SimpleNamespace(user_id=UID), guild_id=GID, channel_id=900,
        request_id="r1", confirmed=False)))
    assert reply.outcome == "success" and reply.user_message is None
    (name, args), = opened
    assert name == "rps_tournament.pvp"
    assert args["stage"] == "challenge"
    assert args["session_id"] == f"{GID}.{UID}.900"
    assert args["challenger"] == UID
    assert args["target"] == 43000000000000043
    assert args["bet"] == 25


# --- ORDER-004 walking skeleton: challenge → accept → moves → settled edit --------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/state seams,
    so the challenge, escrow, and settle legs run end-to-end in CI."""
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
    from sb.domain.games.session import install_games_dispatcher
    from sb.domain.rps.panels import register_rps_sessions

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
    yield h, economy, games
    asyncio.run(h.close())


def test_walking_skeleton_rps_pvp_end_to_end(skeleton):
    harness, economy, games = skeleton
    economy.balances[(ADMIN, W_GUILD)] = 100
    economy.balances[(MEMBER, W_GUILD)] = 100

    # 1. the challenge: the shipped embed + Accept/Decline on g1 ids
    run(harness.send_command(f"!rps <@{MEMBER}> 25", persona="admin"))
    calls = harness.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == "✂️ RPS Challenge!"
    assert embed["color"] == 10181046                 # shipped GAME_COLOR
    assert embed["description"] == (
        f"<@{ADMIN}> challenges <@{MEMBER}> to Rock Paper Scissors "
        f"(**25** 🪙).\n<@{MEMBER}>, do you accept?")
    (row,) = payload["components"]
    accept, decline = row["components"]
    assert accept["label"] == "Accept" and decline["label"] == "Decline"
    assert accept["custom_id"].startswith("g1:rps_tournament:")
    assert accept["custom_id"].endswith(":accept")
    message_id = calls[0].response_id
    # pending challenge row written, no coins moved yet
    assert [r["subsystem"] for r in games.rows.values()] == [
        "rps_pvp_pending"]
    assert not economy.audit

    # 2. a stranger's Accept is peer-locked by the op
    run(harness.click(message_id=message_id,
                      custom_id=accept["custom_id"],
                      persona="second_member"))
    stranger = harness.take_calls()
    assert any("This challenge isn't for you." in str(c.payload)
               for c in stranger if c.payload)
    assert economy.balances[(ADMIN, W_GUILD)] == 100  # nothing escrowed

    # 3. the target's Accept escrows BOTH stakes and edits the message
    # onto the move stage (deferred-update ack + edit, ids g1-stable)
    run(harness.click(message_id=message_id,
                      custom_id=accept["custom_id"], persona="member"))
    accepted = harness.take_calls()
    assert [c.method for c in accepted] == ["interaction_response",
                                            "edit_followup"]
    assert accepted[0].payload == {"type": 6}
    edited = accepted[1].payload
    (match_embed,) = edited["embeds"]
    assert match_embed["description"] == (
        "✅ Challenge accepted — both players, choose your move!")
    (move_row,) = edited["components"]
    moves = {b["label"]: b["custom_id"] for b in move_row["components"]}
    assert set(moves) == {"Rock", "Paper", "Scissors"}
    assert moves["Rock"].endswith(":move_rock")
    assert economy.balances[(ADMIN, W_GUILD)] == 75
    assert economy.balances[(MEMBER, W_GUILD)] == 75
    assert [a["reason"] for a in economy.audit] == [
        "rps:pvp_escrow", "rps:pvp_escrow"]

    # 4. first throw: hidden — the edit only says one move is in
    run(harness.click(message_id=message_id, custom_id=moves["Rock"],
                      persona="admin"))
    first = harness.take_calls()
    assert [c.method for c in first] == ["interaction_response",
                                         "edit_followup"]
    (waiting_embed,) = first[1].payload["embeds"]
    assert "⏳" in waiting_embed["description"]
    assert "rock" not in waiting_embed["description"]  # never revealed early

    # 5. second throw settles: pot to the winner, the shipped result embed
    run(harness.click(message_id=message_id, custom_id=moves["Scissors"],
                      persona="member"))
    settled = harness.take_calls()
    assert [c.method for c in settled] == ["interaction_response",
                                           "edit_followup"]
    (result_embed,) = settled[1].payload["embeds"]
    assert result_embed["title"] == "✂️ RPS PvP Result"
    assert result_embed["color"] == 3066993           # shipped SUCCESS_COLOR
    assert result_embed["description"] == (
        f"<@{ADMIN}>: **rock** 🪨\n<@{MEMBER}>: **scissors** ✂️\n\n"
        f"🎉 <@{ADMIN}> wins!")
    (final_row,) = settled[1].payload["components"]
    assert all(b["disabled"] for b in final_row["components"])
    assert economy.balances[(ADMIN, W_GUILD)] == 125
    assert economy.balances[(MEMBER, W_GUILD)] == 75
    assert economy.audit[-1]["reason"] == "rps:pvp_win"
    assert not games.rows                              # pending + escrow consumed

    # 6. terminal expired the panel session — a late click still routes to
    # the op (g1 is restart-safe) and gets the polite expiry from the
    # consumed checkpoint row.
    run(harness.click(message_id=message_id, custom_id=moves["Paper"],
                      persona="admin"))
    late = harness.take_calls()
    assert any("expired" in str(c.payload) for c in late if c.payload)


def test_walking_skeleton_rps_pvp_decline(skeleton):
    harness, economy, games = skeleton
    economy.balances[(ADMIN, W_GUILD)] = 50
    economy.balances[(MEMBER, W_GUILD)] = 50

    run(harness.send_command(f"!rps <@{MEMBER}> 10", persona="admin"))
    calls = harness.take_calls()
    (row,) = calls[0].payload["components"]
    decline = row["components"][1]
    message_id = calls[0].response_id

    run(harness.click(message_id=message_id,
                      custom_id=decline["custom_id"], persona="member"))
    declined = harness.take_calls()
    assert [c.method for c in declined] == ["interaction_response",
                                            "edit_followup"]
    (embed,) = declined[1].payload["embeds"]
    assert embed["description"] == (
        f"❌ <@{MEMBER}> declined the challenge.")
    (drow,) = declined[1].payload["components"]
    assert all(b["disabled"] for b in drow["components"])
    # no coins ever moved; the pending row is gone
    assert economy.balances[(ADMIN, W_GUILD)] == 50
    assert not economy.audit
    assert not games.rows
