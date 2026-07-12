"""The CASINO parity-flip surfaces: the shipped 🎰 hub (footer literal +
DISABLED Roulette placeholder via the renderer_override, the standard
nav row with the "↩ Games" hub label) and the ♠ poker table lobby
(live Seated field + host footer, the four shipped buttons, the closed
terminal, the per-channel launch guard).

Oracle: menno420/superbot disbot/views/casino/hub.py +
disbot/views/casino/poker_table.py + disbot/cogs/casino_cog.py;
parity/goldens/casino/sweep_casino.json + sweep_poker.json pin the
wire bytes.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _fresh_tables():
    from sb.domain.casino.table import reset_tables_for_tests

    reset_tables_for_tests()
    yield
    reset_tables_for_tests()


def _ctx(channel_id: int = 2):
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=1, actor=SimpleNamespace(user_id=42),
        channel_id=channel_id, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


# --- the hub spec: golden-pinned bytes -----------------------------------------------


def test_hub_spec_shape_matches_the_golden():
    from sb.domain.casino.panels import casino_hub_spec
    from sb.spec.panels import ActionStyle, Audience, FooterMode

    spec = casino_hub_spec()
    assert spec.panel_id == "casino.hub"
    assert spec.title == "🎰 Casino"
    assert spec.audience is Audience.INVOKER
    assert spec.frame.style_token == "purple"        # GAME_COLOR 10181046
    assert spec.frame.footer_mode is FooterMode.NONE
    assert spec.session_lifecycle is True            # <cid:N>, no anchor row
    assert spec.navigation.show_help is True
    assert spec.navigation.show_home is True
    assert spec.navigation.home_hub == "games"

    by_id = {a.action_id: a for a in spec.actions}
    assert by_id["casino_new_poker"].label == "New Poker Table"
    assert by_id["casino_new_poker"].emoji == "🃏"
    assert by_id["casino_new_poker"].style is ActionStyle.SUCCESS  # wire 3
    assert by_id["casino_roulette"].label == "Roulette (soon)"
    assert by_id["casino_roulette"].emoji == "🎡"
    assert by_id["casino_roulette"].style is ActionStyle.SECONDARY  # wire 2
    assert spec.layout.pages[0].rows == (
        ("casino_new_poker", "casino_roulette"),)


def test_specs_pass_the_compile_fences():
    from sb.domain.casino.panels import casino_hub_spec, poker_table_spec
    from sb.kernel.panels.compile import check_panel

    check_panel(casino_hub_spec())
    check_panel(poker_table_spec())


# --- the hub render: footer literal + disabled placeholder + nav labels --------------


def test_hub_render_matches_the_golden_bytes():
    from sb.domain.casino.panels import _render_hub, casino_hub_spec

    rendered = run(_render_hub(casino_hub_spec(), _ctx()))
    # views/casino/hub.py build_casino_hub_embed, verbatim.
    assert rendered.embed.description == (
        "Group casino games you play together at one table — everyone "
        "gets their **own private, live-updating hand**.\n\n"
        "Pick a game below. Typed shortcut: `!poker`.")
    assert rendered.embed.fields == (
        ("🃏 Texas Hold'em Poker",
         "Multiplayer poker, 2–8 players. Take a seat, get a private "
         "hand, and bet it out — your cards update live as everyone "
         "plays. Play-chips."),
        ("🎡 Roulette",
         "_Coming soon — built on the same shared-table framework._"),
    )
    # the shared invoker-lock footer (outside FooterMode's vocabulary).
    assert rendered.embed.footer == (
        "Only you can interact with this panel.")
    by_id = {c.custom_id: c for c in rendered.components}
    # the shipped decorator pins disabled=True on Roulette (soon) — set
    # by the override on the CANONICAL id, pre-mint.
    assert by_id["casino.hub.casino_roulette"].disabled is True
    assert by_id["casino.hub.casino_new_poker"].disabled is False
    # the shipped standard nav row, labeled with the HUB'S display name.
    assert by_id["nav:help"].label == "📚 Help"
    assert by_id["nav:hub:games"].label == "↩ Games"


# --- the poker table: spec + live lobby render ----------------------------------------


def test_poker_table_spec_shape_matches_the_golden():
    from sb.domain.casino.panels import poker_table_spec
    from sb.spec.panels import ActionStyle, Audience

    spec = poker_table_spec()
    assert spec.panel_id == "casino.poker_table"
    assert spec.title == "♠ Poker Table — open!"
    # the shipped lobby message is public in-channel (anyone may Join).
    assert spec.audience is Audience.PUBLIC
    assert spec.session_lifecycle is True
    assert spec.navigation.show_help is False        # no nav slots
    assert spec.navigation.show_home is False

    by_id = {a.action_id: a for a in spec.actions}
    assert (by_id["poker_join"].label, by_id["poker_join"].emoji,
            by_id["poker_join"].style) == ("Join", "🪑",
                                           ActionStyle.SUCCESS)
    assert (by_id["poker_leave"].label, by_id["poker_leave"].emoji,
            by_id["poker_leave"].style) == ("Leave", "🚪",
                                            ActionStyle.SECONDARY)
    assert (by_id["poker_start"].label, by_id["poker_start"].emoji,
            by_id["poker_start"].style) == ("Start", "▶️",
                                            ActionStyle.PRIMARY)
    assert (by_id["poker_close"].label, by_id["poker_close"].emoji,
            by_id["poker_close"].style) == ("Close", "🗑️",
                                            ActionStyle.DANGER)
    assert spec.layout.pages[0].rows == (
        ("poker_join", "poker_leave", "poker_start", "poker_close"),)


def test_poker_render_carries_the_live_lobby_state():
    from sb.domain.casino.panels import (
        _render_poker_table,
        poker_table_spec,
    )
    from sb.domain.casino.table import launch_table

    launch_table(2, 42, "AdminActor")
    rendered = run(_render_poker_table(poker_table_spec(), _ctx(2)))
    assert rendered.embed.description == (
        "**Texas Hold'em**, group play. Press **Join** to take a seat — "
        "you'll get a private hand that updates live as everyone "
        "plays.\n\n"
        "Buy-in: **1000** play-chips · Blinds 5/10 · up to 8 seats.")
    # the live Seated field: host crown + count (the golden's fresh open).
    assert rendered.embed.fields == (("Seated (1/8)", "👑 AdminActor"),)
    assert rendered.embed.footer == "Host AdminActor starts when ready."
    assert len(rendered.components) == 4


def test_poker_render_closed_stage_is_the_shipped_teardown_terminal():
    from sb.domain.casino.panels import (
        _render_poker_table,
        poker_table_spec,
    )

    ctx = _ctx(2)
    ctx.params["stage"] = "closed"
    rendered = run(_render_poker_table(poker_table_spec(), ctx))
    assert rendered.embed.title == "♠ Poker Table — closed"
    assert rendered.embed.description == "The host closed the table."
    assert rendered.components == ()


# --- the launch guard: one live table per channel -------------------------------------


def _req(*, channel_id: int = 2, uid: int = 42, args: dict | None = None):
    return SimpleNamespace(
        guild_id=1, channel_id=channel_id,
        actor=SimpleNamespace(user_id=uid), args=dict(args or {}),
        origin=SimpleNamespace(message=None))


def test_poker_open_refuses_a_second_table_with_the_shipped_copies():
    from sb.domain.casino import service
    from sb.domain.casino.table import launch_table
    from sb.spec.outcomes import BLOCKED
    from sb.spec.refs import HandlerRef, resolve

    service.ensure_handler_refs()
    launch_table(2, 7, "Host")
    poker_open = resolve(HandlerRef("casino.poker_open"))
    # the command's shipped channel copy (cogs/casino_cog.py).
    reply = run(poker_open(_req()))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "♠ There's already an active poker table in this channel — "
        "join that one or wait for it to finish.")
    # the hub click's shipped ephemeral copy (views/casino/hub.py).
    reply = run(poker_open(_req(args={"session_action":
                                      "casino_new_poker"})))
    assert reply.outcome == BLOCKED
    assert reply.user_message == (
        "There's already an active poker table in this channel — join "
        "that one (scroll up) or wait for it to finish.")


def test_lobby_registry_round_trip():
    from sb.domain.casino.table import (
        close_table,
        get_table,
        launch_table,
    )

    lobby = launch_table(2, 42, "AdminActor")
    assert lobby is not None
    assert launch_table(2, 43, "Other") is None       # one table per channel
    assert get_table(2) is lobby
    assert lobby.is_seated(42) and not lobby.is_seated(43)
    close_table(2)
    assert get_table(2) is None


# --- the refs + manifest ---------------------------------------------------------------


def test_refs_registered_and_manifest_routes():
    from sb.domain.casino import panels, service
    from sb.manifest.casino import MANIFEST
    from sb.spec.refs import HandlerRef, PanelRef, is_registered

    panels.ensure_panel_refs()
    service.ensure_handler_refs()
    assert is_registered(PanelRef("casino.hub"))
    assert is_registered(PanelRef("casino.poker_table"))
    for name in ("casino.render_hub", "casino.render_poker_table",
                 "casino.poker_open", "casino.roulette_soon",
                 "casino.poker_join", "casino.poker_leave",
                 "casino.poker_start", "casino.poker_close"):
        assert is_registered(HandlerRef(name)), name

    by_name = {c.name: c for c in MANIFEST.commands}
    assert by_name["casino"].route == PanelRef("casino.hub")
    assert by_name["poker"].route == HandlerRef("casino.poker_open")
    assert by_name["poker"].aliases == ("holdem",)
    assert {p.panel_id for p in MANIFEST.panels} == {
        "casino.hub", "casino.poker_table"}
