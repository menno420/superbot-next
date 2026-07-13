"""Game sections slice 2 (D-0082, docs/design/game-sections.md §5): the
``games.sections`` settings surface — per-section Enable all + pick-a-few
multi-select over the slice-1 registry, every mutation through the
governance K7 ``SET_VISIBILITY`` seam (``set_subsystem_visibility``), and
the settings-hub ``games`` group routing to it."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

run = asyncio.run

GID = 1

_COMPETITIVE = ("blackjack", "casino", "deathmatch", "rps_tournament")
_ACTIVITIES = ("mining", "fishing", "creature", "farm", "counting", "chain")


@pytest.fixture(autouse=True)
def _default_sections():
    """Deterministic registry: exactly the manifest's DEFAULT sections
    (idempotent re-register — a peer test may have cleared the table),
    with the panel/handler/provider refs re-armed; restored after."""
    from sb.domain.games import sections_panel
    from sb.manifest import games as manifest
    from sb.spec import sections as mod

    saved = dict(mod._SECTIONS)
    mod.clear_sections_for_tests()
    manifest._register_sections()
    sections_panel.ensure_sections_panel_refs()
    yield
    mod.clear_sections_for_tests()
    mod._SECTIONS.update(saved)


def _install_enabled(monkeypatch, enabled):
    """Stub the governance READ the panel lazily imports."""
    from sb.domain.governance import service

    async def fake_subsystem_enabled(guild_id: int, subsystem: str) -> bool:
        return subsystem in enabled

    monkeypatch.setattr(service, "subsystem_enabled", fake_subsystem_enabled)


def _install_write_port(monkeypatch, outcome: str = "success"):
    """Stub the governance WRITE seam (the K7 op wrapper); returns the
    write log as (subsystem, enabled) in call order."""
    from sb.domain.governance import service

    writes: list[tuple[str, bool | None]] = []

    async def fake_set_visibility(ctx, *, scope_type, scope_id, subsystem,
                                  enabled):
        assert scope_type == "guild" and scope_id == GID
        writes.append((subsystem, enabled))
        return SimpleNamespace(outcome=outcome, user_message="")

    monkeypatch.setattr(service, "set_subsystem_visibility",
                        fake_set_visibility)
    return writes


def _req(args=None, guild_id=GID):
    return SimpleNamespace(
        args=dict(args or {}), guild_id=guild_id, channel_id=2,
        actor=SimpleNamespace(user_id=42), request_id="req-1",
        confirmed=False, origin=SimpleNamespace(message=None))


def _handler(name):
    from sb.spec.refs import HandlerRef, resolve

    return resolve(HandlerRef(name))


def _ctx():
    from sb.kernel.interaction.locale import LocaleContext
    from sb.kernel.panels.context import PanelContext, PanelOrigin
    from sb.spec.panels import Audience

    return PanelContext(
        bot=None, guild_id=GID, actor=SimpleNamespace(user_id=42),
        channel_id=2, origin=PanelOrigin.INTERACTION,
        audience=Audience.INVOKER, locale=LocaleContext(), params={})


# --- the spec: registry-driven shape + compile fences -------------------------


def test_spec_shape_is_registry_driven():
    from sb.domain.games.sections_panel import games_sections_spec
    from sb.spec.panels import ActionStyle, Audience
    from sb.spec.refs import HandlerRef, PanelRef

    spec = games_sections_spec()
    assert spec.panel_id == "games.sections"
    assert spec.subsystem == "games"
    assert spec.title == "🎮 Game sections"
    assert spec.audience is Audience.INVOKER
    assert spec.session_lifecycle is True
    # opened from the settings hub — ↩ Back returns there.
    assert spec.navigation.parent == PanelRef("settings.hub")

    pick_comp, pick_act = spec.selectors
    assert pick_comp.selector_id == "pick_competitive"
    assert pick_act.selector_id == "pick_activities"
    # pick-a-few: empty selection allowed (disable every game), cap = the
    # section roster size.
    assert (pick_comp.min_values, pick_comp.max_values) == (0, 4)
    assert (pick_act.min_values, pick_act.max_values) == (0, 6)
    for sel in spec.selectors:
        assert sel.audience_tier == "administrator"
        assert sel.on_select == HandlerRef(
            f"games.sections_{sel.selector_id}")

    by_id = {a.action_id: a for a in spec.actions}
    assert set(by_id) == {"enable_all_competitive", "enable_all_activities"}
    for aid, act in by_id.items():
        assert act.audience_tier == "administrator", aid
        assert act.style is ActionStyle.SUCCESS, aid
        assert act.handler == HandlerRef(f"games.sections_{aid}"), aid

    assert spec.layout.pages[0].rows == (
        ("pick_competitive",),
        ("pick_activities",),
        ("enable_all_competitive", "enable_all_activities"),
    )


def test_spec_passes_the_compile_fences_and_is_registered():
    from sb.domain.games.sections_panel import games_sections_spec
    from sb.kernel.panels.compile import check_panel
    from sb.spec.refs import PanelRef, is_registered

    check_panel(games_sections_spec())
    assert is_registered(PanelRef("games.sections"))


def test_manifest_installs_the_sections_panel():
    from sb.manifest.games import MANIFEST

    assert "games.sections" in {p.panel_id for p in MANIFEST.panels}


# --- providers: per-guild state renders from the governance read --------------


def test_fields_provider_marks_disabled_games(monkeypatch):
    from sb.spec.refs import ProviderRef, resolve

    _install_enabled(monkeypatch,
                     set(_COMPETITIVE + _ACTIVITIES) - {"casino", "chain"})
    fields = run(resolve(ProviderRef("games.sections_fields"))(_ctx()))
    assert fields[0][0] == "🏆 Competitive"
    assert "🚫 🎰 **Casino**" in fields[0][1]
    assert "✅ 🃏 **Blackjack**" in fields[0][1]
    assert fields[1][0] == "🎲 Activities"
    assert "🚫 🔗 **Word Chain**" in fields[1][1]


def test_options_provider_defaults_track_enablement(monkeypatch):
    from sb.spec.refs import ProviderRef, resolve

    _install_enabled(monkeypatch, {"blackjack", "deathmatch"})
    options = run(resolve(
        ProviderRef("games.sections_options_competitive"))(_ctx()))
    assert [o["value"] for o in options] == list(_COMPETITIVE)
    assert [o["default"] for o in options] == [True, False, True, False]
    assert options[0]["label"] == "Blackjack"
    assert options[0]["emoji"] == "🃏"


# --- enable-all: one None-write per game in the section -----------------------


def test_enable_all_writes_none_per_game(monkeypatch):
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_enable_all_activities")(_req()))
    assert writes == [(k, None) for k in _ACTIVITIES]
    assert reply.outcome == "success"
    assert "all 6 games enabled" in reply.user_message


def test_enable_all_requires_a_guild(monkeypatch):
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_enable_all_competitive")(
        _req(guild_id=0)))
    assert writes == []
    assert "per server" in reply.user_message


def test_enable_all_reports_a_failed_write(monkeypatch):
    writes = _install_write_port(monkeypatch, outcome="denied")
    reply = run(_handler("games.sections_enable_all_competitive")(_req()))
    # stopped at the FIRST failed write — honest partial count in the copy.
    assert writes == [("blackjack", None)]
    assert reply.outcome == "denied"
    assert "Couldn't enable `blackjack`" in reply.user_message
    assert "0/4 updated" in reply.user_message


# --- pick-a-few: the selection DIFF becomes per-game writes --------------------


def test_pick_diff_enables_and_disables_only_the_changed_games(monkeypatch):
    # current: casino + deathmatch disabled; pick casino IN, blackjack OUT.
    _install_enabled(monkeypatch, {"blackjack", "rps_tournament"})
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_pick_competitive")(
        _req({"values": ("casino", "rps_tournament")})))
    # newly selected → None (back to default-enabled); newly deselected →
    # False; unchanged (rps_tournament kept, deathmatch left off) → NO write.
    assert writes == [("blackjack", False), ("casino", None)]
    assert reply.outcome == "success"
    assert "1 enabled, 1 disabled" in reply.user_message


def test_pick_with_no_changes_writes_nothing(monkeypatch):
    _install_enabled(monkeypatch, set(_COMPETITIVE))
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_pick_competitive")(
        _req({"values": tuple(_COMPETITIVE)})))
    assert writes == []
    assert "no changes" in reply.user_message


def test_pick_empty_selection_disables_the_whole_section(monkeypatch):
    _install_enabled(monkeypatch, set(_ACTIVITIES))
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_pick_activities")(
        _req({"values": ()})))
    assert writes == [(k, False) for k in _ACTIVITIES]
    assert "0 enabled, 6 disabled" in reply.user_message


def test_pick_requires_a_guild(monkeypatch):
    writes = _install_write_port(monkeypatch)
    reply = run(_handler("games.sections_pick_activities")(
        _req({"values": ("mining",)}, guild_id=0)))
    assert writes == []
    assert "per server" in reply.user_message


def test_pick_reports_a_failed_write(monkeypatch):
    _install_enabled(monkeypatch, set())        # everything disabled
    writes = _install_write_port(monkeypatch, outcome="denied")
    reply = run(_handler("games.sections_pick_competitive")(
        _req({"values": ("blackjack", "casino")})))
    assert writes == [("blackjack", None)]
    assert reply.outcome == "denied"
    assert "0/2 applied" in reply.user_message


# --- the settings hub: the games group routes to the panel --------------------


def test_settings_hub_roster_carries_the_games_group():
    from sb.domain.settings.panels import _HUB_GROUPS

    assert ("games", "Games", "🎮",
            "Competitive games and channel activities") in _HUB_GROUPS
    # appended AFTER the 19 shipped groups — their golden order survives.
    assert [g[0] for g in _HUB_GROUPS].index("games") == 19


def test_open_group_games_routes_to_the_sections_panel(monkeypatch):
    import sb.kernel.panels.engine as engine
    from sb.domain.settings import handlers

    handlers.ensure_handler_refs()
    opened: list[str] = []

    async def fake_open(ref, req):
        opened.append(ref.name)

    monkeypatch.setattr(engine, "open_panel", fake_open)
    # navigation returns None (open_panel took over) — never the
    # BLOCKED pending terminal, never f"{group}.hub" (that id is the
    # PLAYER games hub).
    assert run(_handler("settings.open_group")(
        _req({"values": ("games",)}))) is None
    assert opened == ["games.sections"]
