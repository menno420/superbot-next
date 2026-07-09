"""LEADERBOARD subsystem manifest (band 4) — the shipped centralised
boards (cogs/leaderboard_cog.py): !leaderboard + the per-game
compatibility aliases VERBATIM (Q-A03 held default: legacy routes stay
callable; `!leaderboard <category>` is canonical). The category panel's
selector is PROVIDER-FED from the registry, so band-6 game categories
appear with zero edits here (the shipped PR-G invariant, now grammar).

Alias caveat carried: the shipped alias list includes game categories
whose providers register at band 6 — until then those aliases resolve to
the overview (honest, never a fake board).
"""

from __future__ import annotations

from sb.domain.community import handlers as _handlers
from sb.domain.community import panels as _panels
from sb.spec.commands import CommandKind, CommandSpec, CooldownSpec
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef

MANIFEST = SubsystemManifest(
    key="leaderboard",
    version=1,
    commands=(
        CommandSpec(name="leaderboard", kind=CommandKind.PREFIX,
                    route=HandlerRef("leaderboard.board_view"),
                    aliases=("lb", "rankings", "minelb",
                             "miningleaderboard", "fishlb",
                             "dm_leaderboard", "dm_lb", "rpslb", "farmlb",
                             "countlb", "counting_leaderboard"),
                    cooldown=CooldownSpec(rate=2, per_s=10),
                    audience_tier="user", capability="leaderboard",
                    summary="Show a leaderboard "
                            "(xp/coins/karma/… — game boards join with "
                            "the games band).",
                    usage="!leaderboard [category]"),
    ),
    panels=(_panels.leaderboard_board_spec(),),
    settings=(),
    stores=(), events=(), capabilities=(),
)


def _ensure_refs() -> None:
    _panels.ensure_panel_refs()
    _handlers.ensure_handler_refs()


ENSURE_REFS = _ensure_refs
