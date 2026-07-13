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
    _rearm_cached_game_providers()


def _rearm_cached_game_providers():
    """AFTER-leg re-arm (the #199 hygiene idiom): reset_providers_for_tests
    restores only the band-4 builtins, but under the canonical order the
    #213 integration suite has already imported the WHOLE composition at
    session start — the band-6 game rows registered at those modules'
    import can never re-fire from a cached import, so wiping without
    re-arm strands `get_provider("countlb")`-class lookups for every
    later-listed suite. Re-run each cached registrant's idempotent hook."""
    import sys

    for mod_name, hook_name in (
        ("sb.domain.games.providers", "register_game_providers"),
        ("sb.domain.counting.service", "register_provider_rows"),
        ("sb.domain.deathmatch.service", "register_provider_rows"),
    ):
        mod = sys.modules.get(mod_name)
        hook = getattr(mod, hook_name, None) if mod is not None else None
        if callable(hook):
            hook()


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
    from sb.kernel.panels import engine as panel_engine
    from sb.spec.refs import HandlerRef, resolve

    seen = []
    opened = []

    async def fake_board(name, gid):
        seen.append(name)
        return f"board:{name}"

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(spotlight, "provider_board_text", fake_board)
    monkeypatch.setattr(panel_engine, "open_panel", fake_open)
    handlers.ensure_handler_refs()
    board_view = resolve(HandlerRef("leaderboard.board_view"))

    out = run(board_view(FakeReq(invoked="lb")))
    assert seen == ["lb"] and "board:lb" in out.user_message

    out = run(board_view(FakeReq(argv=("karma",), invoked="leaderboard")))
    assert seen[-1] == "karma"

    # no category → the shipped overview PANEL opens (embed + category
    # selector — the sweep_leaderboard.json shape), not a text reply.
    out = run(board_view(FakeReq(invoked="leaderboard")))
    assert out is None and opened == ["leaderboard.board"]


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
    # shipped alias set verbatim on !leaderboard — exact-tuple pin lives
    # in test_leaderboard_alias_set_is_ledgered_deliberate below
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


def test_leaderboard_alias_set_is_ledgered_deliberate():
    """Curation row 44 guard: the ELEVEN legacy aliases are DELIBERATE.

    Q-A03 (owner-held default, applied at D-0038 docs/decisions.md:290)
    rules "legacy routes stay callable" — the oracle-marked
    legacy_duplicate alias set stays VERBATIM, ledgered in the
    DELIBERATE ALIAS SET block in sb/manifest/leaderboard.py. Drift in
    EITHER direction (a trimmed alias or a grown one) is a contradiction
    of that ruling and must arrive as an owner turn amending Q-A03, with
    this pin and the ledger block updated together.
    """
    import inspect

    import sb.manifest.leaderboard as lb_manifest

    drift_msg = (
        "leaderboard alias tuple drifted — the 11-alias set is pinned "
        "VERBATIM by the owner-held Q-A03 ruling (docs/decisions.md:290, "
        "'legacy routes stay callable'); see the DELIBERATE ALIAS SET "
        "ledger block in sb/manifest/leaderboard.py. Changing the set "
        "requires an owner turn amending Q-A03, not a code-side edit.")
    lb = lb_manifest.MANIFEST.commands[0]
    assert lb.name == "leaderboard" and lb.kind.name == "PREFIX", drift_msg
    # exact tuple, order included — the shipped declaration verbatim
    assert lb.aliases == ("lb", "rankings", "minelb",
                          "miningleaderboard", "fishlb",
                          "dm_leaderboard", "dm_lb", "rpslb", "farmlb",
                          "countlb", "counting_leaderboard"), drift_msg

    # the ledger block itself must stay present and name its authority —
    # a future edit that trims the comment silently un-ledgers the set
    source = inspect.getsource(lb_manifest)
    for marker in ("DELIBERATE ALIAS SET", "Q-A03", "legacy_duplicate"):
        assert marker in source, (
            f"sb/manifest/leaderboard.py lost its '{marker}' ledger "
            "marker — the DELIBERATE ALIAS SET block (curation row 44) "
            "must ride above the CommandSpec; see Q-A03 at "
            "docs/decisions.md:290.")
