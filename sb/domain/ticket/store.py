"""Ticket admin CRUD (the `_unmapped` ticket-admin re-home) — asyncpg SQL
behind the K3 seam; migration ``0032_ticket_admin.sql`` (the oracle's
disbot/migrations/098_tickets.sql ``ticket_config``/``ticket_blacklist``
pair, imported NAME_STABLE). Sole-writer discipline: mutations happen only
in the K7 ticket ops (sb/domain/ticket/ops.py).

The oracle's third table (``tickets`` — one row per open/closed ticket)
is deliberately NOT minted: no golden touches it; it lands with the
channel-provisioning open-flow slice (sb/domain/ticket/service.py module
docstring carries the under-port boundary).

Rollback disposition (S14): ticket_config is guild CONFIG —
bears_value=False, NAME_STABLE, no reverse importers. ticket_blacklist is
keyed on member ids => MEMBER_ID with a delete-rows erasure body (a
blacklist entry is a live pointer, not a trail — the role_grants
precedent).
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
    "TICKET_BLACKLIST_STORE",
    "TICKET_CONFIG_STORE",
    "add_blacklist",
    "ensure_refs",
    "get_config_row",
    "remove_blacklist",
    "upsert_config_fields",
]


def _store(table: str, **kw) -> StoreSpec:
    return register_store(StoreSpec(
        table=table,
        sole_writer=EngineRef("ticket.store"),
        retention="permanent",
        checkpoint_class=CheckpointClass.AGGREGATE,
        invariant_tag=table,
        forward_map_kind=ForwardMapKind.NAME_STABLE,
        reader_domains=("diagnostics",),
        bears_value=False,
        data_class=kw.pop("data_class", DataClass.NONE),
        **kw))


TICKET_CONFIG_STORE = _store("ticket_config")
TICKET_BLACKLIST_STORE = _store(
    "ticket_blacklist", data_class=DataClass.MEMBER_ID,
    erasure_ref=WorkflowRef("ticket.erase_subject_blacklist"))


@engine("ticket.store")
def _store_marker() -> str:
    """The sole-writer marker (P6 sole_writer resolution target)."""
    return "sb/domain/ticket/store.py"


def ensure_refs() -> None:
    """Re-arm the sole-writer marker after a sanctioned clear_ref_table
    (the #141 doctrine — a manifest re-import re-fires decorators only for
    freshly-imported modules)."""
    from sb.spec.refs import is_registered
    from sb.spec.refs import engine as _engine

    if not is_registered(EngineRef("ticket.store")):
        _engine("ticket.store")(_store_marker)


# --- ticket_config ---------------------------------------------------------------

#: the columns the shipped ``update_config(**fields)`` accepted (disbot
#: utils/db/tickets.py upsert column list minus the key) — the whitelist
#: keeps the dynamic upsert closed over the shipped vocabulary.
_CONFIG_COLUMNS = ("enabled", "staff_role_id", "category_id",
                   "log_channel_id", "panel_channel_id", "panel_message_id",
                   "max_open_per_user", "ping_staff_on_open")


async def get_config_row(guild_id: int, conn: Any = None) -> dict | None:
    """The shipped ``ticket_service.get_config`` row read (None until a
    config write mints the guild's row)."""
    return await fetchone(
        "SELECT guild_id, enabled, staff_role_id, category_id, "
        "log_channel_id, panel_channel_id, panel_message_id, "
        "max_open_per_user, ping_staff_on_open, updated_at "
        "FROM ticket_config WHERE guild_id=$1", (guild_id,), conn=conn)


async def upsert_config_fields(conn: Any, *, guild_id: int, now: int,
                               **fields: Any) -> None:
    """The shipped ``upsert_config`` semantics verbatim (disbot
    utils/db/tickets.py): a brand-new row falls back to the column
    defaults for unset fields; an existing row updates ONLY the given
    fields (+ ``updated_at``). goldens/ticket/sweep_ticketlimit pins the
    fresh-row shape (enabled/ping defaults TRUE, max_open_per_user set)."""
    unknown = [k for k in fields if k not in _CONFIG_COLUMNS]
    if unknown:
        raise ValueError(f"unknown ticket_config field(s): {unknown}")
    cols = list(fields.keys())
    insert_cols = ["guild_id", *cols, "updated_at"]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(insert_cols)))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in (*cols, "updated_at"))
    await execute(
        f"INSERT INTO ticket_config ({', '.join(insert_cols)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT (guild_id) DO UPDATE SET {updates}",
        (guild_id, *fields.values(), now), conn=conn)


# --- ticket_blacklist -------------------------------------------------------------

async def add_blacklist(conn: Any, *, guild_id: int, user_id: int,
                        added_by: int, reason: str | None,
                        added_at: int) -> None:
    """Add (or refresh) a blacklist entry — the shipped upsert verbatim
    (disbot utils/db/tickets.py)."""
    await execute(
        "INSERT INTO ticket_blacklist (guild_id, user_id, added_by, reason, "
        "added_at) VALUES ($1, $2, $3, $4, $5) "
        "ON CONFLICT (guild_id, user_id) DO UPDATE SET "
        "    added_by = $3, reason = $4, added_at = $5",
        (guild_id, user_id, added_by, reason, added_at), conn=conn)


async def remove_blacklist(conn: Any, *, guild_id: int,
                           user_id: int) -> bool:
    """Remove a blacklist entry (no-op if absent) — the shipped bare
    DELETE; the caller acks success UNCONDITIONALLY (the #193
    unsetrole/removereactrole oracle-wins precedent:
    goldens/ticket/sweep_ticketblacklist_remove pins the ack with an
    empty table)."""
    rows = await fetchall(
        "DELETE FROM ticket_blacklist WHERE guild_id = $1 AND user_id = $2 "
        "RETURNING guild_id", (guild_id, user_id), conn=conn)
    return bool(rows)


async def erase_subject_blacklist_rows(conn: Any, *, user_id: int) -> int:
    """S11 erasure body: blacklist entries are live pointers keyed on the
    member id — hard delete (the role_grants posture)."""
    rows = await fetchall(
        "DELETE FROM ticket_blacklist WHERE user_id = $1 RETURNING guild_id",
        (user_id,), conn=conn)
    return len(rows)
