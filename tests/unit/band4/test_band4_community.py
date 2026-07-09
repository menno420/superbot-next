"""Band 4 (community/leaderboard/spotlight) — the provider registry, the
declared xp.level_up consumption, panel registration, and the manifest
surfaces."""

from __future__ import annotations

import asyncio

import pytest

run = asyncio.run


@pytest.fixture(autouse=True)
def _clean_state():
    from sb.domain.community.rank_providers import reset_providers_for_tests
    from sb.domain.community.spotlight import reset_feed_for_tests

    reset_providers_for_tests()
    reset_feed_for_tests()
    yield
    reset_providers_for_tests()
    reset_feed_for_tests()


# --- the provider registry -----------------------------------------------------------------

def test_builtin_providers_and_aliases():
    from sb.domain.community.rank_providers import get_provider, provider_names

    assert provider_names() == ["xp", "coins", "karma"]
    assert get_provider("lb").name == "xp"          # shipped ALIASES rows
    assert get_provider("rankings").name == "xp"
    assert get_provider("rep").name == "karma"
    assert get_provider("karmalb").name == "karma"
    assert get_provider("minelb") is None           # band-6 provider absent
    assert get_provider(None) is None


def test_band6_registration_needs_no_consumer_edits():
    from sb.domain.community.rank_providers import (
        RankProvider,
        get_provider,
        provider_names,
        register_provider,
    )

    async def top(guild_id):
        return []

    async def member_rank(guild_id, user_id):
        return None, None

    register_provider(RankProvider(
        name="mining", display_title="⛏️ Mining Leaderboard",
        select_label="Mining", select_emoji="⛏️",
        empty_hint="No mining records yet.",
        top=top, member_rank=member_rank),
        aliases=("minelb", "miningleaderboard"))
    assert "mining" in provider_names()
    assert get_provider("minelb").name == "mining"


# --- the declared xp.level_up consumption ----------------------------------------------------

class FakeBus:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)

    async def emit(self, name, **payload):
        for handler in self.handlers.get(name, []):
            await handler(**payload)


def test_spotlight_feed_rides_the_bus():
    from sb.domain.community import spotlight

    bus = FakeBus()
    spotlight.subscribe(bus)
    assert "xp.level_up" in bus.handlers
    for lv in range(1, 8):
        run(bus.emit("xp.level_up", guild_id=1, user_id=7, new_level=lv,
                     source="chat"))
    feed = spotlight.levelup_feed(1)
    assert len(feed) == 5                          # bounded (shipped maxlen)
    assert feed[-1] == "**<@7>** reached Level **7**"
    assert spotlight.levelup_feed(2) == []


def test_provider_board_text_empty_and_unknown():
    from dataclasses import replace

    from sb.domain.community import spotlight
    from sb.domain.community.rank_providers import get_provider, register_provider

    async def top(guild_id):
        return []

    register_provider(replace(get_provider("xp"), top=top))
    text = run(spotlight.provider_board_text("xp", 1))
    assert "No XP earned yet" in text
    assert "Unknown category" in run(spotlight.provider_board_text("nope", 1))


# --- handlers ---------------------------------------------------------------------------------

class FakeReq:
    def __init__(self, argv=(), invoked="", gid=1, uid=42):
        self.args = {"argv": tuple(argv), "invoked_with": invoked}
        self.guild_id = gid
        self.request_id = "r1"
        self.confirmed = False

        class _A:
            user_id = uid
            actor_type = "user"

        self.actor = _A()


def test_board_view_resolves_alias_then_argv(monkeypatch):
    from sb.domain.community import handlers, spotlight
    from sb.spec.refs import HandlerRef, resolve

    seen = []

    async def fake_board(name, gid):
        seen.append(name)
        return f"board:{name}"

    monkeypatch.setattr(spotlight, "provider_board_text", fake_board)
    handlers.ensure_handler_refs()
    board_view = resolve(HandlerRef("leaderboard.board_view"))

    out = run(board_view(FakeReq(invoked="lb")))
    assert seen == ["lb"] and "board:lb" in out.user_message

    out = run(board_view(FakeReq(argv=("karma",), invoked="leaderboard")))
    assert seen[-1] == "karma"

    out = run(board_view(FakeReq(invoked="leaderboard")))
    assert "Leaderboards" in out.user_message      # overview fallback


# --- panels + manifests -----------------------------------------------------------------------

def test_band4_panels_register_clean():
    from sb.domain.community.panels import install_community_panels
    from sb.domain.xp.panels import install_xp_panels
    from sb.kernel.panels.registry import clear_panels_for_tests, static_route

    clear_panels_for_tests()
    try:
        install_xp_panels()
        specs = install_community_panels()
        assert [s.panel_id for s in specs] == [
            "community.hub", "leaderboard.board",
            "community_spotlight.hub", "community_spotlight.games"]
        # G-10: the xp modals mint their roots into the static table
        assert static_route("xp.givexp_form") is not None
        assert static_route("xp.resetxp_form") is not None
    finally:
        clear_panels_for_tests()


def test_band4_manifest_surfaces():
    from sb.manifest.community import MANIFEST as community
    from sb.manifest.community_spotlight import MANIFEST as spotlight
    from sb.manifest.karma import MANIFEST as karma
    from sb.manifest.leaderboard import MANIFEST as leaderboard
    from sb.manifest.xp import MANIFEST as xp

    assert {m.key for m in (xp, karma, community, spotlight, leaderboard)} \
        == {"xp", "karma", "community", "community_spotlight", "leaderboard"}
    # shipped alias set verbatim on !leaderboard
    lb = leaderboard.commands[0]
    assert set(lb.aliases) == {"lb", "rankings", "minelb",
                               "miningleaderboard", "fishlb",
                               "dm_leaderboard", "dm_lb", "rpslb", "farmlb",
                               "countlb", "counting_leaderboard"}
    # the karma group: add rides qualified dispatch
    add = next(c for c in karma.commands if c.name == "add")
    assert add.group == "karma" and add.qualified_name == "karma add"
    # xp declares the three shipped events (level_up now DECLARED)
    assert [e.name for e in xp.events] == ["xp.awarded", "xp.level_up",
                                           "xp.reset"]
    # spotlight/community/leaderboard own no stores or settings
    for m in (community, spotlight, leaderboard):
        assert m.stores == () and m.settings == ()
