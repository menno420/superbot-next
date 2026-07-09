"""rps_players CRUD (band 6 slice 4) — the shipped stats table
(migration-005 (user_id, guild_id) PK; name captured at game time per
the shipped leaderboard query). Written from the quick-play lane (the
shipped ``_bot_matches.update_player_stats`` site); tournament/PvP
stat rows ride the orchestration successor port."""

from __future__ import annotations

from typing import Any

from sb.kernel.db.pool import execute, fetchall
from sb.spec.refs import EngineRef, WorkflowRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "RPS_PLAYERS_STORE",
    "erase_subject_stats",
    "leaderboard",
    "record_result",
]

RPS_PLAYERS_STORE = register_store(StoreSpec(
    table="rps_players",
    sole_writer=EngineRef("rps.stats_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="rps_players",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_PII,   # stores a display name snapshot
    erasure_ref=WorkflowRef("rps.erase_subject_stats"),
))


@engine("rps.stats_store")
def _store_marker() -> str:
    return "sb/domain/rps/stats.py"


async def record_result(conn: Any, *, user_id: int, guild_id: int,
                        name: str, result: str) -> None:
    """Idempotent ensure + one stat increment (win|loss|tie); any other
    token is a silent no-op (shipped rps_update_stat contract)."""
    await execute(
        "INSERT INTO rps_players (user_id, guild_id, name) "
        "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
        (user_id, guild_id, name), conn=conn)
    # Explicit three-arm match — no dynamic identifier interpolation
    # (the shipped PR-R1 hardening, kept).
    match result:
        case "win":
            query = ("UPDATE rps_players SET wins=wins+1 "
                     "WHERE user_id=$1 AND guild_id=$2")
        case "loss":
            query = ("UPDATE rps_players SET losses=losses+1 "
                     "WHERE user_id=$1 AND guild_id=$2")
        case "tie":
            query = ("UPDATE rps_players SET ties=ties+1 "
                     "WHERE user_id=$1 AND guild_id=$2")
        case _:
            return
    await execute(query, (user_id, guild_id), conn=conn)


async def leaderboard(guild_id: int, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, name, wins, losses, ties FROM rps_players "
        "WHERE guild_id=$1 ORDER BY wins DESC LIMIT 15",
        (guild_id,), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_stats(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM rps_players WHERE user_id=$1",
        (user_id,), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import engine as _engine, is_registered

    if not is_registered(EngineRef("rps.stats_store")):
        _engine("rps.stats_store")(_store_marker)
