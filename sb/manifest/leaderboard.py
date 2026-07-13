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
        # DELIBERATE ALIAS SET (curation row 44 ruling, 2026-07-13).
        # Provenance: the oracle ships all eleven per-game aliases live
        # on the centralised board command and classifies the set
        # legacy_duplicate (oracle-context.md: leaderboard_cog:211
        # alias_classification) — the pre-centralisation per-game entry
        # points, folded into one command and kept callable.
        # Ruling: Q-A03 is an OWNER-HELD default, applied at D-0038
        # (docs/decisions.md:290): "!leaderboard + the ELEVEN shipped
        # per-game aliases VERBATIM (Q-A03 held default: legacy routes
        # stay callable; aliases whose game providers don't exist yet
        # resolve to the overview — honest, never a fake board)".
        # Trimming, renaming, or growing this tuple contradicts that
        # ruling; a curation sweep flagging it as unexplained duplicates
        # is answered HERE, not by a trim.
        # What changes it: an owner turn amending Q-A03 — never a
        # curation/rework lane acting alone.
        # Pinned by two guards: the band4 exact-tuple assertion
        # (tests/unit/band4/test_band4_community.py::
        # test_leaderboard_alias_set_is_ledgered_deliberate) and the
        # manifest snapshot (manifest.snapshot.json carries the tuple;
        # compat/compat-frozen.json freezes it) — drift in either
        # direction reds with a pointer back to this block.
        # NOT this layer: the provider-registry alias rows
        # (sb/domain/community/rank_providers.py "lb"/"rankings"/…,
        # band-6 rows like "minelb" in sb/domain/games/providers.py)
        # share names but map category KEYWORDS → providers at dispatch
        # time (sb/domain/community/handlers.py) — a separate seam; do
        # not conflate the two when editing either.
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
