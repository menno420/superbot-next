"""Game-sections enablement read seam (D-0082, docs/design/game-sections.md §4).

``enabled_games(guild_id)`` projects the registered sections
(``sb.spec.sections``, declared in ``sb/manifest/games.py``) through the
ONE per-guild enablement truth — governance ``subsystem_enabled`` (the
same K8 read that gates every command dispatch), so the sections view
and the dispatch gate can never drift. Honest semantics inherited from
governance: unknown subsystem keys are ENABLED (fail-open — compiled
manifests own existence; governance only gates registered rows).

The governance import is LAZY (call-time, inside the function) — the
established domain→governance seam shape
(``sb/domain/platform/guild_teardown.py:78``); design §4 flags this as
the deliberate no-new-port choice (PL-001).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.sections import GameEntry, GameSectionSpec, all_sections

__all__ = [
    "GameSectionView",
    "enabled_games",
]


@dataclass(frozen=True)
class GameSectionView:
    """One section projected to a guild: only its ENABLED games remain."""

    key: str
    title: str
    emoji: str
    games: tuple[GameEntry, ...]

    @classmethod
    def from_spec(cls, spec: GameSectionSpec,
                  games: tuple[GameEntry, ...]) -> "GameSectionView":
        return cls(key=spec.key, title=spec.title, emoji=spec.emoji,
                   games=games)


async def enabled_games(guild_id: int) -> tuple[GameSectionView, ...]:
    """The registered sections with disabled games filtered out, in
    declaration order. A section whose games are ALL disabled is dropped
    (nothing to render). Enablement is read per game key via governance
    ``subsystem_enabled`` — overrides + dependency rules, fail-open for
    unregistered keys."""
    from sb.domain.governance import service as governance

    views: list[GameSectionView] = []
    for spec in all_sections():
        games = tuple(
            [entry for entry in spec.games
             if await governance.subsystem_enabled(guild_id, entry.key)])
        if games:
            views.append(GameSectionView.from_spec(spec, games))
    return tuple(views)
