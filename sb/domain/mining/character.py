"""Character stats — the gear + skills merge point (ported verbatim from the
oracle ``disbot/utils/mining/character.py``).

The single read model for "how strong is this character?", combining equipped
gear (:func:`sb.domain.mining.equipment.compute_stats`) with allocated skill
points (:func:`sb.domain.mining.skills.skill_stats`) into one
:class:`~sb.domain.mining.equipment.EffectiveStats` block.  Game logic reads
*this*, never gear or skills separately.

Pure + stdlib-only.  An **empty allocation makes the result byte-identical to
gear-only stats** — the additive safety property that lets the skill tree ship
without changing existing play.
"""

from __future__ import annotations

from sb.domain.mining.equipment import EffectiveStats, compute_stats
from sb.domain.mining.skills import skill_stats


def character_stats(
    equipped: dict[str, str],
    alloc: dict[str, int] | None = None,
) -> EffectiveStats:
    """Combined gear + skill stats.

    *equipped* is ``{slot: item_name}``; *alloc* is ``{branch: points}`` (or
    ``None``/empty for a player who has spent nothing — in which case the result
    equals :func:`sb.domain.mining.equipment.compute_stats` exactly).
    """
    stats = compute_stats(equipped)
    if alloc:
        stats = stats + skill_stats(alloc)
    return stats


__all__ = ["character_stats"]
