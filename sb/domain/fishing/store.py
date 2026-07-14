"""fishing_catch_log + fishing_energy + fishing_venue + fishing_rod +
fishing_bait CRUD (band 6) — the dex/trophy record (shipped 075/095
shape), the per-(user, guild) cast-energy bar (shipped 088 shape), the
per-(user, guild) current venue (shipped 094 shape), the
per-(user, guild) owned rod tier (shipped 087 shape) and the
per-(user, guild) loaded bait + remaining charges (shipped 091 shape);
all NAME_STABLE, MEMBER_ID delete erasure. Plain CRUD only — the energy
regen math and the cast cost live in sb/domain/fishing/energy.py, the
venue keys + per-venue tuning in sb/domain/fishing/venue.py, the rod
ladder knobs + recipes in sb/domain/fishing/rods.py, the bait catalog +
craft shelves in sb/domain/fishing/bait.py (the shipped layering,
verbatim)."""

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

__all__ = [
    "FISHING_BAIT_STORE",
    "FISHING_CATCH_LOG_STORE",
    "FISHING_ENERGY_STORE",
    "FISHING_ROD_STORE",
    "FISHING_VENUE_STORE",
    "clear_active_bait",
    "consume_bait_charge",
    "get_active_bait",
    "get_catch_log",
    "get_fishing_energy",
    "get_fishing_venue",
    "get_rod_tier",
    "lock_bait_slot",
    "lock_charm_slot",
    "lock_coral_slot",
    "lock_rod_slot",
    "record_catch",
    "set_active_bait",
    "set_fishing_energy",
    "set_fishing_venue",
    "set_rod_tier",
    "top_fishers",
    "top_trophies",
]

FISHING_CATCH_LOG_STORE = register_store(StoreSpec(
    table="fishing_catch_log",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_catch_log",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games", "community"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_catch_log"),
))


FISHING_ENERGY_STORE = register_store(StoreSpec(
    table="fishing_energy",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_energy",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_energy"),
))


FISHING_VENUE_STORE = register_store(StoreSpec(
    table="fishing_venue",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_venue",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_venue"),
))


FISHING_ROD_STORE = register_store(StoreSpec(
    table="fishing_rod",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_rod",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_rod"),
))


