"""Game sections slice 1 (D-0082, docs/design/game-sections.md §3/§4):
the DEFAULT inventory declared in ``sb/manifest/games.py`` (drift-guarded
against the shipped hub roster in ``sb/domain/games/panels.py``) and the
per-guild enablement read seam ``sb/domain/games/sections.py`` riding
governance ``subsystem_enabled``."""

from __future__ import annotations

import asyncio
import dataclasses

import pytest

run = asyncio.run

GID = 1

_COMPETITIVE = ("blackjack", "casino", "deathmatch", "rps_tournament")
_ACTIVITIES = ("mining", "fishing", "creature", "farm", "counting", "chain")


@pytest.fixture(autouse=True)
def _default_sections():
    """Deterministic registry: exactly the manifest's DEFAULT sections
    (re-registered idempotently — a peer test may have cleared the table
    the games manifest populated at import), restored after."""
    from sb.manifest import games as manifest
    from sb.spec import sections as mod

    saved = dict(mod._SECTIONS)
    mod.clear_sections_for_tests()
    manifest._register_sections()
    yield
    mod.clear_sections_for_tests()
    mod._SECTIONS.update(saved)


def _install_enabled(monkeypatch, enabled: set[str]):
    """Stub the governance read the seam lazily imports; returns the
    call log."""
    from sb.domain.governance import service

    calls: list[tuple[int, str]] = []

    async def fake_subsystem_enabled(guild_id: int, subsystem: str) -> bool:
        calls.append((guild_id, subsystem))
        return subsystem in enabled

    monkeypatch.setattr(service, "subsystem_enabled", fake_subsystem_enabled)
    return calls


# --- the DEFAULT inventory: drift-guard against the shipped hub roster -------


def test_default_inventory_matches_the_shipped_hub_roster():
    # The design-card idea landed: the sections constant is hand-derived
    # from the hub roster — pin the agreement (keys/emoji/labels/hub refs,
    # both directions, order included) so neither can drift silently.
    from sb.domain.games import panels
    from sb.manifest.games import GAME_SECTIONS

    by_key = {s.key: s for s in GAME_SECTIONS}
    assert tuple(by_key) == ("competitive", "activities")
    assert (by_key["competitive"].title, by_key["competitive"].emoji) == \
        ("Competitive", "🏆")
    assert (by_key["activities"].title, by_key["activities"].emoji) == \
        ("Activities", "🎲")
    for section_key, roster in (("competitive", panels.GAMES_COMPETITIVE),
                                ("activities", panels.GAMES_ACTIVITIES)):
        assert [(e.key, e.emoji, e.label, e.hub)
                for e in by_key[section_key].games] == \
            [(key, emoji, display, ref)
             for key, emoji, display, _desc, ref in roster]


def test_manifest_sections_registered_in_declaration_order():
    from sb.manifest import games as manifest
    from sb.spec.sections import all_sections, get_section

    assert all_sections() == manifest.GAME_SECTIONS
    assert get_section("competitive") == manifest.GAME_SECTIONS[0]
    assert get_section("activities") == manifest.GAME_SECTIONS[1]
    # re-registration (module re-import / ENSURE_REFS discipline): no-op.
    manifest._register_sections()
    assert all_sections() == manifest.GAME_SECTIONS


# --- the enablement read seam -------------------------------------------------


def test_enabled_games_all_enabled_is_the_full_roster(monkeypatch):
    from sb.domain.games.sections import enabled_games

    calls = _install_enabled(monkeypatch, set(_COMPETITIVE + _ACTIVITIES))
    views = run(enabled_games(GID))

    assert [v.key for v in views] == ["competitive", "activities"]
    assert [e.key for e in views[0].games] == list(_COMPETITIVE)
    assert [e.key for e in views[1].games] == list(_ACTIVITIES)
    # the view carries the section frame verbatim
    assert (views[0].title, views[0].emoji) == ("Competitive", "🏆")
    # one governance read per game key, guild-scoped
    assert set(calls) == {(GID, k) for k in _COMPETITIVE + _ACTIVITIES}


def test_enabled_games_pick_a_few_filters_in_order(monkeypatch):
    from sb.domain.games.sections import enabled_games

    _install_enabled(monkeypatch, {"blackjack", "fishing", "counting"})
    views = run(enabled_games(GID))

    assert [v.key for v in views] == ["competitive", "activities"]
    assert [e.key for e in views[0].games] == ["blackjack"]
    assert [e.key for e in views[1].games] == ["fishing", "counting"]


def test_enabled_games_drops_a_fully_disabled_section(monkeypatch):
    from sb.domain.games.sections import enabled_games

    _install_enabled(monkeypatch, set(_ACTIVITIES))
    views = run(enabled_games(GID))

    assert [v.key for v in views] == ["activities"]
    assert [e.key for e in views[0].games] == list(_ACTIVITIES)


def test_enabled_games_empty_when_nothing_is_enabled(monkeypatch):
    from sb.domain.games.sections import enabled_games

    _install_enabled(monkeypatch, set())
    assert run(enabled_games(GID)) == ()


def test_enabled_games_view_is_frozen(monkeypatch):
    from sb.domain.games.sections import enabled_games

    _install_enabled(monkeypatch, {"blackjack"})
    (view,) = run(enabled_games(GID))
    with pytest.raises(dataclasses.FrozenInstanceError):
        view.games = ()  # type: ignore[misc]


def test_fail_open_unknown_key_through_the_real_governance_read(monkeypatch):
    # The REAL subsystem_enabled over a stubbed visibility store (the
    # band-5 pattern): a guild override disables blackjack; an unknown
    # subsystem key stays ENABLED (governance fail-open — the compiled
    # manifests own existence).
    from sb.domain.games.sections import enabled_games
    from sb.domain.governance import store
    from sb.spec.refs import PanelRef
    from sb.spec.sections import GameEntry, GameSectionSpec, register_section

    async def fetch(guild_id, chain, conn=None):
        return {(s, i): {"blackjack": False} for s, i in chain}

    monkeypatch.setattr(store, "fetch_visibility_for_chain", fetch)
    register_section(GameSectionSpec(
        key="lab", title="Lab", emoji="🧪",
        games=(GameEntry("not_a_subsystem", "Prototype", "🧪",
                         PanelRef("lab.hub")),)))

    views = run(enabled_games(GID))
    by_key = {v.key: v for v in views}
    assert [e.key for e in by_key["competitive"].games] == \
        ["casino", "deathmatch", "rps_tournament"]      # blackjack overridden off
    assert [e.key for e in by_key["activities"].games] == list(_ACTIVITIES)
    assert [e.key for e in by_key["lab"].games] == ["not_a_subsystem"]  # fail-open
