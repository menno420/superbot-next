"""chicken_farm CRUD (band 6) — shipped migration 090 shape, NAME_STABLE.
Game state, not money truth (collect pays through the economy ledger) —
bears_value=False DECLARED_LOSS, the job_progress posture."""

from __future__ import annotations

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

__all__ = ["CHICKEN_FARM_STORE", "get_farm", "set_farm", "top_farmers"]

CHICKEN_FARM_STORE = register_store(StoreSpec(
    table="chicken_farm",
    sole_writer=EngineRef("farm.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="chicken_farm",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("farm.erase_subject_farm"),
))


@engine("farm.store")
def _store_marker() -> str:
    return "sb/domain/farm/store.py"


async def get_farm(user_id: int, guild_id: int, conn: Any = None, *,
                   for_update: bool = False) -> tuple[int, int, int, int]:
    """(chickens, eggs, eggs_updated_at, coop_level) — shipped defaults
    for a fresh farmer (1 starter hen, level-0 coop, epoch-0 timestamp).

    ``for_update=True`` (the F-001/F-002 fix's farm sibling, PR #213
    class): every farm K7 leg composes this read inside its own txn ahead
    of a settle → coin-leg → upsert sequence under
    ``IdempotencyPosture.NATURAL_KEY`` — a posture whose "intrinsically
    once" contract puts the WHOLE concurrency fence on the DB legs. A
    plain SELECT let two concurrent collects both read ``eggs > 0`` and
    both credit the payout (a pure mint), and let a stale buy/upgrade
    write pre-collect eggs back over a committed ``eggs=0`` (a re-mint).
    Two locks close the two halves:

    - ``pg_advisory_xact_lock`` keyed on the SAME (guild, user) pair the
      ``set_farm`` upsert conflicts on — ``FOR UPDATE`` cannot fence the
      no-row-yet first-insert race (two concurrent first buys both read
      the starter defaults, both debit, and one purchase vanishes into
      the other's upsert); the advisory lock serializes racers before the
      row exists. Auto-released at commit/rollback
      (``lock_new_checkpoint_slot`` precedent, sb/domain/games/store.py).
    - ``FOR UPDATE`` on the row itself — belt for the existing-row case
      and a fence against non-farm writers (the erasure lane's DELETE).

    Money-bearing legs MUST pass ``for_update=True`` (and therefore a
    conn); plain reads (panels, leaderboards) stay unlocked."""
    if for_update:
        if conn is None:
            raise ValueError("for_update=True requires the caller's leg "
                             "conn — a locking read outside a transaction "
                             "fences nothing")
        await execute(
            "SELECT pg_advisory_xact_lock(hashtext($1))",
            (f"farm:slot:{guild_id}:{user_id}",), conn=conn)
    row = await fetchone(
        "SELECT chickens, eggs, eggs_updated_at, coop_level FROM "
        "chicken_farm WHERE user_id=$1 AND guild_id=$2"
        + (" FOR UPDATE" if for_update else ""),
        (user_id, guild_id), conn=conn)
    if row is None:
        return 1, 0, 0, 0
    return (int(row["chickens"]), int(row["eggs"]),
            int(row["eggs_updated_at"]), int(row["coop_level"]))


async def set_farm(conn: Any, *, user_id: int, guild_id: int, chickens: int,
                   eggs: int, now: int, coop_level: int) -> None:
    await execute(
        "INSERT INTO chicken_farm (user_id, guild_id, chickens, eggs, "
        "eggs_updated_at, coop_level) VALUES ($1,$2,$3,$4,$5,$6) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET chickens=$3, "
        "eggs=$4, eggs_updated_at=$5, coop_level=$6",
        (user_id, guild_id, chickens, eggs, now, coop_level), conn=conn)


async def top_farmers(guild_id: int, limit: int = 10,
                      conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, chickens, coop_level FROM chicken_farm WHERE "
        "guild_id=$1 AND chickens > 0 "
        "ORDER BY chickens DESC, coop_level DESC LIMIT $2",
        (guild_id, limit), conn=conn)
    return [dict(r) for r in rows]


async def erase_subject_farm(conn: Any, *, user_id: int) -> int:
    result = await execute("DELETE FROM chicken_farm WHERE user_id=$1",
                           (user_id,), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("farm.store")):
        _engine("farm.store")(_store_marker)