FISHING_BAIT_STORE = register_store(StoreSpec(
    table="fishing_bait",
    sole_writer=EngineRef("fishing.store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="fishing_bait",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("diagnostics", "games"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("fishing.erase_subject_bait"),
))


@engine("fishing.store")
def _store_marker() -> str:
    return "sb/domain/fishing/store.py"


async def get_fishing_energy(user_id: int, guild_id: int,
                             conn: Any = None) -> tuple[int, int]:
    """(energy, energy_updated_at) — table defaults for a row-less player
    (full bar, epoch-0 stamp: settles to the cap on first read; the
    shipped ``utils/db/games/fishing_energy.py`` default posture). A
    PLAIN read — the open is not a money lane (energy is game pacing,
    never coins) and the shipped read carried no lock."""
    row = await fetchone(
        "SELECT energy, energy_updated_at FROM fishing_energy WHERE "
        "user_id=$1 AND guild_id=$2", (user_id, guild_id), conn=conn)
    if row is None:
        return 60, 0
    return int(row["energy"]), int(row["energy_updated_at"])


async def set_fishing_energy(user_id: int, guild_id: int, energy: int,
                             updated_at: int, conn: Any = None) -> None:
    """Upsert the settled pair (the shipped ``_SET_ENERGY_SQL`` shape)."""
    await execute(
        "INSERT INTO fishing_energy (user_id, guild_id, energy, "
        "energy_updated_at) VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "energy = EXCLUDED.energy, "
        "energy_updated_at = EXCLUDED.energy_updated_at",
        (user_id, guild_id, energy, updated_at), conn=conn)


async def record_catch(conn: Any, *, user_id: int, guild_id: int,
                       species: str, weight: float,
                       now: int) -> float | None:
    """Upsert the dex row (count+1, best_weight max). Returns the PRIOR
    best weight (None on a first catch) — the personal-best signal."""
    prior = await fetchone(
        "SELECT best_weight FROM fishing_catch_log WHERE user_id=$1 AND "
        "guild_id=$2 AND species=$3", (user_id, guild_id, species),
        conn=conn)
    await execute(
        "INSERT INTO fishing_catch_log (user_id, guild_id, species, count, "
        "best_weight, total_value, first_caught, last_caught) "
        "VALUES ($1,$2,$3,1,$4,0,$5,$5) "
        "ON CONFLICT (user_id, guild_id, species) DO UPDATE SET "
        "count = fishing_catch_log.count + 1, "
        "best_weight = GREATEST(fishing_catch_log.best_weight, $4), "
        "last_caught = $5",
        (user_id, guild_id, species, weight, now), conn=conn)
    return float(prior["best_weight"]) if prior else None


async def get_catch_log(user_id: int, guild_id: int,
                        conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT species, count, best_weight FROM fishing_catch_log WHERE "
        "user_id=$1 AND guild_id=$2 ORDER BY count DESC",
        (user_id, guild_id), conn=conn)
    return [dict(r) for r in rows]


async def top_fishers(guild_id: int, known_species: list[str],
                      limit: int = 10, conn: Any = None) -> list[dict]:
    """Catalog-scoped totals (a superseded catalog never inflates) plus
    the shipped per-angler unique-species count (``COUNT(*) AS
    species``, utils/db/games/fishing.py ``top_fishers``: one catch-log
    row per (user, species), so the group row-count IS the dex breadth
    the ``!fishtop`` body prints)."""
    rows = await fetchall(
        "SELECT user_id, COALESCE(SUM(count), 0) AS total, "
        "COUNT(*) AS species FROM "
        "fishing_catch_log WHERE guild_id=$1 AND species = ANY($2) "
        "GROUP BY user_id ORDER BY total DESC LIMIT $3",
        (guild_id, known_species, limit), conn=conn)
    return [dict(r) for r in rows]


async def top_trophies(guild_id: int, known_species: list[str],
                       limit: int = 10, conn: Any = None) -> list[dict]:
    rows = await fetchall(
        "SELECT user_id, species, best_weight FROM fishing_catch_log "
        "WHERE guild_id=$1 AND species = ANY($2) AND best_weight > 0 "
        "ORDER BY best_weight DESC LIMIT $3",
        (guild_id, known_species, limit), conn=conn)
    return [dict(r) for r in rows]


async def get_fishing_venue(user_id: int, guild_id: int,
                            conn: Any = None) -> str:
    """The player's current venue (``'shore'`` when no row exists yet —
    the shipped ``utils/db/games/fishing_venue.py`` default posture). A
    PLAIN read (venue is game state, never coins)."""
    row = await fetchone(
        "SELECT venue FROM fishing_venue WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return str(row["venue"]) if row else "shore"


async def set_fishing_venue(user_id: int, guild_id: int, venue: str,
                            conn: Any = None) -> None:
    """Set the player's current venue (insert the row or flip it — the
    shipped ``_SET_VENUE_SQL`` upsert shape)."""
    await execute(
        "INSERT INTO fishing_venue (user_id, guild_id, venue) "
        "VALUES ($1,$2,$3) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET venue = $3",
        (user_id, guild_id, venue), conn=conn)


async def get_rod_tier(user_id: int, guild_id: int,
                       conn: Any = None) -> int:
    """The player's owned rod tier (0 = starter when no row exists yet —
    the shipped ``utils/db/games/fishing_rod.py`` default posture). A
    PLAIN read on the read surfaces; the buy/craft legs re-read it
    behind :func:`lock_rod_slot` inside their own txn."""
    row = await fetchone(
        "SELECT tier FROM fishing_rod WHERE user_id=$1 AND guild_id=$2",
        (user_id, guild_id), conn=conn)
    return int(row["tier"]) if row else 0


async def set_rod_tier(user_id: int, guild_id: int, tier: int,
                       conn: Any = None) -> None:
    """Set the player's owned rod tier (insert the first row or raise it
    — the shipped ``_SET_ROD_TIER_SQL`` upsert shape). Transaction-aware:
    the buy/craft workflows debit coins / fish and bump the tier in ONE
    workflow-owned txn (the shipped Q-0071 posture)."""
    await execute(
        "INSERT INTO fishing_rod (user_id, guild_id, tier) "
        "VALUES ($1,$2,$3) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET tier = $3",
        (user_id, guild_id, tier), conn=conn)


async def lock_rod_slot(conn: Any, *, user_id: int,
                        guild_id: int) -> None:
    """Fence concurrent rod buy/craft attempts for one (user, guild)
    against a first-insert / read-then-settle double-charge (the
    #213/#217 doctrine; ``lock_vault_upgrade_slot`` precedent). Both rod
    legs read the current tier (to size the coin/fish cost), debit, then
    bump the tier — a read-then-settle over a natural-key row that may
    not exist yet (a fresh player has no fishing_rod row), so FOR UPDATE
    alone can lock nothing. A transaction-scoped advisory lock keyed on
    the SAME (guild, user) pair serializes two racing upgrades: the loser
    blocks here until the winner's txn commits, then re-reads the
    winner's committed tier. Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"fishing:rod:{guild_id}:{user_id}",), conn=conn)


async def get_active_bait(user_id: int, guild_id: int,
                          conn: Any = None) -> tuple[str, int]:
    """The player's loaded ``(bait_key, charges)`` (``("", 0)`` when none
    — the shipped ``utils/db/games/fishing_bait.py`` default posture).
    An empty key or non-positive charge count both mean "no bait"; the
    caller resolves the key to a :class:`sb.domain.fishing.bait.Bait`. A
    PLAIN read on the read surfaces; the buy/craft legs re-read it
    behind :func:`lock_bait_slot` inside their own txn."""
    row = await fetchone(
        "SELECT bait_key, charges FROM fishing_bait WHERE user_id=$1 "
        "AND guild_id=$2", (user_id, guild_id), conn=conn)
    if row is None:
        return "", 0
    return str(row["bait_key"]), int(row["charges"])


async def set_active_bait(user_id: int, guild_id: int, bait_key: str,
                          charges: int, conn: Any = None) -> None:
    """Load *bait_key* with *charges* for the player (insert the row or
    replace — the shipped ``_SET_BAIT_SQL`` upsert shape).
    Transaction-aware: the buy workflow debits coins and loads the bait
    in ONE workflow-owned txn (the shipped Q-0071 posture)."""
    await execute(
        "INSERT INTO fishing_bait (user_id, guild_id, bait_key, charges) "
        "VALUES ($1,$2,$3,$4) "
        "ON CONFLICT (user_id, guild_id) DO UPDATE SET "
        "bait_key = $3, charges = $4",
        (user_id, guild_id, bait_key, charges), conn=conn)


async def clear_active_bait(user_id: int, guild_id: int,
                            conn: Any = None) -> None:
    """Drop the player's loaded bait (charges spent) → back to bait-less
    fishing (the shipped ``clear_active_bait`` shape; the per-cast
    consume's empty-pack clear now happens inside
    :func:`consume_bait_charge`'s single statement)."""
    await set_active_bait(user_id, guild_id, "", 0, conn=conn)


async def consume_bait_charge(user_id: int, guild_id: int, bait_key: str,
                              conn: Any = None) -> int | None:
    """Spend ONE charge of *bait_key* — the cast's per-attempt consume
    (``begin_cast``), as a single CONDITIONAL RELATIVE decrement so it
    can never clobber a concurrent buy/craft: the bait legs stack or
    replace ABSOLUTE loadouts behind :func:`lock_bait_slot` in their own
    txn, and the cast leg runs lockless outside any txn — an absolute
    ``charges - 1`` write-back here would lose a purchase committing
    between the cast's read and its consume (the #213/#217
    read-then-settle lost update; bait is coin-purchased, so the eaten
    charges are paid coins). The decrement is relative
    (``charges = charges - 1``) and keyed on the loadout the cast
    actually rolled with (``bait_key`` must still match,
    ``charges >= 1``), so a raced stack keeps its bought charges (the
    cast eats one charge of the NEW count) and a raced replace is left
    untouched. The last charge clears the pack in the SAME statement
    (``bait_key = ''``, charges 0 — the exact
    :func:`clear_active_bait` end state). Returns the remaining charges,
    or ``None`` when nothing matched — the loadout was swapped or
    emptied concurrently; the caller treats that as the shipped
    "no bait" posture (nothing to spend, nothing clobbered)."""
    row = await fetchone(
        "UPDATE fishing_bait SET "
        "charges = fishing_bait.charges - 1, "
        "bait_key = CASE WHEN fishing_bait.charges - 1 <= 0 THEN '' "
        "ELSE fishing_bait.bait_key END "
        "WHERE user_id=$1 AND guild_id=$2 AND bait_key=$3 "
        "AND charges >= 1 RETURNING charges",
        (user_id, guild_id, bait_key), conn=conn)
    return int(row["charges"]) if row else None


async def lock_bait_slot(conn: Any, *, user_id: int,
                         guild_id: int) -> None:
    """Fence concurrent bait buy/craft attempts for one (user, guild)
    against a first-insert / read-then-settle double-charge (the
    #213/#217 doctrine; ``lock_rod_slot`` precedent). All three bait
    legs read the current loadout (to stack or replace charges), debit
    coins / fish / pearls, then write the loadout — a read-then-settle
    over a natural-key row that may not exist yet (a fresh player has no
    fishing_bait row), so FOR UPDATE alone can lock nothing. A
    transaction-scoped advisory lock keyed on the SAME (guild, user)
    pair serializes two racing loads: the loser blocks here until the
    winner's txn commits, then re-reads the winner's committed loadout.
    Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"fishing:bait:{guild_id}:{user_id}",), conn=conn)


async def lock_charm_slot(conn: Any, *, user_id: int,
                          guild_id: int) -> None:
    """Fence concurrent charm-craft attempts for one (user, guild)
    against a double-craft over the same fish (the mining quick_craft
    posture — materials, not coins, so this lock is the only guard).
    The charm leg reads the fish inventory, plans the spend, then
    debits + grants — a read-then-settle; the advisory lock serializes
    two racing crafts. Auto-released at commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"fishing:charm:{guild_id}:{user_id}",), conn=conn)


