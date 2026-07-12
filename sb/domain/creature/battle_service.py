"""Creature PvP battle service (band 6) — the read boundary between a
player's collection and the pure battle engine (D-0078).

Ported from the shipped ``services/creature_battle_service.py`` (corpus sha
7f7628e1): load each player's owned-creature pool from the collection log,
build a **level-normalized** 6-mon team (one of each element at
:data:`NORMALIZED_LEVEL`), and resolve the match through the pure engine
(:mod:`sb.domain.creature.battle`).

- :func:`resolve_pvp` — the pure **read** path: read collections, compute a
  winner. No writes; the caller (the ``creature.challenge_accept`` handler)
  then feeds the winner/loser to the already-live audited record lane
  (``creature.record_battle_result`` — sb/domain/creature/ops.py), which
  writes both W/L rows + the winner's battle-win game-xp in ONE txn. This
  keeps the pure math here and the side effects on the audited seam, exactly
  as the oracle split ``resolve_pvp`` / ``resolve_and_record_pvp``.

The anti-P2W rule (Q-0039): PvP normalizes every creature to a flat level,
so collection breadth + type matchups + move policy decide the outcome — the
win xp is prestige only, never PvP power.

Presentation helpers (:func:`build_result_view`) turn a :class:`PvpResult`
into the outcome card's description + fields — pure, so they unit-test on a
plain result object (ported from ``views/creature_battle/render.py``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from sb.domain.creature import battle as engine
from sb.domain.creature.battle import (
    NORMALIZED_LEVEL,
    BattleOutcome,
    Combatant,
    standard_team,
)
from sb.domain.creature.catalog import Creature, creature_by_name

__all__ = [
    "NO_TEAM_MSG",
    "PvpResult",
    "build_normalized_team",
    "build_result_view",
    "load_pool",
    "resolve_pvp",
]

#: The shipped "go catch some first" nudge (challenge.py ``_NO_TEAM_MSG``).
NO_TEAM_MSG = (
    "🐾 Both fighters need at least one creature to battle — use `!catch` first!"
)

#: Cap on KO lines shown in the highlights field (a 6v6 fight KOs at most 12).
_MAX_HIGHLIGHTS = 12


@dataclass(frozen=True)
class PvpResult:
    """The resolved PvP battle: the outcome plus each side's starting roster.

    ``team_a`` / ``team_b`` are snapshotted **before** resolution (the engine
    mutates combatant HP in place), so renderers list the rosters as the same
    combatant objects the engine resolved — final HP and faint state included.
    """

    outcome: BattleOutcome
    team_a: tuple[Combatant, ...]
    team_b: tuple[Combatant, ...]

    @property
    def a_won(self) -> bool:
        return self.outcome.a_won


async def load_pool(user_id: int, guild_id: int,
                    conn: Any = None) -> list[Creature]:
    """The catalog creatures a player currently owns (their battle pool).

    Reads the collection log and resolves each owned name against the live
    catalog; names for a creature no longer in the catalog are simply skipped
    (the fishing reconciliation lesson).
    """
    from sb.domain.creature import store

    collection = await store.get_collection(user_id, guild_id, conn=conn)
    pool: list[Creature] = []
    for name in collection:
        creature = creature_by_name(name)
        if creature is not None:
            pool.append(creature)
    return pool


def build_normalized_team(pool: list[Creature],
                          rng: random.Random) -> list[Combatant]:
    """A level-normalized 'one of each element' team drawn from *pool* —
    pinned to :data:`NORMALIZED_LEVEL` so no caller can seed a raw-level
    (pay-to-win) PvP team."""
    return standard_team(pool, rng, level=NORMALIZED_LEVEL)


async def resolve_pvp(challenger_id: int, opponent_id: int, guild_id: int,
                      *, rng: random.Random | None = None,
                      conn: Any = None) -> PvpResult | None:
    """Resolve a creature PvP battle between two players (read-only).

    Returns ``None`` when either player has no usable team (an empty
    collection, or one with no catalog-known creatures) — the caller surfaces
    the :data:`NO_TEAM_MSG` nudge. Both teams build at
    :data:`NORMALIZED_LEVEL`. *rng* is injectable so the resolution is
    deterministic + golden-replayable (D-0078); it defaults to an unseeded
    :class:`random.Random`, mirroring the oracle's injectable seam.
    """
    rng = rng if rng is not None else random.Random()
    pool_a = await load_pool(challenger_id, guild_id, conn=conn)
    pool_b = await load_pool(opponent_id, guild_id, conn=conn)

    team_a = build_normalized_team(pool_a, rng)
    team_b = build_normalized_team(pool_b, rng)
    if not team_a or not team_b:
        return None

    # Snapshot the rosters before resolve_battle mutates combatant HP in place.
    roster_a = tuple(team_a)
    roster_b = tuple(team_b)
    outcome = engine.resolve_battle(team_a, team_b, rng=rng)
    return PvpResult(outcome=outcome, team_a=roster_a, team_b=roster_b)


# ---------------------------------------------------------------------------
# Presentation — build the outcome card's description + fields (pure)
# ---------------------------------------------------------------------------


def _roster_line(team: tuple[Combatant, ...]) -> str:
    """One creature per line: emoji + name, with a 💀 marker if it fainted."""
    if not team:
        return "*no creatures*"
    return "\n".join(
        f"{'💀 ' if m.fainted else ''}{m.creature.emoji} {m.name}" for m in team
    )


def _highlights(result: PvpResult) -> str:
    """The KO moments from the battle log, in order, capped for readability."""
    kos = [
        f"💥 **{e.actor}** took down **{e.target}**"
        for e in result.outcome.events
        if e.faint
    ]
    if not kos:
        return "*A swift, decisive bout.*"
    shown = kos[:_MAX_HIGHLIGHTS]
    if len(kos) > _MAX_HIGHLIGHTS:
        shown.append(f"…and {len(kos) - _MAX_HIGHLIGHTS} more")
    return "\n".join(shown)


def build_result_view(
    challenger_name: str,
    opponent_name: str,
    challenger_id: int,
    opponent_id: int,
    result: PvpResult,
    *,
    winner_id: int,
    records: dict[int, tuple[int, int]] | None = None,
    xp_note: str | None = None,
) -> tuple[str, tuple[tuple[str, str, bool], ...]]:
    """Render the resolved battle as ``(description, fields)`` for the outcome
    embed (``views/creature_battle/render.py`` build_result_embed, verbatim
    copy over the panel-seam field tuples).

    ``challenger`` is team A, ``opponent`` is team B (the order
    :func:`resolve_pvp` was called with). *records* (``{user_id: (W, L)}``
    from the recorded battle) adds a Records field; *xp_note* adds the
    winner's level-up notice.
    """
    description = (
        f"<@{challenger_id}> vs <@{opponent_id}>\n"
        "*Teams are level-normalized — type matchups and your collection "
        "decide it.*"
    )
    fields: list[tuple[str, str, bool]] = [
        (f"{challenger_name}'s team", _roster_line(result.team_a), True),
        (f"{opponent_name}'s team", _roster_line(result.team_b), True),
        ("Highlights", _highlights(result), False),
    ]
    winner_value = f"🏆 <@{winner_id}>"
    if xp_note:
        winner_value += f"\n{xp_note}"
    fields.append(("Winner", winner_value, False))
    if records is not None:
        lines = []
        for name, uid in ((challenger_name, challenger_id),
                          (opponent_name, opponent_id)):
            wins, losses = records.get(uid, (0, 0))
            lines.append(f"{name} — **{wins}**W · **{losses}**L")
        fields.append(("Records", "\n".join(lines), False))
    return description, tuple(fields)
