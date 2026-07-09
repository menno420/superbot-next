"""counting_state CRUD (band 6) — the shipped one-JSONB-row-per-guild
shape (``utils/db/games/counting.py``), NAME_STABLE. Game state + the
per-channel counting leaderboards, not money. The state blob keys
per-user tallies by user id ⇒ MEMBER_ID with a scrub erasure body
(strip the subject's leaderboard entries + last_user marker from every
guild row)."""

from __future__ import annotations

import json
from typing import Any

from sb.kernel.db.pool import execute, fetchall, fetchone
from sb.spec.refs import EngineRef, WorkflowRef, engine
from sb.spec.versioning import (
    CheckpointClass,
    DataClass,
    ForwardMapKind,
    StoreSpec,
    register_store,
)

__all__ = [
    "COUNTING_STATE_STORE",
    "get_state",
    "scrub_subject",
    "set_state",
]

COUNTING_STATE_STORE = register_store(StoreSpec(
    table="counting_state",
    sole_writer=EngineRef("counting.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="counting_state",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("counting.scrub_subject_counts"),
))


@engine("counting.store")
def _store_marker() -> str:
    return "sb/domain/counting/store.py"


def _decode(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


async def get_state(guild_id: int, conn: Any = None) -> dict:
    """The guild's whole counting state blob (``{"channels": {...}}``)."""
    row = await fetchone(
        "SELECT state FROM counting_state WHERE guild_id=$1",
        (guild_id,), conn=conn)
    return _decode(row["state"]) if row else {}


async def set_state(conn: Any, *, guild_id: int, state: dict) -> None:
    await execute(
        "INSERT INTO counting_state (guild_id, state) "
        "VALUES ($1, $2::jsonb) "
        "ON CONFLICT (guild_id) DO UPDATE SET state=EXCLUDED.state",
        (guild_id, json.dumps(state)), conn=conn)


async def scrub_subject(conn: Any, *, user_id: int) -> int:
    """Strip the subject from every guild's leaderboards/last_user —
    the counting erasure body (counts are per-user tallies inside the
    JSONB blob, so erasure is a rewrite, not a row delete)."""
    rows = await fetchall(
        "SELECT guild_id, state FROM counting_state", (), conn=conn)
    uid = str(user_id)
    touched = 0
    for row in rows or ():
        state = _decode(row["state"])
        changed = False
        for ch in (state.get("channels") or {}).values():
            lb = ch.get("leaderboard") or {}
            if uid in lb:
                del lb[uid]
                changed = True
            if ch.get("last_user") == uid:
                ch["last_user"] = None
                changed = True
        if changed:
            await execute(
                "UPDATE counting_state SET state=$2::jsonb "
                "WHERE guild_id=$1",
                (int(row["guild_id"]), json.dumps(state)), conn=conn)
            touched += 1
    return touched


def ensure_refs() -> None:
    from sb.spec.refs import engine as _engine, is_registered

    if not is_registered(EngineRef("counting.store")):
        _engine("counting.store")(_store_marker)