async def lock_coral_slot(conn: Any, *, user_id: int,
                          guild_id: int) -> None:
    """Fence EVERY fishing-side coral spend for one (user, guild) — the
    curio carve AND the structure build take this SAME key, so a racing
    `!craftcurio` × Build pair serializes (PR #350 codex finding): the
    shared ``mining_inventory`` decrement floors at zero
    (``GREATEST(0, quantity + delta)``), so two unserialized spenders
    could both pass their pre-spend guards and both be granted from one
    coral stack — the lock makes the loser re-read the winner's
    committed count and refuse honestly. Materials, not coins, so for
    the carve this lock is the only guard (the ``lock_charm_slot``
    posture); the build additionally holds ``mining.store.
    lock_structure_build_slot`` (taken FIRST, a stable order — no
    deadlock: the carve holds only this key). Auto-released at
    commit/rollback."""
    await execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        (f"fishing:coral:{guild_id}:{user_id}",), conn=conn)


async def erase_subject_catch_log(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_catch_log WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def erase_subject_energy(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_energy WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def erase_subject_venue(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_venue WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def erase_subject_rod(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_rod WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


async def erase_subject_bait(conn: Any, *, user_id: int) -> int:
    result = await execute(
        "DELETE FROM fishing_bait WHERE user_id=$1", (user_id,),
        conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, AttributeError):
        return 0


def ensure_refs() -> None:
    from sb.spec.refs import is_registered, engine as _engine

    if not is_registered(EngineRef("fishing.store")):
        _engine("fishing.store")(_store_marker)
