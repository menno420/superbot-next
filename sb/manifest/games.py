"""GAMES subsystem manifest (band 6) — the shipped router-only hub
(!games + /games, !world, !worldcard/!mystats), the games SUBSTRATE the
whole band rides (game_state checkpoint store, game_xp shared track, the
g1: dynamic-session dispatcher install, the session_gc sweep), and the
game_xp event vocabulary."""

from __future__ import annotations

from sb.domain.games import panels as _panels
from sb.domain.games import service as _service
from sb.domain.games.ops import register_ops
from sb.domain.games.providers import register_game_providers
from sb.domain.games.session import install_games_dispatcher
from sb.domain.games.store import GAME_STATE_STORE, GAME_XP_STORE
from sb.domain.games.tournament_flag import TOURNAMENT_FLAG_STORE
from sb.domain.games.xp import EVT_GAME_LEVEL_UP, EVT_GAME_XP_AWARDED
from sb.kernel.scheduler.due_queue import declare_task
from sb.spec.commands import CommandKind, CommandSpec
from sb.spec.outcomes import ReplyVisibility
from sb.spec.events import (
    DeliveryClass,
    EventSpec,
    FieldSpec,
    register_event_specs,
)
from sb.spec.manifest import SubsystemManifest
from sb.spec.refs import HandlerRef, PanelRef
from sb.spec.scheduler import Interval, ManagedTaskSpec, TaskDurability
from sb.spec.sections import GameEntry, GameSectionSpec, register_section

GAME_XP_AWARDED_EVENT = EventSpec(
    name=EVT_GAME_XP_AWARDED,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("game", "str"),
        FieldSpec("action", "str"),
        FieldSpec("delta", "int"),
        FieldSpec("new_game_xp", "int"),
        FieldSpec("new_total_xp", "int"),
    ),
    owner_subsystem="games",
    delivery=DeliveryClass.BEST_EFFORT,
)
GAME_LEVEL_UP_EVENT = EventSpec(
    name=EVT_GAME_LEVEL_UP,
    payload_schema=(
        FieldSpec("guild_id", "int"),
        FieldSpec("user_id", "int"),
        FieldSpec("game", "str"),
        FieldSpec("new_level", "int"),
    ),
    owner_subsystem="games",
    delivery=DeliveryClass.BEST_EFFORT,
)

_EVENTS = (GAME_XP_AWARDED_EVENT, GAME_LEVEL_UP_EVENT)

#: The stranded-checkpoint GC (shipped session_gc; A-8 consumer list) —
#: hourly sweep past the 24 h TTL; refunds ride the audited K7 lane.
SESSION_GC_TASK = declare_task(ManagedTaskSpec(
    name="games:session_gc",
    trigger=Interval(seconds=3600),
    handler=HandlerRef("games.session_gc_fire"),
    durability=TaskDurability.IN_MEMORY,
))

# --- game sections (D-0082, docs/design/game-sections.md §3) --------------------
#
# The DEFAULT section inventory, derived from the shipped games-hub roster
# (sb/domain/games/panels.py GAMES_COMPETITIVE / GAMES_ACTIVITIES — the
# drift-guard test pins the agreement). This constant is the SINGLE SBW-spec
# REPLACEMENT SLOT (design §7): when the SBW inventory+consolidation spec
# lands (outbox SIM-REQUEST 2026-07-13T00:55Z, PR #325), replace THIS tuple
# (+ extend GameSectionSpec if the spec adds fields); no engine changes, no
# store changes.
GAME_SECTIONS: tuple[GameSectionSpec, ...] = (
    GameSectionSpec(
        key="competitive", title="Competitive", emoji="🏆",
        games=(
            GameEntry("blackjack", "Blackjack", "🃏",
                      PanelRef("blackjack.hub")),
            GameEntry("casino", "Casino", "🎰", PanelRef("casino.hub")),
            GameEntry("deathmatch", "Deathmatch", "⚔️",
                      PanelRef("deathmatch.hub")),
            GameEntry("rps_tournament", "Rock Paper Scissors", "✂️",
                      PanelRef("rps_tournament.hub")),
        )),
    GameSectionSpec(
        key="activities", title="Activities", emoji="🎲",
        games=(
            GameEntry("mining", "Mining", "⛏️", PanelRef("mining.hub")),
            GameEntry("fishing", "Fishing", "🎣", PanelRef("fishing.hub")),
            GameEntry("creature", "Creatures", "🐾",
                      PanelRef("creature.hub")),
            GameEntry("farm", "Chicken Farm", "🐔", PanelRef("farm.hub")),
            GameEntry("counting", "Counting", "🔢",
                      PanelRef("counting.hub")),
            GameEntry("chain", "Word Chain", "🔗", PanelRef("chain.hub")),
        )),
)


def _register_sections() -> None:
    for _section in GAME_SECTIONS:
        register_section(_section)


MANIFEST = SubsystemManifest(
    key="games",
    version=1,
    commands=(
        CommandSpec(name="games", kind=CommandKind.PREFIX,
                    route=PanelRef("games.hub"),
                    audience_tier="user", capability="games",
                    summary="Open the Games hub — competitive games and "
                            "channel activities.",
                    usage="!games"),
        # the shipped /games answered type-4 direct WITH flags 64
        # (goldens/games/sweep_slash_games) — slash+PanelRef resolves
        # DeferMode.NONE (trap 26) and the declared EPHEMERAL rides the
        # type-4 data (the community slash-twin precedent); an ephemeral
        # interaction returns no message_ref ⇒ no panel_anchors row.
        CommandSpec(name="games", kind=CommandKind.SLASH,
                    route=PanelRef("games.hub"),
                    reply_visibility=ReplyVisibility.EPHEMERAL,
                    audience_tier="user", capability="games",
                    summary="Open the Games hub — competitive games and "
                            "channel activities.",
                    usage="/games"),
        CommandSpec(name="world", kind=CommandKind.PREFIX,
                    route=PanelRef("games.world"),
                    audience_tier="user", capability="games",
                    summary="Open the Explore world hub — the open-world "
                            "town square.",
                    usage="!world"),
        CommandSpec(name="worldcard", kind=CommandKind.PREFIX,
                    aliases=("mystats",),
                    route=PanelRef("games.world_card"),
                    audience_tier="user", capability="games",
                    summary="Show your cross-game world card — global "
                            "level + per-game standing.",
                    usage="!worldcard"),
    ),
    panels=_panels.install_games_panels(),
    settings=(),
    stores=(GAME_STATE_STORE, GAME_XP_STORE, TOURNAMENT_FLAG_STORE),
    events=_EVENTS,
    capabilities=(),
)

register_event_specs(list(_EVENTS))
register_ops()
install_games_dispatcher()
register_game_providers()
_register_sections()


def _ensure_refs() -> None:
    from sb.domain.games import ops as _ops
    from sb.domain.games import store as _store
    from sb.domain.games import tournament_flag as _flag

    _store.ensure_refs()
    _flag.ensure_flag_refs()
    _ops.ensure_ops_refs()
    _panels.ensure_panel_refs()
    _service.ensure_service_refs()
    register_event_specs(list(_EVENTS))
    register_ops()
    install_games_dispatcher()
    register_game_providers()
    _register_sections()


ENSURE_REFS = _ensure_refs
