"""Band 6 — the rps quick-play picker (the shipped views/rps/solo_play
view as a session-lifecycle panel) + the ORDER-004 walking-skeleton drive:
boot the replay composition root, drive `!rps` through the REAL pipeline,
click a minted move button, and get the audited solo_play result back."""

from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace

import pytest

from tests.unit.band6.conftest import FakeEconomy, FakeGamesStore

run = asyncio.run

_HEX32 = re.compile(r"^[0-9a-f]{32}$")

GID, UID = 1, 42


def _panel_ctx(params: dict, uid: int = UID):
    return SimpleNamespace(params=params,
                           actor=SimpleNamespace(user_id=uid))


# --- renderer: the shipped embed + button shape -------------------------------------


def test_quickplay_render_free_play_shape():
    from sb.domain.rps.panels import _render_quickplay, rps_quickplay_spec

    spec = rps_quickplay_spec()
    rendered = run(_render_quickplay(spec, _panel_ctx({"argv": ()})))
    assert rendered.embed.title == "✂️ Rock · Paper · Scissors"
    assert rendered.embed.description == (
        "Bet: Free play (win = +30 🪙)\nChoose your move!")
    assert rendered.embed.style_token == "purple"
    assert rendered.embed.footer == ""
    labels = [(c.label, c.emoji, c.style) for c in rendered.components]
    assert labels == [("Rock", "🪨", "secondary"),
                      ("Paper", "📄", "secondary"),
                      ("Scissors", "✂️", "secondary")]
    assert rendered.invoker_lock == UID


def test_quickplay_render_bet_line():
    from sb.domain.rps.panels import _render_quickplay, rps_quickplay_spec

    rendered = run(_render_quickplay(rps_quickplay_spec(),
                                     _panel_ctx({"argv": ("25",)})))
    assert rendered.embed.description == "Bet: **25** 🪙\nChoose your move!"


def test_purple_style_token_is_shipped_game_color():
    from sb.kernel.panels.render import STYLE_TOKEN_COLORS

    assert STYLE_TOKEN_COLORS["purple"] == 10181046   # discord.Color.purple()


# --- the !rps handler branches --------------------------------------------------------


def _req(args: dict, uid: int = UID):
    return SimpleNamespace(
        args=args, actor=SimpleNamespace(user_id=uid), guild_id=GID,
        channel_id=900, request_id="r1", confirmed=False)


def test_bare_rps_opens_the_quickplay_picker(monkeypatch):
    import sb.manifest.rps_tournament  # noqa: F401 — registers the refs
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    play = resolve_ref(HandlerRef("rps.play"))
    reply = run(play(_req({"argv": ()})))
    assert opened == ["rps_tournament.quickplay"]
    assert reply.outcome == "success" and reply.user_message is None


def test_overbet_rps_is_refused_before_the_view_opens(monkeypatch,
                                                      fake_economy):
    import sb.manifest.rps_tournament  # noqa: F401
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import HandlerRef, resolve as resolve_ref

    fake_economy.balances[(UID, GID)] = 10
    opened = []

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    play = resolve_ref(HandlerRef("rps.play"))
    reply = run(play(_req({"argv": ("25",)})))
    assert opened == []
    assert reply.outcome == "blocked"
    assert reply.user_message == "❌ You only have **10** 🪙."


# --- ORDER-004 walking skeleton: boot → !rps → click → resolved result -----------------


@pytest.fixture()
def skeleton(monkeypatch):
    """The replay composition root (DB-free) + in-memory money/stats seams,
    so the click leg's audited op runs end-to-end in CI."""
    from sb.adapters.parity.boot import Harness

    economy = FakeEconomy().install(monkeypatch)
    FakeGamesStore().install(monkeypatch)

    from sb.domain.rps import stats as rps_stats

    async def _mute(*a, **k):
        return None

    monkeypatch.setattr(rps_stats, "record_result", _mute)

    import contextlib

    from sb.kernel.db import pool
    from tests.unit.workflow.conftest import FakeConn

    conn = FakeConn()

    @contextlib.asynccontextmanager
    async def fake_transaction():
        yield conn

    monkeypatch.setattr(pool, "transaction", fake_transaction)

    h = asyncio.run(Harness.start(require_db=False))

    # DB-free: the platform manifest's real access-policy reader (installed
    # at import) would hit the uninitialised pool — pin the unconfigured-
    # allow default (what a guild with no policy rows resolves to anyway).
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
    yield h, economy
    asyncio.run(h.close())


def test_walking_skeleton_rps_quickplay_end_to_end(skeleton):
    harness, economy = skeleton
    run(harness.send_command("!rps", persona="admin"))
    calls = harness.take_calls()
    assert [c.method for c in calls] == ["send_message"]
    payload = calls[0].payload
    (embed,) = payload["embeds"]
    assert embed["title"] == "✂️ Rock · Paper · Scissors"
    assert embed["description"] == (
        "Bet: Free play (win = +30 🪙)\nChoose your move!")
    assert embed["color"] == 10181046
    (row,) = payload["components"]
    buttons = row["components"]
    assert [b["label"] for b in buttons] == ["Rock", "Paper", "Scissors"]
    assert all(_HEX32.match(b["custom_id"]) for b in buttons)
    message_id = calls[0].response_id

    # a stranger's click is invoker-locked (the shipped interaction_check)
    run(harness.click(message_id=message_id,
                      custom_id=buttons[0]["custom_id"], persona="member"))
    stranger = harness.take_calls()
    assert any("This game isn't yours." in str(c.payload)
               for c in stranger if c.payload)

    # the invoker's click runs the audited solo_play op and answers
    from sb.domain.rps import ops

    class _AlwaysScissors:
        def choice(self, seq):
            return "scissors"

    ops.set_rng_for_tests(_AlwaysScissors())
    run(harness.click(message_id=message_id,
                      custom_id=buttons[0]["custom_id"], persona="admin"))
    clicked = harness.take_calls()
    texts = [str(c.payload) for c in clicked if c.payload]
    assert any("🎉 You win! +30 🪙" in t for t in texts), texts
    # the free-play win credited the wallet through the fake economy seam
    assert 30 in list(economy.balances.values())
