"""The shipped ACTIVE_TOURNAMENT runtime flag (band 6) — the ONE
`guild_settings` KV row the game bands write.

Old-bot semantics verbatim (disbot/services/tournament_state_service.py):
the flag is **runtime tournament state**, not guild configuration — the
shipped PR B' classification kept it OUT of the durable settings home, and
the shipped invariant pinned that direct writes happen only inside the one
service module. This module is that service's port: the write helpers take
an explicit txn `conn` and are called ONLY by the K7 tournament legs
(sb/domain/rps/ops.py today; the blackjack tournament successor rides the
same rows — the shipped shared-write is intentional and documented).

Migration ``0027_guild_settings.sql`` (NAME_STABLE import of the shipped
table). The rpsregister golden pins the row bytes:
``{guild_id, key: "active_tournament", value: "rps"}``.
"""

from __future__ import annotations

from typing import Any

from sb.kernel.db.pool import execute, fetchone
from sb.spec.refs import EngineRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "ACTIVE_TOURNAMENT",
    "TOURNAMENT_FLAG_STORE",
    "clear_active",
    "ensure_flag_refs",
    "get_active",
    "set_active",
]

#: the shipped utils/settings_keys/games.py key string, verbatim.
ACTIVE_TOURNAMENT = "active_tournament"


@engine("games.tournament_flag")
def _flag_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/games/tournament_flag.py"


def ensure_flag_refs() -> None:
    from sb.spec.refs import is_registered

    if not is_registered(EngineRef("games.tournament_flag")):
        engine("games.tournament_flag")(_flag_marker)

# NAME_STABLE: the shipped KV table imports verbatim. bears_value=False —
# a runtime flag, re-derivable from the live orchestration (the shipped
# clear_stale_tournament_flag swept it at every boot); rollback class
# DECLARED_LOSS by posture.
TOURNAMENT_FLAG_STORE = register_store(StoreSpec(
    table="guild_settings",
    sole_writer=EngineRef("games.tournament_flag"),
    retention="runtime flag (cleared at tournament end / stale-sweep)",
    checkpoint_class=CheckpointClass.SESSION,
    invariant_tag="guild_settings",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("games", "rps_tournament", "blackjack", "diagnostics"),
    bears_value=False,
    data_class=DataClass.NONE,        # guild id + game key — no member data
))


async def set_active(conn: Any, *, guild_id: int, game: str) -> None:
    """Mark *game*'s tournament active for the guild (the shipped
    tournament_state_service.set_active upsert)."""
    await execute(
        "INSERT INTO guild_settings (guild_id, key, value) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value",
        (int(guild_id), ACTIVE_TOURNAMENT, str(game)), conn=conn)


async def clear_active(conn: Any, *, guild_id: int) -> int:
    """Remove the flag row (tournament ended / aborted)."""
    result = await execute(
        "DELETE FROM guild_settings WHERE guild_id = $1 AND key = $2",
        (int(guild_id), ACTIVE_TOURNAMENT), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (TypeError, ValueError):
        return 0


async def get_active(guild_id: int, conn: Any = None) -> str | None:
    """The currently flagged game key for the guild, or None."""
    row = await fetchone(
        "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = $2",
        (int(guild_id), ACTIVE_TOURNAMENT), conn=conn)
    return None if row is None else str(row["value"])
