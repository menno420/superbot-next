"""Command routing — per-scope per-cog enable/disable (the routing port;
ORACLE disbot/services/command_routing.py + utils/db/command_routing.py
@ f969b95, migration 036 → 0054_command_routing.sql).

Reads ``command_routing_policy`` and walks the scope chain **channel →
category → guild → default-true** so absence of any policy row leaves a
cog enabled (the safe default). The resolver deliberately carries NO
cache — three sequential indexed lookups with an early exit, the oracle's
own posture ("PostgreSQL evaluation of three indexed lookups is
sub-millisecond and we want the early exit").

ENFORCEMENT SURFACE, ported verbatim: the oracle has **no dispatch-time
command guard** calling this resolver — its consumers are the access
READ MODEL (access_projection axis 3, wired here) and the setup
dispatcher's change-plan read; the live dispatch gates are the bootstrap
admission gate + the governance guard, neither of which reads routing.
Do NOT invent a hard command block on top of this module.

Sole-writer discipline: mutations happen only in the K7
``routing.set_policy`` op (sb/domain/server_management/ops.py — the
oracle ``command_routing.set_policy`` twin). ``cog_name`` rows carry the
staged payload's cog/subsystem key vocabulary unchanged
(sb/domain/governance/registry.SUBSYSTEM_META keys — the oracle
``utils.subsystem_registry`` names; access_projection keys axis 3 on the
same subsystem key).

Rollback disposition (S14): guild CONFIG — bears_value=False,
NAME_STABLE, DECLARED_LOSS. ``actor_id`` is a member id ⇒ MEMBER_ID with
a tombstone erasure body (scrub the actor pointer, keep the policy row —
the governance_audit_log posture).
"""

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
    "COMMAND_ROUTING_STORE",
    "ensure_refs",
    "get_policy",
    "is_cog_enabled",
    "list_for_guild",
    "tombstone_policy_actor",
    "upsert_policy",
]

#: the oracle scope vocabulary (utils/db/command_routing._KNOWN_SCOPES).
KNOWN_SCOPES: frozenset[str] = frozenset({"guild", "category", "channel"})

COMMAND_ROUTING_STORE = register_store(StoreSpec(
    table="command_routing_policy",
    sole_writer=EngineRef("server_management.routing_store"),
    retention="permanent",
    checkpoint_class=CheckpointClass.AGGREGATE,
    invariant_tag="command_routing_policy",
    forward_map_kind=ForwardMapKind.NAME_STABLE,
    reader_domains=("server_management", "diagnostics"),
    bears_value=False,
    data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("routing.tombstone_policy_actor"),
))


@engine("server_management.routing_store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/server_management/routing.py"


def _check_scope(scope_type: str) -> None:
    if scope_type not in KNOWN_SCOPES:
        raise ValueError(
            f"scope_type must be one of {sorted(KNOWN_SCOPES)}, "
            f"got {scope_type!r}")


async def get_policy(guild_id: int, scope_type: str, scope_id: int | None,
                     cog_name: str, conn: Any = None) -> dict | None:
    """Return the routing row for ``(guild, scope, cog)``, or ``None``.

    Uses ``COALESCE(scope_id, -1) = COALESCE($3, -1)`` so guild-scope
    lookups (scope_id=NULL) match cleanly against the COALESCE unique
    index (oracle utils/db/command_routing.get_one, verbatim)."""
    _check_scope(scope_type)
    return await fetchone(
        "SELECT enabled, actor_id, updated_at FROM command_routing_policy "
        "WHERE guild_id=$1 AND scope_type=$2 "
        "AND COALESCE(scope_id, -1)=COALESCE($3, -1) AND cog_name=$4",
        (guild_id, scope_type, scope_id, cog_name), conn=conn)


async def upsert_policy(conn: Any, *, guild_id: int, scope_type: str,
                        scope_id: int | None, cog_name: str, enabled: bool,
                        actor_id: int | None) -> None:
    """Upsert the routing row (oracle utils/db/command_routing.set_one,
    verbatim conflict resolution: replace enabled + actor)."""
    _check_scope(scope_type)
    await execute(
        "INSERT INTO command_routing_policy "
        "(guild_id, scope_type, scope_id, cog_name, enabled, actor_id) "
        "VALUES ($1, $2, $3, $4, $5, $6) "
        "ON CONFLICT (guild_id, scope_type, COALESCE(scope_id, -1), cog_name) "
        "DO UPDATE SET enabled=EXCLUDED.enabled, actor_id=EXCLUDED.actor_id, "
        "updated_at=NOW()",
        (guild_id, scope_type, scope_id, cog_name, enabled, actor_id),
        conn=conn)


async def list_for_guild(guild_id: int, conn: Any = None) -> list[dict]:
    """Every routing row for ``guild_id`` ordered by scope (the oracle
    list read — the diagnostics/panel surface)."""
    return await fetchall(
        "SELECT scope_type, scope_id, cog_name, enabled, actor_id, "
        "updated_at FROM command_routing_policy WHERE guild_id=$1 "
        "ORDER BY scope_type, cog_name, scope_id NULLS FIRST",
        (guild_id,), conn=conn)


async def is_cog_enabled(*, guild_id: int, cog_name: str,
                         channel_id: int | None,
                         category_id: int | None) -> bool:
    """Return whether ``cog_name`` is enabled in the given scope.

    ORACLE VERBATIM (services/command_routing.is_cog_enabled:57-85):
    walks channel → category → guild → default-true; the FIRST scope
    that has a policy row wins. Default-true means a fresh guild (no
    policy rows) gets all cogs enabled; routing only restricts. NO
    caching — three sequential indexed lookups, deliberately (the
    early-exit posture)."""
    if channel_id is not None:
        row = await get_policy(guild_id, "channel", channel_id, cog_name)
        if row is not None:
            return bool(row["enabled"])
    if category_id is not None:
        row = await get_policy(guild_id, "category", category_id, cog_name)
        if row is not None:
            return bool(row["enabled"])
    row = await get_policy(guild_id, "guild", None, cog_name)
    if row is not None:
        return bool(row["enabled"])
    return True


async def tombstone_policy_actor(conn: Any, *, user_id: int) -> int:
    """S11 class-12 TOMBSTONE: scrub the subject's ``actor_id`` pointer
    in place, keep the policy rows (the governance_audit_log twin —
    routing policy is guild config, not the subject's trail)."""
    result = await execute(
        "UPDATE command_routing_policy SET actor_id=NULL WHERE actor_id=$1",
        (user_id,), conn=conn)
    try:
        return int(str(result).rsplit(" ", 1)[-1])
    except (ValueError, TypeError):
        return 0


def ensure_refs() -> None:
    """Re-arm the sole-writer marker after a sanctioned clear_ref_table
    (the #141 doctrine)."""
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("server_management.routing_store")):
        _engine("server_management.routing_store")(_store_marker)
