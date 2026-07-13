"""Game-section grammar + registry (D-0082, docs/design/game-sections.md §2)."""

from __future__ import annotations

import dataclasses

import pytest

from sb.spec.refs import PanelRef
from sb.spec.sections import (
    GameEntry,
    GameSectionSpec,
    SectionRedefined,
    all_sections,
    clear_sections_for_tests,
    get_section,
    register_section,
)


@pytest.fixture(autouse=True)
def _fresh_sections():
    # Snapshot-and-restore: the games manifest registers the DEFAULT
    # sections at import, and other tests may rely on them being present.
    from sb.spec import sections as _mod

    saved = dict(_mod._SECTIONS)
    clear_sections_for_tests()
    yield
    clear_sections_for_tests()
    _mod._SECTIONS.update(saved)


def _entry(key: str = "blackjack") -> GameEntry:
    return GameEntry(key, "Blackjack", "🃏", PanelRef(f"{key}.hub"))


def _section(key: str = "competitive", **kw) -> GameSectionSpec:
    kw.setdefault("title", "Competitive")
    kw.setdefault("emoji", "🏆")
    kw.setdefault("games", (_entry(),))
    return GameSectionSpec(key=key, **kw)


def test_specs_are_frozen() -> None:
    entry, section = _entry(), _section()
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.key = "casino"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        section.games = ()  # type: ignore[misc]


def test_entry_key_is_the_subsystem_key_and_hub_is_a_panel_ref() -> None:
    entry = _entry("mining")
    assert entry.key == "mining"
    assert isinstance(entry.hub, PanelRef)
    assert entry.hub.kind == "panel"


def test_register_identical_is_noop_different_raises() -> None:
    spec = _section()
    assert register_section(spec) is spec
    assert register_section(spec) is spec              # identical: no-op
    assert register_section(_section()) is not None    # equal spec: no-op
    with pytest.raises(SectionRedefined):
        register_section(_section(title="Competitive games"))
    # the fence did not clobber the first registration
    assert get_section("competitive") == spec


def test_get_section_and_declaration_order() -> None:
    first = register_section(_section("competitive"))
    second = register_section(_section(
        "activities", title="Activities", emoji="🎲",
        games=(GameEntry("mining", "Mining", "⛏️", PanelRef("mining.hub")),)))
    assert get_section("competitive") == first
    assert get_section("activities") == second
    assert get_section("nope") is None
    assert all_sections() == (first, second)


def test_clear_sections_for_tests() -> None:
    register_section(_section())
    clear_sections_for_tests()
    assert all_sections() == ()
    assert get_section("competitive") is None
