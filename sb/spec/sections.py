"""Game-section grammar + registry (D-0082, docs/design/game-sections.md §2).

A section groups shipped game subsystems for per-guild enablement —
enable a whole section OR pick a few games. ``GameEntry.key`` IS the
owning subsystem key: enablement rides the existing governance
``subsystem_visibility`` rows (no section-side store, D-0082), so a game
disabled via sections and via the governance explorer is the SAME row.

The module-level registry mirrors the panel registry's collision fence
(``sb/kernel/panels/registry.py::register_panel``): identical
re-registration is a no-op (module re-import discipline, matching
sb.spec.events), a differing spec under the same key raises. Sections
are DECLARED in ``sb/manifest/games.py`` — the SBW-spec replacement
slot (§7) — and registered at manifest import. Stdlib-only leaf
(imports only sibling sb.spec leaves).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.refs import PanelRef
from sb.spec.roles import register_field_roles

__all__ = [
    "GameEntry",
    "GameSectionSpec",
    "SectionRedefined",
    "all_sections",
    "clear_sections_for_tests",
    "get_section",
    "register_section",
]


@dataclass(frozen=True)
class GameEntry:
    """One game in a section; ``key`` is the owning subsystem key."""

    key: str        # [S] owning subsystem key, verbatim (the governance row key)
    label: str      # [S] semantic copy (the shipped hub display name)
    emoji: str      # [S]
    hub: PanelRef   # [S] the game's hub panel (spec→spec import, §2)


@dataclass(frozen=True)
class GameSectionSpec:
    """One section: an ordered group of games (§2)."""

    key: str                        # [S] section key
    title: str                      # [S] semantic copy
    emoji: str                      # [S]
    games: tuple[GameEntry, ...]    # [S] declaration order is render order


register_field_roles("GameEntry", key="S", label="S", emoji="S", hub="S")
register_field_roles(
    "GameSectionSpec", key="S", title="S", emoji="S", games="S")


class SectionRedefined(Exception):
    """Two GameSectionSpecs claimed the same section key (mirror of
    EventRedefined / the panel registry's ``panel_redefined`` fence)."""


_SECTIONS: dict[str, GameSectionSpec] = {}


def register_section(spec: GameSectionSpec) -> GameSectionSpec:
    """Fence → table. Idempotent re-registration of the identical spec is
    a no-op; a differing spec under the same key is an error."""
    prior = _SECTIONS.get(spec.key)
    if prior is not None:
        if prior == spec:
            return spec
        raise SectionRedefined(
            f"section {spec.key!r} registered twice with differing specs")
    _SECTIONS[spec.key] = spec
    return spec


def get_section(key: str) -> GameSectionSpec | None:
    return _SECTIONS.get(key)


def all_sections() -> tuple[GameSectionSpec, ...]:
    """Every registered section, in declaration order."""
    return tuple(_SECTIONS.values())


def clear_sections_for_tests() -> None:
    """Test seam (mirrors panels registry ``clear_panels_for_tests``)."""
    _SECTIONS.clear()
